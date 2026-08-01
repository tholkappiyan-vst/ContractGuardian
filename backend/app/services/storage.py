import uuid
import boto3
from fastapi import UploadFile
from app.core.config import get_settings


def _get_s3_client():
    settings = get_settings()
    kwargs = {
        "region_name": settings.s3_region,
        "aws_access_key_id": settings.aws_access_key_id,
        "aws_secret_access_key": settings.aws_secret_access_key,
    }
    if settings.s3_endpoint_url:
        kwargs["endpoint_url"] = settings.s3_endpoint_url
    return boto3.client("s3", **kwargs)


async def upload_file(file: UploadFile, user_id: str) -> tuple[str, int]:
    """Upload file to S3, return (storage_key, file_size)."""
    settings = get_settings()
    ext = file.filename.rsplit(".", 1)[-1].lower()
    storage_key = f"contracts/{user_id}/{uuid.uuid4()}.{ext}"

    content = await file.read()
    file_size = len(content)

    client = _get_s3_client()
    client.put_object(
        Bucket=settings.s3_bucket,
        Key=storage_key,
        Body=content,
        ContentType=file.content_type or "application/octet-stream",
    )

    return storage_key, file_size


async def download_file(storage_key: str) -> bytes:
    """Download file content from S3."""
    settings = get_settings()
    client = _get_s3_client()
    response = client.get_object(Bucket=settings.s3_bucket, Key=storage_key)
    return response["Body"].read()


async def delete_file(storage_key: str):
    """Delete file from S3."""
    settings = get_settings()
    client = _get_s3_client()
    client.delete_object(Bucket=settings.s3_bucket, Key=storage_key)
