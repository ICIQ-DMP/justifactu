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

**A note on testing against a scoped folder:** `--sharepoint-sync-folder` uses `type=parse_directory`, which
auto-creates the *local* target directory as part of argument parsing — before any sync runs, and regardless of
whether that name means anything on the SharePoint side. A typo'd or wrong folder name here won't error at parse
time; it silently creates an empty local directory, the sync then matches nothing remotely, and `run_all_phases`
fails later with a `list_dir`/`ValueError` on a missing `FACTURES_prova`/`Remeses_prova` subfolder. If that error
shows up, check the actual local folder contents and the real SharePoint path before assuming a code regression.

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

### SharePoint/Graph API code: back, but only as a download fallback

`sharepoint.py` was deleted entirely in commit `ae2474f` as dead code, then **recreated in commit `d374242`** with
a deliberately narrower scope than before: it's no longer the primary input path, and it no longer has the old
upload/rename/delete-remote functions at all. It now exists purely to back up the OneDrive-for-Linux download step
if that sync ever fails. Current contents: `get_site_id`, `get_drive_id`, `list_folder_contents`, `download_file`
(retries on HTTP 503, raises `RuntimeError` after `max_retries`), `download_folder_recursive`, `download_input_folder`,
and `connect_sharepoint` (no longer private/underscored — `main.py` calls it directly). `token_manager.py`, which
had been sitting orphaned since `sharepoint.py`'s deletion, is live again as this module's only consumer of
`TokenManager`/`get_token_manager`.

**How the fallback is wired (`main.py`):** the download `run_onedrive_sync()` call is now in its own nested
`try/except MainCriticalError`, not the outer one. On failure, it logs a warning and calls `connect_sharepoint()` +
`download_input_folder(token_manager, drive_id, args.sharepoint_sync_folder, args.runtime_location)` — same remote
scope and local destination the OneDrive sync would have used. If *that* also fails, the resulting exception is
wrapped into a fresh `MainCriticalError` and re-raised, so it's still caught by the outer handler and still produces
exactly one `log.critical` + `exit(1)` — not two stacked failures. Only the **download** step has this fallback;
a failed upload or a failed phase still goes straight to the outer handler, no fallback attempted.

**Worth knowing before relying on this in production:** this reintroduces a second, independent SharePoint
credential path (Graph app-only auth via `TokenManager` — `CLIENT_ID`/`CLIENT_SECRET`/`TENANT_ID`) alongside
OneDrive-for-Linux's own delegated-user OAuth token. That's exactly the "two credentials to operate, authorize,
rotate and monitor" situation `docs/explanation/onedrive_sync_and_orchestration.md`'s D19 decided to get away from.
A fallback whose own credentials nobody is actively rotating is a fallback that can silently stop working — this
hasn't been verified against the actual tenant's current app registration.

`tests/test_sharepoint.py` was recreated in commit `3d88e85`, covering all seven functions above (the original
file, before deletion, only ever tested `get_site_id`/`get_drive_id`/`list_folder_contents` — `download_file`,
`download_folder_recursive`, `download_input_folder`, and `connect_sharepoint` are newly covered). Tests patch at
`justifactu.sharepoint.X` (e.g. `justifactu.sharepoint.requests.get`, `justifactu.sharepoint.time.sleep`), matching
how the module imports those names — patching the global `requests`/`time` modules instead would miss the binding.

