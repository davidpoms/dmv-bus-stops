"""Permanent recognition foundation; no imports, requests, or workers activate it."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RecognitionGate:
    capture: bool = False
    issuance: bool = False


DISABLED = RecognitionGate()
