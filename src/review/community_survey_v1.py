"""
Canonical DMV Bus Stops Community Review Survey v1.0

This file is the source of truth for survey questions.
The UI should render from this structure rather than hardcoded questions.
"""


SURVEY_VERSION = "1.0"


SURVEY = {

    "review_mode": {
        "label": "How are you reviewing this stop?",
        "type": "radio",
        "options": [
            ("remote", "Remote review (Street View / imagery / online data)"),
            ("in_person", "In-person review (visited the stop)")
        ]
    },


    "remote": [

        {
            "field": "shelter_present",
            "label": "Is there a shelter at this stop?",
            "options": [
                ("yes", "Yes"),
                ("no", "No"),
                ("unknown", "Unsure")
            ]
        },

        {
            "field": "shelter_protection",
            "label": "How well does the shelter appear to protect riders while waiting?",
            "condition": "shelter_present=yes",
            "options": [
                ("good", "Provides meaningful protection from sun/rain"),
                ("partial", "Provides some protection but has limitations"),
                ("poor", "Provides little protection"),
                ("unknown", "Unsure")
            ]
        },

        {
            "field": "seating_type",
            "label": "What seating is available for riders?",
            "multiple": True,
            "options": [
                ("full_bench", "Full bench suitable for multiple riders"),
                ("shelter_bench", "Small shelter bench"),
                ("individual_seats", "Individual seats"),
                ("leaning_support", "Leaning/perch support"),
                ("non_shelter_bench", "Non-shelter bench"),
                ("other", "Other seating"),
                ("none", "No seating observed"),
                ("unknown", "Unsure")
            ]
        },

        {
            "field": "seating_limitations",
            "label": "Do any features appear to limit normal use of the seating?",
            "options": [
                ("none", "No apparent limitations"),
                ("dividers", "Seat dividers limit shared seating"),
                ("small", "Seating is too narrow/small"),
                ("leaning", "Seating encourages leaning instead of sitting"),
                ("other", "Other limitation"),
                ("unknown", "Unsure")
            ]
        },

        {
            "field": "bench_feasible",
            "label": "If additional seating were installed, could riders still move through the stop safely?",
            "options": [
                ("yes", "Yes"),
                ("no", "No"),
                ("unknown", "Unsure")
            ]
        },

        {
            "field": "concrete_pad_needed",
            "label": "Would a concrete pad likely be needed to install seating without affecting accessibility?",
            "options": [
                ("yes", "Yes"),
                ("no", "No"),
                ("unknown", "Unsure")
            ]
        },

        {
            "field": "accessibility_status",
            "label": "Does the stop appear accessible for riders using mobility devices?",
            "options": [
                ("good", "Clear accessible path"),
                ("possible_obstruction", "Possible obstruction"),
                ("blocked", "Not accessible"),
                ("unknown", "Unsure")
            ]
        },

        {
            "field": "weather_exposure",
            "label": "Does the waiting area appear exposed to sun or weather?",
            "options": [
                ("protected", "Mostly protected"),
                ("partial", "Partially exposed"),
                ("exposed", "Mostly exposed"),
                ("unknown", "Unsure")
            ]
        },

        {
            "field": "waiting_environment_rating",
            "label": "Overall, how well does this stop support riders while waiting?",
            "options": [
                ("good", "Good — functional waiting environment"),
                ("fair", "Fair — usable but has limitations"),
                ("poor", "Poor — inadequate waiting environment"),
                ("unknown", "Unsure")
            ]
        }

    ],


    "in_person": [

        {
            "field": "reviewer_relationship",
            "label": "What is your relationship to this stop?",
            "options": [
                ("rider", "I regularly ride this bus"),
                ("passerby", "I regularly pass by this stop"),
                ("nearby", "I live or work nearby"),
                ("reviewer", "I am visiting this stop specifically for review"),
                ("other", "Other")
            ]
        },

        {
            "field": "usage_times",
            "label": "When have you observed this stop being used?",
            "multiple": True,
            "options": [
                ("morning", "Morning commute"),
                ("midday", "Midday"),
                ("afternoon", "Afternoon commute"),
                ("evening", "Evening"),
                ("weekends", "Weekends"),
                ("other", "Other")
            ]
        },

        {
            "field": "rider_activity",
            "label": "How would you describe activity at this stop when you observe it?",
            "options": [
                ("low", "Usually few riders"),
                ("moderate", "Moderate activity"),
                ("busy", "Frequently busy"),
                ("peak", "Crowded at certain times"),
                ("unknown", "Unsure")
            ]
        },

        {
            "field": "riders_avoid_facilities",
            "label": "Do riders appear to avoid the available seating or shelter?",
            "options": [
                ("yes", "Yes"),
                ("no", "No"),
                ("unknown", "Unsure")
            ]
        }

    ],


    "steward": [

        {
            "field": "steward_interest",
            "label": "Would you be willing to help advocate for improvements at this stop, including speaking with nearby property owners about possible improvements?",
            "options": [
                ("yes", "Yes"),
                ("maybe", "Maybe"),
                ("no", "No")
            ]
        },

        {
            "field": "steward_email",
            "label": "Email address",
            "type": "text",
            "always_visible": True,
            "required_when": [
                "steward_interest=yes",
                "steward_interest=maybe"
            ]
        }

    ],


    "notes": {
        "field": "notes",
        "label": "Anything else about this stop that would help improve rider experience?",
        "type": "textarea"
    }

}
