import os
import re
import time
import json
import logging
import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from urllib.parse import urljoin

logger = logging.getLogger("HyperOSBot.Scraper")

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
}

class APKMirrorScraper:
    def __init__(self, session=None):
        self.session = session or requests.Session()
        self.session.headers.update(HEADERS)
        self.base_url = "https://www.apkmirror.com"
        self.feed_url = "https://www.apkmirror.com/apk/xiaomi-inc/feed/"

    def fetch_latest_feed_items(self):
        """Fetch latest uploads from Xiaomi Inc RSS feed."""
        logger.info(f"Fetching RSS feed: {self.feed_url}")
        resp = self.session.get(self.feed_url, timeout=15)
        resp.raise_for_status()

        root = ET.fromstring(resp.content)
        items = []
        for item in root.findall('.//item'):
            title = item.find('title').text.strip() if item.find('title') is not None else ''
            link = item.find('link').text.strip() if item.find('link') is not None else ''
            pub_date = item.find('pubDate').text.strip() if item.find('pubDate') is not None else ''
            
            # Clean up title: e.g. "Xiaomi Security 13.6.5-261003.0.1 by Xiaomi Inc."
            title_clean = re.sub(r'\s+by Xiaomi Inc\.?$', '', title, flags=re.IGNORECASE).strip()

            items.append({
                'title': title_clean,
                'raw_title': title,
                'link': link,
                'pub_date': pub_date
            })
        return items

    def is_tracked_app(self, title, tracked_keywords):
        """Check if the title matches any tracked app keywords."""
        if not tracked_keywords or "ALL" in [k.upper() for k in tracked_keywords]:
            return True
        title_lower = title.lower()
        for kw in tracked_keywords:
            if kw.lower() in title_lower:
                return True
        return False

    def get_release_details(self, release_url):
        """Fetch details, changelog, variants, and direct download links from release page."""
        logger.info(f"Fetching release details: {release_url}")
        resp = self.session.get(release_url, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')

        # 1. Changelog / notes
        changelog = "Bug fixes and performance improvements."
        notes_div = soup.find('div', class_='notes')
        if notes_div:
            notes_text = notes_div.get_text(separator='\n', strip=True)
            # Remove "From version X:" prefix if present
            notes_text = re.sub(r'^From version\s*[\d\.]+:\s*', '', notes_text, flags=re.IGNORECASE)
            if notes_text.strip():
                changelog = notes_text.strip()

        # 2. Extract Min Android, Architecture, and Variant download link
        min_android = "Android 8.0+"
        arch = "universal"
        variant_url = None

        # Look in variants table
        variants_table = soup.find('div', class_='variants-table')
        if variants_table:
            for row in variants_table.find_all('div', class_='table-row'):
                # We want standard APK (skip bundle if possible)
                row_text = row.get_text()
                if 'BUNDLE' in row_text:
                    continue

                # Find link to variant
                v_link = row.find('a', href=re.compile(r'-android-apk-download/'))
                if v_link:
                    variant_url = urljoin(self.base_url, v_link['href'])
                    
                    # Extract specs from row if present
                    cells = row.find_all('div')
                    # Typically: cell 1=variant/version, cell 2=arch, cell 3=min android, cell 4=dpi
                    for cell in cells:
                        c_text = cell.get_text(strip=True)
                        if 'Android' in c_text:
                            min_android = c_text.replace('Minimum Version', '').strip()
                        elif any(a in c_text.lower() for a in ['arm64', 'armeabi', 'universal', 'x86']):
                            arch = c_text.replace('Architecture', '').strip()
                    break

        # Fallback if no table row found
        if not variant_url:
            btn = soup.find('a', class_=re.compile(r'downloadButton'))
            if btn and btn.get('href'):
                variant_url = urljoin(self.base_url, btn['href'])

        return {
            'changelog': changelog,
            'min_android': min_android,
            'arch': arch,
            'variant_url': variant_url
        }

    def resolve_download_url(self, variant_url):
        """Follow variant page to final download.php direct URL."""
        if not variant_url:
            return None

        logger.info(f"Resolving download step 1 from variant: {variant_url}")
        self.session.headers.update({'Referer': variant_url})
        resp1 = self.session.get(variant_url, timeout=15)
        resp1.raise_for_status()
        soup1 = BeautifulSoup(resp1.text, 'html.parser')

        dl_btn = soup1.find('a', class_=re.compile(r'downloadButton'))
        if not dl_btn or not dl_btn.get('href'):
            logger.warning("Could not find download button on variant page.")
            return None

        step2_url = urljoin(self.base_url, dl_btn['href'])
        logger.info(f"Resolving download step 2: {step2_url}")
        self.session.headers.update({'Referer': variant_url})
        resp2 = self.session.get(step2_url, timeout=15)
        resp2.raise_for_status()
        soup2 = BeautifulSoup(resp2.text, 'html.parser')

        # Find final download link
        final_link = soup2.find('a', id='download-link')
        if not final_link:
            final_link = soup2.find('a', href=re.compile(r'download\.php'))

        if final_link and final_link.get('href'):
            file_url = urljoin(self.base_url, final_link['href'])
            return file_url, step2_url

        logger.warning("Could not find final download link on step 2.")
        return None, None

    def download_apk(self, download_url, referer_url, dest_folder="downloads", filename="app.apk"):
        """Downloads APK file with progress reporting."""
        os.makedirs(dest_folder, exist_ok=True)
        file_path = os.path.join(dest_folder, filename)

        self.session.headers.update({'Referer': referer_url})
        logger.info(f"Starting download to {file_path}...")
        with self.session.get(download_url, stream=True, timeout=60) as resp:
            resp.raise_for_status()
            total_size = int(resp.headers.get('content-length', 0))
            downloaded = 0
            with open(file_path, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=1024 * 512):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        logger.info(f"Download complete: {file_path} ({file_size_mb:.2f} MB)")
        return file_path, file_size_mb
