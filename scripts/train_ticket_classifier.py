import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.ai.training import train_and_evaluate


if __name__ == "__main__":
    report = train_and_evaluate()
    print(json.dumps(report, indent=2))
