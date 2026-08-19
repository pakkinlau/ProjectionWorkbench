"""Compatibility membrane for terminal/admission calibration normalization.

The W3R.B1 payload names the canonical adapter module ``calibration`` while the
integrated W3I public surface uses the semantic role name ``normalization``.
This module is intentionally a lossless re-export: it adds no scoring,
authority, evidence promotion, or alternate terminal semantics.
"""
from .calibration import *
