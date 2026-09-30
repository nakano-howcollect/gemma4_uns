import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import chat
import download_model


def stream(parts, done=True):
    events = ["data: " + json.dumps({"choices": [{"delta": {"content": p}}]}) + "\n\n"
              for p in parts]
    if done:
        events.append("data: [DONE]\n\n")
    return io.BytesIO("".join(events).encode())


class ChatTests(unittest.TestCase):
    def test_system_and_history_sent_and_japanese_stream_returned(self):
        messages = [{"role": "system", "content": "日本語で回答"},
                    {"role": "user", "content": "名前は？"},
                    {"role": "assistant", "content": "Gemmaです"},
                    {"role": "user", "content": "こんにちは"}]
        with patch("chat.urlopen", return_value=stream(["こん", "にちは"])) as request:
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(chat.chat_completion(messages), "こんにちは")
        self.assertEqual(json.loads(request.call_args.args[0].data)["messages"], messages)

    def test_unused_loop_split_across_chunks_is_rejected(self):
        parts = ["<unused", "50>"] * 12
        with patch("chat.urlopen", return_value=stream(parts)):
            with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(chat.ModelOutputError):
                chat.chat_completion([])

    def test_unfinished_stream_is_rejected(self):
        with patch("chat.urlopen", return_value=stream(["hello"], done=False)):
            with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(RuntimeError):
                chat.chat_completion([])

    def test_size_and_hash_are_both_checked(self):
        content = b"valid model fixture"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "model.gguf"
            with patch.object(download_model, "SIZE", len(content)), patch.object(
                download_model, "SHA256", hashlib.sha256(content).hexdigest()
            ):
                path.write_bytes(content)
                self.assertTrue(download_model.valid(path))
                path.write_bytes(b"x" * len(content))
                self.assertFalse(download_model.valid(path))
                path.write_bytes(content * 2)
                self.assertFalse(download_model.valid(path))


if __name__ == "__main__":
    unittest.main()
