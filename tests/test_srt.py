import unittest

from caption_app.models import CaptionEntry
from caption_app.srt import format_srt, format_timestamp, parse_srt, parse_timestamp


class TimestampTests(unittest.TestCase):
    def test_parse_timestamp(self) -> None:
        self.assertEqual(parse_timestamp("00:01:02,345"), 62_345)

    def test_format_timestamp(self) -> None:
        self.assertEqual(format_timestamp(3_723_004), "01:02:03,004")


class SrtTests(unittest.TestCase):
    def test_parse_srt(self) -> None:
        content = """1
00:00:01,000 --> 00:00:03,500
Hello world.

2
00:00:04,000 --> 00:00:06,000
Second line.
Wrapped line.
"""
        captions = parse_srt(content)

        self.assertEqual(len(captions), 2)
        self.assertEqual(captions[0].text, "Hello world.")
        self.assertEqual(captions[1].text, "Second line.\nWrapped line.")

    def test_format_srt(self) -> None:
        content = format_srt(
            [
                CaptionEntry(1_000, 3_500, "Hello world."),
                CaptionEntry(4_000, 6_000, "Second line.\nWrapped line."),
            ]
        )

        expected = """1
00:00:01,000 --> 00:00:03,500
Hello world.

2
00:00:04,000 --> 00:00:06,000
Second line.
Wrapped line.
"""
        self.assertEqual(content, expected)


if __name__ == "__main__":
    unittest.main()
