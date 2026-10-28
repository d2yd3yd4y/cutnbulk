from __future__ import annotations

import io
from pathlib import Path
from uuid import uuid4

from PIL import Image, ImageOps

from app.config import get_settings


class StorageError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def _prepare_image_bytes(raw: bytes) -> tuple[bytes, str]:
    settings = get_settings()
    if len(raw) > settings.max_upload_bytes:
        raise StorageError("图片太大，请压缩后再上传。")
    try:
        with Image.open(io.BytesIO(raw)) as image:
            image.load()
            width, height = image.size
            if width * height > settings.max_image_pixels:
                raise StorageError("图片尺寸过大。")
            # Fix phone EXIF orientation and strip metadata (GPS, etc.).
            image = ImageOps.exif_transpose(image)
            if image.mode not in {"RGB", "L"}:
                image = image.convert("RGB")
            elif image.mode == "L":
                image = image.convert("RGB")
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG", quality=85, optimize=True)
            return buffer.getvalue(), "image/jpeg"
    except StorageError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise StorageError("请上传有效的图片文件。") from exc


class StorageService:
    def save_meal_image(self, user_id: str, raw: bytes, filename: str | None = None) -> str:
        content, content_type = _prepare_image_bytes(raw)
        object_key = f"meals/{user_id}/{uuid4().hex}.jpg"
        settings = get_settings()
        if settings.is_production or settings.uses_cloud_storage:
            self._upload_supabase(object_key, content, content_type)
        else:
            self._save_local(object_key, content)
        return object_key

    def delete_object(self, object_key: str | None) -> None:
        if not object_key:
            return
        settings = get_settings()
        if object_key.startswith("/uploads/"):
            path = settings.local_upload_dir / object_key.replace("/uploads/", "", 1)
            if path.exists():
                path.unlink()
            return
        if settings.uses_cloud_storage:
            try:
                client = self._supabase_client()
                client.storage.from_(settings.supabase_storage_bucket).remove([object_key])
            except Exception:
                return
        else:
            path = settings.local_upload_dir / object_key
            if path.exists():
                path.unlink()

    def open_local_file(self, object_key: str) -> Path | None:
        settings = get_settings()
        if object_key.startswith("/uploads/"):
            path = settings.local_upload_dir / object_key.replace("/uploads/", "", 1)
        else:
            path = settings.local_upload_dir / object_key
        return path if path.exists() else None

    def create_signed_url(self, object_key: str) -> str | None:
        settings = get_settings()
        if not settings.uses_cloud_storage:
            return None
        client = self._supabase_client()
        result = client.storage.from_(settings.supabase_storage_bucket).create_signed_url(
            object_key,
            settings.signed_url_ttl_seconds,
        )
        if isinstance(result, dict):
            return result.get("signedURL") or result.get("signedUrl")
        return getattr(result, "signed_url", None) or getattr(result, "signedURL", None)

    def _save_local(self, object_key: str, content: bytes) -> None:
        settings = get_settings()
        destination = settings.local_upload_dir / object_key
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)

    def _upload_supabase(self, object_key: str, content: bytes, content_type: str) -> None:
        settings = get_settings()
        if not settings.uses_cloud_storage:
            raise StorageError("生产环境未配置云存储。")
        client = self._supabase_client()
        try:
            client.storage.from_(settings.supabase_storage_bucket).upload(
                object_key,
                content,
                {"content-type": content_type, "upsert": "false"},
            )
        except Exception as exc:  # noqa: BLE001
            raise StorageError("图片上传失败，请稍后重试。") from exc

    def _supabase_client(self):
        settings = get_settings()
        from supabase import create_client

        return create_client(settings.supabase_url, settings.supabase_service_role_key)


storage_service = StorageService()
