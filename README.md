# DMV Bus Stop Intelligence

## Community-powered analysis of bus stop experiences across the Washington DC region

DMV Bus Stop Intelligence is a civic data project focused on understanding whether bus stops provide riders with the safe, comfortable, and accessible waiting environments they deserve.

The project analyzes Metrobus stops across Washington DC, Maryland, and Virginia by combining transit data, public datasets, imagery review, and community observations.

---

# Why this project exists

Public transportation does not begin when a bus arrives.

For many riders, the bus stop itself is part of the transit experience:

- Is there somewhere safe to wait?
- Is there protection from weather?
- Is there a place to sit during a long wait?
- Can older adults, disabled riders, and people carrying groceries or children comfortably use the stop?
- Does the physical environment match the number of people relying on the service?

DMV Bus Stop Intelligence exists to help communities identify places where the waiting environment may not meet rider needs.

---

# Primary project focus

The initial volunteer effort focuses on identifying high-priority opportunities for improved seating at bus stops.

This includes understanding:

- where riders are likely waiting frequently
- where seating may be insufficient
- where a bench installation may be feasible
- where accessibility considerations require attention

The project does not assume that every stop without a standalone bench needs one.

For example:

- a shelter may already provide seating
- a bench may not fit without a concrete pad or other site improvement
- accessibility space may require thoughtful placement
- some locations may need further review before recommending improvements

---

# Data philosophy

The project separates:

## Evidence

What we know:

- transit service
- ridership context
- existing infrastructure
- imagery observations
- volunteer reviews
- public datasets

## Interpretation

What we think the evidence may mean:

- possible seating need
- accessibility concern
- opportunity for further review
- advocacy opportunity

Recommendations should always remain connected to the underlying evidence.

---

# Current system

DMV Bus Stop Intelligence combines:

- transit and stop data
- ridership information
- geographic analysis
- open data sources
- imagery review
- volunteer observations
- community feedback

The system is designed to help communities surface important questions and priorities. It is not intended to replace agency planning processes.

---

# Volunteer review

Volunteers help answer questions that public datasets cannot answer alone.

The dashboard offers one primary **Review a seating opportunity** entry point. It
includes every active stop; the priority score ranks the review order and does
not decide whether a stop is included. Reviewers can instead choose a stop from
My Route, Near Me, or the map when that better matches how they want to help.

The review page explains these two ideas separately:

- why that stop was selected (the entry path)
- what evidence would be most useful to check at that stop

The same survey is used for every path. Its emphasis adapts to the evidence
already available without hiding the other observation fields.

Examples:

- What seating exists today?
- How comfortable does the waiting environment appear?
- Could a bench fit safely?
- Would additional site improvements likely be needed?
- Are there accessibility concerns?

Volunteer observations help create a clearer picture of rider experience.

---

# Project principles

## Riders deserve quality transit environments

A bus stop is not just a sign on a sidewalk.

It is a place where people:

- wait
- rest
- transfer
- begin and end trips
- depend on public transportation

The goal of this project is to help communities advocate for bus stops that reflect the importance of the riders who use them.

---

# Development

Current components:

- Flask application
- SQLite database
- dashboard
- volunteer review tools
- recommendation pipeline
- geographic analysis tools

The project is actively evolving through community feedback.

---

# Documentation

Additional documentation:

- `docs/DMV_Bus_Stop_Intelligence_Handbook.md`
- `docs/Volunteer_Review_Handbook.md`
- `docs/DATABASE_SCHEMA.md`
- `docs/ROADMAP.md`

