#!/usr/bin/env bash
set -euo pipefail

APP_NAME="atta"
APP_DIR="/opt/${APP_NAME}"
RELEASES_DIR="${APP_DIR}/releases"
CURRENT_DIR="${APP_DIR}/current"
STATE_DIR="${APP_DIR}/state"
ENV_FILE="${APP_DIR}/.env"
RUNTIME_ENV_FILE="${STATE_DIR}/runtime.env"

TAG="${TAG:?TAG is required}"
SSM_PATH="${SSM_PATH:-/atta/dev}"
ATTA_IMAGE="${ATTA_IMAGE:?ATTA_IMAGE is required}"

sudo mkdir -p "${RELEASES_DIR}/${TAG}" "${STATE_DIR}/output"

command -v aws >/dev/null 2>&1 || { echo "AWS CLI missing on EC2"; exit 1; }

# install docker on EC2 if missing
if ! command -v docker >/dev/null 2>&1; then
  echo "Docker missing. Installing..."
  sudo dnf install -y docker
fi

echo "Enable & start docker..."
sudo systemctl enable --now docker

echo "Copy deploy bundle to releases..."
# persist the extracted deploy bundle to /opt/atta/releases/<TAG>
sudo rm -rf "${RELEASES_DIR:?}/${TAG:?}"/*
sudo cp -a ./* "${RELEASES_DIR}/${TAG}/"

echo "Switch current symlink..."
sudo ln -sfn "${RELEASES_DIR}/${TAG}" "${CURRENT_DIR}"

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

sudo test -s "${ENV_TMP}"
sudo mv "${ENV_TMP}" "${ENV_FILE}"
sudo chmod 600 "${ENV_FILE}"
echo "OK: rendered env keys count: $(sudo wc -l < "${ENV_FILE}")"

# write runtime env (image uri) for systemd unit expansion
echo "ATTA_IMAGE=${ATTA_IMAGE}" | sudo tee "${RUNTIME_ENV_FILE}" >/dev/null
sudo chmod 600 "${RUNTIME_ENV_FILE}"

# docker login to ECR and pull image (uses instance role)
AWS_REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-us-east-1}}"
ECR_REGISTRY="$(echo "${ATTA_IMAGE}" | awk -F/ '{print $1}')"

echo "Login to ECR: ${ECR_REGISTRY}"
aws ecr get-login-password --region "${AWS_REGION}" \
  | sudo docker login --username AWS --password-stdin "${ECR_REGISTRY}"

echo "Pull image: ${ATTA_IMAGE}"
sudo docker pull "${ATTA_IMAGE}"

echo "Install systemd unit..."
sudo cp "${CURRENT_DIR}/deploy/systemd/atta.service" /etc/systemd/system/atta.service
sudo test -f /etc/systemd/system/atta.service

sudo systemctl daemon-reload

# enable unit on boot
sudo systemctl enable atta.service

echo "Done. Docker image pulled, unit installed."