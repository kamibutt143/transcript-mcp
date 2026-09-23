import unittest

from app.validation import validate_facebook_url


class FacebookUrlValidationTests(unittest.TestCase):
    def test_accepts_reel(self):
        url = "https://www.facebook.com/reel/123456789"
        self.assertEqual(validate_facebook_url(url), url)

    def test_accepts_fb_watch(self):
        url = "https://fb.watch/abc123/"
        self.assertEqual(validate_facebook_url(url), url)

    def test_rejects_non_facebook(self):
        with self.assertRaises(ValueError):
            validate_facebook_url("https://example.com/video.mp4")

    def test_rejects_embedded_credentials(self):
        with self.assertRaises(ValueError):
            validate_facebook_url("https://user:pass@facebook.com/reel/1")


if __name__ == "__main__":
    unittest.main()
