from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Ticket(Base):
    __tablename__ = "tickets"
    __table_args__ = (
        CheckConstraint(
            "status IN ('open', 'in_progress', 'pending_review', 'resolved', 'escalated')",
            name="ck_tickets_status",
        ),
        CheckConstraint(
            "priority IN ('low', 'medium', 'high', 'urgent')",
            name="ck_tickets_priority",
        ),
        CheckConstraint(
            "status != 'resolved' OR resolved_at IS NOT NULL",
            name="ck_tickets_resolved_at",
        ),
        Index("ix_tickets_status_created_at", "status", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticket_number: Mapped[str] = mapped_column(
        String(36), unique=True, index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    priority: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    assigned_team: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default="open", index=True, nullable=False
    )
    requester_name: Mapped[str] = mapped_column(String(120), nullable=False)
    requester_email: Mapped[str] = mapped_column(String(254), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, index=True, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    events: Mapped[list["TicketEvent"]] = relationship(
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="TicketEvent.timestamp, TicketEvent.id",
    )
    suggestions: Mapped[list["TicketSuggestion"]] = relationship(
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="TicketSuggestion.created_at, TicketSuggestion.id",
    )


class TicketEvent(Base):
    __tablename__ = "ticket_events"
    __table_args__ = (
        Index("ix_ticket_events_ticket_timestamp", "ticket_id", "timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticket_id: Mapped[int] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    previous_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    actor: Mapped[str] = mapped_column(String(100), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    ticket: Mapped[Ticket] = relationship(back_populates="events")


class TicketSuggestion(Base):
    __tablename__ = "ticket_suggestions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'accepted', 'edited', 'rejected')",
            name="ck_ticket_suggestions_status",
        ),
        CheckConstraint(
            "evidence_state IN ('suggested', 'insufficient_evidence')",
            name="ck_ticket_suggestions_evidence_state",
        ),
        Index("ix_ticket_suggestions_ticket_status", "ticket_id", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticket_id: Mapped[int] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE"), index=True, nullable=False
    )
    issue_summary: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_resolution: Mapped[str] = mapped_column(Text, nullable=False)
    approved_resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_state: Mapped[str] = mapped_column(String(32), nullable=False)
    recommended_steps: Mapped[list[dict[str, object]]] = mapped_column(
        JSON, default=list, nullable=False
    )
    supporting_sources: Mapped[list[dict[str, object]]] = mapped_column(
        JSON, default=list, nullable=False
    )
    confidence_warning: Mapped[str] = mapped_column(Text, nullable=False)
    manual_review_required: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    manual_review_reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), default="pending", index=True, nullable=False
    )
    reviewer: Mapped[str | None] = mapped_column(String(40), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    ticket: Mapped[Ticket] = relationship(back_populates="suggestions")
