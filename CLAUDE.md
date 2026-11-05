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
    make run CMD="--mode prod"      # full run against justifactu/runtime instead of justifactu/runtime-test
    make auth                       # one-time OneDrive OAuth bootstrap (python -m justifactu --auth)
    make notify CMD="--subject '...' --body '...'"   # python -m justifactu.notify <CMD>; standalone one-off email

Run a single test file or test function directly with pytest (bypassing the Makefile), same env var the `test`
target uses:

    PYTHONPATH=src pytest tests/test_bills.py -v
    PYTHONPATH=src pytest tests/test_bills.py::test_parse_bill_filename_valid -v

`tests/test_mail.py::test_send_mail_authenticated_real` sends a real email and fails wherever the SMTP secrets
aren't available. That's the expected baseline, not a regression.

Docker (app image): `make docker-build` / `make docker-push` (pushes `davidromeroiciq/justifactu:latest`). Root
`compose.yml` runs the app alongside a long-running `onedrive --monitor` sidecar. That's the *old* sync
architecture, local-dev only, and currently out of date (its `app` service still passes `--input-location`, a flag
that no longer exists).

Docker (Jenkins agent image): `make prodbuild` / `make prodrun` build and start the agent defined in
`service/agent/`, via `service/agent/compose.yml`. See "Jenkins agent" below.

Git commit messages must follow Conventional Commits (enforced by `conventional-pre-commit` in
`.pre-commit-config.yaml`); a license header (`LICENSE_HEADER`) is auto-inserted into `.py` files before formatting.

All CLI flags use hyphens (`--onedrive-data-folder`, `--sharepoint-sync-folder`), not underscores. argparse maps
both to the same attribute (`args.onedrive_data_folder`), but only the hyphenated spelling is registered.

## Architecture

### `main()` is the only entry path

`__main__.py` is a thin wrapper around `main.py::main()`. `main()` does, in order:

1. Configures logging (run log + QA report under the repo's `logs/` folder) and records `started_at`.
2. `args = process_parse_arguments()`.
3. **`--phase` present** (`1`/`2`/`3`) → `run_phase(args.phase, args.runtime_location, args.mode)`, then
   `log_run_summary(...)`, then `return`. No OneDrive sync, no `--auth` check, no log copy, no QA-report email.
   This path exists to test one phase in isolation.
4. **`--auth`** (with `--location sharepoint`, the default) → `run_onedrive_auth(...)`, then `return`.
5. **Full run**, inside `try`:
   - OneDrive download (`run_onedrive_sync(direction="download")`), with a Graph API fallback on failure.
   - `metrics = run_all_phases(args.runtime_location, args.mode)` + `log_run_summary(metrics, elapsed)`.
   - Copies the QA report into `FACTURES+PAGAMENTS/QA_ERRORS/` and the run log into `FACTURES+PAGAMENTS/logs/`.
     The summary is logged *before* this copy so the uploaded QA report contains it.
   - OneDrive upload (`run_onedrive_sync(direction="upload")`), no fallback.
6. `except MainCriticalError` → `log.critical` + `exit(1)`. `finally` → `send_qa_report_mail(...)`, whose own
   failures are logged and swallowed.

Only `MainCriticalError` is caught. Anything else a phase raises propagates out of `main()`. The `finally` still
sends the mail, the exit code is non-zero, and the upload is skipped, so SharePoint is never mutated on a failed run.

### Runtime folder layout and `--mode`

Each run works on one local folder, `args.runtime_location` (default:
`--onedrive-data-folder / --sharepoint-sync-folder`). `--sharepoint-sync-folder` defaults to
`paths.py::sharepoint_sync_folder(mode)`:

| `--mode` | SharePoint folder synced | Bills deleted after a merge (`delete_processed`) |
|---|---|---|
| `prod` | `justifactu/runtime` | yes |
| `test` (default) | `justifactu/runtime-test` | yes |
| `dev` | `justifactu/runtime-test` | **no**, so local fixtures survive repeated runs |

```text
<runtime>/
├── FACTURES/                        # FolderName.BILLS: bills named "F <sap_id>.pdf"
├── Remeses/                         # FolderName.PAYMENTS: bank remittance PDFs
├── Targetes/<year>/                 # FolderName.CARD_STATEMENTS: one ledger .xlsx + card statement PDFs
└── FACTURES+PAGAMENTS/              # FolderName.BILLS_AND_PAYMENTS: all output
    ├── <year>_FACTURA+PAGAMENT/{sap_id}_F_P.pdf
    ├── QA_ERRORS/                   # QA report, copied after a full run
    └── logs/                        # run log, copied after a full run
```

`mode` only selects the SharePoint folder and `delete_processed`. The folder *names* inside the runtime folder are
the same in every mode.

**Every path flag uses `type=parse_directory`, which creates the directory if it's missing.** A typo'd
`--sharepoint-sync-folder` or `--runtime-location` doesn't fail at parse time. It creates an empty local folder and
the run fails later with a `list_dir` `ValueError` on a missing `FACTURES/`. Check the actual folder before assuming
a code regression.

### Path and folder-name composition: `defines.py` / `paths.py` / `defaults.py`

No module outside `defines.py` hardcodes a folder or file-name string.

- **`defines.py`**: bare-name `StrEnum`s only (`FolderName`, `FileSuffix`, `Mode`, `Phase`, `Metric`,
  `InputLocation`, `SyncDirection`, `SecretNames`) plus `ROOT_FOLDER`, `NOW`, `DATETIME_FORMAT`. No composed paths.
- **`paths.py`**: composes runtime `Path`s from an already-resolved base folder: `bills_folder`, `payments_folder`,
  `card_statements_folder`, `merged_bills_and_payments_folder`, `qa_errors_folder`, `logs_folder`,
  `year_merged_folder`, `sharepoint_sync_folder(mode)`.
- **`defaults.py`**: `ROOT_FOLDER`-relative fallbacks for CLI flags: `default_onedrive_data_folder`,
  `default_onedrive_conf_folder`, `default_secrets_folder`.

Tests build fixture folders from the enums (`FolderName.BILLS.value`, ...), never from string literals, so a
rename of an enum value is caught by the suite.

### The phase pipeline (`process.py`)

`_build_phase_map(input_folder, mode)` returns `{Phase: closure}`. `run_phase` calls one entry; `run_all_phases`
calls every phase in `FULL_RUN_PHASES = (PHASE_1, PHASE_2, PHASE_3)` in order. Both paths share the same closures,
so `--phase N` exercises exactly the production code. Phases pass nothing to each other in memory: each rediscovers
its input from the filesystem, which is why the order matters.

**Error-handling pattern:** low-level functions (`payments.py`, `pdf.py`, `bills.py`) raise specific exceptions
from `custom_except.py` and log nothing. The loops in `process.py` catch them, write the QA line, count the metric
and `continue`. Keep reporting decisions in `process.py`.

**Metrics:** every phase function returns `Metrics = Counter[Metric]`. `run_all_phases` adds them with
`Counter.update` (not `+`, which drops zero keys), and `process.py::log_run_summary(metrics, elapsed_seconds)` writes
one `qa_report`-tagged INFO block:

| `Metric` | Counted in |
|---|---|
| `TRASH_FILES` | Phase 1: `NotAPaymentFileError` (non-PDF in `Remeses`) |
| `UNPARSEABLE_PAYMENTS` | Phase 1: `ParseSAPIdException` (no `Fra. <sap_id>` in the PDF) |
| `PAYMENT_MERGES` | Phase 2: after a successful `merge_pdfs` |
| `CARD_STATEMENT_MERGES` | Phase 3: after a successful `merge_pdfs` |
| `FAILED_MERGES` | Phases 2 and 3: `MergingBillWithPaymentError` |
| `UNMATCHED_BILLS` | Phase 3 only: bill with no payment and no card statement |

The counts describe the current backlog, not what's new since the last run: trash, unparseable payments and
unmatched bills stay where they are and are counted again every run.

#### SAP ID: the correlation key

`SAP_ID.py` validates `(?P<year>20\d{2})(?P<sapid>\d{6})` and compares by its full string, so every match below is a
`dict.get(sap)`. It's built from three sources: the bill filename (`bills.py::parse_bill_filename`, `F <sap_id>`),
the payment PDF's text (`payments.py::parse_sap_id_from_payment`, regex `Fra\.?\s+<sap_id>`, first match on the
first matching page), and ledger column J (Phase 3).

#### Phase 1: rename payments (`process.py::rename_payments`)

Walks `Remeses/` recursively (snapshot via `list(rglob)` before renaming). Skips folders and files already handled
(`payments.py::is_renamed_payment`: stem contains `<sap_id>-P` or `<sap_id>-P_merged`). For every other file,
`payments.py::rename_payment` raises `NotAPaymentFileError` for non-PDFs, raises `ParseSAPIdException` when no SAP ID
is found, or renames the file in place to `{sap_id}-P.pdf`. Never merges, never touches bills.

#### Phase 2: bills × bank payments (`process.py::merge_bills_and_payments`)

1. Indexes `Remeses/` by **filename** (`index_folder` + `payments.py::index_payments`), skipping `_merged` files.
   Payments that Phase 1 never renamed have no SAP ID in their name and are skipped, so `--phase 2` on a fresh
   folder matches nothing. (`freshly_renamed_payments` is a leftover parameter nothing passes any more.)
2. For each bill in `FACTURES/`: non-PDF or bad name → QA line (Phase 2 owns these; Phase 3 skips them silently).
   No payment → `info` only, deferred to Phase 3. Otherwise `merge_pdfs(bill, payment, output)` (bill first).
3. `cleanup_processed_files`: renames the payment to `{sap_id}-P_merged.pdf` in every mode (the audit trail, and
   what stops it matching again) and deletes the bill unless `dev`.

Phase 2 does not check whether the output already exists; it overwrites it.

#### Phase 3: remaining bills × card statements (`process.py::merge_bills_and_card_statements`)

Card payments never carry a SAP ID. A hand-maintained Excel ledger per year links a card transaction
(date + amount) to one:

```text
<runtime>/Targetes/
└── <year>/                 # any subfolder name works; every subfolder is scanned
    ├── <anything>.xlsx     # exactly ONE ledger per year folder (Excel "~$" lock files ignored)
    └── <anything>.pdf      # the statement PDFs, any filename
```

Builds a `SAP_ID -> statement PDF` index across every year folder, then walks `FACTURES/`. Already-existing output →
skip (idempotency for `dev`). No match → QA error "No matching payment or card statement found", the only place an
unmatched bill is reported. Otherwise the bill is merged with the **whole** statement into the same
`{year}_FACTURA+PAGAMENT/{sap_id}_F_P.pdf` as Phase 2, and the bill is deleted unless `dev`. **Statements and
ledgers are never renamed, moved or deleted**: one statement backs many bills. A missing `Targetes/` is QA-warned
but the bill loop still runs, so every remaining bill is reported (guarded by
`test_phase_3_qa_logs_unmatched_bill_when_targetes_missing`).

What `bank_statement.py` does:

- `extract_bank_entries`: pdfplumber `extract_words()`, grouped into rows by `top` (`_group_into_rows`, tolerance
  1.0, sorted by `x0`). A row is a transaction only if its first word matches `DATE_PATTERN` (`DDMM`). Concept =
  words left of `CONCEPT_COLUMN_END_X = 289`; total = last word matching `AMOUNT_PATTERN` (`1.234,56`). These are
  tuned to the current bank's layout; a different bank needs them revisited.
- `_merge_commission_rows`: a row starting with `COMMISSION_MARKER` ("Comissió per conversió de divises") is folded
  into the previous same-date row (totals summed, first concept kept), because the ledger records them as one.
- `read_sap_id_ledger`: active sheet from row 2, columns A (date, `'DD/MM` text, apostrophe stripped), H (total),
  J (SAP ID) → `{(DDMM, round(total, 2)): SAP_ID}`. Empty J → skipped silently; non-numeric H or invalid J → QA.
  Loads `_strip_autofilters(path)`, an in-memory copy with every `<autoFilter>` removed, because openpyxl rejects
  the whole-row ranges (`ref="1:644"`) Excel writes. The file on disk is never modified.
- `index_statement_entries`: joins on `(date, total)` (deliberately no concept). No ledger row → QA warning.
- `find_year_ledger`: exactly one `.xlsx` per year folder, else QA error and the year is skipped.

