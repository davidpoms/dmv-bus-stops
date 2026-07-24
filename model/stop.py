"""
Canonical bus stop model.

Every stage of the pipeline operates on this object.

External data sources (WMATA, OSM, Google Street View, volunteer reviews,
database records, etc.) are translated into this model before analysis.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class BusStop:
    """
    Represents one physical bus stop.

    A BusStop is the canonical in-memory representation used throughout
    the repository.
    """

    ####################################################################
    # Identity
    ####################################################################

    stop_id: str

    stop_name: Optional[str] = None

    jurisdiction: Optional[str] = None

    latitude: float = 0.0

    longitude: float = 0.0

    route_ids: list[str] = field(default_factory=list)

    ####################################################################
    # Existing infrastructure
    ####################################################################

    has_bench: Optional[bool] = None

    has_shelter: Optional[bool] = None

    has_trash_can: Optional[bool] = None

    has_lighting: Optional[bool] = None

    ada_accessible: Optional[bool] = None

    waiting_area_type: Optional[str] = None

    ####################################################################
    # Physical suitability
    ####################################################################

    concrete_pad_width_ft: Optional[float] = None

    concrete_pad_depth_ft: Optional[float] = None

    unobstructed_curb_access: Optional[bool] = None

    accessible_landing_zone: Optional[bool] = None

    rear_clear_zone_ft: Optional[float] = None

    articulated_bus_clearance: Optional[bool] = None

    ####################################################################
    # Volunteer review
    ####################################################################

    review_count: int = 0

    confidence: float = 0.0

    last_reviewed: Optional[datetime] = None

    ####################################################################
    # Demand
    ####################################################################

    monthly_boardings: Optional[float] = None

    estimated_wait_demand: Optional[float] = None

    public_requests: int = 0

    ####################################################################
    # OSM comparison
    ####################################################################

    osm_bench: Optional[bool] = None

    osm_shelter: Optional[bool] = None

    osm_match_distance_m: Optional[float] = None

    ####################################################################
    # Priority scores
    ####################################################################

    review_priority: float = 0.0

    bench_priority: float = 0.0

    ####################################################################
    # Imagery
    ####################################################################

    streetview_status: Optional[str] = None

    streetview_images: list[str] = field(default_factory=list)

    ####################################################################
    # Metadata
    ####################################################################

    notes: list[str] = field(default_factory=list)

    tags: list[str] = field(default_factory=list)

    ####################################################################
    # Convenience methods
    ####################################################################

    def needs_review(self) -> bool:
        """
        Returns True if additional volunteer review is recommended.
        """
        return self.confidence < 0.90

    def is_bench_candidate(self) -> bool:
        """
        Returns True if the stop currently appears to lack a bench.
        """
        return self.has_bench is False

    def has_complete_accessibility_data(self) -> bool:
        """
        Returns True if all ADA-related fields have been populated.
        """
        return all(
            value is not None
            for value in (
                self.ada_accessible,
                self.accessible_landing_zone,
                self.unobstructed_curb_access,
            )
        )

    def add_route(self, route_id: str) -> None:
        """
        Adds a serving route if it isn't already present.
        """
        if route_id not in self.route_ids:
            self.route_ids.append(route_id)

    def add_note(self, note: str) -> None:
        """
        Adds a free-form note.
        """
        self.notes.append(note)

    def add_tag(self, tag: str) -> None:
        """
        Adds a tag if not already present.
        """
        if tag not in self.tags:
            self.tags.append(tag)

    @property
    def location(self) -> tuple[float, float]:
        """
        Returns (latitude, longitude).
        """
        return (self.latitude, self.longitude)

    @property
    def has_any_amenity(self) -> bool:
        """
        True if the stop has at least one passenger amenity.
        """
        return any(
            x is True
            for x in (
                self.has_bench,
                self.has_shelter,
                self.has_trash_can,
                self.has_lighting,
            )
        )
