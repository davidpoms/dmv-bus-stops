-- DMV Bus Stops Intelligence Platform
-- Core database schema
--
-- Purpose:
-- Store every bus stop as a persistent physical location,
-- combine automated data sources with human intelligence,
-- and support bench/shelter prioritization.

CREATE EXTENSION IF NOT EXISTS postgis;


------------------------------------------------------------
-- BUS STOP MASTER TABLE
------------------------------------------------------------

CREATE TABLE bus_stops (

    stop_id TEXT PRIMARY KEY,

    agency TEXT DEFAULT 'WMATA',

    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,

    geom GEOGRAPHY(Point,4326),

    street_name TEXT,
    direction TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

);


------------------------------------------------------------
-- ROUTE SERVICE INFORMATION
------------------------------------------------------------

CREATE TABLE stop_routes (

    id SERIAL PRIMARY KEY,

    stop_id TEXT REFERENCES bus_stops(stop_id),

    route_id TEXT,

    service_type TEXT,

    estimated_monthly_boardings NUMERIC,

    weekday_boardings NUMERIC,
    saturday_boardings NUMERIC,
    sunday_boardings NUMERIC

);



------------------------------------------------------------
-- CURRENT PHYSICAL CONDITIONS
--
-- Automated + human verified infrastructure
------------------------------------------------------------

CREATE TABLE stop_conditions (

    stop_id TEXT PRIMARY KEY
        REFERENCES bus_stops(stop_id),

    has_shelter BOOLEAN,

    has_bench BOOLEAN,

    shelter_confidence NUMERIC,

    bench_confidence NUMERIC,

    condition_source TEXT,
    -- examples:
    -- streetview
    -- volunteer
    -- agency_data
    -- field_visit


    last_verified TIMESTAMP

);



------------------------------------------------------------
-- BENCH INSTALLATION OPPORTUNITY
------------------------------------------------------------

CREATE TABLE bench_opportunities (

    stop_id TEXT PRIMARY KEY
        REFERENCES bus_stops(stop_id),


    suitable_for_bench BOOLEAN,

    concrete_pad_present BOOLEAN,

    estimated_pad_width_feet NUMERIC,

    estimated_pad_depth_feet NUMERIC,


    ADA_clearance_available BOOLEAN,


    bus_ramp_access_clear BOOLEAN,


    pole_landing_zone_clear BOOLEAN,


    rear_clear_zone_clear BOOLEAN,


    extended_bus_clear_zone_clear BOOLEAN,


    obstruction_notes TEXT,


    opportunity_score NUMERIC,


    reviewed_by TEXT,

    reviewed_at TIMESTAMP

);



------------------------------------------------------------
-- WHERE PEOPLE ACTUALLY WAIT
--
-- Important because bus stop pole location != waiting location
------------------------------------------------------------

CREATE TABLE waiting_environment (

    stop_id TEXT PRIMARY KEY
        REFERENCES bus_stops(stop_id),


    waiting_location TEXT,
    -- examples:
    -- front_of_pole
    -- behind_pole
    -- shelter_area
    -- sidewalk_edge
    -- grass_strip
    -- uncertain


    sun_exposure TEXT,
    -- morning
    -- afternoon
    -- all_day
    -- shaded
    -- unknown


    shade_available BOOLEAN,


    weather_protection_available BOOLEAN,


    volunteer_notes TEXT

);



------------------------------------------------------------
-- STREETVIEW / IMAGE REVIEW DATA
------------------------------------------------------------

CREATE TABLE imagery_reviews (

    review_id SERIAL PRIMARY KEY,


    stop_id TEXT REFERENCES bus_stops(stop_id),


    image_url TEXT,


    reviewer_id TEXT,


    reviewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,


    shelter_visible BOOLEAN,

    bench_visible BOOLEAN,


    people_waiting_visible BOOLEAN,


    accessibility_notes TEXT,


    reviewer_comments TEXT

);



------------------------------------------------------------
-- COMMUNITY REQUESTS
--
-- Captures "people asked us for a bench here"
------------------------------------------------------------

CREATE TABLE community_requests (

    request_id SERIAL PRIMARY KEY,


    stop_id TEXT REFERENCES bus_stops(stop_id),


    requester_name TEXT,


    request_source TEXT,
    -- email
    -- web form
    -- neighborhood group
    -- volunteer


    request_date DATE,


    urgency TEXT,


    notes TEXT

);



------------------------------------------------------------
-- VOLUNTEER ACTIVITY
------------------------------------------------------------

CREATE TABLE volunteers (

    volunteer_id TEXT PRIMARY KEY,


    name TEXT,


    email TEXT,


    skill_level TEXT,


    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

);



------------------------------------------------------------
-- REVIEW TASK QUEUE
--
-- Powers "give me the next 500 useful images"
------------------------------------------------------------

CREATE TABLE review_tasks (

    task_id SERIAL PRIMARY KEY,


    stop_id TEXT REFERENCES bus_stops(stop_id),


    task_type TEXT,
    -- classify_image
    -- verify_bench
    -- verify_shelter
    -- accessibility_review


    priority_score NUMERIC,


    assigned_volunteer TEXT
        REFERENCES volunteers(volunteer_id),


    completed BOOLEAN DEFAULT FALSE,


    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

);



------------------------------------------------------------
-- INTELLIGENCE SCORES
--
-- The project "brain"
------------------------------------------------------------

CREATE TABLE stop_scores (

    stop_id TEXT PRIMARY KEY
        REFERENCES bus_stops(stop_id),


    ridership_score NUMERIC,


    shelter_gap_score NUMERIC,


    bench_gap_score NUMERIC,


    community_demand_score NUMERIC,


    feasibility_score NUMERIC,


    equity_score NUMERIC,


    final_priority_score NUMERIC,


    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

);
