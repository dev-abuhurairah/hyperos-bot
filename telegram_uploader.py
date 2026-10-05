import os
import re
import html
import asyncio
import logging
import requests

logger = logging.getLogger("HyperOSBot.Telegram")

class TelegramUploader:
    def __init__(self, config=None):
        config = config or {}
        # Support both Heroku/GitHub Environment Variables and config.json
        self.bot_token = (os.getenv("BOT_TOKEN") or config.get("telegram_bot_token", "")).strip()
        self.chat_id = (os.getenv("CHAT_ID") or config.get("telegram_chat_id", "")).strip()
        self.channel_username = (os.getenv("CHANNEL_USERNAME") or config.get("channel_username", "@hyperosapks_miui")).strip()
        
        api_id_env = os.getenv("API_ID") or config.get("telegram_api_id")
        self.api_id = int(api_id_env) if api_id_env and str(api_id_env).strip().isdigit() else None
        self.api_hash = (os.getenv("API_HASH") or config.get("telegram_api_hash") or "").strip()
        
        self.signature = config.get("channel_signature") or f"📢 Updates: {self.channel_username}\n⚡️ #HyperOS #Xiaomi #AppUpdate"

        # Telethon client for large files (up to 2 GB)
        self.telethon_client = None
        if self.api_id and self.api_hash and self.bot_token:
            try:
                from telethon import TelegramClient
                self.telethon_client = TelegramClient(
                    "hyperos_bot_session", 
                    self.api_id, 
                    self.api_hash
                )
                logger.info("Telethon MTProto client initialized (supports up to 2 GB uploads).")
            except Exception as e:
                logger.warning(f"Could not initialize Telethon client: {e}")

    def format_caption(self, item, details, file_size_mb):
        """Format an ultra-clean, stylish HTML caption attached to the APK file."""
        title = item['title']

        # Extract clean App Name and Version
        match = re.search(r'^(.*?)\s+([vV]?\d+[\d\.\-\w]+)$', title)
        if match:
            app_name = match.group(1).strip()
            version = match.group(2).strip()
        else:
            app_name = title
            version = "Latest"

        clean_tag = re.sub(r'[^a-zA-Z0-9]', '', app_name.replace('Xiaomi', '').replace('MIUI', '').strip())
        if not clean_tag:
            clean_tag = "SystemApp"

        # Escape HTML special chars
        app_name_esc = html.escape(app_name)
        version_esc = html.escape(version)
        min_android_esc = html.escape(details.get('min_android', 'Android 8.0+'))
        arch_esc = html.escape(details.get('arch', 'Universal'))
        link_esc = html.escape(item['link'])

        # Format changelog
        raw_changelog = details.get('changelog', '').strip()
        if not raw_changelog or "Fixed known bugs" in raw_changelog:
            formatted_changelog = (
                "  ▫️ Fixed known issues and system bugs.\n"
                "  ▫️ Improved performance and system stability."
            )
        else:
            lines = [line.strip() for line in raw_changelog.split('\n') if line.strip()]
            cleaned_bullets = []
            for l in lines:
                l_clean = re.sub(r'^[\d\.\-\*\•\>\s]+', '', l).strip()
                if l_clean:
                    cleaned_bullets.append(f"  ▫️ {html.escape(l_clean)}")
            
            if cleaned_bullets:
                formatted_changelog = "\n".join(cleaned_bullets[:6])
            else:
                formatted_changelog = "  ▫️ Bug fixes and performance improvements."

        caption = (
            f"⚡️ <b>HyperOS System Update</b> ⚡️\n\n"
            f"📱 <b>App:</b> <code>{app_name_esc}</code>\n"
            f"🏷 <b>Version:</b> <code>{version_esc}</code>\n"
            f"▫️ <b>Architecture:</b> <code>{arch_esc}</code>\n"
            f"▫️ <b>Min Android:</b> <code>{min_android_esc}</code>\n"
            f"▫️ <b>File Size:</b> <code>{file_size_mb:.2f} MB</code>\n\n"
            f"📋 <b>What's New / Changelog:</b>\n"
            f"{formatted_changelog}\n\n"
            f"#{clean_tag} #HyperOS #Xiaomi #Update\n"
            f"📢 Updates: {html.escape(self.channel_username)}"
        )
        return caption

    def send_via_bot_api(self, file_path, caption):
        """Send APK file via standard Telegram Bot API (< 50 MB) using HTML mode."""
        logger.info(f"Sending APK file via Telegram Bot API (HTML mode) to {self.chat_id}...")
        url = f"https://api.telegram.org/bot{self.bot_token}/sendDocument"

        filename = os.path.basename(file_path)
        with open(file_path, 'rb') as f:
            files = {'document': (filename, f, 'application/vnd.android.package-archive')}
            data = {
                'chat_id': self.chat_id,
                'caption': caption,
                'parse_mode': 'HTML'
            }
            resp = requests.post(url, data=data, files=files, timeout=300)
            result = resp.json()

            if not result.get('ok'):
                err_msg = result.get('description', 'Unknown Telegram Error')
                logger.error(f"Telegram Bot API Error: {err_msg}")
                raise Exception(f"Telegram Bot API Error: {err_msg}")

            logger.info("Successfully uploaded APK to Telegram channel!")
            return result

    async def _send_via_telethon(self, file_path, caption):
        """Send APK file via Telethon MTProto (supports up to 2 GB) using HTML mode."""
        from telethon import TelegramClient
        async with TelegramClient("hyperos_bot_session", self.api_id, self.api_hash) as client:
            await client.start(bot_token=self.bot_token)
            logger.info(f"Uploading APK file via Telethon MTProto to {self.chat_id}...")

            def progress(current, total):
                pct = (current / total) * 100
                if int(pct) % 25 == 0:
                    logger.info(f"Upload Progress: {pct:.1f}% ({current // (1024*1024)}MB / {total // (1024*1024)}MB)")

            msg = await client.send_file(
                entity=self.chat_id,
                file=file_path,
                caption=caption,
                parse_mode='html',
                force_document=True,
                progress_callback=progress
            )
            logger.info("Successfully uploaded APK to Telegram via Telethon!")
            return msg

    def upload_post(self, file_path, item, details, file_size_mb):
        """Uploads the APK file attached with the beautiful caption."""
        caption = self.format_caption(item, details, file_size_mb)

        if not self.bot_token or not self.chat_id:
            logger.error("Telegram BOT_TOKEN or CHAT_ID not provided!")
            raise ValueError("Please provide BOT_TOKEN and CHAT_ID in config.json or Heroku Config Vars.")

        # If file is over 49 MB, use Telethon MTProto
        if file_size_mb >= 49.0:
            if self.api_id and self.api_hash:
                logger.info(f"File is {file_size_mb:.2f} MB. Using Telethon for high-capacity upload...")
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                return loop.run_until_complete(self._send_via_telethon(file_path, caption))
            else:
                logger.warning(
                    f"File is {file_size_mb:.2f} MB (exceeds 50MB Bot API limit) and API_ID/API_HASH are not set. "
                    "Sending post with direct download link."
                )
                return self.send_text_post(caption + "\n\n⚠️ <i>(File >50MB: Download directly from APKMirror link above)</i>")
        else:
            return self.send_via_bot_api(file_path, caption)

    def send_text_post(self, text):
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        resp = requests.post(url, json={
            'chat_id': self.chat_id,
            'text': text,
            'parse_mode': 'HTML',
            'disable_web_page_preview': False
        }, timeout=30)
        res = resp.json()
        if not res.get('ok'):
            raise Exception(f"Telegram Bot API Error: {res.get('description')}")
        return res
