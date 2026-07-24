"""
Human review model.

A review represents one volunteer's observation of one bus stop.
Multiple reviews can exist for the same stop so the system can:
- measure agreement
- detect uncertainty
- prioritize stops needing more review
- build confidence scores over time
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class StopReview:
    """
    A single human review of a bus stop.

    One reviewer may answer only part of this schema.
    For example:
    - a neighborhood volunteer may only report "needs bench"
    - an image classifier volunteer may only tag shelter visibility
    """

    stop_id: str
    reviewer_id: str

    # What was reviewed
    review_source: str = "streetview"

    # Shelter observations
    has_shelter: Optional[bool] = None
    shelter_type: Optional[str] = None
    shelter_condition: Optional[str] = None

    # Bench observations
    has_bench: Optional[bool] = None
    bench_condition: Optional[str] = None

    # Space suitability for community bench installation
    bench_candidate: Optional[bool] = None

    # Site feasibility observations
    flat_concrete_pad: Optional[bool] = None
    estimated_available_width_ft: Optional[float] = None
    curb_clearance_ok: Optional[bool] = None
    bus_ramp_access_clear: Optional[bool] = None

    # Human intelligence fields
    where_people_wait: Optional[str] = None
    shade_available: Optional[str] = None
    sun_exposure_notes: Optional[str] = None

    # Freeform notes
    reviewer_notes: Optional[str] = None

    # Confidence from reviewer
    reviewer_confidence: Optional[int] = None

    created_at: datetime = datetime.utcnow()

    def is_bench_priority_candidate(self) -> bool:
        """
        Basic rule for identifying possible bench installations.

        This is intentionally simple.
        Later the scoring engine will combine:
        - ridership
        - requests
        - ADA feasibility
        - review confidence
        - neighborhood patterns
        """

        return (
            self.has_bench is False
            and self.bench_candidate is True
            and self.flat_concrete_pad is True
            and self.curb_clearance_ok is True
            and self.bus_ramp_access_clear is True
        )

    def completeness_score(self) -> float:
        """
        Estimate how much useful information this review contains.

        Used later to prioritize additional review.
        """

        fields = [
            self.has_shelter,
            self.has_bench,
            self.bench_candidate,
            self.flat_concrete_pad,
            self.curb_clearance_ok,
            self.bus_ramp_access_clear,
            self.where_people_wait,
            self.shade_available,
            self.reviewer_notes,
        ]

        completed = sum(value is not None for value in fields)

        return completed / len(fields)
