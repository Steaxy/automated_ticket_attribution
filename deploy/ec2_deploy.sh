#!/usr/bin/env bash
set -euo pipefail

APP_NAME="atta"
APP_DIR="/opt/${APP_NAME}"
RELEASES_DIR="${APP_DIR}/releases"
CURRENT_DIR="${APP_DIR}/current"
VENV_DIR="${APP_DIR}/venv"
STATE_DIR="${APP_DIR}/state"
ENV_FILE="${APP_DIR}/.env"

TAG="${TAG:?TAG is required}"
S3_URI="${S3_URI:?S3_URI is required}"
SSM_PATH="${SSM_PATH:-/atta/dev}"

sudo mkdir -p "${RELEASES_DIR}/${TAG}" "${STATE_DIR}/output"

command -v aws >/dev/null 2>&1 || { echo "AWS CLI missing on EC2"; exit 1; }

echo "Downloading artifact: ${S3_URI}"
aws s3 cp "${S3_URI}" "/tmp/${APP_NAME}-${TAG}.tar.gz"

echo "Unpacking..."
tar -xzf "/tmp/${APP_NAME}-${TAG}.tar.gz" -C "${RELEASES_DIR}/${TAG}"

echo "Switch current symlink..."
ln -sfn "${RELEASES_DIR}/${TAG}" "${CURRENT_DIR}"

# persist output across releases
rm -rf "${CURRENT_DIR}/output" || true
ln -sfn "${STATE_DIR}/output" "${CURRENT_DIR}/output"

echo "Create venv if missing..."
if [ ! -d "${VENV_DIR}" ]; then
  python3 -m venv "${VENV_DIR}"
fi

# Install deps (hardened: always use venv python, force-sync, sanity checks)
echo "Install deps..."
"${VENV_DIR}/bin/python" -m pip install --upgrade pip setuptools wheel
"${VENV_DIR}/bin/python" -m pip install --upgrade --no-cache-dir -r "${CURRENT_DIR}/requirements.txt"
"${VENV_DIR}/bin/python" -m pip check

# fail fast if runtime deps/imports are missing (prevents systemd crash later)
"${VENV_DIR}/bin/python" -c "import requests; print('OK: requests installed')"
"${VENV_DIR}/bin/python" -c "import app.cmd.main; print('OK: app.cmd.main imports')"

# render env atomically and fail deploy if empty/missing
echo "Render .env from Parameter Store path: ${SSM_PATH}"
ENV_TMP="/tmp/${APP_NAME}.env.${TAG}.$RANDOM"

aws ssm get-parameters-by-path \
  --path "${SSM_PATH}" \
  --recursive \
  --with-decryption \
  --query "Parameters[*].[Name,Value]" \
  --output text \
| awk -F'\t' '{name=$1; sub(".*/","",name); print name"="$2}' \
| sudo tee "${ENV_TMP}" >/dev/null

# ensure env file is not empty
sudo test -s "${ENV_TMP}"

sudo mv "${ENV_TMP}" "${ENV_FILE}"
sudo chmod 600 "${ENV_FILE}"

# safe debug signal (doesn't print secrets)
echo "OK: rendered env keys count: $(sudo wc -l < "${ENV_FILE}")"

echo "Install systemd units..."
sudo cp "${CURRENT_DIR}/deploy/systemd/atta.service" /etc/systemd/system/atta.service

# verify unit installed
sudo test -f /etc/systemd/system/atta.service

sudo systemctl daemon-reload
sudo systemctl --no-pager --full status atta.service | sed -n '1,40p' || true

echo "Done. Service is installed."