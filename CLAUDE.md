# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

All development commands are defined once in the `Makefile` and reused by pre-commit hooks and CI — treat the
`Makefile` as the source of truth, not these as a separate reference.

    make dev              # install runtime + dev deps, install git hooks (pre-commit/commit-msg/pre-push)
    make lint              # ruff check . && mypy src   (mypy runs in strict mode — see pyproject.toml)
    make fmt                # black src tests && ruff check --fix .
    make test                # PYTHONPATH=src pytest -s -v   (testpaths = tests, per pyproject.toml)
    make run CMD="--phase 1" # python -m justifactu <CMD>; CMD defaults to --help if omitted

Run a single test file or test function directly with pytest (bypassing the Makefile), same env var the `test`
target uses:

    PYTHONPATH=src pytest tests/test_bills.py -v
    PYTHONPATH=src pytest tests/test_bills.py::test_parse_bill_filename_valid -v

Docker: `make docker-build` / `make docker-push` (pushes `davidromeroiciq/justifactu:latest`, requires Docker Hub
credentials). `compose.yml` runs the app alongside a long-running `onedrive` sync sidecar container for local dev —
this is the *old* sync architecture (see "OneDrive sync" below), kept for local dev convenience, not the target
production design.

Git commit messages must follow Conventional Commits (enforced by `conventional-pre-commit` in
`.pre-commit-config.yaml`); a license header (`LICENSE_HEADER`) is auto-inserted into `.py` files before formatting.

## Architecture

### Two independent entry paths, not one

`src/justifactu/__main__.py` is the actual program entry point (`python -m justifactu`) — `main.py`'s own
`if __name__ == "__main__"` guard is dead code, since nothing runs `main.py` directly. `__main__.py` parses CLI
args once and branches:

- `--phase` **absent** → `main()` (`main.py`) runs the full production pipeline: `run_all_phases()` (`process.py`),
  bracketed by an OneDrive download/upload sync (see below).
- `--phase` **present** (`1`, `2`, or `3` — see `Phase` enum in `defines.py`) → `run_phase()` (`process.py`) runs
  *only* that one stage, via a `phase → zero-arg lambda` dispatch dict built fresh per call. This path exists
  specifically to test one stage in isolation against disposable local fixtures, without touching the rest of the
  pipeline, and does **not** trigger an OneDrive sync.

`run_phase()` and `run_all_phases()` share one dispatch table (`process.py::_build_phase_map`), so there's a single
place defining what each phase does — `run_all_phases` just loops `FULL_RUN_PHASES = (Phase.PHASE_1, Phase.PHASE_2)`
against the same map `run_phase` looks a single key up in. Phase 3 (`mock_phase3`) is reachable via `--phase 3` for
testing but deliberately excluded from `FULL_RUN_PHASES`, since it's a placeholder, not real logic — don't add it to
the full-run tuple until it's actually implemented.

### SAP ID is the correlation key between bills and payments

A bill and a payment are matched purely by a shared `SAP_ID` (`SAP_ID.py`) — a 4-digit year + 6-digit sequence,
parsed via regex from two different sources:

- **Bills** arrive from Docuware already named `F <sap_id>` (`bills.py::parse_bill_filename`).
- **Payments** start as bank-statement PDFs with arbitrary filenames; `payments.py::rename_payments` extracts the
  SAP ID from the PDF's *content* (a `Fra.` marker inside the text — `bills.py::parse_sap_id_from_bill`, regex
  tolerates both old `Fra. <id>` and a newer no-period/newline BBVA statement format) and renames the file to
  `{sap_id}-P.pdf` **on disk**, in place — this is a real filesystem rename, not just an in-memory mapping.

`process.py::merge_bills_and_payments` matches bills against an index of already-renamed payment files, merges each
matched pair into one PDF (bill first, then payment) under `{year}_FACTURA+PAGAMENT/{sap_id}_F_P.pdf`, then
(`cleanup_processed_files`) renames the payment with a `_merged` suffix and deletes the bill. A bill with no
matching payment isn't necessarily an error — unmatched bills are routed to a separate, not-yet-implemented
"own treatment" flow (`mock_phase3` in `process.py`) for card payments, travel expenses, and direct debits.

### The SharePoint/Graph API code is legacy and unreachable — do not extend it

`sharepoint.py`, `token_manager.py`, the `FolderPaths`/`InputLocation` enums and the `-l/--location`,
`--download-input` CLI flags (`arguments.py`) still exist in the tree, but **nothing calls any of them anymore**.
The pipeline was migrated to a filesystem-only model: `main()` and `process.py` read/write local paths under
`args.input_location` exclusively. This code was deliberately kept rather than deleted, in case it's needed again —
but no current code path reaches it, and `tests/test_sharepoint.py` tests it in isolation from the rest of the
suite. Don't wire new work through it without confirming that's actually intended.

### OneDrive-for-Linux sync brackets the phase pipeline in `main()`

`main()` calls `run_onedrive_sync()` (`onedrive_sync.py`) twice: once with `direction=SyncDirection.DOWNLOAD.value`
before `run_all_phases()`, once with `direction=SyncDirection.UPLOAD.value` after it (and after the QA report/log
get copied into the output tree, so they're included in that upload). Each call shells out to the real `onedrive`
binary as a **one-shot** `--sync --download-only`/`--upload-only` pass and blocks until it exits — deliberately not
`onedrive --monitor` (the long-running mode `compose.yml`'s sidecar still uses for local dev), specifically to avoid
a background sync racing the phase stages' renames/deletes over the same `_input` tree. `subprocess.CalledProcessError`
and `FileNotFoundError` (binary missing) are both normalized into `MainCriticalError`, so a sync failure is caught by
`main()`'s existing exception handling the same way a phase failure is — the upload call is only ever reached if
every prior step succeeded, so SharePoint is never mutated on a failed run.

`confdir` — the directory holding OneDrive's own auth token and sync-state database, distinct from `input_folder`
— comes from the `OD_CONFDIR` environment variable, defaulting to `/onedrive/conf` if unset. It must be the same
directory on every invocation (download and upload alike) or OneDrive has no memory of what it already synced.

The `--phase` testing path (above) never calls `run_onedrive_sync` — this sync is only part of the full production
run. The deeper design rationale and decision log for this two-pass architecture live in the `docs` git submodule
(`ICIQ-DMP/justifactu-docs`, `docs/explanation/onedrive_sync_and_orchestration.md`); `compose.yml`'s `onedrive`
sidecar service reflects the *old* architecture being phased out, kept only for local dev per that doc's decision
log (D18), not the production design.

### Module layout (only the non-obvious relationships)

- `arguments.py` → `defines.py`: CLI flags validate against enums defined in `defines.py` (`Phase`, `InputLocation`)
  via small `parse_*` functions, each raising a specific `custom_except.py` exception on invalid input.
- `logger.py`: a `extra={"qa_report": True}` tag on any `log.*()` call anywhere in the codebase routes that line into
  a separate QA report file (mailed at the end of every run via `mail.py::send_qa_report_mail`), independent of the
  main run log.
- `secret.py` / `vault.py`: secrets resolve through a fallback chain (mounted Docker secret → repo `secrets/` file →
  env var → HashiCorp Vault), so the same code runs unmodified in local dev and deployed containers.