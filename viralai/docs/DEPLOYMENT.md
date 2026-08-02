# Deployment

## Current deployment tier

The supplied `compose.yaml` runs ViralAI as a **single-node research deployment**. It
uses a named Docker volume for the existing file-backed API state, a non-root process,
a read-only application filesystem, a required encryption key, and `/health` plus
`/ready` probes.

It is appropriate for one trusted research team on one host. It is not a horizontally
scaled or multi-tenant deployment: the Event Bus, Task Scheduler, research graph, and
application stores remain process-local or file-backed. Those are the next Phase 11
migrations described in the ADR review.

## Run locally or on one server

1. Copy `.env.example` to `.env`.
2. Generate a Fernet key using the command in that file, then set
   `VIRALAI_ENCRYPTION_KEY`. In a cloud deployment, inject this value from that
   provider's secret manager rather than storing it in `.env`.
3. Run `docker compose up --build -d`.
4. Verify `http://localhost:8000/ready` returns `{"status":"ready",...}`.
5. Bootstrap an administrator key:

   ```bash
   docker compose exec api viralai issue-api-key --label initial-admin --role admin
   ```

   Record the raw key immediately; it is shown only once.

## Before exposing it publicly

Put the API behind TLS termination (a managed load balancer or reverse proxy), restrict
network access to trusted users, configure backups for the `viralai-data` volume, and
use a managed secret store. Do not treat this tier as suitable for regulated or
patient-adjacent data.

## Dataset acquisition and training

ViralAI now supports explicit dataset registration and training via the AI API.
Use `POST /ai/datasets` with a researcher API key to register a training dataset with
labeled mutation examples and optional validation examples. Then train a model from
that dataset with `POST /ai/datasets/{name}/{version}/train`.

For real viral genomics data, obtain reference genomes and sample sequences from
verifiable sources such as NCBI GenBank/RefSeq or GISAID. Do not commit raw sequence
FASTA or patient-derived samples into source control. Plugins that require a virus
reference genome should load it from local plugin data paths, as described by the
plugin's own `README.md` and the repository's plugin development standard.

Recommended sources:

- NCBI GenBank / RefSeq accession pages (e.g. `efetch.fcgi` for FASTA retrieval)
- GISAID for curated pathogen sequence collections when your project has access
- Local plugin reference directories under `plugins/<name>/data/reference`

If you are using the local Docker deployment, mount a persistent volume for
`/var/lib/viralai` and keep `VIRALAI_ENCRYPTION_KEY` in the hosted secret manager.

## Planned durable backend migration

The next deployment increment will introduce PostgreSQL for API state, Redis plus
Celery for durable background work, and Neo4j for the persistent Research Graph. It
will include migrations, readiness checks for each service, and a provider-specific KMS
adapter once the hosting provider is selected.
