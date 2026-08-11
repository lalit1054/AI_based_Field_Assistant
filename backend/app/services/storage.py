"""Presigned MinIO/S3 URLs for attachment upload/download. Milestone 4.

Presigning is a local HMAC computation, not a network call, so a plain
(sync) boto3 client is fine here — no need for aioboto3's async wrapper.
"""

import uuid

import boto3
from botocore.client import Config

from app.config import get_settings


def _client():
    settings = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=settings.minio_endpoint,
        aws_access_key_id=settings.minio_access_key,
        aws_secret_access_key=settings.minio_secret_key,
        region_name=settings.minio_region,
        config=Config(signature_version="s3v4"),
    )


def build_object_key(prefix: str, filename: str) -> str:
    suffix = filename.rsplit(".", 1)[-1] if "." in filename else ""
    unique = uuid.uuid4().hex
    return f"{prefix}/{unique}.{suffix}" if suffix else f"{prefix}/{unique}"


def presign_put(bucket: str, key: str, content_type: str) -> str:
    settings = get_settings()
    return _client().generate_presigned_url(
        "put_object",
        Params={"Bucket": bucket, "Key": key, "ContentType": content_type},
        ExpiresIn=settings.minio_presigned_url_expire_seconds,
    )


def presign_get(bucket: str, key: str) -> str:
    settings = get_settings()
    return _client().generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=settings.minio_presigned_url_expire_seconds,
    )
