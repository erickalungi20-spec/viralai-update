# ADR-012: Phase 9 security scope -- API keys not OAuth2/JWT, pattern-scan not sandboxing

## Status
Accepted

## Context
Blueprint Ch.35 specifies Security Architecture (authentication, authorization,
encryption at rest, audit logging, plugin security) and Ch.36 specifies a Responsible AI
Framework. The Commercial Development Workflow's Phase 9 line item names OAuth2/JWT,
RBAC, encryption, audit logging, and plugin security review.

## Decisions

1. **API keys, not OAuth2/JWT.** A research platform's real access pattern is lab
   members and service-to-service calls (scripts, CI, the CLI), not end-user browser
   login sessions -- API keys are the right-sized tool, the same choice GitHub, Stripe,
   and most scientific/research APIs make for this exact usage pattern. OAuth2/JWT solve
   a different problem (delegated authorization, session expiry, third-party login) that
   doesn't exist here yet. This is a real, considered choice, not a shortcut -- adding
   JWT later for a genuine session-based use case is straightforward without needing to
   rearchitect the API key system, since they can coexist.

2. **API keys hashed with SHA-256, not bcrypt/argon2.** Stated explicitly in
   `security/api_keys.py`'s docstring: bcrypt-family algorithms are intentionally slow to
   resist brute-forcing *low-entropy human passwords*. API keys here are
   `secrets.token_urlsafe(32)` (256 bits of entropy) -- already infeasible to brute-force,
   so a slow hash only costs legitimate verification performance for zero security
   benefit. This is the same reasoning major API providers use for their own tokens.

3. **Reads open, writes gated.** `GET` endpoints (list plugins, query knowledge, get
   model/experiment records) require no authentication. `POST` endpoints that write
   curated data or consume real compute (knowledge writes, AI predictions, simulation
   runs) require a RESEARCHER-role API key at minimum; API key management itself
   requires ADMIN. This matches how most public-data-with-gated-contribution research
   platforms actually operate, and keeps the blast radius of Phase 9's changes contained
   to the endpoints that actually need protecting.

4. **No HTTP endpoint issues the first (bootstrap) API key.** Deliberately -- an
   unauthenticated "create an admin key" endpoint would be a standing security hole. The
   first key is issued via `viralai issue-api-key` (CLI, direct filesystem access, no
   HTTP/auth involved), the same bootstrap pattern as `django-admin createsuperuser`.
   Once one ADMIN key exists, further keys can be issued through the authenticated
   `/admin/api-keys` endpoint.

5. **Encryption at rest is a real, working primitive with an honestly-scoped key
   management gap.** `security/encryption.py` provides real Fernet (AES-128-CBC + HMAC)
   encryption, fully tested. But the key itself comes from an environment variable with
   an ephemeral-key fallback for convenience in dev/test -- this is explicitly NOT a
   production key management solution. Integrating a real secret manager (AWS KMS,
   HashiCorp Vault) is separate infrastructure work not undertaken here. The module's own
   docstring says so; this isn't a gap discovered later, it's disclosed at the point of
   design.

6. **The plugin security scanner is static pattern-matching, not sandboxed execution
   analysis.** It catches `eval`/`exec`/dangerous imports via AST inspection -- real
   protection against careless or lazy violations of the "plugins provide data, not
   logic" contract (Ch.5.10), but a determined adversary can trivially evade pattern
   matching (e.g. `getattr(__builtins__, "e"+"val")`). This is explicitly not a claim of
   adversarial security; Ch.16.5's human scientific review and digital signature
   validation remain the actual defense against a deliberately malicious plugin author.
   Building a real sandboxed execution analyzer is a substantial, separate undertaking.

7. **Responsible AI disclosure is now enforced at the API response schema level, not
   just in generated text.** `ResponsibleAIEnvelope` is a required wrapper -- there is no
   `pydantic` construction path that produces an AI or simulation API response without
   `disclosure`/`limitations` fields present. This closes the gap between "Phase 4's
   reasoning engine generates disclaimer text" (which a caller could theoretically ignore
   or a future code change could drop) and "the API response literally cannot omit it."

## Consequences
- **Positive:** every claim in this phase (hashed key auth, RBAC, real encryption, real
  audit trail, real static plugin scanning, structurally-enforced AI disclosure) is fully
  implemented and tested against actual endpoints, not documented as a policy.
- **Positive:** the bootstrap problem (how does the first admin key get created) has a
  real, tested answer, not an unaddressed gap.
- **Negative:** no OAuth2/browser-session support exists -- a future web frontend with
  human user login will need that layer built separately.
- **Negative:** encryption-at-rest's key management is dev/test-appropriate only; a real
  production deployment handling sensitive data needs a real KMS integration before this
  should be trusted for regulated data.
- **Negative:** the plugin scanner gives false confidence if mistaken for adversarial
  security -- it is not, and this ADR (and the module's own docstring) says so explicitly
  to prevent that misunderstanding.

## Trigger for revisiting
- OAuth2/JWT: the first time a real end-user-facing frontend needs browser session login.
- KMS integration: before handling any data with real regulatory sensitivity (e.g. if
  BREATHE-TB-style patient-adjacent data ever entered this platform).
- Sandboxed plugin analysis: if the platform ever accepts plugins from untrusted
  third-party contributors at scale, where human review can't be the only gate.
