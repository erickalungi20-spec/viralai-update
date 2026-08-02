"""
Common Services Layer.

Logging, configuration, error handling, file I/O, sequence validation, and ID generation
live here so no engine or plugin ever reimplements them. Import from here, not around it.
"""

from viralai.common.errors import (
    ConfigurationError,
    PluginError,
    ValidationError,
    ViralAIError,
)
from viralai.common.ids import new_id
from viralai.common.logging import get_logger
from viralai.common.validation import is_valid_nucleotide_sequence

__all__ = [
    "ViralAIError",
    "ConfigurationError",
    "ValidationError",
    "PluginError",
    "new_id",
    "get_logger",
    "is_valid_nucleotide_sequence",
]
