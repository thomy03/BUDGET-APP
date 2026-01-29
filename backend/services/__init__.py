"""
Budget Famille v4.2 - Services Index
Architecture Consolidation

This module provides the service registry for the Budget Famille application.
Services are organized into primary (active) and deprecated (legacy) categories.

PRIMARY SERVICES (Use these):
==============================
- unified_ml_tagging_service: Main ML tagging orchestrator
- ml_tagging_engine: Core ML pattern matching engine
- ml_feedback_learning: Feedback-based learning system
- intelligent_tag_service: Web research integration
- expense_classification: FIXED/VARIABLE classification

DEPRECATED SERVICES (Backward compatibility only):
==================================================
- tag_automation: Use unified_ml_tagging_service instead
- tag_suggestion_service: Use intelligent_tag_service instead
- enhanced_auto_tagging_service: Use unified_ml_tagging_service instead

Author: Claude Code - Architecture Consolidation v4.2
Date: 2026-01-26
"""

import logging
import warnings

logger = logging.getLogger(__name__)

# =============================================================================
# PRIMARY SERVICES - Active and Maintained
# =============================================================================

def get_unified_ml_tagging_service(db_session):
    """
    Get the primary unified ML tagging service.
    This is the RECOMMENDED service for all tag suggestion operations.
    """
    from services.unified_ml_tagging_service import get_unified_ml_tagging_service as _get_service
    return _get_service(db_session)


def get_ml_tagging_engine(db_session):
    """Get the ML tagging engine for pattern-based suggestions."""
    from services.ml_tagging_engine import get_ml_tagging_engine as _get_engine
    return _get_engine(db_session)


def get_intelligent_tag_service(db_session):
    """Get the intelligent tag service with web research capabilities."""
    from services.intelligent_tag_service import get_intelligent_tag_service as _get_service
    return _get_service(db_session)


def get_expense_classification_service(db_session):
    """Get the expense classification service for FIXED/VARIABLE classification."""
    from services.expense_classification import get_expense_classification_service as _get_service
    return _get_service(db_session)


# =============================================================================
# DEPRECATED SERVICES - For backward compatibility only
# =============================================================================

def get_tag_automation_service(db_session):
    """DEPRECATED: Use get_unified_ml_tagging_service() instead."""
    warnings.warn(
        "get_tag_automation_service() is deprecated. Use get_unified_ml_tagging_service() instead.",
        DeprecationWarning, stacklevel=2
    )
    from services.tag_automation import get_tag_automation_service as _get_service
    return _get_service(db_session)


def get_tag_suggestion_service(db_session):
    """DEPRECATED: Use get_intelligent_tag_service() instead."""
    warnings.warn(
        "get_tag_suggestion_service() is deprecated. Use get_intelligent_tag_service() instead.",
        DeprecationWarning, stacklevel=2
    )
    from services.tag_suggestion_service import get_tag_suggestion_service as _get_service
    return _get_service(db_session)


# =============================================================================
# SERVICE REGISTRY
# =============================================================================

SERVICE_REGISTRY = {
    "unified_ml_tagging": {"module": "services.unified_ml_tagging_service", "status": "active"},
    "ml_tagging_engine": {"module": "services.ml_tagging_engine", "status": "active"},
    "intelligent_tag": {"module": "services.intelligent_tag_service", "status": "active"},
    "ml_feedback_learning": {"module": "services.ml_feedback_learning", "status": "active"},
    "expense_classification": {"module": "services.expense_classification", "status": "active"},
    "tag_automation": {"module": "services.tag_automation", "status": "deprecated", "replacement": "unified_ml_tagging"},
    "tag_suggestion": {"module": "services.tag_suggestion_service", "status": "deprecated", "replacement": "intelligent_tag"},
}


def list_services(include_deprecated: bool = False) -> dict:
    """List all available services and their status."""
    if include_deprecated:
        return SERVICE_REGISTRY
    return {k: v for k, v in SERVICE_REGISTRY.items() if v["status"] == "active"}


__all__ = [
    "get_unified_ml_tagging_service",
    "get_ml_tagging_engine",
    "get_intelligent_tag_service",
    "get_expense_classification_service",
    "get_tag_automation_service",
    "get_tag_suggestion_service",
    "SERVICE_REGISTRY",
    "list_services"
]
