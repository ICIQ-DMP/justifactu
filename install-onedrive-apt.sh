#!/usr/bin/env bash
# install-onedrive-apt.sh — idempotent install of OneDrive-for-Linux via the
# OpenSuSE Build Service (OBS) community package repo, for Debian/Ubuntu
# hosts. Works on a bare PC (needs sudo) or inside a Docker build (root,
# sudo often absent).

set -euo pipefail

KEYRING="/usr/share/keyrings/obs-onedrive.gpg"
SOURCES_FILE="/etc/apt/sources.list.d/onedrive.list"
OBS_BASE="https://download.opensuse.org/repositories/home:/npreining:/debian-ubuntu-onedrive"

log() { printf '[install-onedrive] %s\n' "$*" >&2; }
die() { log "ERROR: $*"; exit 1; }


command -v apt-get >/dev/null 2>&1 || die "this script targets Debian/Ubuntu (apt-get) hosts only"

[ -r /etc/os-release ] || die "cannot detect the OS version (/etc/os-release missing)"
. /etc/os-release
[ -n "${VERSION_ID:-}" ] || die "could not determine VERSION_ID from /etc/os-release"

REPO_URL="${OBS_BASE}/xUbuntu_${VERSION_ID}"
log "Target repo: $REPO_URL"

# ---- 0. ensure the tools this script itself needs are present --------------
missing_tools=()
command -v wget >/dev/null 2>&1 || missing_tools+=(wget)
command -v gpg  >/dev/null 2>&1 || missing_tools+=(gnupg)
command -v dpkg >/dev/null 2>&1 || missing_tools+=(dpkg)
if [ "${#missing_tools[@]}" -gt 0 ]; then
    log "Installing missing prerequisite tools: ${missing_tools[*]}"
    apt-get update -y
    apt-get install -y --no-install-recommends "${missing_tools[@]}"
fi

# ---- 1. repo signing key ----------------------------------------------------
log "Fetching and installing the OBS repository key..."
wget -qO - "${REPO_URL}/Release.key" | gpg --dearmor | tee "$KEYRING" > /dev/null

# ---- 2. apt source list entry -----------------------------------------------
log "Registering the apt source..."
echo "deb [arch=$(dpkg --print-architecture) signed-by=${KEYRING}] ${REPO_URL}/ ./" \
    | tee "$SOURCES_FILE" > /dev/null

# ---- 3. refresh the package cache -------------------------------------------
log "Updating apt package cache..."
apt-get update -y

# ---- 4. install ---------------------------------------------------------------
log "Installing onedrive..."
apt install -y --no-install-recommends --no-install-suggests onedrive

# ---- 5. verify ------------------------------------------------------------------
command -v onedrive >/dev/null 2>&1 || die "post-install check failed: 'onedrive' not found on PATH"
log "onedrive installed: $(onedrive --version 2>/dev/null | tr '\n' ' ')"
