import json
from pathlib import Path

from sqlalchemy import select

from app.db.base import Base
from app.db.database import SessionLocal, engine
from app.models.ticket import Ticket, TicketEvent, utc_now
from app.schemas.ticket import TicketStatus

SEED_FILE = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "sample_tickets"
    / "demo_tickets.json"
)


def seed_tickets() -> int:
    with SEED_FILE.open(encoding="utf-8") as seed_file:
        seed_data = json.load(seed_file)

    Base.metadata.create_all(bind=engine)
    inserted = 0
    database = SessionLocal()
    try:
        with database.begin():
            for record in seed_data:
                exists = database.scalar(
                    select(Ticket.id).where(
                        Ticket.ticket_number == record["ticket_number"]
                    )
                )
                if exists is not None:
                    continue
                status = TicketStatus(record["status"])
                resolved_at = utc_now() if status is TicketStatus.RESOLVED else None
                ticket = Ticket(
                    **record,
                    created_at=utc_now(),
                    updated_at=utc_now(),
                    resolved_at=resolved_at,
                )
                ticket.events.append(
                    TicketEvent(
                        event_type="created",
                        previous_value=None,
                        new_value=status.value,
                        actor="demo-user",
                    )
                )
                database.add(ticket)
                inserted += 1
    finally:
        database.close()
    return inserted


if __name__ == "__main__":
    print(f"Inserted {seed_tickets()} fictional demo tickets.")
