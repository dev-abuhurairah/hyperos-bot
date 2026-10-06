import asyncio
import os
import sys
import traceback
import requests
from telethon import TelegramClient

api_id = 29882735
api_hash = '2c1d54d7179a8c1b0ce2d4ace0cbd715'
bot_token = '8984371861:AAGCHaFCmXnQzA_5PPbdmnx9FyQR4oOdtms'
chat_id = -1002054234005 # Using numeric ID from getChat

log_output = []
def log(msg):
    print(msg)
    log_output.append(str(msg))

async def main():
    log("=== Starting Telethon Upload Test v2 ===")

    client = TelegramClient("test_bot_session", api_id, api_hash)
    try:
        log("Connecting client...")
        await client.connect()
        
        log("Checking authorization...")
        if not await client.is_user_authorized():
            log("Signing in with bot token...")
            await client.sign_in(bot_token=bot_token)
            
        me = await client.get_me()
        log(f"Successfully logged in as: @{me.username} (ID: {me.id})")

        # Create dummy 1MB file and test sending
        test_file = "test_sample.apk"
        with open(test_file, "wb") as f:
            f.write(b"PK\x03\x04" + b"\x00" * 1024 * 500) # 500 KB dummy apk
        log(f"Created dummy file: {test_file}")

        log(f"Sending file to chat {chat_id}...")
        msg = await client.send_file(
            entity=chat_id,
            file=test_file,
            caption="🧪 <b>Telethon MTProto Test Upload</b>\nTesting direct file attachment up to 2GB.",
            parse_mode="html",
            force_document=True
        )
        log(f"SUCCESS! Message sent with ID: {msg.id}")

        if os.path.exists(test_file):
            os.remove(test_file)

    except Exception as e:
        log(f"FATAL Error: {type(e).__name__}: {e}")
        log(traceback.format_exc())
    finally:
        await client.disconnect()

    with open("telethon_test_result.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(log_output))

if __name__ == "__main__":
    asyncio.run(main())