Two smaller known-dead leftovers, not yet removed: `arguments.py::parse_input_location` (superseded by
`parse_directory`'s auto-create behavior everywhere; only its own tests call it) and `filesystem.py::move_file`
(tested in isolation, but no production code path calls it).

`FolderPaths` (`defines.py`) has a single member — `SHAREPOINT_SYNC_FOLDER` — feeding the real CLI default consumed
by every OneDrive sync call. `InputLocation` and the `-l/--location` CLI flag are in active use — `main.py`'s
one-time `--auth` bootstrap is gated on `args.location == InputLocation.SHAREPOINT`.

`--download-input` and `--onedrive-logs-folder` (`arguments.py`) were both removed outright in commit `aa7dd21` —
the former was parsed but never read by any code path; the latter was parsed but never passed to the `onedrive`
subprocess, and structurally couldn't be (no `log_dir` CLI equivalent exists in OneDrive-for-Linux).

### OneDrive-for-Linux sync brackets the phase pipeline in `main()`

**This whole section replaced a Docker-sidecar/env-var design with a fully CLI-args-driven one — the old
`OD_CONFDIR` environment variable approach is gone.**

`main()` calls `run_onedrive_sync()` (`onedrive_sync.py`) around the phase pipeline: once with
`direction=SyncDirection.DOWNLOAD.value` before `run_all_phases()` (now with a Graph-API fallback on failure — see
above), once with `direction=SyncDirection.UPLOAD.value` after it (no fallback). Each call shells out to the real
`onedrive` binary as a one-shot `--sync --download-only`/`--upload-only` pass and blocks until it exits — never
`onedrive --monitor` (the long-running mode `compose.yml`'s sidecar still uses for local dev only).

**Every path OneDrive touches is now a CLI argument, not a hardcoded Docker path:**
- `confdir` = `args.onedrive_conf_folder` (default: `ROOT_FOLDER/service/onedrive/conf`)
- sync root = `args.onedrive_data_folder`, passed as `--syncdir` (overrides the `config` file's own `sync_dir`)
- sync scope = `args.sharepoint_sync_folder`, passed as `--single-directory` — this is the *only* scope filter;
  there is no `sync_list` file anymore (deliberately deleted — it conflicted with `--single-directory` and caused a
  real local-data-loss incident when both were active at once)
- `args.runtime_location` (computed: `onedrive_data_folder / sharepoint_sync_folder`, auto-created via
  `parse_directory` if missing) is what `run_all_phases` actually processes — `_output`/`QA_ERRORS` now nest
  *inside* it, specifically so the upload pass can actually reach the merged-output/QA artifacts.

`--cleanup-local-files` is appended only on the download call, and `--dry-run` only when `args.dry_run` is set.
**`--dry-run` only gates the OneDrive sync call itself** — it does not skip `run_all_phases()` afterward, so running
`--dry-run` against a never-before-synced local folder leaves it empty and the phase pipeline will fail trying to
read files that were never downloaded.

**How `--sync`/`--monitor` actually interact with authentication** (confirmed against upstream `onedrive` source,
not just docs): `main.d` calls `oneDriveApiInstance.initialise()` — where OAuth and token persistence happen —
**unconditionally**, regardless of `--sync`/`--monitor`. The "switches missing" fail-fast error only fires when (1)
a valid refresh token *already exists* on disk, or (2) `--auth-files`/`--auth-response` are used (a quirk specific
to those flags, not a general rule). On a genuinely fresh, never-authenticated `confdir`, a plain invocation with
no `--sync`/`--monitor`/`--single-directory` completes OAuth, persists the token, and exits `0` — no sync engine, no
file transfer. This is exactly what the `--auth` bootstrap below now relies on.

**The one-time `--auth` bootstrap** (`main.py`, gated on `args.auth and args.location == InputLocation.SHAREPOINT` —
`--auth` is a plain `store_true` flag) was reworked in commit `2ea3480` to use a dedicated
`onedrive_sync.py::run_onedrive_auth(confdir, data_folder)` function — **not** `run_onedrive_sync`. It shells out to
just `onedrive --confdir <confdir> --syncdir <data_folder> --verbose`. No `--single-directory`, no `--sync`/
`--monitor`, no `--dry-run`. On a `confdir` with no existing refresh token this drives the interactive OAuth flow
and persists the token with no file listing or transfer at all (one caveat: the sync engine's own `initialise()`
still makes two small Graph metadata calls — drive details and root details — not a bulk download). `exit(0)`
immediately after, so phases/upload never run in this mode. This replaced the earlier design, which scoped a real
`--sync --download-only` pass to a dedicated empty remote folder (`FolderPaths.SHAREPOINT_AUTH_PATH`,
`justifactu/_auth_sync`) — that folder/path constant no longer exists. **Known limitation of the new approach,
intentionally accepted since `--auth` is documented as a one-time, per-new-system action:** re-running `--auth`
after a token already exists for that `confdir` now exits non-zero ("missing switches") instead of the old design's
harmless no-op, since the fast-fail path only triggers when a token is already present.

`subprocess.CalledProcessError` and `FileNotFoundError` are both normalized into `MainCriticalError` in both
`run_onedrive_sync` and `run_onedrive_auth`. **As of commit `ea6b710`, `main()`'s outer `except MainCriticalError`
block logs the error and calls `exit(1)`** — before that, it only logged, so a failed sync, a failed upload, or a
missing `onedrive` binary all produced exit code `0`, indistinguishable from success. This was the one thing making
`docs/explanation/onedrive_sync_and_orchestration.md`'s D10/D15/D16/D23 and its §7.1/§9 (which all assume failures
produce a non-zero exit, tripping Jenkins' `post { failure }`) actually true — before this commit, that whole
design was describing behavior the code didn't have. The upload call is still only ever reached if every prior step
(including a successful fallback, if the primary download failed) succeeded, so SharePoint is never mutated on a
failed run.

**`drive_id` is no longer permanently stored in the git-tracked config file** (commit `1a1fded`, revised in
`fe369cb`/`8ec9257`). `service/onedrive/conf/config` now has `drive_id = ""` as a placeholder.
`onedrive_sync.py::_write_drive_id` resolves the real value via `read_secret(SecretNames.DRIVE_ID.value)` (already
mapped in `vault.py`'s `_SECRET_MAP`) and rewrites the `drive_id` line in the config file. `erase_drive_id` blanks
it back to `""`. Both share one line-rewrite helper, `_set_drive_id(confdir, value)`. The write/erase happens
per-call, wrapping each individual `onedrive` subprocess invocation (not once per whole process) — `main()`'s own
`finally` block no longer calls `erase_drive_id` at all; that responsibility moved entirely into `onedrive_sync.py`.

**As of commit `4cc2c62`, the erase is correctly guaranteed on every exit path.** `erase_drive_id(confdir)` is now
called from a `finally` on the outer `try` in both `run_onedrive_sync` and `run_onedrive_auth`, so it runs whether
the call succeeds, raises `CalledProcessError`/`FileNotFoundError` (both normalized into `MainCriticalError`), or
hits something unexpected. (An earlier version of this — committed in `8ec9257` — called `erase_drive_id` as plain
sequential code *after* a successful `subprocess.run`, which meant a failed sync skipped the erase entirely and
left the real secret sitting in the git-tracked file with nothing left to clean it up, since the top-level backstop
in `main()` was already gone. That's fixed now; don't reintroduce the sequential-call version.)

`_base_onedrive_args`'s docstring (`"""Flags shared by every sync invocation (download/upload)."""`) is still
slightly stale — `run_onedrive_auth` uses it too (see the module-layout note below), so it's shared by every
invocation, not just sync. Minor, cosmetic, not yet fixed.

**What's still only in `service/onedrive/conf/config`, with no CLI equivalent at all** (confirmed against the
client's own docs): `sync_dir_permissions`, `sync_file_permissions`. (`sync_dir` is still physically present in the
file but is dead weight — `--syncdir` on every call overrides it regardless of what's written there.)
`onedrive --get-sharepoint-drive-id` can look up a drive ID without a sync (a one-off Graph query), which is a
different thing from the `drive_id` secret-injection above but worth knowing about if that ID ever needs rediscovering.

The deeper design rationale and decision log for this architecture live in the `docs` git submodule
(`ICIQ-DMP/justifactu-docs`, `docs/explanation/onedrive_sync_and_orchestration.md`) — but several decisions there
are now superseded by what's actually implemented (D6's "compile from source" was amended to installing via the
OBS apt repo; D21's "remove `download_only`/keep `cleanup_local_files` in config" is now "remove both from config,
make both per-call CLI flags instead"; the `--auth` design has changed twice since; D19's "drop Microsoft Graph
entirely" is now only true for the *upload* side — Graph is back for download, as a fallback). Treat the doc as
historical context, not a live spec, until it's updated to match.

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
- `onedrive_sync.py`: `_base_onedrive_args(confdir, data_folder)` builds the flags common to **every** invocation
  (`--confdir`, `--syncdir`, `--verbose`) — as of commit `8ec9257`, `single_dir`/`--single-directory` moved *out* of
  it and into `run_onedrive_sync` itself (the only caller that needs it), and `run_onedrive_auth` was switched to
  use the shared helper too, removing what used to be a duplicated inline arg list between the two functions.
  `_write_drive_id`/`erase_drive_id` (both via `_set_drive_id`) handle the `drive_id` secret injection per call,
  with the erase now correctly guaranteed via `finally` as of `4cc2c62` — see above.
- `sharepoint.py`: Graph API fallback for the OneDrive download step only — see "SharePoint/Graph API code" above.
  Not used for upload under any circumstance; `onedrive --upload-only` remains the only upload path.
- `logger.py`: a `extra={"qa_report": True}` tag on any `log.*()` call routes that line into a separate QA report
  file (mailed via `mail.py::send_qa_report_mail`), independent of the main run log.
- `secret.py` / `vault.py`: secrets resolve through a fallback chain (mounted Docker secret → repo `secrets/` file →
  env var → HashiCorp Vault), so the same code runs unmodified in local dev and deployed containers. `vault.py`'s
  `_SECRET_MAP` is the authoritative list of which `SecretNames` values actually have a Vault path configured.