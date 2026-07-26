# DMV Bus Stops

## Community-powered bus stop experience analysis for the Washington DC region

DMV Bus Stops is a civic data project analyzing Metrobus stops across Washington DC, Maryland, and Virginia.

The project originally focused on identifying bus stops without benches. During development, this framing was found to be incomplete.

WMATA shelters generally include standardized built-in curved seating. The question is not whether a bench exists, but whether the existing waiting environment adequately supports the riders who use the stop.

The project has therefore evolved into:

> Identifying high-demand bus stops where existing waiting conditions may not adequately support riders.

---

# Project Goals

The project seeks to combine:

- transit infrastructure data
- ridership context
- open data sources
- imagery review
- volunteer observations
- community input

to identify locations where additional investigation or improvement may be warranted.

The system is designed to complement, not duplicate, WMATA capital improvement programs.

---

# Current Prototype

The current application includes:

## Backend

- Flask API
- SQLite database
- stop-level analysis
- evidence storage
- volunteer review workflow

## Frontend

- interactive map dashboard
- stop prioritization visualization
- reviewer tools
- community action concepts

## Data Sources

Current and planned sources include:

- WMATA stop data
- GTFS transit data
- ridership information
- OpenStreetMap evidence
- Google Street View imagery
- volunteer observations

---

# Core Conceptual Model

The project evaluates stops across three dimensions.

## 1. Infrastructure

What physically exists?

Examples:

- shelter presence
- shelter type
- seating availability
- seating capacity
- lighting
- ADA features
- sidewalk conditions

---

## 2. Passenger Experience

What is the rider actually experiencing?

Examples:

- ability to sit while waiting
- comfort
- weather protection
- accessibility
- crowding
- suitability for long waits

---

## 3. Improvement Opportunity

Where should attention be directed?

Examples:

- high ridership with limited amenities
- accessibility concerns
- unclear conditions requiring review
- technically compliant but inadequate passenger experience

---

# Design Principles

## Avoid false conclusions

The project should not claim:

"this stop has no bench"

when the actual condition is:

"this stop has a shelter with limited seating capacity relative to demand."

---

## Separate evidence from interpretation

Raw observations should be stored separately from recommendations.

Example:

Evidence:

- shelter exists
- built-in seating exists
- 600 daily riders

Interpretation:

- possible seating capacity mismatch
- recommended review

---

# Current Questions

The project is actively evaluating:

- How should rider experience be measured?
- How can volunteers provide useful evidence?
- How should WMATA improvement projects affect recommendations?
- What findings would be actionable for transit agencies?

---

# Development Philosophy

The goal is not to create another infrastructure inventory.

The goal is to create an evidence-based system that helps answer:

> Where are the busiest stops where the waiting environment may not match rider needs?