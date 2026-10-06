# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

All development commands are defined once in the `Makefile` and reused by pre-commit hooks and CI — treat the
`Makefile` as the source of truth, not these as a separate reference.

    make dev                        # install runtime + dev deps, install git hooks (pre-commit/commit-msg/pre-push)
    make lint                       # ruff check . && mypy src   (mypy runs in strict mode — see pyproject.toml)
    make fmt                        # black src tests && ruff check --fix .
    make test                       # PYTHONPATH=src pytest -s -v   (testpaths = tests, per pyproject.toml)
    make run CMD="--phase 1"        # python -m justifactu <CMD>; CMD defaults to --help if omitted

Run a single test file or test function directly with pytest (bypassing the Makefile), same env var the `test`
target uses:

    PYTHONPATH=src pytest tests/test_bills.py -v
    PYTHONPATH=src pytest tests/test_bills.py::test_parse_bill_filename_valid -v

Docker (app image): `make docker-build` / `make docker-push` (pushes `davidromeroiciq/justifactu:latest`). Root
`compose.yml` runs the app alongside a long-running `onedrive --monitor` sidecar for local dev — this is the *old*
sync architecture (see "OneDrive sync" below), kept for local dev convenience only, not the production design.

Docker (Jenkins agent image): `make prodbuild` / `make prodrun` build and start the agent defined in
`service/agent/`, via `service/agent/compose.yml` — a separate image/compose file from the app's own, carrying the
`onedrive` binary and SSH-agent setup for Jenkins to drive builds on. See "Jenkins agent" below.

Git commit messages must follow Conventional Commits (enforced by `conventional-pre-commit` in
`.pre-commit-config.yaml`); a license header (`LICENSE_HEADER`) is auto-inserted into `.py` files before formatting.

All CLI flags use hyphens (`--onedrive-data-folder`, `--sharepoint-sync-folder`), not underscores — argparse maps
both the same way internally (`args.onedrive_data_folder`), but only the hyphenated spelling is registered, so the
underscored form will not be recognized on the command line.

## Architecture

### Two independent entry paths, not one

`src/justifactu/__main__.py` is the actual program entry point (`python -m justifactu`) — `main.py`'s own
`if __name__ == "__main__"` guard is dead code, since nothing runs `main.py` directly. `__main__.py` parses CLI
args once and branches:

- `--phase` **absent** → `main()` (`main.py`) runs the full production pipeline: `run_all_phases()` (`process.py`),
  bracketed by an OneDrive download/upload sync (see below).
- `--phase` **present** (`1`, `2`, or `3` — see `Phase` enum in `defines.py`) → `run_phase()` (`process.py`) runs
  *only* that one stage, via `process.py::_build_phase_map`'s dispatch dict. This path exists to test one stage in
  isolation without touching the rest of the pipeline, and does **not** trigger an OneDrive sync.

`run_phase()` and `run_all_phases()` share one dispatch table, so there's a single place defining what each phase
does — `run_all_phases` loops `FULL_RUN_PHASES = (Phase.PHASE_1, Phase.PHASE_2)` against the same map `run_phase`
looks a single key up in. Phase 3 (`mock_phase3`) is reachable via `--phase 3` for testing but deliberately excluded
from `FULL_RUN_PHASES`, since it's a placeholder — don't add it to the full-run tuple until it's actually implemented.

`__main__.py` passes `args.runtime_location` (not `args.input_location`, which never existed as a CLI attribute)
to `run_phase` — a prior mismatch between this call and what `arguments.py` actually produces was fixed in commit
`aa7dd21`.

### SAP ID is the correlation key between bills and payments

A bill and a payment are matched purely by a shared `SAP_ID` (`SAP_ID.py`) — a 4-digit year + 6-digit sequence,
parsed via regex from two different sources:

