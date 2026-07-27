"""
Canonical community bus stop review questions.

This file is the source of truth for:
- remote review questions
- in-person review questions
- field names used by the database and dashboard
"""

SURVEY_QUESTIONS = {

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
            "field": "seating_type",
            "label": "What seating is currently available for riders?",
            "options": [
                ("shelter_bench", "Shelter with built-in bench"),
                ("bench", "Non-shelter bench"),
                ("other", "Other seating"),
                ("none", "No seating observed"),
                ("unknown", "Unsure")
            ]
        },

        {
            "field": "rider_comfort_category",
            "label": "How comfortable does the available seating appear for waiting riders?",
            "options": [
                ("comfortable", "Comfortable seating"),
                ("basic", "Basic seating (such as shelter bench or backless bench)"),
                ("poor", "Poor seating"),
                ("unknown", "Unsure")
            ]
        },

        {
            "field": "hostile_design",
            "label": "Does the seating appear designed in a way that discourages normal waiting?",
            "options": [
                ("none", "No apparent hostile design"),
                ("separators", "Seat dividers or barriers"),
                ("sloped", "Sloped or leaning surfaces"),
                ("other", "Other"),
                ("unknown", "Unsure")
            ]
        },

        {
            "field": "bench_feasible",
            "label": "If a bench were installed, could riders still pass through safely?",
            "options": [
                ("yes", "Yes"),
                ("no", "No"),
                ("unknown", "Unsure")
            ]
        },

        {
            "field": "concrete_pad_needed",
            "label": "Would a concrete pad or similar surface improvement likely be needed to install a bench without reducing accessibility?",
            "options": [
                ("yes", "Yes"),
                ("no", "No"),
                ("unknown", "Unsure")
            ]
        },

        {
            "field": "accessibility_status",
            "label": "Does the current waiting area appear accessible for riders using mobility devices?",
            "options": [
                ("good", "Clear accessible path"),
                ("blocked", "Path appears blocked or constrained"),
                ("unknown", "Unsure")
            ]
        }
    ],


    "in_person": [

        {
            "field": "reviewer_relationship",
            "label": "What is your relationship to this stop?",
            "options": [
                ("user", "I regularly use this stop"),
                ("neighbor", "I live or work nearby"),
                ("visitor", "I am visiting specifically to review this stop"),
                ("other", "Other")
            ]
        },

        {
            "field": "usage_times",
            "label": "When have you personally observed this stop being used?",
            "type": "multiselect",
            "options": [
                ("morning", "Morning commute"),
                ("midday", "Midday"),
                ("afternoon", "Afternoon commute"),
                ("evening", "Evening"),
                ("weekend", "Weekends")
            ]
        },

        {
            "field": "rider_activity",
            "label": "How would you describe rider activity during those times?",
            "options": [
                ("low", "Few riders"),
                ("moderate", "Moderate activity"),
                ("high", "Frequent riders waiting"),
                ("crowded", "Crowded waiting area"),
                ("unknown", "Unsure")
            ]
        },

        {
            "field": "waiting_behavior",
            "label": "Where do riders typically wait?",
            "options": [
                ("waiting_area", "Designated waiting area"),
                ("shelter", "Under shelter"),
                ("sidewalk", "Along sidewalk edge"),
                ("grass", "Grass or unpaved area"),
                ("property", "Near nearby business/property"),
                ("unknown", "Unsure")
            ]
        },

        {
            "field": "property_owner_outreach",
            "label": "Would you be willing to help contact nearby property owners about a possible bench installation?",
            "options": [
                ("yes", "Yes"),
                ("maybe", "Maybe"),
                ("no", "No")
            ]
        },

        {
            "field": "steward_email",
            "label": "Email address (if willing to help)",
            "type": "email"
        }

    ],

    "notes": {
        "field": "notes",
        "label": "Anything else about this stop that would help improve it?"
    }
}
