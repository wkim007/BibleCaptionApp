from __future__ import annotations

import json
from pathlib import Path

from caption_app.models import CaptionEntry, CaptionProject


def save_project(path: str | Path, project: CaptionProject) -> None:
    payload = {
        "video_path": project.video_path,
        "captions": [
            {
                "start_ms": caption.start_ms,
                "end_ms": caption.end_ms,
                "text": caption.text,
            }
            for caption in project.captions
        ],
    }
    Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_project(path: str | Path) -> CaptionProject:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    project = CaptionProject(video_path=raw.get("video_path", ""))

    for item in raw.get("captions", []):
        entry = CaptionEntry(
            start_ms=int(item["start_ms"]),
            end_ms=int(item["end_ms"]),
            text=str(item["text"]),
        )
        entry.validate()
        project.captions.append(entry)

    project.sort_captions()
    return project
