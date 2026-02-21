import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from .base import Base

if TYPE_CHECKING:
    from .users import User


class File(Base):
    """
    Physical File Storage (CAS).
    Stores metadata about the physical file on disk.
    Deduplication happens here: multiple Images can point to one File.
    """

    __tablename__ = "files"

    # SHA-256 hash as Primary Key
    hash: Mapped[str] = mapped_column(String(64), primary_key=True)

    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String, nullable=False)

    # Relative path in storage (e.g., "a1/b2/a1b2c3d4...")
    path: Mapped[str] = mapped_column(String, nullable=False)

    # Reference counting for Garbage Collection
    ref_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    images: Mapped[list["Image"]] = relationship("Image", back_populates="file")

    def __repr__(self) -> str:
        return f"<File(hash={self.hash[:8]}..., mime={self.mime_type}, refs={self.ref_count})>"


class Image(Base):
    """
    User Asset (Image).
    Represents a file owned by a user.
    Links a User to a physical File.
    """

    __tablename__ = "images"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Link to physical file (CAS)
    file_hash: Mapped[str] = mapped_column(ForeignKey("files.hash", ondelete="RESTRICT"), nullable=False, index=True)

    filename: Mapped[str] = mapped_column(String, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    file: Mapped["File"] = relationship("File", back_populates="images")
    user: Mapped["User"] = relationship("User", back_populates="images")

    def __repr__(self) -> str:
        return f"<Image(id={self.id}, filename={self.filename})>"
