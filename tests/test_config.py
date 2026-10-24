import unittest
from unittest.mock import patch

from el_rouji_mcp.config import (
    DEFAULT_BASE_URL,
    generation_enabled,
    normalize_base_url,
    validate_language,
    validate_mode,
    validate_text,
)


class ConfigTests(unittest.TestCase):
    def test_default_base_url(self) -> None:
        self.assertEqual(normalize_base_url(None), DEFAULT_BASE_URL)

    def test_normalize_base_url(self) -> None:
        self.assertEqual(normalize_base_url("https://example.com/"), "https://example.com")

    def test_http_remote_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            normalize_base_url("http://example.com")

    def test_embedded_credentials_and_paths_are_rejected(self) -> None:
        for value in ("https://user:pass@example.com", "https://example.com/api", "https://example.com/?token=x"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize_base_url(value)

    def test_local_http_is_allowed(self) -> None:
        self.assertEqual(normalize_base_url("http://localhost:8080"), "http://localhost:8080")

    def test_generation_requires_explicit_opt_in(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            self.assertFalse(generation_enabled())
        with patch.dict("os.environ", {"EL_ROUJI_ENABLE_GENERATION": "true"}, clear=False):
            self.assertTrue(generation_enabled())

    def test_text_limits(self) -> None:
        self.assertEqual(validate_text("  hello  ", "prompt", 10), "hello")
        with self.assertRaises(ValueError):
            validate_text(" ", "prompt", 10)
        with self.assertRaises(ValueError):
            validate_text("12345", "prompt", 4)

    def test_language_and_mode_allowlists(self) -> None:
        self.assertEqual(validate_language("ar"), "ar")
        self.assertEqual(validate_mode("planning"), "planning")
        with self.assertRaises(ValueError):
            validate_language("de")
        with self.assertRaises(ValueError):
            validate_mode("shell")


if __name__ == "__main__":
    unittest.main()
