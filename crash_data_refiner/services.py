"""Compatibility facade for the shared service layer.

This module keeps the historical import surface stable while delegating the
actual work to focused helper modules.
"""
from __future__ import annotations

from .labeling import (
    VALID_LABEL_ORDERS,
    detect_label_order,
    order_and_number_rows,
    resolve_label_order,
)
from .output_paths import (
    coordinate_review_output_path,
    invalid_output_path,
    kmz_output_path,
    pdf_output_path,
    refined_output_path,
    rejected_review_output_path,
    summary_output_path,
)
from .pipeline import (
    RelabelResult,
    RefinementResult,
    build_output_headers,
    load_headers_and_guess_columns,
    relabel_refined_outputs,
    run_pdf_report,
    run_refinement_pipeline,
)

__all__ = [
    "VALID_LABEL_ORDERS",
    "RelabelResult",
    "RefinementResult",
    "build_output_headers",
    "coordinate_review_output_path",
    "detect_label_order",
    "invalid_output_path",
    "kmz_output_path",
    "load_headers_and_guess_columns",
    "order_and_number_rows",
    "pdf_output_path",
    "refined_output_path",
    "rejected_review_output_path",
    "relabel_refined_outputs",
    "resolve_label_order",
    "run_pdf_report",
    "run_refinement_pipeline",
    "summary_output_path",
]
