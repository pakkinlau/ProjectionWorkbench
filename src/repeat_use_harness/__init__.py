"""Public surface for the repeat-use value-discovery harness."""
from .harness import *
from .counterfactual import (
    CounterfactualValidationError,
    build_repair_manifest,
    qualify_counterfactual_assignment,
    validate_actual_exposure_receipt,
    validate_analysis_plan,
    validate_assignment_schedule,
    validate_carryover_ledger,
    validate_comparator_parity_receipt,
    validate_counterfactual_bundle,
    validate_missingness_policy,
    validate_reset_integrity_receipt,
)

__all__ = [name for name in globals() if not name.startswith("_")]
__version__ = "1.3.0"
