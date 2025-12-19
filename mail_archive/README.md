# Enterprise Mail Archive Backend

Production-ready Django service that ingests every corporate email (SMTP journal / IMAP), stores RFC822 payloads immutably, indexes metadata in MySQL + Elasticsearch, and exposes RBAC/MFA-guarded discovery + export APIs. Designed for ~100k users / 1M mails per day.

## Architecture Overview
- **Django API** (Gunicorn/ASGI) with apps `accounts`, `archive`, `searchapp`, `audit`, `core`.
- **MySQL 8** primary + replica for metadata, RBAC, audit ledger (hash chained).
- **Elasticsearch 8** for subject/body/attachment keyword search.
- **Redis 6** for cache, JWT revocation, Celery broker/result backend.
- **Celery workers** for asynchronous export packaging and ingestion fan-out.
- **Object storage** (S3 or MinIO) with Object Lock COMPLIANCE mode; all EML/attachment blobs written once and verified by SHA256 hashes.
- **RBAC + MFA**: JWT based auth with role permissions, mailbox/time scoping, and TOTP step-up for legal/compliance actions.

## System Requirements
| Component | Min Spec |
|-----------|----------|
| Python | 3.11+
| MySQL | 8.0 (GTID + binlog retention >= 365d)
| Redis | 6.2+
| Elasticsearch | 8.13+ (6 primary shards, 1 replica recommended)
| Object Storage | S3-compatible with versioning + object lock (e.g., MinIO, AWS S3)

## Configuration
Copy `.env.example` to `.env` (or export variables another way) and adjust secrets:

```bash
cp .env.example .env
```

Key variables:
- `DJANGO_SECRET_KEY`, `JWT_SIGNING_KEY`: rotate regularly.
- `DB_*`: point to production MySQL.
- `REDIS_URL`: same endpoint for cache + Celery.
- `S3_*`: endpoint/credentials + `S3_LOCK_DAYS` to satisfy retention.
- `ES_HOSTS`: comma-separated Elasticsearch nodes.
- `MFA_SESSION_MINUTES`: lifespan of TOTP-verified sessions.

## Initial Setup
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 manage.py migrate
python3 manage.py createsuperuser
python3 manage.py loaddata fixtures/permissions.json  # optional seed
```

### Database Hardening
1. Create dedicated MySQL user (`mail_archive`) with least privilege.
2. Enable binary logging + row-based replication; enforce `innodb_flush_log_at_trx_commit=1`.
3. Apply migration scripts (generated under `accounts/migrations`, `archive/migrations`, `audit/migrations`).

### Elasticsearch Index
Create the production index with analyzers before serving traffic:
```bash
curl -u elastic:password -X PUT "$ES_URL/emails_archive" \
  -H 'Content-Type: application/json' \
  -d @infrastructure/es/emails_archive.json
```
(`infrastructure/es/emails_archive.json` should contain the mapping shared in the architecture doc.)

### Object Storage
- Create bucket `mail-archive` (or change via `S3_BUCKET`).
- Enable versioning + Object Lock, COMPLIANCE mode, default retention >= `S3_LOCK_DAYS`.
- Ensure server-side encryption (AES-256 or SSE-KMS).

## Running the Stack
```bash
# API
python3 manage.py runserver 0.0.0.0:8000
# Celery worker and beat (for export jobs, retries, scheduled hash audits)
celery -A mail_archive worker -l info
celery -A mail_archive beat -l info
```
For production, run via systemd or containers (e.g., Gunicorn + uvicorn workers, Celery in separate deployment, Redis/ES/MySQL as managed services).

### Docker / Compose
Build images and launch the full dependency stack (MySQL, Redis, Elasticsearch, MinIO) with a single command:
```bash
docker compose up --build
```
Services:
- `web`: Gunicorn-served Django API (auto-runs migrations + deploy checks via `scripts/entrypoint.sh`).
- `celery_worker` / `celery_beat`: background job processors.
- `db`, `redis`, `elasticsearch`, `minio`: stateful dependencies with persistent named volumes.
Override scaling via `docker compose up --scale celery_worker=3`.

## Journaling / Ingestion
- Configure SMTP journaling/IMAP forwarders to POST to `POST /api/v1/archive/ingest/` with mutual TLS + service token with `ARCHIVE_STORE` permission.
- Payloads must contain base64 EML, participants array, attachment metadata; see `archive/serializers.py` for schema.
- Ingestion workers compute SHA256, push to S3, write MySQL row, index ES, and append audit log.

## Search & Export API
- `POST /api/v1/search/emails/` (MFA required) supports department/mailbox/time/keyword filters with pagination.
- `GET /api/v1/archive/emails/<id>/` returns metadata + presigned download URL.
- `POST /api/v1/archive/exports/` queues Celery job to build TAR.GZ in S3; download via presigned URL in UI/tooling.

## Testing & Quality
```bash
# Unit tests
python3 manage.py test
# Django checks
python3 manage.py check --deploy
```
Add integration tests (MySQL/ES/S3) via CI before promotion.

## Observability & Ops
- Logs: structured JSON via STDOUT; include `X-Request-ID` header for traceability.
- Metrics: expose Prometheus metrics via Django middleware or sidecar (not included).
- Audit: `audit_auditlog` table holds immutable ledger; periodically export hashes to external notary.
- Backups: nightly MySQL physical backups + binlog streaming; hourly ES snapshots; S3 cross-region replication.

## Security Checklist
1. Enforce HTTPS + mTLS for ingestion endpoints.
2. Rate-limit login/search/export via reverse proxy + Redis counters.
3. Require MFA (TOTP) for admin/legal roles (`MFA_SETTINGS`).
4. Rotate JWT signing keys and store in HSM/KMS.
5. Deny direct DB writes to `archived_emails`/`audit_logs` except via application.
6. Run `python3 manage.py check --deploy` in CI to verify security-related settings.

## Deployment to Production
1. Build container image (`docker build -t registry/mail-archive:TAG .`); image already bundles Gunicorn + entrypoint migrations.
2. Apply migrations (`python3 manage.py migrate`) during maintenance window.
3. Warm up Elasticsearch index by replaying recent emails or using snapshot restore.
4. Scale Django pods (e.g., 4–8 replicas) behind load balancer; scale Celery workers per throughput.
5. Monitor ingestion lag, ES latency, export job queue depth, and audit hash anomalies.

## Continuous Integration
`.github/workflows/ci.yml` runs on every push/PR to `main`/`master`:
- Spins up MySQL 8, Redis 7, Elasticsearch 8.13, and MinIO containers.
- Installs Python dependencies, waits for DB readiness, runs `python manage.py migrate` and `python manage.py test`.
Extend the workflow with pytest/coverage or add integration steps (e.g., `curl` to seed Elasticsearch) as needed for your org.

## GitHub Workflow
```bash
git status
git add .
git commit -m "feat: bootstrap enterprise mail archive backend"
git remote add origin git@github.com:<org>/<repo>.git  # first time only
git push -u origin main
```
Replace `<org>/<repo>` with your repository and ensure deploy keys/SSH agents are configured.
