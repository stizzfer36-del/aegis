"""Social Media — Mastodon / Tweepy / Telethon integrations."""
from __future__ import annotations
import os


class SocialMediaTopic:
    name = "social_media"
    tools = ["mastodon.py", "tweepy", "praw", "instagrapi", "tiktokapi", "youtube-data-api", "telethon"]

    async def post_mastodon(self, status: str) -> dict:
        url = os.getenv("MASTODON_URL", "")
        token = os.getenv("MASTODON_TOKEN", "")
        if not url or not token:
            return {"error": "MASTODON_URL / MASTODON_TOKEN not set"}
        try:
            from mastodon import Mastodon
            m = Mastodon(access_token=token, api_base_url=url)
            return m.status_post(status)
        except ImportError:
            return {"error": "Mastodon.py not installed"}
