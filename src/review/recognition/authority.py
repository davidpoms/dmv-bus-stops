"""Authority provisioning, separate from approval data and writer APIs.

Production requires the independently installed deployment trust input and
authenticated original owner through runtime_production_governance. Unconfigured
calls still deny. Disposable capabilities own only fresh temporary workspaces.
This is an application boundary, not a sandbox against arbitrary Python/SQL.
"""

from pathlib import Path
import tempfile


class Authority:
    """Opaque handle; only provisioned identities are accepted by verification."""

    __slots__ = ('__weakref__',)

    def __new__(cls):
        raise TypeError('authority_requires_provisioning')

    def __reduce_ex__(self, protocol):
        raise TypeError('authority_nonserializable')


def _provisioning():
    from weakref import WeakKeyDictionary
    provisioned = WeakKeyDictionary()

    def check(handle, authorization):
        from .authorization import AuthorizationError, target_identity
        if type(handle) is not Authority or handle not in provisioned:
            from .runtime_production_governance import check_registered
            return check_registered(handle,authorization)
        root, root_identity, approved = provisioned[handle]
        path = Path(authorization.target.database)
        stat = root.stat()
        if (authorization.environment != 'disposable' or
                (stat.st_dev, stat.st_ino) != root_identity or
                root.resolve() != root or not path.is_relative_to(root) or
                path.resolve() != path or path.stat().st_nlink != 1 or
                target_identity(path) != authorization.target):
            raise AuthorizationError('authority_target_environment_mismatch')
        if authorization not in approved:
            raise AuthorizationError('authorization_not_approved')

    class DisposableWorkspace:
        """Explicit test/rehearsal provisioning; never adopts an existing root."""

        def __init__(self):
            self._temporary = tempfile.TemporaryDirectory(prefix='recognition-disposable-')
            self.name = str(Path(self._temporary.name).resolve())
            self.authority = object.__new__(Authority)
            self.approved = set()
            root = Path(self.name)
            stat = root.stat()
            provisioned[self.authority] = (root, (stat.st_dev, stat.st_ino), self.approved)

        def approve(self, database, **binding):
            from .authorization import Authorization, target_identity
            approval = Authorization(target=target_identity(database), environment='disposable',
                                     **{'reference': 'disposable-schema-review', **binding})
            self.approved.add(approval)
            try:
                check(self.authority, approval)
            except Exception:
                self.approved.discard(approval)
                raise
            return approval

        def cleanup(self):
            provisioned.pop(self.authority, None)
            self._temporary.cleanup()

    return check, DisposableWorkspace

check_authority, DisposableWorkspace = _provisioning()
del _provisioning


def provision_production_authority(*args, **kwargs):
    """Fixed signed-owner provisioning; never accepts a caller verifier callback."""
    from .runtime_production_governance import provision
    return provision(*args,**kwargs)
