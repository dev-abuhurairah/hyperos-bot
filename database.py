import os
import json
import logging
from datetime import datetime

logger = logging.getLogger("HyperOSBot.Database")

class BotDatabase:
    def __init__(self, db_path="database.json"):
        self.db_path = db_path
        self.data = self._load()

    def _load(self):
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading {self.db_path}: {e}")
        return {"posted_releases": {}}

    def _save(self):
        try:
            temp_path = self.db_path + ".tmp"
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            os.replace(temp_path, self.db_path)
        except Exception as e:
            logger.error(f"Error saving {self.db_path}: {e}")

    def is_posted(self, release_url):
        return release_url in self.data["posted_releases"]

    def mark_posted(self, release_url, title, file_size_mb=0):
        self.data["posted_releases"][release_url] = {
            "title": title,
            "posted_at": datetime.now().isoformat(),
            "file_size_mb": round(file_size_mb, 2)
        }
        self._save()
        logger.info(f"Marked as posted in database: {title}")
