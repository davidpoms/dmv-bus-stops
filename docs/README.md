# DMV Bus Stops

A civic data project analyzing Metrobus stops across Washington, DC, Maryland, and Virginia to identify opportunities for improving transit access, rider experience, and neighborhood investment.

## Project Vision

DMV Bus Stops began as an effort to identify bus stops lacking seating amenities. During development, we discovered that this framing was incomplete: many WMATA shelters already include standardized built-in seating. The more meaningful question is not:

> "Does this stop have a bench?"

but:

> "Does this stop provide a dignified, accessible, and reliable waiting environment for the people who depend on transit?"

This project builds a transparent evidence system to understand bus stop conditions and prioritize improvements.

The long-term goal is to connect transit infrastructure, land use, and community advocacy by making it easier for residents, volunteers, researchers, and policymakers to understand where investment is needed.

---

# Core Goals

## 1. Build a Reliable Evidence Base

Combine multiple sources of evidence:

- Metrobus stop locations
- Street-level imagery
- OpenStreetMap amenities and tags
- Roadway context
- Community review observations
- Geographic and demographic context

The goal is not to make assumptions about stop quality, but to create a structured record of what is known, what is uncertain, and what needs verification.

---

## 2. Support Volunteer Participation

A central design goal is lowering the barrier for community involvement.

Volunteers should be able to:

- Review individual stops
- Confirm visible conditions
- Add observations
- Resolve uncertainty
- Help prioritize improvements
- Build collective knowledge about transit access

The review workflow is designed around human verification rather than automated guesses.

---

## 3. Support Transit and Land Use Advocacy

Transit quality is closely connected to questions of:

- Where people live
- Where jobs and services are located
- How public infrastructure is distributed
- Which neighborhoods receive investment
- Whether transportation systems support opportunity

This project aims to provide evidence that can support conversations around:

- Transit equity
- Better bus stop investments
- Neighborhood accessibility
- Public realm improvements
- Land use decisions that support transit ridership

The dataset should help communities ask better questions:

- Which neighborhoods have the greatest need?
- Which stops serve the most vulnerable riders?
- Where are small infrastructure improvements likely to have the greatest impact?
- Where does transit investment align with broader community development goals?

---

# Current System

The project currently includes:

## Evidence Pipeline

Collects and organizes stop-level evidence from:

- OpenStreetMap exports
- Street View imagery
- Stop metadata
- Community observations

Key components:

- OSM evidence ingestion
- Amenity tagging
- Stop evidence summaries
- Evidence API endpoints

---

## Review Workflow

The review system allows community members to evaluate stops.

Current capabilities:

- Reviewer assignments
- Stop review queues
- Observation tracking
- Consensus workflows
- Recommendation generation

The system has moved from a simple review model to an observation-based model:
