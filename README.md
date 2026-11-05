<a id="readme-top"></a>

[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![project_license][license-shield]][license-url]

<br />
<div align="center">
<a href="https://github.com/ICIQ-DMP/justifactu">
    <img src="https://raw.githubusercontent.com/ICIQ-DMP/ICIQ-DMP.github.io/refs/heads/master/assets/images/logo-ICIQ-horizontal-catalan.png" alt="Logo" width="all" height="all">
  </a>
<h3 align="center">justifactu</h3>

  <p align="center">
    Software to automate billing justification at ICIQ.
    <br />
    <a href="https://iciq-dmp.github.io/justifactu-docs/"><strong>Explore the docs »</strong></a>
    <br />
    <br />
    <a href="https://github.com/ICIQ-DMP/justifactu/issues/new?labels=bug&template=bug-report---.md">Report Bug</a>
    &middot;
    <a href="https://github.com/ICIQ-DMP/justifactu/issues/new?labels=enhancement&template=feature-request---.md">Request Feature</a>
  </p>
</div>



<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#about-the-project">About The Project</a>
      <ul>
        <li><a href="#how-it-works">How it works</a></li>
        <li><a href="#built-with">Built With</a></li>
      </ul>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#installation">Installation</a></li>
      </ul>
    </li>
    <li>
      <a href="#usage">Usage</a>
      <ul>
        <li><a href="#folder-layout">Folder layout</a></li>
        <li><a href="#running-it">Running it</a></li>
        <li><a href="#trying-it-on-local-files">Trying it on local files</a></li>
        <li><a href="#the-qa-report">The QA report</a></li>
      </ul>
    </li>
    <li><a href="#development">Development</a></li>
    <li><a href="#deploy-to-production">Deploy to production</a></li>
    <li><a href="#contributing">Contributing</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
  </ol>
</details>


## About The Project

justifactu automates the justification of ICIQ's bills (*factures*). For every bill it finds the document that proves
it was paid and merges the two into a single justification PDF, stored back in SharePoint. It replaces a manual,
repetitive process that previously took significant time each month for the people responsible for these
justifications, leaving only the final review as manual work.

Bills and payments are linked by their **SAP ID** (a 4-digit year plus a 6-digit number, e.g. `2026000123`). Bills
arrive already named `F <SAP ID>.pdf`; the proof of payment comes from one of two sources:

- **Bank remittances** (*remeses*): bank PDFs that contain the SAP ID in their text (`Fra. 2026000123`).
- **Card statements** (*targetes*): monthly card statement PDFs, linked to SAP IDs through a yearly Excel ledger that
  Finance keeps by hand (date + amount → SAP ID).

### How it works

A run is a single one-shot process:

1. **Download.** OneDrive-for-Linux brings the SharePoint folder down to local disk (with a Microsoft Graph download as
   a fallback if that sync fails).
2. **Phase 1 — rename payments.** Each remittance PDF in `Remeses/` is renamed to `<SAP ID>-P.pdf` from the SAP ID
   found in its content.
3. **Phase 2 — bills × bank payments.** Each bill with a matching payment is merged with it into
   `<SAP ID>_F_P.pdf`; the payment is marked `_merged` and the bill is removed.
4. **Phase 3 — remaining bills × card statements.** Bills still left are looked up in the card statements through the
   yearly ledger and merged with the whole statement. Statements and ledgers are never modified.