Only `.xlsx` is supported. Every statement is re-parsed and its ledger re-read on every run.

### Logging and the QA report (`logger.py`)

- Format: `DD/MM/YYYY HH:MM:SS.mmm | LEVEL | logger | message` (`DATE_FORMAT` + `%(msecs)03d` in `MESSAGE_FORMAT`).
  Don't use `%f` in `DATE_FORMAT`: logging formats dates with `time.strftime`, which doesn't support it.
- `extra={"qa_report": True}` on any `log.*()` call routes that line into the separate QA report file
  (`logs/<NOW>_qa_report.log`), via a handler with `QAFilesFilter` at **INFO** level (INFO so the run summary gets
  in; untagged lines never do). The QA report is copied to `QA_ERRORS/` and mailed after a full run.
- Log file names use `NOW` to the second: two runs starting in the same second share files.
- The `RichHandler` runs with `markup=False`, and the `pdfminer`/`pdfplumber` loggers are pinned to `WARNING`:
  pdfminer's debug output contains `[...]` sequences Rich parsed as markup and crashed on (`MarkupError`).

### OneDrive-for-Linux sync (`onedrive_sync.py`)

`run_onedrive_sync` shells out to the real `onedrive` binary as a one-shot `--sync --download-only` /
`--upload-only` pass and blocks until it exits. Never `--monitor` (that's the local-dev `compose.yml` only).

- **Paths are CLI args:** `--confdir` = `args.onedrive_conf_folder`, `--syncdir` = `args.onedrive_data_folder`
  (overrides `sync_dir` in `config`), `--single-directory` = `args.sharepoint_sync_folder`, the only scope filter.
  There is no `sync_list` file: it was deliberately deleted after it conflicted with `--single-directory` and
  caused a real local-data-loss incident. Don't reintroduce it.
- **Defaults come from env vars first:** `OD_CONF` / `OD_DATA`, else `defaults.py`'s repo-relative folders. The
  Jenkins agent image sets `ENV OD_CONF=/onedrive/conf` / `ENV OD_DATA=/onedrive/data`, so every process in that
  container, including a manual `--auth`, uses the persistent volumes rather than the ephemeral workspace.
- `--cleanup-local-files` only on the download; `--dry-run` only when `args.dry_run`. **`--dry-run` only affects
  the sync calls**: the phases still run on whatever is on disk.
- **The upload deletes remotely** whatever is missing locally (`--no-remote-delete` is deliberately not passed).
  That's how deleted bills disappear from SharePoint, and why a phase must never be pointed at the synced folder
  for experiments: the next full run uploads its changes.
- Outside `--mode prod`, `_base_onedrive_args` adds `--verbose --verbose` (debug logging, needed to see why
  OneDrive asks for a resync); in `prod` it's left out so logs don't grow unbounded.
- **Exit code 126** ("resync required", e.g. the first sync after a fresh `--auth`) → retried once with
  `--resync --resync-auth`.
- `CalledProcessError` and `FileNotFoundError` (no `onedrive` binary) become `MainCriticalError` → `exit(1)`.
- **`drive_id` is static.** `_write_drive_id_if_missing` writes the `DRIVE_ID` secret into
  `service/onedrive/conf/config` only when the line is missing or empty, then leaves it. The earlier
  write-then-erase-per-call design was dropped: the changing file made OneDrive's `.config.backup` check demand a
  `--resync` on every run. The git-tracked `config` currently contains the real value.

**`--auth` bootstrap:** `run_onedrive_auth` runs `onedrive --confdir <c> --syncdir <d>` with no
`--sync`/`--monitor`/`--single-directory`. On a `confdir` with no refresh token, OneDrive's `initialise()` drives
the interactive OAuth flow and persists the token without transferring files. Re-running it once a token exists
exits non-zero ("missing switches"); that's accepted, since `--auth` is a one-time action per system.

**Graph API download fallback (`sharepoint.py`, `token_manager.py`):** if the OneDrive download raises
`MainCriticalError`, `main()` calls `connect_sharepoint()` + `download_input_folder(...)` into the same local folder.
If that also fails, it's re-raised as one `MainCriticalError`. There is no upload fallback: SharePoint is only ever
written by `onedrive --upload-only`. This is a second credential path (app-only `CLIENT_ID`/`CLIENT_SECRET`/
`TENANT_ID`) next to OneDrive's delegated token, and it hasn't been verified against the tenant's current app
registration. Tests patch at `justifactu.sharepoint.X` (e.g. `justifactu.sharepoint.requests.get`).

The design rationale lives in the `docs` submodule (`ICIQ-DMP/justifactu-docs`,
`docs/explanation/onedrive_sync_and_orchestration.md`), but parts of it are superseded (Graph is back as a
download fallback, `drive_id` handling changed, `--mode` folders changed). Treat it as context, not a spec.

### Jenkins agent (`service/agent/`)

A separate image/compose stack from the app: `service/agent/dockerfile/Dockerfile` (from `jenkins/ssh-agent`,
installs Python + the `onedrive` binary via `install-onedrive-apt.sh`), `entrypoint/entrypoint.sh`, and
`compose.yml` (volumes for `onedrive/conf` + `onedrive/data`, Vault AppRole secrets, SSH-key bind mount).

The agent joins an **external Docker network owned by another project** (`justicier_justicier_net`). Don't
repoint it until Jenkins has its own stack, or the agent fails to start.

`Jenkinsfile` is a **draft, not wired to any job**: one stage running
`make install && make run CMD="--onedrive-conf-folder ${OD_CONF} --onedrive-data-folder ${OD_DATA} --mode prod"`,
no `checkout scm`, no cron trigger, no timeout. Its `post` blocks call `make notify` (`notify.py`).

### Module layout (only the non-obvious relationships)

- `arguments.py`: flags validate against `defines.py` enums via small `parse_*` functions that raise
  `custom_except.py` exceptions. `-l/--location` gates `--auth` (`InputLocation.SHAREPOINT`).
- `payments.py`: single-file operations only (`rename_payment`, `is_renamed_payment`,
  `parse_sap_id_from_payment`, `index_payments`). The Phase 1 loop lives in `process.py`.
- `pdf.py::merge_pdfs`: wraps `PyPdfError`/`OSError` into `MergingBillWithPaymentError` and deletes a half-written
  output, so a later run doesn't mistake it for a finished merge.
- `filesystem.py::change_file_name`: renames even if the target exists (only logs a warning), which **replaces**
  the existing file on Linux. See "Known issues".
- `secret.py` / `vault.py`: secrets resolve through mounted Docker secret → `default_secrets_folder()` → env var →
  HashiCorp Vault. `vault.py::_SECRET_MAP` is the authoritative list of secrets with a Vault path.
- `notify.py`: standalone entry point (`make notify`) for one-off emails; lets exceptions propagate, unlike
  `main()`'s QA mail.

### Known issues and leftovers

- **Duplicate SAP IDs silently overwrite payments.** Two bank PDFs with the same `Fra. <sap_id>` → the second
  Phase 1 rename replaces the first file (see `change_file_name`). Same risk at the `_merged` rename.
- **A failed Phase 2 merge also counts as unmatched**: the bill stays, Phase 3 can't find it in a statement.
- **A corrupt card statement or ledger still crashes the run**: Phase 3's index loop doesn't catch pdfplumber /
  openpyxl / `zipfile` errors.
- **A remittance is matched to one SAP ID only**: Phase 1 takes the first `Fra.` match in the PDF.
- `main.py` still has `# NEW` / `# CHANGED` markers on the metrics lines (cosmetic).
- `pyproject.toml` lists `types-openpyxl` in runtime `dependencies`; it belongs in the `dev` extras.
- Dead code: `arguments.py::parse_input_location`, `filesystem.py::move_file`, the `freshly_renamed_payments`
  parameter. `Dockerfile`'s `ENV BILLS_INPUT_FOLDER`/`PAYMENTS_INPUT_FOLDER` are read by nothing.
- `Jenkinsfile`'s `aborted` message still mentions a 20h initial-sync timeout that no longer applies.
- `_base_onedrive_args`' docstring says "every sync invocation"; `run_onedrive_auth` uses it too.