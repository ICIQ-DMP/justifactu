#!/bin/sh
set -eu

if [ ! -f "${ONEDRIVE_CONF_DIR}/refresh_token" ]; then
  cp "${SECRETS_DIR}/ONEDRIVE_TOKEN" "${ONEDRIVE_CONF_DIR}/refresh_token"
fi

exec setup-sshd "$@"