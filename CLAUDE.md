No `--single-directory`, no `--sync`/`--monitor`, no `--dry-run`. On a `confdir` with no existing refresh token this
drives the interactive OAuth flow and persists the token with no file listing or transfer at all (one caveat: the
sync engine's own `initialise()` still makes two small Graph metadata calls — drive details and root details — not
a bulk download). `exit(0)` immediately after, so phases/upload never run in this mode. This replaced the earlier
design, which scoped a real `--sync --download-only` pass to a dedicated empty remote folder
(`FolderPaths.SHAREPOINT_AUTH_PATH`, `justifactu/_auth_sync`) — that folder/path constant no longer exists (see
above). **Known limitation of the new approach, intentionally accepted since `--auth` is documented as a one-time,
per-new-system action:** re-running `--auth` after a token already exists for that `confdir` now exits non-zero
("missing switches") instead of the old design's harmless no-op, since the fast-fail path only triggers when a
token is already present.

`subprocess.CalledProcessError` and `FileNotFoundError` are both normalized into `MainCriticalError` in both
`run_onedrive_sync` and `run_onedrive_auth`, caught by `main()`'s existing exception handling — the upload call is
only ever reached if every prior step succeeded, so SharePoint is never mutated on a failed run.

**What's still only in `service/onedrive/conf/config`, with no CLI equivalent at all** (confirmed against the
client's own docs, not assumed): `drive_id`, `sync_dir_permissions`, `sync_file_permissions`. `drive_id` especially
is why this file can't be eliminated outright — there's no `--drive-id` flag, though `onedrive --get-sharepoint-
drive-id` can *look one up* without a sync (a one-off Graph query, not a config substitute). (`sync_dir` is still
physically present in the file but is dead weight — `--syncdir` on every call overrides it regardless of what's
written there.) Moving `drive_id` to be generated at runtime from Vault (`SecretNames.DRIVE_ID`, already mapped in
`vault.py`'s `_SECRET_MAP`) rather than hand-maintained in a git-tracked file is a discussed-but-not-yet-implemented
direction — don't assume it's done.

The deeper design rationale and decision log for this architecture live in the `docs` git submodule
(`ICIQ-DMP/justifactu-docs`, `docs/explanation/onedrive_sync_and_orchestration.md`) — but several decisions there
are now superseded by what's actually implemented (D6's "compile from source" was amended to installing via the
OBS apt repo; D21's "remove `download_only`/keep `cleanup_local_files` in config" is now "remove both from config,
make both per-call CLI flags instead"; the `--auth` design has since changed again per `2ea3480` above). Treat the
doc as historical context, not a live spec, until it's updated to match.

### Jenkins agent (`service/agent/`)

A separate Docker image/compose stack from the app's own — `service/agent/dockerfile/Dockerfile` (built from
`jenkins/ssh-agent`, installs Python + the `onedrive` binary via `install-onedrive-apt.sh`), `service/agent/
entrypoint/entrypoint.sh`, and `service/agent/compose.yml` (volumes for `onedrive/conf`+`onedrive/data`, Vault
AppRole secrets, an SSH-key bind mount). `make prodbuild`/`make prodrun` drive this compose file specifically.

The agent currently joins an **external Docker network owned by a different project** (`justicier_justicier_net`,
per the `networks:` TODO in `compose.yml`) — Jenkins' controller currently lives inside that other project's own
compose stack, not an independent one yet. Don't rename/repoint that network reference without first confirming
Jenkins has actually been given its own stack — doing so prematurely points at a network that doesn't exist yet and
breaks the agent's startup.

`Jenkinsfile` (repo root) is explicitly marked **draft, not wired into any real Jenkins job** — currently a
single-stage pipeline (`make install && make run CMD="--dry-run"`, with a TODO to drop `--dry-run` once ready for
real production runs), no `checkout scm` stage, no cron trigger, no build timeout. The `OD_CONF` environment
variable it still declares is dead (same reason as above — `confdir` comes from a CLI arg now, not an env var) and
the `aborted` post-block's message still references a 20h-timeout/multi-night-convergence story that no longer
applies to this architecture. Don't treat this file as a finished, production-ready pipeline.

### Module layout (only the non-obvious relationships)

- `arguments.py` → `defines.py`: CLI flags validate against enums defined in `defines.py` (`Phase`, `InputLocation`)
  via small `parse_*` functions, each raising a specific `custom_except.py` exception on invalid input.
  `parse_directory` (distinct from the now-orphaned `parse_input_location`) auto-creates a missing directory rather
  than erroring, used by every OneDrive-path argument.
- `onedrive_sync.py`: `_base_onedrive_args` builds the flags common to **sync** invocations only (`--confdir`,
  `--single-directory`, `--syncdir`, `--verbose`); `run_onedrive_sync` adds `--sync`/`--{direction}-only` plus the
  conditional flags on top. `run_onedrive_auth` is separate and does **not** use `_base_onedrive_args` — it builds
  its own minimal, `--single-directory`-free argument list (see the `--auth` bootstrap above).
- `logger.py`: a `extra={"qa_report": True}` tag on any `log.*()` call routes that line into a separate QA report
  file (mailed via `mail.py::send_qa_report_mail`), independent of the main run log.
- `secret.py` / `vault.py`: secrets resolve through a fallback chain (mounted Docker secret → repo `secrets/` file →
  env var → HashiCorp Vault), so the same code runs unmodified in local dev and deployed containers. `vault.py`'s
  `_SECRET_MAP` is the authoritative list of which `SecretNames` values actually have a Vault path configured.