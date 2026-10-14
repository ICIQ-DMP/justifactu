## Goal
[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![project_license][license-shield]][license-url]
[![LinkedIn][linkedin-shield]][linkedin-url]

<a id="readme-top"></a>
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
    <li><a href="#usage">Usage</a></li>
    <li><a href="#deploy-to-production">Deploy to production</a></li>
    <li><a href="#contributing">Contributing</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
  </ol>
</details>


## About The Project

justifactu automates matching and merging bills (*factures*) with their corresponding payments (*remeses*) stored in
SharePoint. Payments are renamed to the SAP ID found inside their PDF content; bills, already named with their SAP
ID, are matched against that renamed set and combined into a single justification PDF per pair. It replaces a
manual, repetitive process that previously took significant time each month for the people responsible for these
justifications, leaving only the final review as manual work.

The pipeline runs as a one-shot process: a OneDrive-for-Linux sync brings the relevant SharePoint folder down to
local disk, the matching/merging logic runs entirely against that local copy, and a second one-shot sync pushes the
results (and any renames/deletions) back up. For the full architecture, decision log, and data-flow documentation,
see the [docs site](https://iciq-dmp.github.io/justifactu-docs/) (source: [justifactu-docs](https://github.com/ICIQ-DMP/justifactu-docs)).

### Built With

* [![Python][Python]][Python-url]
* [![Pytest][Pytest]][Pytest-url]
* [![Docker][Docker]][Docker-url]
* [![OneDriveLinux][OneDriveLinux]][OneDriveLinux-url]
* [![SharePoint][SharePoint]][SharePoint-url]
* [![GitHubActions][GitHubActions]][GitHubActions-url]
* [![SFTP][SFTP]][SFTP-url]
* [![Excel][Excel]][Excel-url]
* [![Alpine][Alpine]][Alpine-url]
* [![Git][Git]][Git-url]
<p align="right">(<a href="#readme-top">back to top</a>)</p>


<!-- GETTING STARTED -->
## Getting Started
You may follow these steps to get a local copy up and running.

### Prerequisites

* Install Python version 3.12, Git and other required dependencies.
   ```sh
    sudo apt install python3.12 python3.12-venv git make -y
   ```
### Installation

1. Clone GitHub repository:
   ```sh
   git clone https://github.com/ICIQ-DMP/justifactu.git
   ```
2. Initialize the virtual environment and install git hooks:
   ```sh
    cd justifactu
    make dev
    ```

<p align="right">(<a href="#readme-top">back to top</a>)</p>


<!-- USAGE EXAMPLES -->
## Usage

All commands are defined once in the `Makefile` and run through it; `CMD` passes flags straight to the underlying
`python -m justifactu` invocation.

```sh
make run CMD="--help"              # list every CLI flag
make run CMD=""                    # full run against SharePoint, test-mode folders (the default)
make run CMD="--mode prod"         # full run against SharePoint, production folders
make run CMD="--auth"              # one-time OAuth bootstrap for a fresh OneDrive confdir
make run CMD="--dry-run"           # preview the OneDrive sync without applying it
make run CMD="--phase 1"           # run only payment renaming, against local data, no sync
make run CMD="--phase 2"           # run only bill/payment matching and merging, against local data, no sync
```

Common flags: `-l/--location` (`sharepoint`/`local`), `--auth`, `--dry-run`, `-p/--phase` (`1`/`2`/`3`, isolated
single-stage testing), `--mode` (`prod`/`test`, default `test`), `--onedrive-data-folder`, `--onedrive-conf-folder`,
`--sharepoint-sync-folder`, `--runtime-location`. Full architecture and the reasoning behind each flag are documented
in the [docs site](https://iciq-dmp.github.io/justifactu-docs/).

Other Makefile targets:

```sh
make test      # run the test suite (pytest)
make lint      # static checks (ruff + mypy, strict)
make fmt       # auto-format (black + ruff --fix)
make notify CMD="--subject '...' --body '...'"   # send a one-off notification email
make docker-build / make docker-push             # build/push the app's Docker image
```

<p align="right">(<a href="#readme-top">back to top</a>)</p>


## Deploy to production

Production runs on a dedicated Jenkins agent image, defined in `service/agent/` and built from
`service/agent/dockerfile/Dockerfile` — a separate image from the app's own `Dockerfile`, carrying the `onedrive`
binary and SSH-agent setup Jenkins drives builds on.

```sh
make prodbuild    # build the Jenkins agent image (service/agent/compose.yml)
make prodrun       # build and start it, detached
```

<p align="right">(<a href="#readme-top">back to top</a>)</p>


<!-- CONTRIBUTING -->
## Contributing

Contributions are what make the open source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

If you have a suggestion that would make this better, please fork the repo and create a pull request. You can also simply open an issue with the tag "enhancement".
Don't forget to give the project a star! Thanks again!

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

<p align="right">(<a href="#readme-top">back to top</a>)</p>

### Top contributors:

<a href="https://github.com/ICIQ-DMP/justifactu/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=ICIQ-DMP/justifactu" alt="contrib.rocks image" />
</a>


<!-- LICENSE -->
## License

Distributed under the GNU GPL v3. See `LICENSE.txt` for more information.

<p align="right">(<a href="#readme-top">back to top</a>)</p>


<!-- CONTACT -->
## Contact

Aleix Mariné-Tena- [amarine@iciq.es](amarine@iciq.es)

David Romero San Millán- [dromero@iciq.es](dromero@iciq.es)

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
[license-url]: https://github.com/ICIQ-DMP/justifactu/blob/master/LICENSE.txt
[linkedin-shield]: https://img.shields.io/badge/-LinkedIn-black.svg?style=for-the-badge&logo=linkedin&colorB=555
[linkedin-url]: https://linkedin.com/in/linkedin_username
[product-screenshot]: images/screenshot.png

<!-- Build with section -->
[Python]: https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54
[Python-url]: https://www.python.org/

[Pytest]: https://img.shields.io/badge/Pytest-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white
[Pytest-url]: https://docs.pytest.org/

[Docker]: https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white
[Docker-url]: https://www.docker.com/

[OneDriveLinux]: https://img.shields.io/badge/OneDrive%20for%20Linux-0078D4?style=for-the-badge&logo=onedrive&logoColor=white
[OneDriveLinux-url]: https://github.com/abraunegg/onedrive

[SharePoint]: https://img.shields.io/badge/SharePoint-0078D4?style=for-the-badge&logo=sharepoint&logoColor=white
[SharePoint-url]: https://www.microsoft.com/sharepoint

[GitHubActions]: https://img.shields.io/badge/GitHub%20Actions-2088FF?style=for-the-badge&logo=github-actions&logoColor=white
[GitHubActions-url]: https://github.com/features/actions

[SFTP]: https://img.shields.io/badge/SFTP-3A3A3A?style=for-the-badge&logo=ssh&logoColor=white
[SFTP-url]: https://datatracker.ietf.org/doc/html/draft-ietf-secsh-filexfer

[Excel]: https://img.shields.io/badge/Microsoft%20Excel-217346?style=for-the-badge&logo=excel&logoColor=white
[Excel-url]: https://www.microsoft.com/microsoft-365/excel

[Alpine]: https://img.shields.io/badge/Alpine%20Linux-0D597F?style=for-the-badge&logo=alpine-linux&logoColor=white
[Alpine-url]: https://www.alpinelinux.org/

[Git]: https://img.shields.io/badge/Git-F05032?style=for-the-badge&logo=git&logoColor=white
[Git-url]: https://git-scm.com/