- **Bills** arrive already named `F <sap_id>` (`bills.py::parse_bill_filename`).
- **Payments** start as bank-statement PDFs with arbitrary filenames; `payments.py::rename_payments` extracts the
  SAP ID from the PDF's *content* (`bills.py::parse_sap_id_from_bill`) and renames the file to `{sap_id}-P.pdf`
  **on disk**, in place.

`process.py::merge_bills_and_payments` matches bills against an index of already-renamed payment files, merges each
matched pair into one PDF under `{year}_FACTURA+PAGAMENT/{sap_id}_F_P.pdf`, then (`cleanup_processed_files`) renames
the payment with a `_merged` suffix and deletes the bill. An unmatched bill isn't necessarily an error — it's
routed to a separate, not-yet-implemented "own treatment" flow (`mock_phase3`).

### SharePoint/Graph API code: removed, with one orphan left behind

`sharepoint.py` and `tests/test_sharepoint.py` are **gone entirely** (commit `ae2474f`) — OneDrive-for-Linux replaced
every direct Microsoft Graph file-transfer call, and the module had no production importer left (only its own
tests used it). Along with it, `defines.py::FolderPaths` lost its four dead members (`SHAREPOINT_INPUT_PATH`,
`SHAREPOINT_OUTPUT_PATH`, `SHAREPOINT_BILLS_PATH`, `SHAREPOINT_PAYMENTS_PATH`), and `custom_except.py` lost two
never-raised exceptions (`SkippedPdfRenamingInvalidSapId`, `UnexpectedRenamingError`), and `logger.py` lost two
never-called functions (`obfuscate_text`, `process_log_flags`).

**`token_manager.py` was not removed, and is now fully orphaned** — its only importer was `sharepoint.py`. Nothing
in `src/` or `tests/` references it anymore. Treat it as the next thing to delete, not as still-needed.

