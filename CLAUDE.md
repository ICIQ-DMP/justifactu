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

### SharePoint/Graph API code: mostly dead, but not entirely anymore

`sharepoint.py`'s file-transfer functions (`download_input_folder`, `upload_folder_recursive`, `rename_file_remote`,
`delete_file_remote`, etc.) and `token_manager.py` are still **unreachable from any production code path** — OneDrive-
for-Linux replaced direct Microsoft Graph calls for every file operation. Don't wire new work through them without
confirming that's actually intended. (The SharePoint-*list*-specific code — `get_list_id` and its tests — was
removed outright as genuinely dead weight, rather than kept around; see commits `a4514d2`/`7fca48b`.)

**What's no longer dead, though:** `InputLocation` (`defines.py`) and the `-l/--location` CLI flag are back in active
use — `main.py`'s one-time `--auth` bootstrap is gated on `args.location == InputLocation.SHAREPOINT` (see below).
`FolderPaths` (`defines.py`) is also fully live — `SHAREPOINT_SYNC_FOLDER` and `SHAREPOINT_AUTH_PATH` feed real CLI
defaults consumed by every OneDrive sync call. Don't assume everything derived from the old SharePoint/Graph era is
inert; check whether it's referenced from `arguments.py`/`main.py` before treating it as legacy.

`--download-input` (`arguments.py`) is still unused by any code path — that one genuinely is dead.

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
  mode, regardless of what other flags are present.
- `--dry-run` never persists a freshly-obtained OAuth token to disk — only a real (non-dry-run) sync does.

**The one-time `--auth` bootstrap** (`main.py`, gated on `args.auth is not None and args.location ==
InputLocation.SHAREPOINT`) exists because of both constraints above: it's a real `run_onedrive_sync(..., dry_run=
False)` call (not a bespoke auth-only function — an earlier `run_onedrive_auth` attempt was removed, since no
flag-free invocation actually works), scoped via `--single-directory` to `FolderPaths.SHAREPOINT_AUTH_PATH`
(`justifactu/_auth_sync`) — a dedicated, deliberately-empty folder, so the real sync pass has nothing to transfer
while still being "real" enough to persist the resulting token. `exit(0)` immediately after, so phases/upload never
run in this mode.

`subprocess.CalledProcessError` and `FileNotFoundError` are both normalized into `MainCriticalError` in
`run_onedrive_sync`, caught by `main()`'s existing exception handling — the upload call is only ever reached if
every prior step succeeded, so SharePoint is never mutated on a failed run.

**What's still only in `service/onedrive/conf/config`, with no CLI equivalent at all** (confirmed against the
client's own docs, not assumed): `drive_id`, `sync_dir_permissions`, `sync_file_permissions`. `drive_id` especially
is why this file can't be eliminated outright — there's no `--drive-id` flag. (`sync_dir` is still physically present
in the file but is dead weight — `--syncdir` on every call overrides it regardless of what's written there.) Moving
`drive_id` to be generated at runtime from Vault (`SecretNames.DRIVE_ID`, already mapped in `vault.py`'s
`_SECRET_MAP`) rather than hand-maintained in a git-tracked file is a discussed-but-not-yet-implemented direction —
don't assume it's done.

`--onedrive-logs-folder` (`arguments.py`) is parsed into `args` but **never actually passed to `onedrive`** — there
is no CLI equivalent for `log_dir` at all, so this argument currently can't do what its name implies. Treat it as
dead until/unless that's resolved differently.

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
  `parse_directory` (distinct from `parse_input_location`) auto-creates a missing directory rather than erroring,
  used by every OneDrive-path argument.
- `onedrive_sync.py`: `_base_onedrive_args` builds the flags common to every invocation (`--confdir`,
  `--single-directory`, `--syncdir`, `--verbose`); `run_onedrive_sync` adds `--sync`/`--{direction}-only` plus the
  conditional flags on top. There is no separate "auth-only" function anymore — see the `--auth` bootstrap above.
- `logger.py`: a `extra={"qa_report": True}` tag on any `log.*()` call routes that line into a separate QA report
  file (mailed via `mail.py::send_qa_report_mail`), independent of the main run log.
- `secret.py` / `vault.py`: secrets resolve through a fallback chain (mounted Docker secret → repo `secrets/` file →
  env var → HashiCorp Vault), so the same code runs unmodified in local dev and deployed containers. `vault.py`'s
  `_SECRET_MAP` is the authoritative list of which `SecretNames` values actually have a Vault path configured.