"""Local owner control, activation ceremony and fixed approval orchestration."""

from dataclasses import asdict
from datetime import datetime, timezone
import hmac
import sqlite3

from flask import Blueprint, current_app, jsonify, request, session

from . import admin_auth as auth, administration as a


def now_utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def configuration():
    from src.api import app as api
    from src.api.deployment import recognition_admin_configuration
    return recognition_admin_configuration(api.DATABASE_PATH,
        current_app.config.get("RECOGNITION_ADMIN_CONTROL"), current_app.config.get("RECOGNITION_ADMIN_KEY_FILE"))


def revoke_admin_login():
    token = session.get("recognition_primary")
    if token:
        config = configuration()
        a.need(config is not None, "administrative_logout_unavailable", 503)
        auth.invalidate_primary(config, token, now=now_utc())


def authentication_backend(config):
    """Durable format dispatch for authentication only; no fallback on failure."""
    from . import administration_schema, runtime_profile_schema
    from .trust import load
    with a.connect(config.control) as conn:
        administration_schema.check_control(conn)
        rows = conn.execute('SELECT body_json FROM recognition_admin_bindings ORDER BY generation').fetchall()
        a.need(bool(rows), 'installation_not_initialized', 503)
        bodies = [load(row[0]) for row in rows]
        a.need(all(type(body) is dict for body in bodies), 'installation_history_integrity_failure', 503)
        formats = [body.get('format') for body in bodies]
        a.need(all(value in ('recognition-local-control-v2', runtime_profile_schema.V3) for value in formats),
               'installation_history_integrity_failure', 503)
    if runtime_profile_schema.V3 in formats:
        from . import runtime_auth
        return runtime_auth
    return auth


def record_admin_login(actor_id, reviewer_key):
    try:
        config = configuration()
        if config is not None:
            session["recognition_primary"] = authentication_backend(config).record_primary_authentication(config,
                actor_id=actor_id, reviewer_key=reviewer_key, now=now_utc())
    except (a.AdminError, ValueError, OSError, sqlite3.Error):
        # Reviewer login stays available; no administrative authentication is minted.
        session.pop("recognition_primary", None)