Two smaller known-dead leftovers from the same sweep, also not yet removed: `arguments.py::parse_input_location`
(superseded by `parse_directory`'s auto-create behavior everywhere; only its own tests call it) and
`filesystem.py::move_file` (tested in isolation, but no production code path calls it — `main.py`/`process.py`/
`payments.py` use `copy_file`/`change_file_name` instead).

`FolderPaths` (`defines.py`) is now fully live top to bottom — `SHAREPOINT_SYNC_FOLDER` and `SHAREPOINT_AUTH_PATH`
feed real CLI defaults consumed by every OneDrive sync call, and nothing else remains on the enum. `InputLocation`
and the `-l/--location` CLI flag are likewise in active use — `main.py`'s one-time `--auth` bootstrap is gated on
`args.location == InputLocation.SHAREPOINT` (see below).

`--download-input` (`arguments.py`) was removed outright in commit `aa7dd21` — it was parsed but never read by any
code path. `--onedrive-logs-folder` was removed in the same cleanup, for the same reason (it was never passed to
the `onedrive` subprocess, and structurally couldn't be — there's no `log_dir` CLI equivalent in OneDrive-for-Linux).

### OneDrive-for-Linux sync brackets the phase pipeline in `main()`

**This whole section replaced a Docker-sidecar/env-var design with a fully CLI-args-driven one — the old
`OD_CONFDIR` environment variable approach is gone.**

`main()` calls `run_onedrive_sync()` (`onedrive_sync.py`) around the phase pipeline: once with
`direction=SyncDirection.DOWNLOAD.value` before `run_all_phases()`, once with `direction=SyncDirection.UPLOAD.value`
after it. Each call shells out to the real `onedrive` binary as a one-shot `--sync --download-only`/`--upload-only`
pass and blocks until it exits — never `onedrive --monitor` (the long-running mode `compose.yml`'s sidecar still
uses for local dev only).

**Every path OneDrive touches is now a CLI argument, not a hardcoded Docker path:**
- `confdir` = `args.onedrive_conf_folder` (default: `ROOT_FOLDER/service/onedrive/conf`)
- sync root = `args.onedrive_data_folder`, passed as `--syncdir` (overrides the `config` file's own `sync_dir`)
- sync scope = `args.sharepoint_sync_folder`, passed as `--single-directory` — this is the *only* scope filter;
  there is no `sync_list` file anymore (deliberately deleted — it conflicted with `--single-directory` and caused a
  real local-data-loss incident when both were active at once)
- `args.runtime_location` (computed: `onedrive_data_folder / sharepoint_sync_folder`, auto-created via
  `parse_directory` if missing) is what `run_all_phases` actually processes — `_output`/`QA_ERRORS` now nest
  *inside* it (`args.runtime_location / FolderName.OUTPUT.value / ...`, not a sibling via `.parent`), specifically
  so the upload pass can actually reach the merged-output/QA artifacts.

`--cleanup-local-files` is appended only on the download call, and `--dry-run` only when `args.dry_run` is set —
both used to be static settings in `service/onedrive/conf/config` (`download_only`/`cleanup_local_files`), but
those were **removed from the config file entirely**, since a static `download_only=true` conflicts with
`--upload-only` the moment the upload call actually runs for real.

**Two hard `onedrive` CLI constraints, confirmed the hard way, worth knowing before changing this code:**
- Every invocation requires exactly one of `--sync`/`--monitor` — there is no flag-free "just check credentials"
  mode, regardless of what other flags are present. (This was re-checked against the upstream docs during this
  round of work — a *literally bare* `onedrive --confdir <dir>` invocation, with no `--single-directory`/`--syncdir`
  at all, is documented upstream as the supported way to do first-time interactive auth without triggering this
  error. That's a real discrepancy with what's stated here; it hasn't been re-tested against this project's actual
  installed `onedrive` build yet, so don't change the `--auth` bootstrap on the strength of the docs alone.)
- `--dry-run` never persists a freshly-obtained OAuth token to disk — only a real (non-dry-run) sync does.

**The one-time `--auth` bootstrap** (`main.py`, now gated on plain `args.auth and args.location ==
InputLocation.SHAREPOINT` — `--auth` became a `store_true` flag in commit `aa7dd21`, replacing the earlier
value-taking flag that was only ever checked via `is not None`) exists because of both constraints above: it's a
real `run_onedrive_sync(..., dry_run=False)` call (not a bespoke auth-only function — an earlier `run_onedrive_auth`
attempt was removed, since no flag-free invocation actually works), scoped via `--single-directory` to
`FolderPaths.SHAREPOINT_AUTH_PATH` (`justifactu/_auth_sync`) — a dedicated, deliberately-empty folder, so the real
sync pass has nothing to transfer while still being "real" enough to persist the resulting token. `exit(0)`
immediately after, so phases/upload never run in this mode.

`subprocess.CalledProcessError` and `FileNotFoundError` are both normalized into `MainCriticalError` in
`run_onedrive_sync`, caught by `main()`'s existing exception handling — the upload call is only ever reached if
every prior step succeeded, so SharePoint is never mutated on a failed run.

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
make both per-call CLI flags instead"). Treat the doc as historical context, not a live spec, until it's updated to
match.

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
- `onedrive_sync.py`: `_base_onedrive_args` builds the flags common to every invocation (`--confdir`,
  `--single-directory`, `--syncdir`, `--verbose`); `run_onedrive_sync` adds `--sync`/`--{direction}-only` plus the
  conditional flags on top. There is no separate "auth-only" function anymore — see the `--auth` bootstrap above.
- `logger.py`: a `extra={"qa_report": True}` tag on any `log.*()` call routes that line into a separate QA report
  file (mailed via `mail.py::send_qa_report_mail`), independent of the main run log.
- `secret.py` / `vault.py`: secrets resolve through a fallback chain (mounted Docker secret → repo `secrets/` file →
  env var → HashiCorp Vault), so the same code runs unmodified in local dev and deployed containers. `vault.py`'s
  `_SECRET_MAP` is the authoritative list of which `SecretNames` values actually have a Vault path configured.