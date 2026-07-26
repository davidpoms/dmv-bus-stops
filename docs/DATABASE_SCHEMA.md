# DMV Bus Stops Database Schema

## Design Principles

The database separates:

1. Observed facts
2. Evidence sources
3. Human observations
4. Analytical interpretation
5. Recommended actions

---

# Core Entities

## physical_stops

Represents a bus stop location.

Fields:

| Field | Description |
|-|-|
| id | Internal stop ID |
| stop_id | Agency stop identifier |
| stop_name | Stop name |
| latitude | Latitude |
| longitude | Longitude |
| jurisdiction | DC/MD/VA |
| municipality | City/county |
| created_at | Record creation |

---

# stop_amenities

Represents physical infrastructure.

| Field | Description |
|-|-|
| stop_id | Related stop |
| shelter_present | Whether shelter exists |
| shelter_type | WMATA/custom/unknown |
| built_in_seating | Built-in shelter seating |
| seating_capacity | Estimated seats |
| additional_seating | Other seating |
| lighting_present | Lighting availability |
| ada_features | Accessibility features |
| sidewalk_access | Pedestrian access |

---

# seating_assessments

Represents quality of seating.

Important because presence does not equal usability.

| Field | Description |
|-|-|
| stop_id | Related stop |
| seating_available | Yes/no |
| comfort_rating | Volunteer rating |
| duration_suitable | Short wait vs long wait |
| accessibility_rating | Accessibility |
| notes | Comments |

---

# ridership_context

Represents demand.

| Field | Description |
|-|-|
| stop_id | Related stop |
| daily_boardings | Boarding count |
| daily_alightings | Alighting count |
| route_count | Number of routes |
| transfer_activity | Transfer importance |

---

# improvement_program_status

Tracks existing agency plans.

| Field | Description |
|-|-|
| stop_id | Related stop |
| program | WMATA improvement program |
| status | planned/in progress/completed |
| phase | Project phase |
| date_updated | Last update |

---

# evidence_sources

Tracks where information comes from.

Examples:

- WMATA
- OSM
- Street View
- volunteer review

Fields:

| Field | Description |
|-|-|
| id | Evidence ID |
| stop_id | Related stop |
| source_type | Dataset/source |
| source_date | Snapshot date |
| confidence | Reliability |

---

# stop_observations

Volunteer review data.

| Field | Description |
|-|-|
| id | Observation ID |
| stop_id | Related stop |
| reviewer | Reviewer |
| method | remote/field |
| shelter_visible | Yes/no |
| seating_visible | Yes/no |
| seating_condition | Rating |
| accessibility_issue | Yes/no |
| weather_issue | Yes/no |
| notes | Comments |
| confidence | Reviewer confidence |

---

# stop_assessments

Interpretation layer.

This is not raw data.

Example:

Evidence:

- shelter exists
- 700 daily riders
- one curved seat

Assessment:

- possible waiting capacity gap

Fields:

| Field | Description |
|-|-|
| stop_id | Related stop |
| condition | Assessment category |
| explanation | Human-readable explanation |
| recommended_action | Next step |
| confidence | Confidence level |

---

# recommended_actions

Possible interventions.

Examples:

- field review
- community observation
- agency inquiry
- accessibility review

---

# Current Prototype Mapping

Existing tables:

- physical_stops
- stop_osm_evidence
- stop_observations
- stop_consensus
- stop_validation
- stop_review_assignments

Future refactor may separate these concepts more clearly.