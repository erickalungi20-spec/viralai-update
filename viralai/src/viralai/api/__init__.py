"""
Phase 8 API Layer: FastAPI application exposing Analysis, Plugin, Knowledge Base, AI,
Simulation, and Reporting operations over HTTP, with auto-generated OpenAPI docs.
"""

from viralai.api.app import app

__all__ = ["app"]
