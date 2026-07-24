# Processing Pipeline

This directory contains the data processing pipeline that transforms raw transit datasets into actionable bus stop improvement recommendations.

Each script has one responsibility and produces data used by later stages.

---

# Pipeline Overview

```
Raw WMATA Data
      │
      ▼
load_bus_stops.py
      │
      ▼
bus_stops
      │
      ▼
link_gtfs_stops.py
      │
      ▼
GTFS-linked bus stops
      │
      ▼
build_physical_stops.py
      │
      ▼
physical_stops
      │
      ├──────────────┐
      ▼              ▼
Street View      OpenStreetMap
      │              │
      └──────┬───────┘
             ▼
Opportunity Assessment
             ▼
Priority Recommendations
```

---

# Processing Stages

## 1. load_bus_stops.py

### Purpose

Import the official WMATA bus stop inventory.

### Input

* WMATA GeoJSON

### Output

Table:

* `bus_stops`

Each record represents one official WMATA bus stop.

---

## 2. link_gtfs_stops.py

### Purpose

Associate WMATA stop records with GTFS stop IDs.

### Input

* `bus_stops`
* GTFS `stops.txt`

### Output

Updated fields:

* `gtfs_stop_id`

This enables joining routes and schedules.

---

## 3. build_physical_stops.py

### Purpose

Group multiple WMATA stop records that represent the same physical bus stop location.

### Input

* `bus_stops`

### Output

Tables:

* `physical_stops`
* `physical_stop_members`

This becomes the canonical entity used throughout the application.

Future processing should reference `physical_stops`, not individual WMATA stop records.

---

## 4. Import Ridership

### Purpose

Associate route-level ridership with physical stops.

### Inputs

* GTFS routes
* GTFS stop_times
* WMATA ridership data

### Output

Daily boarding estimates for each physical stop.

---

## 5. Street View Processing

### Purpose

Capture current imagery for every physical stop.

### Inputs

* Google Street View

### Output

Images and metadata for review.

---

## 6. OpenStreetMap Processing

### Purpose

Identify nearby infrastructure.

Examples include:

* benches
* shelters
* sidewalks
* crossings
* curb ramps
* lighting

---

## 7. Opportunity Assessment

### Purpose

Combine all available evidence into a structured assessment.

Evidence includes:

* ridership
* infrastructure
* accessibility
* community observations
* feasibility

The assessment explains *why* a stop may need improvement.

---

## 8. Priority Recommendations

### Purpose

Rank physical bus stop improvement opportunities.

Recommendations are generated from the assessment and remain fully explainable.

Each recommendation includes the evidence supporting it.

---

# Guiding Principles

## One Script, One Responsibility

Each processing script should perform one task well.

Avoid scripts that import data, clean data, compute scores, and update reports all at once.

---

## Immutable Raw Data

Raw WMATA and GTFS imports should remain unchanged.

Derived datasets should be stored in new tables.

---

## Physical Stops are the Canonical Entity

Individual WMATA stop records describe transit operations.

Physical stops describe real-world locations.

All future analysis should use `physical_stops`.

---

## Explainable Results

Every recommendation should be traceable back to measurable evidence.

Users should always be able to understand why a location was prioritized.

---

# Long-Term Vision

Create an open, evidence-based platform that helps agencies, advocates, and communities identify where bus stop improvements will have the greatest impact.

The goal is not simply to map bus stops.

The goal is to improve the experience of waiting for the bus.
