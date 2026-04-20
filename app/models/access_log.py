from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AccessLog(Base):
    __tablename__ = "access_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), nullable=False, index=True)
    rfid_card_id: Mapped[int | None] = mapped_column(ForeignKey("rfid_cards.id"), nullable=True, index=True)
    authorized_user_id: Mapped[int | None] = mapped_column(ForeignKey("authorized_users.id"), nullable=True, index=True)
    assignment_id: Mapped[int | None] = mapped_column(ForeignKey("rfid_assignments.id"), nullable=True, index=True)

    uid_scanned: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    access_status: Mapped[str] = mapped_column(String(20), nullable=False)
    access_direction: Mapped[str | None] = mapped_column(String(20), nullable=True)
    reason: Mapped[str | None] = mapped_column(String(100), nullable=True)

    scanned_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    door_opened: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    device = relationship("Device")
    rfid_card = relationship("RfidCard")
    authorized_user = relationship("AuthorizedUser")
    assignment = relationship("RfidAssignment")