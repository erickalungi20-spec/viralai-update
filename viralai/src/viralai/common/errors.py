"""
Shared exception hierarchy.

Blueprint Ch.15.5 requires errors to be classified (configuration, validation, plugin,
computational, AI model, export) so the Core Engine can respond appropriately rather than
treating every failure identically. Start narrow; widen as real engines surface new
failure modes — do not pre-invent categories nobody has hit yet.
"""

from __future__ import annotations


class ViralAIError(Exception):
    """Base class for all ViralAI-raised exceptions. Never raise this directly."""


class ConfigurationError(ViralAIError):
    """Raised when a configuration file or object is missing, malformed, or inconsistent."""


class ValidationError(ViralAIError):
    """Raised when input data (a sequence, a dataset, an IDM object) fails validation."""


class PluginError(ViralAIError):
    """Raised when a plugin fails to load, validate, or register."""


class WorkflowError(ViralAIError):
    """Raised when a workflow step fails in a way the Core Engine cannot recover from."""
