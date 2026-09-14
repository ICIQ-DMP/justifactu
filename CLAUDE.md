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

- `--phase` **absent** → `main()` (`main.py`) runs the full production pipeline unconditionally, on
  `args.input_location`.
- `--phase` **present** (`1`, `2`, or `3` — see `Phase` enum in `defines.py`) → `run_phase()` (`process.py`) runs
  *only* that one stage, via a `phase → zero-arg lambda` dispatch dict built fresh per call. This path exists
  specifically to test one stage in isolation against disposable local fixtures, without touching the rest of the
  pipeline.

**Known duplication**: `main()`'s `try` block calls `rename_payments()` then `merge_bills_and_payments()` directly,
inline — the same two calls that `run_phase()`'s internal `_run_phase_1`/`_run_phase_2` wrap independently in
`process.py`. These are two separate implementations of "what phase 1/2 do," not one shared one. If asked to add a
phase or change phase 1/2 behavior, check both places, or consider consolidating `main()` to call into `process.py`'s
phase machinery instead of re-implementing the sequence.

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

### OneDrive-for-Linux sync is a documented target design, not yet implemented

There is no sync step anywhere in the current code — `main()` operates purely on whatever is already on local disk.
The intended replacement for both the old Graph-based upload path and the `compose.yml` `onedrive --monitor`
sidecar is two **one-shot** `onedrive --sync --download-only` / `--upload-only` subprocess calls bracketing the
processing (`main()` calling something like `run_onedrive_sync()` before and after the phase pipeline) — chosen
specifically to avoid a background sync racing the phase stages' renames/deletes over the same `_input` tree. The
full design, rationale, and a decision log are in the `docs` git submodule (`ICIQ-DMP/justifactu-docs`,
`docs/explanation/onedrive_sync_and_orchestration.md`) — read it before touching anything sync-related; it's
authoritative over any inference from the current code, since the current code hasn't caught up to it yet. The
draft `Jenkinsfile` at the repo root reflects this target architecture but is explicitly marked not wired into any
running Jenkins job.

### Module layout (only the non-obvious relationships)

- `arguments.py` → `defines.py`: CLI flags validate against enums defined in `defines.py` (`Phase`, `InputLocation`)
  via small `parse_*` functions, each raising a specific `custom_except.py` exception on invalid input.
- `logger.py`: a `extra={"qa_report": True}` tag on any `log.*()` call anywhere in the codebase routes that line into
  a separate QA report file (mailed at the end of every run via `mail.py::send_qa_report_mail`), independent of the
  main run log.
- `secret.py` / `vault.py`: secrets resolve through a fallback chain (mounted Docker secret → repo `secrets/` file →
  env var → HashiCorp Vault), so the same code runs unmodified in local dev and deployed containers.