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

CREATE TABLE IF NOT EXISTS stop_reviews (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    stop_id INTEGER NOT NULL,

    reviewer_id TEXT,

    review_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,


    -- basic infrastructure

    has_shelter BOOLEAN,

    has_bench BOOLEAN,

    bench_condition TEXT,


    -- waiting environment

    waiting_area_type TEXT,

    likely_waiting_location TEXT,

    sun_exposure TEXT,


    -- physical feasibility

    concrete_pad_present BOOLEAN,

    pad_width_feet REAL,

    pad_depth_feet REAL,

    bench_location_feasible BOOLEAN,


    -- ADA observations

    curb_access_clear BOOLEAN,

    bus_ramp_access_clear BOOLEAN,

    landing_zone_clear BOOLEAN,

    rear_clear_zone_clear BOOLEAN,


    reviewer_confidence REAL,


    notes TEXT,


    FOREIGN KEY(stop_id)
        REFERENCES bus_stops(id)
);



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
