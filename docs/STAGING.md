# Staging deployment

## Current preparation

Business data was cleared on request. Kept: ADMIN accounts, asset types, master
categories, location hierarchy (and location photos), warehouse configuration.
Database and uploads backup: `backups/20261007T064020949382Z/`.
Backup contains sensitive data; keep it outside Git with restricted access.
Schema revision: `0018`. PostgreSQL nullable legacy identity columns now match SQLite;
new API writes still require Model and S/N. Removed asset purchase_date, warranty_expiry, vendor,
cost, notes and asset_types.track_serial. Receipt source remains in inventory
transactions; repair cost/vendor remain in maintenance. No historical tables were
dropped: API, search, migration, or audit references still exist.

## Deploy on the staging host

Requires Docker Engine with Compose, a domain and a host reverse proxy terminating
HTTPS. These commands create isolated `helpdesk-stg` volumes; do not reuse production
volumes. This workspace has no Docker executable, so Docker image builds and Compose startup must be verified on that host before staging is accepted.
Native PostgreSQL 16 migrations, configuration import and backend integration tests
were verified in this workspace.

1. Copy `.env.staging.example` to `.env.staging` (ignored by Git), fill two independently
   generated secrets (`openssl rand -hex 32`) and the actual HTTPS domain.
2. Run `python3 scripts/staging-preflight.py .env.staging`.
3. Run `docker compose --env-file .env.staging -p helpdesk-stg up -d --build`.
4. Wait for healthy services: `docker compose --env-file .env.staging -p helpdesk-stg ps`.
5. Import the prepared private configuration bundle to retain existing ADMIN accounts:

   ```sh
   docker compose --env-file .env.staging -p helpdesk-stg cp backups/staging-config.json backend:/tmp/staging-config.json
   docker compose --env-file .env.staging -p helpdesk-stg exec backend python -m app.staging_config import /tmp/staging-config.json
   docker compose --env-file .env.staging -p helpdesk-stg exec backend rm /tmp/staging-config.json
   docker compose --env-file .env.staging -p helpdesk-stg exec backend alembic check
   ```

   Import only works when no target accounts/business data exist and migrations match.
   For a completely independent staging admin instead, skip import and run
   `docker compose --env-file .env.staging -p helpdesk-stg exec backend python -m app.bootstrap`.
   Do not run demo seed. Retained location photos, if any, must be copied separately
   from the backup's `uploads/location-photos` into `/app/uploads/location-photos`.
6. Configure host HTTPS proxy to `http://127.0.0.1:8081` (or configured HTTP_PORT).
   Database and API have no published ports. Session cookies require HTTPS.
7. Check `https://<staging-domain>/api/health`, login with ADMIN, empty dashboard,
   create/issue/return an asset with a signed document, import/export IPs, map ports,
   verify physical graph, upload/download files and verify viewer cannot write.
   Browser network/API errors must be absent. Check backend logs without exporting secrets.

## Back up and restore staging

Before upgrades, stop writes: `docker compose --env-file .env.staging -p helpdesk-stg stop frontend backend`.
Keep the db service running. Export a custom-format dump with the database container:

```sh
mkdir -p backups
chmod 700 backups
docker compose --env-file .env.staging -p helpdesk-stg exec -T db pg_dump -U helpdesk -d helpdesk -Fc > backups/staging.dump
```

Back up the attachments volume too before upgrading. Docker named volumes are
prefixed with `helpdesk-stg_`; archive `helpdesk-stg_attachments` while writes are
stopped. Keep dump and uploads together, with the deployed Git revision.
Restore with writes stopped, into the corresponding schema/code revision:

```sh
docker compose --env-file .env.staging -p helpdesk-stg exec -T db pg_restore -U helpdesk -d helpdesk --clean --if-exists --exit-on-error --single-transaction < backups/staging.dump
```

Restore attachments from the same backup, then start backend/frontend and verify health.
Never use `down -v` for an upgrade: that removes database and files.

## Repeat local business cleanup

Stop the API first; commands run from `backend/`:

```sh
../.venv/bin/python -m app.staging_reset
../.venv/bin/python -m app.staging_reset --apply --backup-dir ../backups
```

Preview does not mutate. Apply refuses without an active ADMIN, backs up DB and
uploads before one database transaction, retains configuration and location images,
deletes non-ADMIN users and business uploads. PostgreSQL apply requires `pg_dump`
on the machine running the command. Do not run against a live writable service.
The bundled SQLite backup predates schema cleanup: restore it together with the
pre-cleanup code revision. Alembic downgrade restores column definitions, not deleted values.

Runtime image dependencies are pinned in `backend/requirements.lock`; developer
test tools are in `requirements-dev.txt`. Update the lock and rerun checks when
changing dependencies. The runtime lock was installed and smoke-tested in a clean
Python 3.12 environment, without pytest/httpx.
