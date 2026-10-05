import os
import sys
import time
import json
import logging
import argparse
from datetime import datetime

# Load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from scraper import APKMirrorScraper
from database import BotDatabase
from telegram_uploader import TelegramUploader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(os.path.dirname(__file__), "bot.log"), encoding="utf-8")
    ]
)
logger = logging.getLogger("HyperOSBot")

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception as e:
            logger.warning(f"Failed to read config.json: {e}")

    # Override or fill from environment variables (Heroku)
    if os.getenv("BOT_TOKEN"):
        config["telegram_bot_token"] = os.getenv("BOT_TOKEN")
    if os.getenv("CHAT_ID"):
        config["telegram_chat_id"] = os.getenv("CHAT_ID")
    if os.getenv("API_ID"):
        config["telegram_api_id"] = os.getenv("API_ID")
    if os.getenv("API_HASH"):
        config["telegram_api_hash"] = os.getenv("API_HASH")
    if os.getenv("CHANNEL_USERNAME"):
        config["channel_username"] = os.getenv("CHANNEL_USERNAME")
    if os.getenv("CHECK_INTERVAL"):
        try:
            config["check_interval_seconds"] = int(os.getenv("CHECK_INTERVAL"))
        except ValueError:
            pass

    return config

def sanitize_filename(filename):
    import re
    return re.sub(r'[\\/*?:"<>| ]', '_', filename)

def check_for_updates(scraper, db, uploader, config, is_first_run=False):
    tracked_apps = config.get("tracked_apps", [])
    delete_after = config.get("delete_apk_after_upload", True)

    logger.info("Checking for new HyperOS / Xiaomi updates...")
    try:
        items = scraper.fetch_latest_feed_items()
    except Exception as e:
        logger.error(f"Failed to fetch APKMirror feed: {e}")
        return

    # If this is first run and DB was completely empty, mark existing items as seen so we don't spam 10 files
    if is_first_run and len(db.data.get("posted_releases", {})) == 0:
        logger.info("First run on fresh database detected. Initializing database with existing items...")
        for item in items:
            db.mark_posted(item['link'], item['title'], 0)
        logger.info("Initialized database. Future new updates will be downloaded and posted!")
        return

    # Process items in chronological order (oldest first so channel history is in sequence)
    new_items = []
    for item in reversed(items):
        link = item['link']
        title = item['title']

        if db.is_posted(link):
            continue

        if not scraper.is_tracked_app(title, tracked_apps):
            logger.info(f"Skipping (not in tracked apps): {title}")
            continue

        new_items.append(item)

    if not new_items:
        logger.info("No new updates found.")
        return

    logger.info(f"Found {len(new_items)} new update(s) to process!")

    for item in new_items:
        title = item['title']
        link = item['link']
        logger.info(f"\n{'='*50}\nProcessing: {title}\nLink: {link}\n{'='*50}")

        try:
            # 1. Fetch release details & changelog
            details = scraper.get_release_details(link)
            variant_url = details.get('variant_url')
            if not variant_url:
                logger.warning(f"No valid variant download link found for {title}. Skipping.")
                continue

            # 2. Resolve direct APK download URL
            dl_url, ref_url = scraper.resolve_download_url(variant_url)
            if not dl_url:
                logger.warning(f"Could not resolve direct download URL for {title}. Skipping.")
                continue

            # 3. Download the APK
            safe_name = sanitize_filename(title) + ".apk"
            file_path, file_size_mb = scraper.download_apk(
                download_url=dl_url,
                referer_url=ref_url,
                dest_folder=os.path.join(os.path.dirname(__file__), "downloads"),
                filename=safe_name
            )

            # 4. Upload APK file to Telegram channel
            logger.info(f"Uploading {safe_name} to Telegram...")
            uploader.upload_post(
                file_path=file_path,
                item=item,
                details=details,
                file_size_mb=file_size_mb
            )

            # 5. Mark as posted in DB
            db.mark_posted(link, title, file_size_mb)

            # 6. Cleanup local file
            if delete_after and os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Cleaned up local file: {file_path}")

            # Sleep between posts to respect Telegram limits
            time.sleep(5)

        except Exception as e:
            logger.error(f"Error processing update '{title}': {e}", exc_info=True)
            with open("last_error.log", "w", encoding="utf-8") as ef:
                ef.write(f"Error: {e}\nApp: {title}\n")
            raise e

def main():
    parser = argparse.ArgumentParser(description="HyperOS APKMirror Auto-Updater Bot for Telegram")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--test", action="store_true", help="Test mode: only check feeds without posting or downloading")
    args = parser.parse_args()

    config = load_config()

    scraper = APKMirrorScraper()
    db = BotDatabase(os.path.join(os.path.dirname(__file__), "database.json"))
    uploader = TelegramUploader(config)

    logger.info("=== HyperOS APKMirror Telegram Bot Started ===")
    logger.info(f"Tracked apps: {len(config.get('tracked_apps', []))} categories")
    logger.info(f"Target Channel: {uploader.chat_id or 'Not set'}")

    if args.test:
        logger.info("Running in TEST mode...")
        items = scraper.fetch_latest_feed_items()
        print(f"\nFeed fetched successfully! Found {len(items)} items:")
        for idx, it in enumerate(items, 1):
            is_tr = scraper.is_tracked_app(it['title'], config.get('tracked_apps', []))
            is_post = db.is_posted(it['link'])
            print(f"{idx}. {it['title']} | Tracked: {is_tr} | Already Posted: {is_post}")
        return

    first_run = True
    if args.once:
        check_for_updates(scraper, db, uploader, config, is_first_run=first_run)
        logger.info("Single run completed.")
        return

    # Continuous loop mode
    interval = config.get("check_interval_seconds", 300)
    logger.info(f"Starting auto-check loop every {interval} seconds ({interval//60} mins)...")
    while True:
        try:
            check_for_updates(scraper, db, uploader, config, is_first_run=first_run)
            first_run = False
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}", exc_info=True)

        logger.info(f"Sleeping for {interval} seconds until next check...")
        time.sleep(interval)

if __name__ == "__main__":
    main()
