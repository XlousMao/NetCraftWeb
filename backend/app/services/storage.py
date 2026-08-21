"""文件存储抽象层。

MVP 使用本地文件系统，接口保持抽象，后续可无痛切换到 MinIO / S3 / OSS。
"""

from __future__ import annotations

import hashlib
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import BinaryIO, Optional

from app.core.config import settings


class StorageService:
    """本地文件存储实现。"""

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(base_dir or settings.UPLOAD_DIR).resolve()

    def _ensure_dir(self) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save(
        self,
        data: bytes,
        filename: str,
        content_type: Optional[str] = None,
    ) -> str:
        """保存字节内容，返回相对路径。"""
        self._ensure_dir()
        ext = Path(filename).suffix.lower() or ".bin"
        # 用内容哈希作为文件名，天然去重
        digest = hashlib.sha256(data).hexdigest()
        rel_path = f"{digest[:2]}/{digest}{ext}"
        abs_path = self.base_dir / rel_path
        if not abs_path.exists():
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            with open(abs_path, "wb") as f:
                f.write(data)
        return rel_path

    def read(self, rel_path: str) -> Optional[bytes]:
        abs_path = (self.base_dir / rel_path).resolve()
        # 防止路径穿越
        if not str(abs_path).startswith(str(self.base_dir)):
            return None
        if not abs_path.exists():
            return None
        return abs_path.read_bytes()

    def delete(self, rel_path: str) -> bool:
        abs_path = (self.base_dir / rel_path).resolve()
        if not str(abs_path).startswith(str(self.base_dir)):
            return False
        try:
            if abs_path.exists():
                abs_path.unlink()
            return True
        except OSError:
            return False

    def sha256(self, data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()


storage = StorageService()