def register_admin_routes(app):
    routes = Blueprint("recognition_control", __name__, url_prefix="/api/admin/recognition-control")

    @routes.after_request
    def private_response(response):
        response.headers["Cache-Control"] = "no-store"
        response.headers["Pragma"] = "no-cache"
        return response

    @routes.errorhandler(a.AdminError)
    def denied(error):
        return {"error": error.code}, error.status

    def unavailable(_error):
        return {"error": "administrative_control_unavailable"}, 503

    for error_type in (OSError, sqlite3.Error, ValueError, ImportError):
        routes.register_error_handler(error_type, unavailable)

    def context(*, administrative=False, authentication_only=False):
        config = configuration()
        a.need(config is not None, "administrative_control_not_configured", 503)
        from src.review.admin_dashboard import owner_access
        with a.connect(config.target) as conn:
            allowed, _ = owner_access(conn, session.get("authenticated_reviewer_id"), session.get("reviewer_key"))
        a.need(allowed, "recognition_owner_required", 403)
        primary = session.get("recognition_primary")
        backend = authentication_backend(config) if authentication_only else auth
        identity = backend.get_admin_identity(config, primary, now=now_utc())
        a.need(identity.actor_id == session.get("authenticated_reviewer_id"), "owner_identity_mismatch")
        if administrative:
            if backend is auth:
                with a.transaction(config) as (conn, target, binding):
                    row, _ = auth._session(conn, target, binding, session.get("recognition_admin"), now_utc())
                    a.need(row["primary_hash"] == a.token_hash(primary), "administrative_browser_session_mismatch")
            else:
                backend.require_recognition_admin(config, session.get('recognition_admin'), primary_token=primary, now=now_utc())
        return config

    def data(fields):
        value = request.get_json(silent=True)
        a.need(type(value) is dict and set(value) == set(fields) | {"csrf_token"}, "invalid_control_request", 400)
        csrf = session.get("auth_csrf")
        a.need(type(csrf) is str and bool(csrf) and type(value["csrf_token"]) is str and value["csrf_token"].isascii()
               and hmac.compare_digest(value["csrf_token"], csrf), "invalid_request_token", 400)
        return value

    @routes.get("/identity")
    def identity():
        config = context(authentication_only=True)
        return jsonify(asdict(authentication_backend(config).get_admin_identity(config, session["recognition_primary"], now=now_utc())))

    @routes.post("/mfa/enrollment")
    def enrollment():
        data(())
        config = context(authentication_only=True)
        uri = authentication_backend(config).begin_enrollment(config, session["recognition_primary"], now=now_utc())
        return {"provisioning_uri": uri, "state": "PENDING_CONFIRMATION"}

    @routes.post("/mfa/verify")
    def verify():
        value = data(("code",))
        config = context(authentication_only=True)
        authentication_backend(config).finish_enrollment(config, session["recognition_primary"], value["code"], now=now_utc())
        return {"state": "ENROLLED"}

    @routes.post("/session")
    def open_session():
        value = data(("code",))
        config = context(authentication_only=True)
        session["recognition_admin"] = authentication_backend(config).open_admin_session(config, session["recognition_primary"], value["code"], now=now_utc())
        return {"state": "ADMINISTRATIVELY_AUTHENTICATED", "lifetime_seconds": auth.SESSION_SECONDS}

    @routes.get("/session")
    def session_status():
        config = context(administrative=True, authentication_only=True)
        backend = authentication_backend(config)
        kwargs = {} if backend is auth else dict(primary_token=session['recognition_primary'])
        return jsonify(asdict(backend.require_recognition_admin(config, session["recognition_admin"], now=now_utc(), **kwargs)))

    @routes.post("/step-up")
    def step_up():
        value = data(("code", "action", "operation_id"))
        config = context(administrative=True)
        token = auth.create_step_up(config, session["recognition_admin"], value["code"],
            action=value["action"], operation_id=value["operation_id"], now=now_utc())
        return {"step_up_token": token, "lifetime_seconds": auth.RECENT_SECONDS}

    @routes.post("/confirmations")
    def begin_confirmation():
        value = data(("operation_id", "step_up_token"))
        config = context(administrative=True)
        token = auth.begin_operation_confirmation(config, session["recognition_admin"], value["step_up_token"],
            operation_id=value["operation_id"], now=now_utc())
        return {"confirmation_token": token, "recognition_approved": False}

    @routes.post("/confirmations/consume")
    def consume_confirmation():
        value = data(("operation_id", "operation_sha256", "confirmation_token"))
        config = context(administrative=True)
        body = auth.consume_operation_confirmation(config, session["recognition_admin"], value["confirmation_token"],
            operation_id=value["operation_id"], operation_sha256=value["operation_sha256"], now=now_utc())
        return dict(body, recognition_approved=False)

    @routes.get("/installation")
    def installation():
        return jsonify(a.get_installation_control(context(administrative=True)))

    @routes.get("/readiness")
    def readiness():
        from . import local_readiness
        return jsonify(local_readiness.assess(context(administrative=True), now=now_utc()))

    @routes.post("/activation")
    def activation():
        from . import local_readiness
        value = data(("state", "step_up_token", "reason", "confirmation_token"))
        result = local_readiness.change_state(context(administrative=True), session["recognition_admin"], value["step_up_token"],
            state=value["state"], reason=value["reason"], confirmation_token=value["confirmation_token"], now=now_utc())
        return jsonify(result), 409 if result.get("result") == "BLOCKED" else 200

    @routes.post("/activation/confirmations")
    def activation_confirmation():
        from . import local_readiness
        value = data(("step_up_token",))
        return jsonify(local_readiness.begin_activation_confirmation(context(administrative=True),
            session["recognition_admin"], value["step_up_token"], now=now_utc()))

    @routes.post("/operations/<operation_id>/approve")
    def approve(operation_id):
        from . import local_execution
        value = data(("step_up_token", "confirmation_token", "reason"))
        config = context(administrative=True)
        result = local_execution.approve_and_execute(config, session["recognition_admin"],
            value["step_up_token"], value["confirmation_token"], operation_id=operation_id,
            reason=value["reason"], now=now_utc())
        return jsonify(result), 202 if result["execution"]["state"] == "WAITING" else 201

    @routes.post("/operations")
    def create_operation():
        from . import production_operations
        value = data(production_operations.REQUEST_FIELDS)
        config = context(administrative=True)
        value.pop("csrf_token")
        result = production_operations.create_operation(config, session["recognition_admin"], value, now=now_utc())
        return jsonify(result), 201

    @routes.get("/operations/<operation_id>")
    def inspect_operation(operation_id):
        from . import production_operations
        config = context(administrative=True)
        return jsonify(production_operations.inspect_operation(config, operation_id))

    @routes.get("/operations/<operation_id>/approvals")
    def operation_approvals(operation_id):
        from . import approvals
        config = context(administrative=True)
        return jsonify(approvals.list_operation_approvals(config, session["recognition_admin"], operation_id, now=now_utc()))

    @routes.get("/approvals/<approval_id>")
    def approval(approval_id):
        from . import approvals
        config = context(administrative=True)
        return jsonify(approvals.get_approval(config, session["recognition_admin"], approval_id, now=now_utc()))

    app.register_blueprint(routes)
