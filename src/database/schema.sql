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


-- =====================================================
-- HUMAN VERIFIED STOP CONDITIONS
-- =====================================================


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

    rider_activity TEXT,

    usage_times TEXT,

    property_owner_outreach TEXT,

    steward_email TEXT,

    steward_candidate BOOLEAN DEFAULT 0,

    FOREIGN KEY(physical_stop_id)
        REFERENCES physical_stops(id)

);


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






