# DMV Bus Stops Project — Technical Handoff Document

**Repository:** `davidpoms/dmv-bus-stops`
**Current branch:** `main`
**Current checkpoint:** Dashboard refactor + script archive consolidation
**Last major commit:** `7c88be1`
**Status:** Active development, stable refactor checkpoint

---

# 1. Project Overview

The DMV Bus Stops project is a data-driven platform for identifying, reviewing, and prioritizing bus stop improvement opportunities across the Washington DC metropolitan region.

The system combines:

* Transit stop inventory data
* WMATA stop information
* Ridership and transit exposure metrics
* Geographic context
* OpenStreetMap amenity evidence
* Community review surveys
* Consensus review workflows
* Dashboard visualization and prioritization

The goal is to move from a static inventory of bus stops toward a community-validated improvement pipeline.

---

# 2. High-Level Architecture

```
Data Sources
    |
    |
    +-- WMATA data
    +-- DC / MD / VA geographic data
    +-- OpenStreetMap amenities
    +-- Road centerlines
    |
    v

Database / Evidence Layer
    |
    |
    +-- Stop records
    +-- Evidence records
    +-- Review observations
    +-- Consensus results
    +-- Improvement recommendations
    |
    v

Application Layer
    |
    |
    +-- Dashboard generator
    +-- Review workflow
    +-- Survey renderer
    +-- Recommendation engine
    |
    v

User Interface
    |
    |
    +-- Public dashboard
    +-- Stop detail popups
    +-- Community survey workflow
    +-- Review validation process
```

---

# 3. Repository Structure

## Active application code

```
src/
├── assessment/
│   └── generate_improvement_recommendations.py
│
├── dashboard/
│   ├── data.py
│   ├── generate_dashboard.py
│   ├── render_docs.py
│   ├── static/
│   │   ├── dashboard.js
│   │   └── survey.js
│   └── templates/
│       └── dashboard.html
│
├── review/
│   ├── community_survey_v1.py
│   ├── create_review_queue.py
│   └── render_survey.py
│
└── spatial/
    └── nearest_road.py
```

---

# 4. Script Organization

The repository previously accumulated hundreds of iterative patch scripts.

These have now been reorganized.

## Current operational scripts

```
scripts/
```

Contains active utilities for:

* data imports
* evidence generation
* debugging
* rebuilding outputs
* validation
* workflow maintenance

Examples:

```
import_wmata_evidence.py
rebuild_stop_consensus.py
generate_improvement_recommendations.py
wire_map_filters.py
validate_geography.py
```

---

## Archived scripts

```
scripts/archive/
```

Contains:

* historical patches
* migrations
* experiments
* one-off fixes
* deprecated workflow scripts

Current archive size:

```
524 scripts
```

These are preserved for historical reference but should not be used in normal development.

---

# 5. Dashboard System

## Entry point

Generate dashboard:

```bash
python -m src.dashboard.generate_dashboard
```

Primary components:

### Dashboard data layer

File:

```
src/dashboard/data.py
```

Responsibilities:

* load stop data
* prepare geographic summaries
* prepare evidence bundles
* supply dashboard metrics

---

### Dashboard renderer

File:

```
src/dashboard/generate_dashboard.py
```

Responsibilities:

* assemble dashboard output
* render templates
* write final HTML

---

### Frontend

Main JavaScript:

```
src/dashboard/static/dashboard.js
```

Handles:

* map rendering
* filters
* stop popup interactions
* review actions
* evidence display
* geography filtering

---

# 6. Review Workflow

The review system allows community reviewers to evaluate bus stops.

Workflow:

```
Stop Candidate
      |
      v
Review Queue
      |
      v
Community Survey
      |
      v
Observation Record
      |
      v
Consensus Processing
      |
      v
Recommendation
```

---

## Review queue generation

File:

```
src/review/create_review_queue.py
```

Responsible for:

* selecting candidate stops
* assigning review status
* preparing review workflow

---

## Survey rendering

Files:

```
src/review/render_survey.py
src/review/community_survey_v1.py
```

Responsibilities:

* generate survey questions
* handle conditional questions
* format reviewer experience

## Seating opportunity review model

`seating_improvement_opportunities` has one derived row per current GTFS stop.
Membership is broad: the priority score ranks rows and never gates inclusion.
The score is `documented_need_index * 0.60 + rider_exposure_percentile * 0.40`.
The need index is the maximum applicable documented-need signal, not a sum.
Rider exposure is route-based exposure associated with the stop; it is not
observed stop-level boarding.

Canonical amenity status, seating adequacy, preliminary clearance, and rider
benefit remain separate concepts. Workflow state describes the next useful
evidence task. Campaign is assignment context derived from that workflow for an
opportunity review; it is not another scoring system.

Public review context also keeps two concepts distinct:

