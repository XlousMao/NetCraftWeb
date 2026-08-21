"""图片服务：上传、SHA-256 去重、主图管理、宽高识别。"""

from __future__ import annotations

import struct
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.item import Item, ItemImage
from app.services.storage import storage


def get_image_size(data: bytes) -> tuple[Optional[int], Optional[int]]:
    """读取常见图片格式（PNG/JPEG/GIF/BMP）的宽高。"""
    try:
        if data[:8] == b"\x89PNG\r\n\x1a\n" and len(data) >= 24:
            width, height = struct.unpack(">II", data[16:24])
            return width, height
        if data[:2] == b"\xff\xd8":  # JPEG
            i = 2
            while i < len(data):
                if data[i] != 0xFF:
                    i += 1
                    continue
                marker = data[i + 1]
                i += 2
                if marker in (0xD8, 0xD9):
                    continue
                if i + 2 > len(data):
                    break
                seg_len = struct.unpack(">H", data[i:i + 2])[0]
                if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                              0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                    if i + 7 <= len(data):
                        height, width = struct.unpack(">HH", data[i + 3:i + 7])
                        return width, height
                i += seg_len
        if data[:6] in (b"GIF87a", b"GIF89a"):
            width, height = struct.unpack("<HH", data[6:10])
            return width, height
        if data[:2] == b"BM" and len(data) >= 26:
            width, height = struct.unpack("<II", data[18:26])
            return width, height
    except Exception:
        pass
    return None, None


class ImageService:
    def __init__(self, db: Session):
        self.db = db

    def upload(
        self,
        item_id: int,
        data: bytes,
        filename: str,
        image_type: str = "icon",
        is_primary: bool = False,
    ) -> ItemImage:
        """上传图片，按 SHA-256 去重：完全相同的内容不重复落盘。"""
        file_hash = storage.sha256(data)

        # 去重：同 item 下同哈希直接返回已有记录
        existing = self.db.execute(
            select(ItemImage).where(
                ItemImage.item_id == item_id, ItemImage.file_hash == file_hash
            )
        ).scalar_one_or_none()
        if existing:
            return existing

        rel_path = storage.save(data, filename)
        width, height = get_image_size(data)

        # 若设为主图，先取消其他主图
        if is_primary:
            self.db.execute(
                ItemImage.__table__.update()
                .where(ItemImage.item_id == item_id)
                .values(is_primary=False)
            )
        # 若该物品还没有主图，自动设为首张为主图
        count = self.db.execute(
            select(ItemImage).where(ItemImage.item_id == item_id)
        ).first()
        if count is None:
            is_primary = True

        image = ItemImage(
            item_id=item_id,
            file_path=rel_path,
            file_hash=file_hash,
            image_type=image_type,
            is_primary=is_primary,
            width=width,
            height=height,
        )
        self.db.add(image)
        
        if is_primary:
            item = self.db.get(Item, item_id)
            if item:
                item.icon_url = f"/storage/{rel_path}"

        self.db.flush()
        return image

    def set_primary(self, item_id: int, image_id: int) -> Optional[ItemImage]:
        image = self.db.get(ItemImage, image_id)
        if image is None or image.item_id != item_id:
            return None
        self.db.execute(
            ItemImage.__table__.update()
            .where(ItemImage.item_id == item_id)
            .values(is_primary=False)
        )
        image.is_primary = True
        
        item = self.db.get(Item, item_id)
        if item:
            item.icon_url = f"/storage/{image.file_path}"
            
        self.db.flush()
        return image
