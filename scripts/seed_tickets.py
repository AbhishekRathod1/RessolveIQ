import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.seed import seed_tickets


if __name__ == "__main__":
    print(f"Inserted {seed_tickets()} fictional demo tickets.")
