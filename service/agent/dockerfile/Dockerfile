# =============================================================================
# DRAFT — Jenkins agent image for the justifactu scheduled data run.
#
# Adds the OneDrive-for-Linux client (abraunegg/onedrive) to the existing agent.
# The client has no official pre-built binary, so it is compiled from a pinned
# source tag in a throw-away build stage and the binary is copied in.
#
# Design and rationale: docs/explanation/onedrive_sync_and_orchestration.md
#   - Section 6.2  (the pinned agent image)
#   - Decision D6  (build from a pinned source tag, not apt / not another image)
#
# Nothing about the existing Python / locale / entrypoint setup changes; the
# only additions are the build stage, the onedrive runtime libraries, and the
# COPY of the binary.
# =============================================================================


# ---- agent stage ------------------------------------------------------------
FROM jenkins/ssh-agent:latest

RUN apt-get update && \
    apt-get install -y python3 python3-pip python3-venv && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY ./install-onedrive-apt.sh .
RUN bash install-onedrive-apt.sh

COPY ../entrypoint/entrypoint.sh /entrypoint.sh
RUN chmod u+x /entrypoint.sh
ENTRYPOINT ["entrypoint.sh"]
