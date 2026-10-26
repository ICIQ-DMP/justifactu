# =============================================================================
# Jenkins agent image for the justifactu scheduled data run.
#
# Adds the OneDrive-for-Linux client (abraunegg/onedrive) to the existing agent,
# installed via the OpenSuSE Build Service (OBS) community apt repo rather than
# compiled from source (amended from D6 — the OBS repo resolves the "no
# properly maintained package" concern that originally motivated compiling).
#
# Design and rationale: docs/explanation/onedrive_sync_and_orchestration.md
#   - Section 6.2  (the pinned agent image)
#   - Decision D6  (amended — see above)
#
# Build context: repo root (not this directory). Build with:
#   docker build -f service/agent/dockerfile/Dockerfile -t justifactu-agent .
# =============================================================================

FROM jenkins/ssh-agent:latest

ENV OD_CONF=/onedrive/conf
ENV OD_DATA=/onedrive/data
ENV BILLS_INPUT_FOLDER=FACTURES
ENV PAYMENTS_INPUT_FOLDER=Remeses

RUN apt-get update && \
    apt-get install -y python3 python3-pip python3-venv && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY scripts/install-onedrive-apt.sh .
RUN bash install-onedrive-apt.sh

# /onedrive/conf and /onedrive/data are mounted as named volumes by compose.yml; /onedrive/logs
# (the client's own log_dir, service/onedrive/conf/config) has no volume at all. None of the
# three exist in the image otherwise, so on first mount Docker would create /onedrive/conf and
# /onedrive/data as fresh root:root 0755 dirs — unwritable by the non-root `jenkins` user Jenkins
# SSH build steps actually run as. Creating them here, owned by jenkins, means Docker's
# volume-initialization-from-image copies that ownership into the new volumes on first mount.
RUN mkdir -p /onedrive/conf /onedrive/data /onedrive/logs && \
    chown -R jenkins:jenkins /onedrive

# onedrive's own config-change/--resync detection (src/config.d, applicationChangeWhereResyncRequired)
# treats --syncdir differing from the confdir's own config.sync_dir as a real, resync-worthy change
# UNLESS it detects /entrypoint.sh at the filesystem root (its heuristic for "this is a container
# where sync_dir is always CLI/env-overridden, so don't flag that"). We always pass --syncdir, and
# this image is built from jenkins/ssh-agent + apt-installed onedrive rather than abraunegg's own
# Docker image (which ships that file), so without it every run spuriously demands a --resync via
# "sync_dir: CLI override of config file option, --resync needed". The file's content is never read,
# only its existence is checked, so an empty marker is sufficient.
RUN touch /entrypoint.sh
