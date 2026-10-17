"""One demo fixture shared with React and the generated standalone builds."""
import json
from pathlib import Path

_SHARED = Path(__file__).resolve().parents[2] / "shared"
DATA = json.loads((_SHARED / "demo.json").read_text(encoding="utf-8"))
DATA["DEMO_TRANSCRIPT"] = json.loads((_SHARED / "transcripts.json").read_text(encoding="utf-8"))
BRD = json.loads((_SHARED / "brd.json").read_text(encoding="utf-8"))
MEETING = json.loads((_SHARED / "meeting.json").read_text(encoding="utf-8"))
MOCKS_BY_MODE = {
    mode: {"transcript": DATA["DEMO_TRANSCRIPT"][mode], "rules": DATA["FALLBACK_RULES"][mode]}
    for mode in DATA["MODE_DOMAIN"]
}
