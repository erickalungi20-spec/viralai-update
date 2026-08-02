"""
Phase 9 Security & Responsible AI. Framework-agnostic security primitives (no FastAPI
dependency here -- see viralai.api.auth for the FastAPI wiring):

- roles.py: Role (VIEWER/RESEARCHER/ADMIN) ordering
- api_keys.py: APIKeyStore -- hashed API key issuance/verification/revocation
- encryption.py: Fernet-based encryption at rest for file-backed stores
- audit.py: append-only AuditLogger
- plugin_scanner.py: static AST-based plugin code security scan
- responsible_ai.py: ResponsibleAIEnvelope -- mechanically-enforced AI/simulation
  response disclosure
"""

from viralai.security.api_keys import APIKeyRecord, APIKeyStore
from viralai.security.audit import AuditEntry, AuditLogger
from viralai.security.encryption import decrypt_text, encrypt_text, read_encrypted, write_encrypted
from viralai.security.plugin_scanner import (
    SecurityFinding,
    is_clean,
    scan_plugin_directory,
    scan_plugin_source,
)
from viralai.security.responsible_ai import (
    ResponsibleAIEnvelope,
    wrap_ai_result,
    wrap_simulation_result,
)
from viralai.security.roles import Role

__all__ = [
    "Role",
    "APIKeyStore",
    "APIKeyRecord",
    "encrypt_text",
    "decrypt_text",
    "write_encrypted",
    "read_encrypted",
    "AuditLogger",
    "AuditEntry",
    "scan_plugin_source",
    "scan_plugin_directory",
    "is_clean",
    "SecurityFinding",
    "ResponsibleAIEnvelope",
    "wrap_ai_result",
    "wrap_simulation_result",
]
