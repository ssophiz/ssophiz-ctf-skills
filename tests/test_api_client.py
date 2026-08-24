from __future__ import annotations

import unittest

from ssophiz_ctf.api_worker import OpenAICompatibleClient


class APIClientTests(unittest.TestCase):
    def test_external_http_is_refused(self) -> None:
        with self.assertRaises(ValueError):
            OpenAICompatibleClient("http://provider.example", "key", "model")

    def test_loopback_ollama_is_allowed(self) -> None:
        client = OpenAICompatibleClient("http://127.0.0.1:11434/v1", "", "qwen3:14b")
        self.assertEqual(client.endpoint, "http://127.0.0.1:11434/v1/chat/completions")


if __name__ == "__main__":
    unittest.main()
