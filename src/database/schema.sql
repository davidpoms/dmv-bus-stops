-- =====================================================
-- DMV Bus Stops Database Schema
-- =====================================================

PRAGMA foreign_keys = ON;


-- =====================================================
-- BUS STOP CORE DATA
-- =====================================================

CREATE TABLE IF NOT EXISTS bus_stops (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    external_stop_id TEXT UNIQUE,

    latitude REAL NOT NULL,
    longitude REAL NOT NULL,

    stop_name TEXT,

    direction TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- =====================================================
-- ROUTE INFORMATION
-- =====================================================

CREATE TABLE IF NOT EXISTS routes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    route_id TEXT UNIQUE NOT NULL,

    route_name TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE IF NOT EXISTS stop_routes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    stop_id INTEGER NOT NULL,
    route_id INTEGER NOT NULL,

    FOREIGN KEY(stop_id)
        REFERENCES bus_stops(id),

    FOREIGN KEY(route_id)
        REFERENCES routes(id)
);

CREATE TABLE IF NOT EXISTS gtfs_feed_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    feed_id TEXT NOT NULL, snapshot_sha256 TEXT NOT NULL,
    source_file TEXT NOT NULL, source_url TEXT,
    feed_publisher_name TEXT, feed_publisher_url TEXT, feed_lang TEXT,
    feed_start_date TEXT, feed_end_date TEXT, feed_version TEXT,
    imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(feed_id, snapshot_sha256)
);

CREATE TABLE IF NOT EXISTS gtfs_stop_structure (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id INTEGER NOT NULL, gtfs_stop_id TEXT NOT NULL,
    stop_code TEXT, stop_name TEXT, stop_lat TEXT, stop_lon TEXT,
    location_type TEXT, parent_station TEXT, platform_code TEXT,
    zone_id TEXT, wheelchair_boarding TEXT,
    quality_flags TEXT NOT NULL DEFAULT '[]', raw_row_json TEXT NOT NULL,
    FOREIGN KEY(snapshot_id) REFERENCES gtfs_feed_snapshots(id),
    UNIQUE(snapshot_id, gtfs_stop_id)
);
CREATE INDEX IF NOT EXISTS idx_gtfs_stop_structure_feed_stop ON gtfs_stop_structure(snapshot_id,gtfs_stop_id);
CREATE INDEX IF NOT EXISTS idx_gtfs_stop_structure_parent ON gtfs_stop_structure(snapshot_id,parent_station);
CREATE INDEX IF NOT EXISTS idx_gtfs_stop_structure_stop_code ON gtfs_stop_structure(snapshot_id,stop_code);


-- =====================================================
-- HUMAN VERIFIED STOP CONDITIONS
-- =====================================================

CREATE TABLE IF NOT EXISTS community_reviewers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reviewer_key TEXT UNIQUE,
    display_name TEXT,
    profile_token TEXT,
    email TEXT,
    profile_created_at TIMESTAMP,
    email_verified_at TIMESTAMP,
    claimed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_community_reviewers_verified_email
ON community_reviewers(email) WHERE email_verified_at IS NOT NULL;

CREATE TABLE IF NOT EXISTS reviewer_login_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reviewer_id INTEGER NOT NULL,
    normalized_email TEXT NOT NULL,
    token_hash TEXT NOT NULL UNIQUE,
    action TEXT NOT NULL CHECK (action IN ('claim','login','conflict')),
    expires_at TIMESTAMP NOT NULL,
    used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(reviewer_id) REFERENCES community_reviewers(id)
);

CREATE INDEX IF NOT EXISTS idx_reviewer_login_tokens_hash
ON reviewer_login_tokens(token_hash);

CREATE TABLE IF NOT EXISTS reviewer_auth_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email_key TEXT NOT NULL,
    source_key TEXT NOT NULL,
    outcome TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_reviewer_auth_attempts_email_time
ON reviewer_auth_attempts(email_key, created_at);
CREATE INDEX IF NOT EXISTS idx_reviewer_auth_attempts_source_time
ON reviewer_auth_attempts(source_key, created_at);


CREATE TABLE IF NOT EXISTS stop_review_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stop_id INTEGER NOT NULL,
    reviewer_id INTEGER NOT NULL,
    scenario TEXT NOT NULL,
    campaign TEXT,
    status TEXT DEFAULT 'assigned',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);


CREATE INDEX IF NOT EXISTS idx_review_assignments_stop
ON stop_review_assignments(stop_id);


CREATE INDEX IF NOT EXISTS idx_review_assignments_reviewer
ON stop_review_assignments(reviewer_id);


