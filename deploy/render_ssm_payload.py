#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shlex


def _q(value: str) -> str:
    # robust shell quoting (handles single quotes safely)
    return shlex.quote(value)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--tag", required=True)
    p.add_argument("--aws-region", required=True)
    p.add_argument("--atta-image", required=True)
    p.add_argument("--bucket", required=True)
    p.add_argument("--ssm-path", required=True)
    args = p.parse_args()

    # avoid embedding S3 URI inside quotes; build it on the instance
    commands = [
        "set -euo pipefail",
        f"export TAG={_q(args.tag)}",
        f"export AWS_REGION={_q(args.aws_region)}",
        f"export AWS_DEFAULT_REGION={_q(args.aws_region)}",
        f"export ATTA_IMAGE={_q(args.atta_image)}",
        f"export SSM_PATH={_q(args.ssm_path)}",
        f"export DEPLOY_BUCKET={_q(args.bucket)}",
        'echo "[SSM] whoami=$(whoami)"',
        'echo "[SSM] TAG=${TAG}"',
        'echo "[SSM] ATTA_IMAGE=${ATTA_IMAGE}"',
        'echo "[SSM] SSM_PATH=${SSM_PATH}"',
        's3_uri="s3://${DEPLOY_BUCKET}/atta/${TAG}/atta-${TAG}.tar.gz"',
        'echo "[SSM] Download bundle: ${s3_uri}"',
        'WORK_DIR="/tmp/atta-deploy-${TAG}-$RANDOM"',
        'mkdir -p "${WORK_DIR}"',
        'cd "${WORK_DIR}"',
        'aws s3 cp "${s3_uri}" bundle.tar.gz',
        "tar -xzf bundle.tar.gz",
        "chmod +x deploy/ec2_deploy.sh",
        "./deploy/ec2_deploy.sh",
    ]

    print(json.dumps({"commands": commands}))


if __name__ == "__main__":
    main()