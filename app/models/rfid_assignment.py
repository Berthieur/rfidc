from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class RfidAssignment(Base):
    __tablename__ = "rfid_assignments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    rfid_card_id: Mapped[int] = mapped_column(ForeignKey("rfid_cards.id"), nullable=False, index=True)
    authorized_user_id: Mapped[int] = mapped_column(ForeignKey("authorized_users.id"), nullable=False, index=True)
    assigned_by_staff_id: Mapped[int] = mapped_column(ForeignKey("staff_users.id"), nullable=False, index=True)

    assigned_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    expired_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    unassigned_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    rfid_card = relationship("RfidCard")
    authorized_user = relationship("AuthorizedUser")
    assigned_by_staff = relationship("StaffUser")