CREATE TABLE IF NOT EXISTS stop_observations (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    physical_stop_id INTEGER NOT NULL,

    observer TEXT,

    shelter_present TEXT,

    bench_present TEXT,

    trash_present TEXT,

    bench_feasible TEXT,

    concrete_pad_needed TEXT,

    ada_clearance_possible TEXT,

    notes TEXT,

    observed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    source TEXT DEFAULT 'unknown',

    reviewer_id INTEGER,

    confidence REAL,

    streetview_checked BOOLEAN,

    osm_checked BOOLEAN,

    review_mode TEXT,

    assignment_id INTEGER,

    streetview_imagery_month TEXT,

    weather_exposure TEXT,

    riders_avoid_facilities TEXT,

    rider_activity TEXT,

    usage_times TEXT,

    property_owner_outreach TEXT,

    steward_email TEXT,

    steward_candidate BOOLEAN DEFAULT 0,

    FOREIGN KEY(physical_stop_id)
        REFERENCES physical_stops(id),

    FOREIGN KEY(assignment_id)
        REFERENCES stop_review_assignments(id)

);


CREATE INDEX IF NOT EXISTS idx_stop_observations_assignment
ON stop_observations(assignment_id);


-- Rebuildable canonical shelter/bench synthesis. Source evidence remains in
-- its own tables; this table contains normalized provenance only.
CREATE TABLE IF NOT EXISTS stop_amenity_status (
    physical_stop_id INTEGER NOT NULL,
    amenity_type TEXT NOT NULL CHECK (amenity_type IN ('shelter', 'bench')),
    derived_status TEXT NOT NULL CHECK (derived_status IN (
        'confirmed_yes', 'confirmed_no', 'likely_yes', 'likely_no',
        'conflicting', 'unknown'
    )),
    consensus_status TEXT NOT NULL,
    local_yes_count INTEGER NOT NULL DEFAULT 0,
    local_no_count INTEGER NOT NULL DEFAULT 0,
    local_yes_sources TEXT NOT NULL DEFAULT '[]',
    local_no_sources TEXT NOT NULL DEFAULT '[]',
    osm_yes INTEGER NOT NULL DEFAULT 0,
    osm_no INTEGER NOT NULL DEFAULT 0,
    community_yes_count INTEGER NOT NULL DEFAULT 0,
    community_no_count INTEGER NOT NULL DEFAULT 0,
    community_observation_count INTEGER NOT NULL DEFAULT 0,
    evidence_conflict INTEGER NOT NULL DEFAULT 0,
    consensus_conflicts_with_other_evidence INTEGER NOT NULL DEFAULT 0,
    rationale TEXT NOT NULL DEFAULT '[]',
    updated_at TEXT NOT NULL,
    FOREIGN KEY (physical_stop_id) REFERENCES physical_stops(id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_stop_amenity_status_identity
ON stop_amenity_status (physical_stop_id, amenity_type);

CREATE TABLE IF NOT EXISTS stop_amenity_review_priority (
    physical_stop_id INTEGER NOT NULL,
    amenity_type TEXT NOT NULL CHECK (amenity_type IN ('shelter','bench')),
    derived_status TEXT NOT NULL,
    consensus_status TEXT NOT NULL,
    workflow_state TEXT NOT NULL,
    rider_exposure_percentile REAL NOT NULL,
    evidence_conflict_component REAL NOT NULL,
    consensus_progress_component REAL NOT NULL,
    exposure_component REAL NOT NULL,
    review_priority_score REAL NOT NULL,
    priority_tier TEXT NOT NULL,
    evidence_conflict INTEGER NOT NULL,
    consensus_conflicts_with_other_evidence INTEGER NOT NULL,
    community_observation_count INTEGER NOT NULL,
    observations_needed_for_consensus INTEGER NOT NULL,
    rationale TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (physical_stop_id, amenity_type),
    FOREIGN KEY (physical_stop_id) REFERENCES physical_stops(id)
);

CREATE INDEX IF NOT EXISTS idx_amenity_review_priority_order
ON stop_amenity_review_priority(priority_tier, review_priority_score DESC);

CREATE TABLE IF NOT EXISTS bench_installation_candidates (
    physical_stop_id INTEGER PRIMARY KEY,
    candidate_rank INTEGER NOT NULL,
    primary_name TEXT,
    state TEXT,
    county TEXT,
    municipality TEXT,
    canonical_status TEXT NOT NULL,
    evidence_strength TEXT NOT NULL,
    local_negative_sources TEXT NOT NULL,
    osm_negative INTEGER NOT NULL,
    community_negative_count INTEGER NOT NULL,
    community_consensus_status TEXT NOT NULL,
    opportunity_score REAL NOT NULL,
    rider_exposure_percentile REAL NOT NULL,
    review_priority_score REAL,
    review_priority_tier TEXT,
    clearance_status TEXT NOT NULL,
    clearance_yes_count INTEGER NOT NULL,
    clearance_no_count INTEGER NOT NULL,
    recommendation_confidence TEXT NOT NULL,
    rationale TEXT NOT NULL,
    next_action TEXT NOT NULL,
    verification_still_needed INTEGER NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_bench_candidates_order
ON bench_installation_candidates(
    next_action, opportunity_score DESC,
    rider_exposure_percentile DESC, physical_stop_id
);

-- Canonical broad seating opportunity universe. Membership is active-stop
-- based; the legacy opportunity score is context and never an eligibility gate.
CREATE TABLE IF NOT EXISTS seating_improvement_opportunities (
    physical_stop_id INTEGER PRIMARY KEY,
    opportunity_rank INTEGER NOT NULL,
    primary_name TEXT,
    state TEXT,
    county TEXT,
    municipality TEXT,
    bench_status TEXT NOT NULL,
    shelter_status TEXT NOT NULL,
    bench_evidence_strength TEXT NOT NULL,
    bench_consensus_status TEXT NOT NULL,
    adequacy_status TEXT NOT NULL,
    adequacy_observation_count INTEGER NOT NULL,
    adequacy_factors TEXT NOT NULL,
    clearance_status TEXT NOT NULL,
    clearance_yes_count INTEGER NOT NULL,
    clearance_no_count INTEGER NOT NULL,
    workflow_state TEXT NOT NULL,
    rider_exposure_percentile REAL NOT NULL,
    documented_need_index REAL NOT NULL,
    strongest_need_signal TEXT NOT NULL,
    need_signals TEXT NOT NULL,
    rider_benefit_component REAL NOT NULL,
    documented_need_component REAL NOT NULL,
    priority_score REAL NOT NULL,
    priority_factors TEXT NOT NULL,
    rationale TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (physical_stop_id) REFERENCES physical_stops(id)
);

CREATE INDEX IF NOT EXISTS idx_seating_opportunity_order
ON seating_improvement_opportunities(priority_score DESC, physical_stop_id);






-- =====================================================
-- COMMUNITY REQUESTS
-- =====================================================

CREATE TABLE IF NOT EXISTS community_requests (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    stop_id INTEGER NOT NULL,


    submitted_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,


    source TEXT,

    requester_name TEXT,

    request_count INTEGER DEFAULT 1,


    description TEXT,


    status TEXT DEFAULT 'new',


    FOREIGN KEY(stop_id)
        REFERENCES bus_stops(id)

);



-- =====================================================
-- WMATA RIDERSHIP DATA
-- Monthly automated import
-- =====================================================

CREATE TABLE ridership_snapshots (

    id INTEGER PRIMARY KEY,

    route_id TEXT NOT NULL,

    service_type TEXT,

    period DATE NOT NULL,

    monthly_boardings REAL,

    weekday_boardings REAL,

    saturday_boardings REAL,

    sunday_boardings REAL,

    source TEXT,

    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

);



CREATE INDEX IF NOT EXISTS idx_ridership_route
ON ridership_snapshots(route_id);



-- =====================================================
-- AUTOMATED DATA PIPELINE LOG
-- =====================================================

CREATE TABLE IF NOT EXISTS data_refresh_log (

    id INTEGER PRIMARY KEY AUTOINCREMENT,


    dataset TEXT NOT NULL,


    refresh_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,


    status TEXT,


    records_loaded INTEGER,


    notes TEXT

);



-- =====================================================
-- PRIORITY ENGINE OUTPUT
-- This is the "brain"
-- =====================================================

CREATE TABLE IF NOT EXISTS stop_priority_snapshots (

    id INTEGER PRIMARY KEY AUTOINCREMENT,


    stop_id INTEGER NOT NULL,


    calculated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,


    priority_score REAL,


    priority_rank INTEGER,


    factors JSON,


    FOREIGN KEY(stop_id)
        REFERENCES bus_stops(id)

);



CREATE INDEX IF NOT EXISTS idx_priority_rank
ON stop_priority_snapshots(priority_rank);



-- =====================================================
-- VOLUNTEER REVIEW QUEUE
-- =====================================================

CREATE TABLE IF NOT EXISTS review_queue (

    id INTEGER PRIMARY KEY AUTOINCREMENT,


    stop_id INTEGER NOT NULL,


    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,


    priority_reason TEXT,


    assigned_reviewer TEXT,


    status TEXT DEFAULT 'pending',


    FOREIGN KEY(stop_id)
        REFERENCES bus_stops(id)

);



-- =====================================================
-- HUMAN FEEDBACK LOOP
-- Tracks disagreements and corrections
-- =====================================================

CREATE TABLE IF NOT EXISTS review_feedback (

    id INTEGER PRIMARY KEY AUTOINCREMENT,


    stop_id INTEGER NOT NULL,


    field_changed TEXT,


    old_value TEXT,


    new_value TEXT,


    reviewer_id TEXT,


    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,


    FOREIGN KEY(stop_id)
        REFERENCES bus_stops(id)

);






