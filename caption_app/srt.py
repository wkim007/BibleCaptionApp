from __future__ import annotations

import re

from caption_app.models import CaptionEntry

SRT_TIME_RE = re.compile(
    r"^(?P<hours>\d{2}):(?P<minutes>\d{2}):(?P<seconds>\d{2}),(?P<millis>\d{3})$"
)


def parse_timestamp(value: str) -> int:
    match = SRT_TIME_RE.match(value.strip())
    if not match:
        raise ValueError(f"Invalid SRT timestamp: {value!r}")

    hours = int(match.group("hours"))
    minutes = int(match.group("minutes"))
    seconds = int(match.group("seconds"))
    millis = int(match.group("millis"))
    return ((hours * 60 + minutes) * 60 + seconds) * 1000 + millis


def format_timestamp(total_ms: int) -> str:
    if total_ms < 0:
        raise ValueError("Timestamp cannot be negative.")

    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, millis = divmod(remainder, 1_000)
    return f"{hours:02}:{minutes:02}:{seconds:02},{millis:03}"


def parse_srt(content: str) -> list[CaptionEntry]:
    normalized = content.replace("\r\n", "\n").strip()
    if not normalized:
        return []

    entries: list[CaptionEntry] = []
    blocks = re.split(r"\n\s*\n", normalized)

    for block in blocks:
        lines = [line.rstrip() for line in block.split("\n") if line.strip() != ""]
        if len(lines) < 2:
            raise ValueError(f"Invalid SRT block: {block!r}")

        index_offset = 1 if lines[0].isdigit() else 0
        timing_line = lines[index_offset]
        text_lines = lines[index_offset + 1 :]

        if not text_lines:
            raise ValueError("SRT entry must include caption text.")

        try:
            start_raw, end_raw = [part.strip() for part in timing_line.split("-->")]
        except ValueError as error:
            raise ValueError(f"Invalid timing line: {timing_line!r}") from error

        entry = CaptionEntry(
            start_ms=parse_timestamp(start_raw),
            end_ms=parse_timestamp(end_raw),
            text="\n".join(text_lines),
        )
        entry.validate()
        entries.append(entry)

    entries.sort(key=lambda caption: (caption.start_ms, caption.end_ms))
    return entries


def format_srt(entries: list[CaptionEntry]) -> str:
    blocks: list[str] = []

    for index, entry in enumerate(sorted(entries, key=lambda item: item.start_ms), start=1):
        entry.validate()
        blocks.append(
            "\n".join(
                [
                    str(index),
                    f"{format_timestamp(entry.start_ms)} --> {format_timestamp(entry.end_ms)}",
                    entry.text.strip(),
                ]
            )
        )

    return "\n\n".join(blocks) + ("\n" if blocks else "")
