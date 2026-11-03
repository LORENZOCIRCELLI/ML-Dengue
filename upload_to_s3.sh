#!/usr/bin/env bash

set -euo pipefail

LOCAL_DIR="/home/admin/ml-dengue/outputs/"
S3_DEST="s3://dengue-model-results-mldengue/outputs/"
AWS_REGION="us-east-1"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting S3 sync..."

aws s3 sync "$LOCAL_DIR" "$S3_DEST" \
  --region "$AWS_REGION"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] S3 sync completed successfully."