5. **Report.** A QA report lists every problem found (unmatched bills, files that aren't payments, unreadable PDFs…)
   and ends with a run summary. It's copied next to the results and e-mailed.
6. **Upload.** A second one-shot sync pushes the results, renames and deletions back to SharePoint.

If anything fails before step 6, SharePoint is left untouched. For the full architecture, decision log and data flow,
see the [docs site](https://iciq-dmp.github.io/justifactu-docs/) (source:
[justifactu-docs](https://github.com/ICIQ-DMP/justifactu-docs)).

### Built With

* [![Python][Python]][Python-url]
* [![Pytest][Pytest]][Pytest-url]
* [![Docker][Docker]][Docker-url]
* [![Jenkins][Jenkins]][Jenkins-url]
* [![OneDriveLinux][OneDriveLinux]][OneDriveLinux-url]
* [![SharePoint][SharePoint]][SharePoint-url]
* [![Excel][Excel]][Excel-url]
* [![GitHubActions][GitHubActions]][GitHubActions-url]
* [![Git][Git]][Git-url]

PDF handling uses [pypdf](https://pypdf.readthedocs.io/) and [pdfplumber](https://github.com/jsvine/pdfplumber);
ledgers are read with [openpyxl](https://openpyxl.readthedocs.io/).

<p align="right">(<a href="#readme-top">back to top</a>)</p>


<!-- GETTING STARTED -->
## Getting Started

You may follow these steps to get a local copy up and running.

### Prerequisites

* Python 3.11 or newer (CI and the Docker image use 3.12), Git and Make.
   ```sh
   sudo apt install python3.12 python3.12-venv git make -y
   ```
* For full runs against SharePoint only: the [`onedrive`](https://github.com/abraunegg/onedrive) client
  (`scripts/install-onedrive-apt.sh` installs it on Debian/Ubuntu) and access to the project's secrets (SharePoint and
  SMTP), resolved from Docker secrets, the local `secrets/` folder, environment variables or HashiCorp Vault.
  Running single phases on local files needs neither.

### Installation

1. Clone the GitHub repository:
   ```sh
   git clone https://github.com/ICIQ-DMP/justifactu.git
   ```
2. Create the virtual environment, install the runtime and dev dependencies, and install the git hooks:
   ```sh
   cd justifactu
   make dev
   ```

<p align="right">(<a href="#readme-top">back to top</a>)</p>


<!-- USAGE EXAMPLES -->
## Usage

All commands are defined once in the `Makefile`; `CMD` passes flags straight to `python -m justifactu`.
`make run` with no `CMD` only prints `--help`.

### Folder layout

Each run works on one folder. In a full run that's the local copy of `justifactu/runtime` (`--mode prod`) or
`justifactu/runtime-test` (`--mode test`, the default, and `--mode dev`):

```text
<runtime>/
├── FACTURES/                        # bills, named "F <SAP ID>.pdf"
├── Remeses/                         # bank remittance PDFs, any name
├── Targetes/
│   └── <year>/                      # exactly one ledger .xlsx + that year's card statement PDFs
└── FACTURES+PAGAMENTS/              # output
    ├── <year>_FACTURA+PAGAMENT/     # <SAP ID>_F_P.pdf: bill + proof of payment
    ├── QA_ERRORS/                   # QA report of each full run
    └── logs/                        # run log of each full run
```

The ledger's columns are: A = date (`DD/MM`), H = total, J = SAP ID. Rows without a SAP ID are ignored. Only `.xlsx`
is supported.

### Running it

```sh
make run CMD="--help"                # list every CLI flag
make run CMD=""                      # full run: sync runtime-test, run all phases, sync back
make run CMD="--mode prod"           # full run against the production folder (justifactu/runtime)
make auth                            # one-time OneDrive login for a fresh config folder
make run CMD="--dry-run"             # preview the OneDrive syncs (the phases still run on local data)
make run CMD="--phase 1"             # run only phase 1, on local data, no sync
make run CMD="--phase 2"             # run only phase 2, on local data, no sync
make run CMD="--phase 3"             # run only phase 3, on local data, no sync
```

| Flag | Meaning |
|---|---|
| `--mode prod\|test\|dev` | `prod` syncs `justifactu/runtime`; `test` (default) and `dev` sync `justifactu/runtime-test`. `dev` also keeps bills after merging, so the same files can be re-run. |
| `-p/--phase 1\|2\|3` | Run one phase only: no OneDrive sync, no log copy, no e-mail. |
| `--runtime-location <folder>` | The folder the phases work on (default: `<onedrive-data-folder>/<sharepoint-sync-folder>`). |
| `--onedrive-conf-folder`, `--onedrive-data-folder` | OneDrive's config and data folders (default: `$OD_CONF` / `$OD_DATA`, else `service/onedrive/conf` and `service/onedrive/data`). |
| `--sharepoint-sync-folder` | The SharePoint folder to sync (default chosen by `--mode`). |
| `--auth` | One-time OneDrive login; nothing is synced or processed. |
| `--dry-run` | Pass `--dry-run` to the OneDrive syncs. |
| `-l/--location sharepoint\|local` | Input location (`sharepoint` by default; `--auth` only works with it). |

> [!WARNING]
> Path flags create the folder if it doesn't exist, so a typo doesn't fail straight away: it creates an empty folder
> and the run fails later on a missing `FACTURES/`.

### Trying it on local files

To try the phases on real documents without touching SharePoint, copy them into a scratch folder with the layout
above and run each phase against it in `dev` mode, which keeps the bills:

```sh
mkdir -p /tmp/justifactu-try
cp -r /path/to/FACTURES /path/to/Remeses /path/to/Targetes /tmp/justifactu-try/
make run CMD="--phase 1 --runtime-location /tmp/justifactu-try --mode dev"
make run CMD="--phase 2 --runtime-location /tmp/justifactu-try --mode dev"
make run CMD="--phase 3 --runtime-location /tmp/justifactu-try --mode dev"
```

Results appear in `/tmp/justifactu-try/FACTURES+PAGAMENTS/`; each phase's QA report and summary are in the
repository's `logs/` folder. To start over, copy the files again.

> [!CAUTION]
> **Always work on a copy.** Never point `--runtime-location` at the OneDrive data folder (`service/onedrive/data/…`
> or `$OD_DATA`): the phases rename and delete files there, and the next full run uploads those changes to
> SharePoint, including deletions.

### The QA report

Every log line marked as QA-relevant goes to `logs/<date>_qa_report.log`. After a full run it's copied to
`FACTURES+PAGAMENTS/QA_ERRORS/` and e-mailed. It ends with a run summary:

```text
04/11/2026 03:12:47.381 | INFO | justifactu.process | Run summary
  Execution time: 0:04:12
  Bill/payment merges completed: 37 (29 bank payment, 8 card statement)
  Failed merges: 0
  Bills with no matching payment: 5
  Non-payment files in Remeses: 1
  Payment files with unparseable SAP ID: 2
```

Problem files are never moved, so these counts are the current backlog: a bill without a payment, a non-PDF in
`Remeses` or an unreadable payment is reported again on every run until someone fixes it.

<p align="right">(<a href="#readme-top">back to top</a>)</p>


## Development

```sh
make test      # run the test suite (pytest)
make lint      # static checks (ruff + mypy, strict)
make fmt       # auto-format (black + ruff --fix)
make notify CMD="--subject '...' --body '...'"   # send a one-off notification email
make docker-build / make docker-push             # build/push the app's Docker image
```

Run a single test file or test with `PYTHONPATH=src pytest tests/test_process.py -v`.
`tests/test_mail.py::test_send_mail_authenticated_real` sends a real e-mail and fails when the SMTP secrets aren't
available.

Commit messages must follow [Conventional Commits](https://www.conventionalcommits.org/) (checked by a pre-commit
hook). A license header is added automatically to every `.py` file.

<p align="right">(<a href="#readme-top">back to top</a>)</p>


## Deploy to production

Production runs on a dedicated Jenkins agent, defined in `service/agent/` and built from
`service/agent/dockerfile/Dockerfile`. It's a separate image from the app's own `Dockerfile`: it carries the
`onedrive` client and the two persistent volumes (`/onedrive/conf` for OneDrive's config and login token,
`/onedrive/data` for the synced files).

```sh
make prodbuild    # build the Jenkins agent image (service/agent/compose.yml)
make prodrun      # build and start it, detached
```

Before the first production run, log in to OneDrive once from inside the agent container:

```sh
make auth
```

The `Jenkinsfile` runs `make run CMD="... --mode prod"` on that agent. It is still a draft and not wired to a
scheduled job yet; see the [docs site](https://iciq-dmp.github.io/justifactu-docs/) for the deployment design and the
remaining steps.

<p align="right">(<a href="#readme-top">back to top</a>)</p>


<!-- CONTRIBUTING -->
## Contributing

Contributions are what make the open source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

If you have a suggestion that would make this better, please fork the repo and create a pull request. You can also simply open an issue with the tag "enhancement".
Don't forget to give the project a star! Thanks again!

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'feat: add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

<p align="right">(<a href="#readme-top">back to top</a>)</p>

### Top contributors:

<a href="https://github.com/ICIQ-DMP/justifactu/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=ICIQ-DMP/justifactu" alt="contrib.rocks image" />
</a>


<!-- LICENSE -->
## License

Distributed under the GNU GPL v3. See `LICENSE` for more information.

<p align="right">(<a href="#readme-top">back to top</a>)</p>


<!-- CONTACT -->
## Contact

Aleix Mariné-Tena - [amarine@iciq.es](mailto:amarine@iciq.es)

David Romero San Millán - [dromero@iciq.es](mailto:dromero@iciq.es)

<p align="right">(<a href="#readme-top">back to top</a>)</p>


<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->
[contributors-shield]: https://img.shields.io/github/contributors/ICIQ-DMP/justifactu.svg?style=for-the-badge
[contributors-url]: https://github.com/ICIQ-DMP/justifactu/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/ICIQ-DMP/justifactu.svg?style=for-the-badge
[forks-url]: https://github.com/ICIQ-DMP/justifactu/network/members
[stars-shield]: https://img.shields.io/github/stars/ICIQ-DMP/justifactu.svg?style=for-the-badge
[stars-url]: https://github.com/ICIQ-DMP/justifactu/stargazers
[issues-shield]: https://img.shields.io/github/issues/ICIQ-DMP/justifactu.svg?style=for-the-badge
[issues-url]: https://github.com/ICIQ-DMP/justifactu/issues
[license-shield]: https://img.shields.io/github/license/ICIQ-DMP/justifactu.svg?style=for-the-badge
[license-url]: https://github.com/ICIQ-DMP/justifactu/blob/master/LICENSE

<!-- Build with section -->
[Python]: https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54
[Python-url]: https://www.python.org/

[Pytest]: https://img.shields.io/badge/Pytest-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white
[Pytest-url]: https://docs.pytest.org/

[Docker]: https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white
[Docker-url]: https://www.docker.com/

[Jenkins]: https://img.shields.io/badge/Jenkins-D24939?style=for-the-badge&logo=jenkins&logoColor=white
[Jenkins-url]: https://www.jenkins.io/

[OneDriveLinux]: https://img.shields.io/badge/OneDrive%20for%20Linux-0078D4?style=for-the-badge&logo=onedrive&logoColor=white
[OneDriveLinux-url]: https://github.com/abraunegg/onedrive

[SharePoint]: https://img.shields.io/badge/SharePoint-0078D4?style=for-the-badge&logo=sharepoint&logoColor=white
[SharePoint-url]: https://www.microsoft.com/sharepoint

[Excel]: https://img.shields.io/badge/Microsoft%20Excel-217346?style=for-the-badge&logo=excel&logoColor=white
[Excel-url]: https://www.microsoft.com/microsoft-365/excel

[GitHubActions]: https://img.shields.io/badge/GitHub%20Actions-2088FF?style=for-the-badge&logo=github-actions&logoColor=white
[GitHubActions-url]: https://github.com/features/actions

[Git]: https://img.shields.io/badge/Git-F05032?style=for-the-badge&logo=git&logoColor=white
[Git-url]: https://git-scm.com/