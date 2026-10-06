import asyncio
import os
import sys
import traceback
import requests
from telethon import TelegramClient

api_id = 29882735
api_hash = '2c1d54d7179a8c1b0ce2d4ace0cbd715'
bot_token = '8984371861:AAGCHaFCmXnQzA_5PPbdmnx9FyQR4oOdtms'
chat_id = '@hyperosapks_miui'

log_output = []
def log(msg):
    print(msg)
    log_output.append(str(msg))

async def main():
    log("=== Starting Telethon Upload Test ===")
    
    # 1. Test HTTP Bot API getChat first
    try:
        r = requests.get(f"https://api.telegram.org/bot{bot_token}/getChat", params={"chat_id": chat_id}, timeout=15)
        log(f"HTTP getChat: {r.status_code} -> {r.text}")
        chat_data = r.json()
        numeric_id = chat_data.get("result", {}).get("id")
        log(f"Numeric Chat ID: {numeric_id}")
    except Exception as e:
        log(f"HTTP getChat failed: {e}")
        numeric_id = None

    # 2. Test Telethon Login
    try:
        log("Initializing TelegramClient...")
        async with TelegramClient("test_bot_session", api_id, api_hash) as client:
            log("Calling client.start(bot_token=...)...")
            await client.start(bot_token=bot_token)
            me = await client.get_me()
            log(f"Logged in as: {me.username} (ID: {me.id}, is_bot: {me.bot})")

            # 3. Test resolving entity
            target_entity = None
            try:
                log(f"Resolving entity by username {chat_id}...")
                target_entity = await client.get_entity(chat_id)
                log(f"Entity resolved by username: {target_entity.title} (ID: {target_entity.id})")
            except Exception as e:
                log(f"Failed to resolve by username: {type(e).__name__}: {e}")

            if not target_entity and numeric_id:
                try:
                    log(f"Resolving entity by numeric ID {numeric_id}...")
                    target_entity = await client.get_entity(numeric_id)
                    log(f"Entity resolved by numeric ID: {target_entity.title} (ID: {target_entity.id})")
                except Exception as e:
                    log(f"Failed to resolve by numeric ID: {type(e).__name__}: {e}")

            # 4. Create dummy 1MB file and test sending
            test_file = "test_sample.apk"
            with open(test_file, "wb") as f:
                f.write(b"PK\x03\x04" + b"\x00" * 1024 * 500) # 500 KB dummy apk
            log(f"Created dummy file: {test_file}")

            entity_to_use = target_entity or chat_id
            log(f"Attempting client.send_file to {entity_to_use}...")
            msg = await client.send_file(
                entity=entity_to_use,
                file=test_file,
                caption="🧪 <b>Telethon MTProto Test Upload</b>\nTesting direct file attachment up to 2GB.",
                parse_mode="html",
                force_document=True
            )
            log(f"SUCCESS! Message sent with ID: {msg.id}")

            if os.path.exists(test_file):
                os.remove(test_file)

    except Exception as e:
        log(f"FATAL Telethon Error: {type(e).__name__}: {e}")
        log(traceback.format_exc())

    with open("telethon_test_result.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(log_output))

if __name__ == "__main__":
    asyncio.run(main())
