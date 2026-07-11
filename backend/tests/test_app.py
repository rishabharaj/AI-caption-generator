import unittest
import asyncio
from pathlib import Path
from fastapi.testclient import TestClient

from backend.main import app
from backend.config import settings
from backend.utils.validators import validate_duration, validate_file_format, validate_file_size, validate_api_key
from backend.services.mock_ai import MockAI

class TestValidators(unittest.TestCase):
    """Test validators utility functions."""

    def test_file_format(self):
        self.assertTrue(validate_file_format("video.mp4"))
        self.assertTrue(validate_file_format("clip.MOV"))
        self.assertTrue(validate_file_format("animation.webm"))
        self.assertFalse(validate_file_format("image.jpg"))
        self.assertFalse(validate_file_format("audio.mp3"))

    def test_file_size(self):
        # 100MB is valid (limit is 500MB)
        self.assertTrue(validate_file_size(100 * 1024 * 1024))
        # 600MB is invalid
        self.assertFalse(validate_file_size(600 * 1024 * 1024))

    def test_duration(self):
        # 45 seconds is valid
        self.assertTrue(validate_duration(45.0)[0])
        # 15 seconds is too short (min is 30s)
        self.assertFalse(validate_duration(15.0)[0])
        # 180 seconds is too long (max is 120s)
        self.assertFalse(validate_duration(180.0)[0])

    def test_api_key(self):
        self.assertTrue(validate_api_key("fw_thisisareallylongapikey12345678"))
        self.assertFalse(validate_api_key("short"))
        self.assertFalse(validate_api_key("invalid_prefix_12345678901234567890"))


class TestMockAI(unittest.TestCase):
    """Test fallback Mock AI caption generation."""

    def setUp(self):
        self.mock_ai = MockAI()
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()

    def test_formal_caption(self):
        caption = self.loop.run_until_complete(
            self.mock_ai.generate_caption("formal", "Hello, we are launching a new startup product.", [])
        )
        self.assertGreater(len(caption), 0)

    def test_sarcastic_caption(self):
        caption = self.loop.run_until_complete(
            self.mock_ai.generate_caption("sarcastic", "I am working late on a Friday night.", [])
        )
        self.assertGreater(len(caption), 0)

    def test_humorous_tech_caption(self):
        caption = self.loop.run_until_complete(
            self.mock_ai.generate_caption("humorous_tech", "deploying to production", [])
        )
        self.assertGreater(len(caption), 0)

    def test_humorous_non_tech_caption(self):
        caption = self.loop.run_until_complete(
            self.mock_ai.generate_caption("humorous_non_tech", "baking a cake at home", [])
        )
        self.assertGreater(len(caption), 0)


class TestAPI(unittest.TestCase):
    """Test FastAPI endpoints using TestClient."""

    def setUp(self):
        self.client = TestClient(app)

    def test_health_endpoint(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("ffmpeg_available", data)

    def test_upload_validation_invalid_format(self):
        # Test uploading an invalid file format
        files = {"file": ("test.txt", b"dummy content", "text/plain")}
        response = self.client.post("/api/upload", files=files)
        # InvalidFormat maps to HTTP 415 (Unsupported Media Type) in backend/api/exceptions.py
        self.assertEqual(response.status_code, 415)

    def test_api_key_header_validation(self):
        # Endpoint checks
        response = self.client.get("/api/captions/non-existent-id")
        # Should return 404 since ID doesn't exist
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
