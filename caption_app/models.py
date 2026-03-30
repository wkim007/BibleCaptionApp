from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class CaptionEntry:
    start_ms: int
    end_ms: int
    text: str

    def validate(self) -> None:
        if self.start_ms < 0 or self.end_ms < 0:
            raise ValueError("Caption times must be zero or positive.")
        if self.end_ms <= self.start_ms:
            raise ValueError("Caption end time must be greater than start time.")
        if not self.text.strip():
            raise ValueError("Caption text cannot be empty.")


@dataclass(frozen=True, slots=True)
class Book:
    book_id: int
    korean_name: str
    english_name: str
    chapter_count: int


@dataclass(frozen=True, slots=True)
class VerseReference:
    book_id: int
    book_korean: str
    book_english: str
    book_spanish: str
    chapter_num: int
    verse_num: int

    @property
    def label(self) -> str:
        return (
            f"{self.book_korean} | {self.book_english} | "
            f"{self.book_spanish} {self.chapter_num}:{self.verse_num}"
        )


@dataclass(frozen=True, slots=True)
class VerseBundle:
    reference: VerseReference
    korean_text: str
    english_text: str
    spanish_text: str


@dataclass(slots=True)
class CaptionProject:
    video_path: str = ""
    captions: list[CaptionEntry] = field(default_factory=list)

    def sort_captions(self) -> None:
        self.captions.sort(key=lambda caption: (caption.start_ms, caption.end_ms))