* entry path explains why the reviewer reached the stop (opportunity, route,
  nearby, map, or direct link)
* review focus explains what evidence would be useful to collect

Assignment-backed submissions append `stop_observations` history and retain the
assignment ID. `review_mode` records in-person, Street View, or other remote
visual review; `streetview_imagery_month` is distinct from `observed_at`.
Preliminary visual clearance never represents engineering, ADA, ownership,
utility, permitting, or construction approval.

The targeted post-submission refresh is:

```
consensus -> amenity status -> amenity review priority
          -> affected seating opportunity -> review queue -> rank refresh
```

Run `scripts/active/create_review_tables.py` when deploying schema additions,
then use the active rebuild scripts when a full derived-data rebuild is
actually required. Do not restore archived patch scripts as migrations.

---

# 7. Evidence Pipeline

Evidence is used to support improvement recommendations.

Evidence sources:

## Transit evidence

Includes:

* ridership exposure
* route information
* stop activity

Relevant scripts:

```
scripts/import_wmata_evidence.py
scripts/rebuild_wmata_evidence.py
```

---

## OSM evidence

Includes:

* nearby benches
* shelters
* amenities

Relevant scripts:

```
scripts/build_stop_osm_evidence.py
scripts/import_local_osm_export.py
```

---

## Road geometry

Used for:

* Street View orientation
* nearest roadway matching

Relevant files:

```
src/spatial/nearest_road.py
```

---

# 8. Consensus System

Consensus transforms individual reviews into validated recommendations.

Important files:

```
scripts/rebuild_stop_consensus.py

src/assessment/generate_improvement_recommendations.py
```

Flow:

```
Reviewer observations
        |
        v
Consensus aggregation
        |
        v
Confidence assessment
        |
        v
Improvement recommendation
```

---

# 9. Recent Major Changes

## Script archive consolidation

Completed:

* moved historical scripts into:

```
scripts/archive/
```

* preserved git history through renames where possible
* reduced active script clutter

---

## Dashboard refactor

Completed:

* dashboard JS cleanup
* review workflow simplification
* survey rendering improvements
* popup improvements
* geography/filter improvements

---

## WMATA evidence improvements

Completed:

* improved WMATA evidence importing
* added matching tools
* improved confidence display
* improved retired stop handling

---

# 10. Known Technical Risks

## 1. Large script history

The archive contains many experimental paths.

Before modifying workflow logic:

Search current code first:

```bash
grep -R "function_name" src scripts
```

Do not resurrect archived scripts without review.

---

## 2. Dashboard JavaScript complexity

Primary frontend file:

```
src/dashboard/static/dashboard.js
```

This remains the largest frontend dependency.

Before editing:

* identify event handlers
* check DOM assumptions
* test dashboard generation afterward

---

## 3. Data dependencies

The project depends on:

* WMATA datasets
* geographic files
* OSM exports
* database state

A clean clone may require rebuilding data artifacts.

---

# 11. Development Workflow

Recommended sequence:

## Before changes

```bash
git status
git pull
```

---

## After code changes

Run:

```bash
python -m src.dashboard.generate_dashboard
```

Check:

* dashboard builds
* HTML renders
* map loads

---

## Before commit

```bash
git status
git diff
```

Commit:

```bash
git add .
git commit -m "Describe change"
```

Push:

```bash
git push
```

---

# 12. Current Known Good State

The repository currently represents:

✅ Archived historical scripts
✅ Cleaner active development structure
✅ Dashboard workflow consolidated
✅ Review workflow rebuilt
✅ WMATA evidence improvements integrated
✅ Geography/filter improvements integrated
✅ GitHub synchronized

Current baseline commit:

```
7c88be1
```

---

# 13. Suggested Next Development Priorities

## Priority 1 — End-to-end validation

Confirm:

* dashboard generation
* map rendering
* popup behavior
* survey submission
* consensus rebuild
* recommendation generation

---

## Priority 2 — Database/documentation cleanup

Document:

* schema
* evidence tables
* review lifecycle
* recommendation lifecycle

---

## Priority 3 — Production readiness

Consider:

* automated tests
* deployment instructions
* environment variable documentation
* data refresh procedures

---

# 14. Quick Start Checklist

A new developer should:

1. Clone repository

```bash
git clone https://github.com/davidpoms/dmv-bus-stops
```

2. Install dependencies

```bash
pip install -r requirements.txt
```

3. Generate dashboard

```bash
python -m src.dashboard.generate_dashboard
```

4. Verify:

* dashboard loads
* stops appear
* filters work
* review workflow opens

---

# End State

The DMV Bus Stops repository has transitioned from an experimental patch-driven workflow into a more maintainable application structure.

The main development focus should now shift from repair/refactoring toward feature completion, validation, and deployment.
