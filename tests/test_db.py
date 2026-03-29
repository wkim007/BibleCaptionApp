import unittest

from caption_app.db import BibleRepository


class BibleRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = BibleRepository()

    def test_books_are_available(self) -> None:
        books = self.repository.list_books()
        self.assertGreater(len(books), 0)
        self.assertEqual(books[0].english_name, "Genesis")

    def test_john_1_1_bundle(self) -> None:
        verse = self.repository.get_verse_bundle(43, 1, 1)

        self.assertEqual(verse.reference.book_english, "John")
        self.assertIn("태초에", verse.korean_text)
        self.assertIn("In the beginning", verse.english_text)
        self.assertIn("En el principio", verse.spanish_text)


if __name__ == "__main__":
    unittest.main()
