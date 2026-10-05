# ⚡️ HyperOS / Xiaomi Apps Telegram Auto-Poster Bot

Yeh bot APKMirror se HyperOS / Xiaomi ki latest system apps automatically download karta hai, clean changelogs aur specs format karta hai, aur aapke Telegram channel par **direct APK file** ke sath upload karta hai.

---

## 📁 Files Overview (`E:\hyperos_bot`)

- **`main.py`**: Automated monitoring loop aur update engine
- **`scraper.py`**: APKMirror feed parser aur APK downloader
- **`telegram_uploader.py`**: Telethon (MTProto up to 2GB) aur Telegram Bot API uploader
- **`database.py`**: Duplicate posts protection
- **`Procfile`**: Heroku deployment configuration (`worker: python main.py`)
- **`requirements.txt`**: Python dependencies for Heroku/Cloud
- **`config.json`**: Local PC settings file
- **`start_bot.bat`**: Windows par 1-click start
- **`test_feed.bat`**: Bina post kiye feed test karna

---

## 🔑 Telegram API_ID & API_HASH Hasil Karne Ka Tareeqa

1. **[my.telegram.org](https://my.telegram.org)** par browser mein jayein.
2. Apna mobile number (e.g. `+92300...`) likh kar login karein. Telegram app par code aayega.
3. **API development tools** par click karein.
4. App Title aur Short Name likh kar submit karein.
5. Screen se **`api_id`** aur **`api_hash`** copy kar lein.

---

## 🚀 Heroku Par 24/7 Deploy Karne Ka Tareeqa

### 1. Heroku App Banayein
1. [Heroku Dashboard](https://dashboard.heroku.com) par login karein.
2. **New** -> **Create new app** par click karein (Naam rakhein e.g. `my-hyperos-bot`).

### 2. Config Vars (Environment Variables) Add Karein
Heroku par aapko files edit nahi karni padti.
App ki **Settings** tab mein ja kar **Reveal Config Vars** par click karein aur yeh add karein:

| KEY | VALUE |
|---|---|
| `BOT_TOKEN` | @BotFather se mila bot token |
| `CHAT_ID` | `@AapkeChannelKaUsername` |
| `API_ID` | `my.telegram.org` se mila App ID |
| `API_HASH` | `my.telegram.org` se mila App Hash |
| `CHANNEL_USERNAME` | `@AapkeChannelKaUsername` |
| `CHECK_INTERVAL` | `300` (har 5 minute baad check karega) |

### 3. Deploy Karein
Apne PC par Git aur Heroku CLI se:
```bash
cd E:\hyperos_bot
git init
git add .
git commit -m "Deploy HyperOS Bot"
heroku login
heroku git:remote -a my-hyperos-bot
git push heroku master
```

### 4. Worker Dyno Enable Karein
Heroku Dashboard -> **Resources** tab par jayein.
`worker: python main.py` ke samne pencil icon click kar ke use **ON** kar dein.

Aapka bot 24/7 bina rukawat background mein chalta rahega!
