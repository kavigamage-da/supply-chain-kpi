"""
s3_utils.py
-----------
Thin boto3 wrapper for uploading / downloading files to/from AWS S3.
All calls are no-ops when USE_S3 is not set to "true" in the environment.

Required env vars (set in .env — never commit real values):
    AWS_ACCESS_KEY_ID
    AWS_SECRET_ACCESS_KEY
    AWS_REGION          (default: ap-south-1  — Mumbai, closest to Sri Lanka)
    S3_BUCKET_NAME
    USE_S3              (true | false)
"""

import os
import logging
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger(__name__)

USE_S3    = os.getenv("USE_S3", "false").lower() == "true"
S3_ENABLED = USE_S3
BUCKET_NAME  = os.getenv("S3_BUCKET_NAME", "supply-chain-kpi-demo")
AWS_REGION   = os.getenv("AWS_REGION", "ap-south-1")

# Lazy-import boto3 so the project runs without AWS credentials when USE_S3=false
_s3_client = None


def _get_client():
    """Return (and cache) a boto3 S3 client."""
    global _s3_client
    if _s3_client is None:
        import boto3
        _s3_client = boto3.client(
            "s3",
            region_name=AWS_REGION,
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        )
    return _s3_client


def upload_file(local_path: str, s3_key: str) -> bool:
    """
    Upload a local file to S3.

    Args:
        local_path: Absolute or relative path to the local file.
        s3_key:     Key (path) under which to store the file in the bucket.

    Returns:
        True on success, False on failure.
    """
    if not USE_S3:
        log.debug("S3 disabled — skipping upload of %s", local_path)
        return False

    if not Path(local_path).exists():
        log.error("Upload failed: %s does not exist", local_path)
        return False

    try:
        client = _get_client()
        client.upload_file(local_path, BUCKET_NAME, s3_key)
        log.info("  ☁ Uploaded  s3://%s/%s", BUCKET_NAME, s3_key)
        return True
    except Exception as exc:
        log.error("  S3 upload error: %s", exc)
        return False


def download_file(s3_key: str, local_path: str) -> bool:
    """
    Download a file from S3 to a local path.

    Args:
        s3_key:     Key in the S3 bucket.
        local_path: Destination path on local disk.

    Returns:
        True on success, False on failure.
    """
    if not USE_S3:
        log.debug("S3 disabled — skipping download of %s", s3_key)
        return False

    try:
        Path(local_path).parent.mkdir(parents=True, exist_ok=True)
        client = _get_client()
        client.download_file(BUCKET_NAME, s3_key, local_path)
        log.info("  ☁ Downloaded s3://%s/%s → %s", BUCKET_NAME, s3_key, local_path)
        return True
    except Exception as exc:
        log.error("  S3 download error: %s", exc)
        return False


def list_bucket(prefix: str = "") -> list[str]:
    """
    List keys in the S3 bucket under an optional prefix.

    Args:
        prefix: Key prefix filter (e.g. "data/").

    Returns:
        List of key strings.
    """
    if not USE_S3:
        return []

    try:
        client   = _get_client()
        paginator = client.get_paginator("list_objects_v2")
        keys     = []
        for page in paginator.paginate(Bucket=BUCKET_NAME, Prefix=prefix):
            for obj in page.get("Contents", []):
                keys.append(obj["Key"])
        return keys
    except Exception as exc:
        log.error("  S3 list error: %s", exc)
        return []


def bucket_exists() -> bool:
    """Check whether the configured S3 bucket is accessible."""
    if not USE_S3:
        return False
    try:
        _get_client().head_bucket(Bucket=BUCKET_NAME)
        return True
    except Exception:
        return False
