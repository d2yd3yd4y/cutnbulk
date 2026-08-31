from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile


UPLOAD_DIR = Path("app/uploads")


async def save_upload(image: UploadFile | None) -> str | None:
    if not image or not image.filename:
        return None

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    suffix = Path(image.filename).suffix.lower() or ".jpg"
    filename = f"{uuid4().hex}{suffix}"
    destination = UPLOAD_DIR / filename
    content = await image.read()
    destination.write_bytes(content)
    return f"/uploads/{filename}"
