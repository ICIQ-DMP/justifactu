#!/bin/sh

# OneDrive token
if [ ! -f "${ONEDRIVE_CONF_DIR}/refresh_token" ]; then
  cp "${SECRETS_DIR}/ONEDRIVE_TOKEN" "${ONEDRIVE_CONF_DIR}/refresh_token"
fi

envsubst < /onedrive/templates/config > /onedrive/conf/config
envsubst < /onedrive/templates/refresh_token > /onedrive/conf/refresh_token

exec setup-sshd $@  # original entrypoint

