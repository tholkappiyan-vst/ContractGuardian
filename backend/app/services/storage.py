import uuid
import os
from pathlib import Path
from fastapi import UploadFile

UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", "./data/uploads"))


async def upload_file(file: UploadFile, user_id: str) -> tuple[str, int]:
    """Upload file to local disk, return (storage_key, file_size)."""
    ext = file.filename.rsplit(".", 1)[-1].lower()
    storage_key = f"contracts/{user_id}/{uuid.uuid4()}.{ext}"

    full_path = UPLOAD_DIR / storage_key
    full_path.parent.mkdir(parents=True, exist_ok=True)

    content = await file.read()
    file_size = len(content)
    full_path.write_bytes(content)

    return storage_key, file_size


async def download_file(storage_key: str) -> bytes:
    """Download file content from local disk."""
    full_path = UPLOAD_DIR / storage_key
    return full_path.read_bytes()


async def delete_file(storage_key: str):
    """Delete file from local disk."""
    full_path = UPLOAD_DIR / storage_key
    if full_path.exists():
        full_path.unlink()
