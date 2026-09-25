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

RUN apt-get update && \
    apt-get install -y python3 python3-pip python3-venv && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY install-onedrive-apt.sh .
RUN bash install-onedrive-apt.sh

COPY service/agent/entrypoint/entrypoint.sh /entrypoint.sh
RUN chmod u+x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]