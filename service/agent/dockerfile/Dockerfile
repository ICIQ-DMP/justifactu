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

# ---- build stage: compile onedrive from a pinned release tag -----------------
FROM debian:12 AS onedrive-build
# TODO: confirm the current 2.5.x tag at https://github.com/abraunegg/onedrive/releases
ARG ONEDRIVE_VERSION=v2.5.6
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential curl ca-certificates pkg-config \
        libcurl4-openssl-dev libsqlite3-dev ldc && \
    rm -rf /var/lib/apt/lists/*
RUN mkdir /src && \
    curl -fsSL "https://github.com/abraunegg/onedrive/archive/refs/tags/${ONEDRIVE_VERSION}.tar.gz" \
        | tar xz --strip-components=1 -C /src
WORKDIR /src
RUN ./configure && make && make install          # -> /usr/local/bin/onedrive

# ---- agent stage ------------------------------------------------------------
FROM jenkins/ssh-agent:latest

RUN apt-get update && \
    apt-get install -y python3 python3-pip python3-venv locales \
                       libcurl4 libsqlite3-0 ca-certificates && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    sed -i '/es_ES.UTF-8/s/^# //' /etc/locale.gen && \
    locale-gen && \
    update-locale LANG=es_ES.UTF-8

ENV LANG=es_ES.UTF-8
ENV LANGUAGE=es_ES:es
ENV LC_ALL=es_ES.UTF-8

# OneDrive-for-Linux client (pinned build from the stage above; see design doc D6)
COPY --from=onedrive-build /usr/local/bin/onedrive /usr/local/bin/onedrive

COPY ../entrypoint/entrypoint.sh /entrypoint.sh
RUN chmod u+x /entrypoint.sh
ENTRYPOINT ["entrypoint.sh"]
