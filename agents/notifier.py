"""TelegramNotifier — Dispatches interactive approval requests and status notifications."""
import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("agents.notifier")


class TelegramNotifier:
    """Sends video previews and 1-click approval requests to Telegram."""

    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        self.bot_token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        self.chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID", "").strip()
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}" if self.bot_token else ""

    @property
    def is_configured(self) -> bool:
        return bool(self.bot_token and self.chat_id)

    def send_message(self, text: str, reply_markup: Optional[Dict] = None) -> bool:
        """Send a text message with optional inline keyboard buttons."""
        if not self.is_configured:
            logger.info("TelegramNotifier: Not configured. Logging notification locally:")
            print("\n[TELEGRAM PREVIEW (MOCK)]")
            print(text)
            print("[END TELEGRAM PREVIEW]\n")
            return False

        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup

        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result.get("ok", False)
        except Exception as exc:
            logger.error(f"TelegramNotifier: Failed to send message: {exc}")
            return False

    def notify_approval_request(
        self,
        date_str: str,
        title: str,
        video_count: int,
        review_score: float,
        review_feedback: str,
        transits_count: int = 0,
    ) -> bool:
        """Send production summary with interactive Approve / Reject buttons."""
        message = (
            f"🎬 <b>AstroPratidin Video Production Ready</b>\n\n"
            f"📅 <b>Target Date:</b> {date_str}\n"
            f"📌 <b>Title:</b> {title}\n"
            f"⭐ <b>AI Reviewer Score:</b> {review_score:.1f} / 10.0\n"
            f"📹 <b>Videos Rendered:</b> 1 Major + 12 Rashi + {transits_count} Transits\n"
            f"📝 <b>Review Notes:</b> <i>{review_feedback}</i>\n\n"
            f"⚡ <i>Action required: Approve to publish immediately to YouTube & Facebook.</i>"
        )

        inline_keyboard = {
            "inline_keyboard": [
                [
                    {"text": "✅ Approve & Publish", "callback_data": f"approve_{date_str}"},
                    {"text": "❌ Reject / Hold", "callback_data": f"reject_{date_str}"},
                ],
                [
                    {"text": "🔍 View Run Logs", "url": "https://github.com/ukumr59/astro-hindi-ai/actions"},
                ]
            ]
        }

        return self.send_message(message, reply_markup=inline_keyboard)

    def notify_published(self, date_str: str, youtube_count: int, facebook_count: int) -> bool:
        """Send notification after successful publication."""
        message = (
            f"🚀 <b>AstroPratidin Published Successfully!</b>\n\n"
            f"📅 <b>Date:</b> {date_str}\n"
            f"🔴 <b>YouTube:</b> {youtube_count} videos live\n"
            f"🔵 <b>Facebook:</b> {facebook_count} videos live\n"
            f"✨ All daily forecasts and transits are available to viewers."
        )
        return self.send_message(message)
