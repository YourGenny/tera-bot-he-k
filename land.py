# TERABOX GROUP BOT - FIXED FOR RENDER

import asyncio
import aiohttp
import time
import os
import tempfile
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# Bot Configuration
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    print("❌ ERROR: BOT_TOKEN not set!")
    exit(1)

API_BASE = "https://teradl.tiiny.io/"
ALLOWED_GROUPS = {
    -1003284051384: "Team Fx Main Group",
    -1002473112174: "Group One",
    -1003199415158: "Group Two"
}

user_sessions = {}
user_cooldown = {}
COOLDOWN_TIME = 30

def create_progress_bar(percent, length=10):
    filled = int(length * percent / 100)
    return "▓" * filled + "░" * (length - filled)

async def get_terabox_link(link):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        async with aiohttp.ClientSession(headers=headers) as session:
            api_url = f"{API_BASE}?key=RushVx&link={link}"
            async with session.get(api_url, timeout=60) as response:
                data = await response.json()
                video_data = data["data"][0]
                return (
                    video_data["download"],
                    video_data.get("title", "Video"),
                    video_data.get("size", "Unknown"),
                    video_data.get("duration", "Unknown")
                )
    except Exception as e:
        raise Exception(f"API Error: {str(e)}")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type == "private":
        await update.message.reply_text("❌ This bot works only in groups!")
        return
    
    chat_id = update.message.chat.id
    if chat_id not in ALLOWED_GROUPS:
        await update.message.reply_text("❌ Unauthorized group!")
        return
    
    await update.message.reply_text(
        "🤖 Terabox Downloader Bot\n\n"
        "Usage: /genny <terabox-link>\n\n"
        "●Creator 𝗚𝗲𝗻𝗻𝘆🎀"
    )

async def genny_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type == "private":
        return
    
    chat_id = update.message.chat.id
    if chat_id not in ALLOWED_GROUPS:
        return
    
    user_id = update.effective_user.id
    current_time = time.time()
    
    if user_id in user_cooldown:
        time_left = COOLDOWN_TIME - (current_time - user_cooldown[user_id])
        if time_left > 0:
            await update.message.reply_text(f"⏳ Please wait {int(time_left)} seconds!")
            return
    
    if not context.args:
        await update.message.reply_text("📝 Usage: /genny <terabox-link>")
        return
    
    link = context.args[0]
    if "terabox" not in link and "1024tera" not in link:
        await update.message.reply_text("❌ Invalid Terabox link!")
        return
    
    user_cooldown[user_id] = current_time
    msg = await update.message.reply_text("🔄 Processing your request...")
    
    try:
        for progress in [10, 25, 50, 75, 90, 100]:
            bar = create_progress_bar(progress)
            await msg.edit_text(f"🔍 Getting download link...\n{bar} {progress}%")
            await asyncio.sleep(0.3)
        
        download_url, title, size, duration = await get_terabox_link(link)
        
        user_sessions[user_id] = {
            "url": download_url,
            "title": title,
            "size": size,
            "duration": duration
        }
        
        keyboard = [
            [InlineKeyboardButton("📥 Direct Download", url=download_url)],
            [InlineKeyboardButton("📲 Telegram Download", callback_data=f"telegram_{user_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        bar = create_progress_bar(100)
        await msg.edit_text(
            f"✅ Ready to Download!\n\n"
            f"📁 Title: {title}\n"
            f"📦 Size: {size}\n"
            f"⏱️ Duration: {duration}\n"
            f"📊 Status: {bar} 100%\n\n"
            f"Choose download method:\n\n"
            f"Creator: 𝗚𝗲𝗻𝗻𝘆🎀",
            reply_markup=reply_markup
        )
        
    except Exception as e:
        await msg.edit_text(f"❌ Error: {str(e)}")

async def download_file_with_retry(url, temp_file, query, max_retries=3):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://www.terabox.com/',
        'Connection': 'keep-alive'
    }
    
    for attempt in range(max_retries):
        try:
            start_time = time.time()
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(url, timeout=300) as response:
                    if response.status != 200:
                        raise Exception(f"HTTP {response.status}")
                    
                    total_size = int(response.headers.get("Content-Length", 0))
                    downloaded = 0
                    
                    with open(temp_file, "wb") as file:
                        last_update = 0
                        async for chunk in response.content.iter_chunked(1024 * 64):
                            if chunk:
                                file.write(chunk)
                                downloaded += len(chunk)
                                
                                current_time = time.time()
                                if total_size > 0 and (current_time - last_update > 5 or downloaded == total_size):
                                    percent = int((downloaded / total_size) * 100)
                                    bar = create_progress_bar(percent)
                                    elapsed = current_time - start_time
                                    speed = downloaded / elapsed / 1024 if elapsed > 0 else 0
                                    
                                    await query.edit_message_text(
                                        f"📥 Downloading... (Attempt {attempt + 1}/{max_retries})\n"
                                        f"{bar} {percent}%\n"
                                        f"📊 {downloaded / 1024 / 1024:.1f} MB / {total_size / 1024 / 1024:.1f} MB\n"
                                        f"⚡ {speed:.1f} KB/s"
                                    )
                                    last_update = current_time
                    
                    return True
                    
        except Exception as e:
            print(f"Download attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2)
                continue
            else:
                raise Exception(f"Download failed after {max_retries} attempts: {str(e)}")
    
    return False

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data_parts = query.data.split("_")
    if len(data_parts) != 2:
        await query.edit_message_text("❌ Invalid request!")
        return
    
    user_id = int(data_parts[1])
    
    if user_id not in user_sessions:
        await query.edit_message_text("❌ Session expired! Please try again.")
        return
    
    session_data = user_sessions[user_id]
    download_url = session_data["url"]
    title = session_data["title"]
    size = session_data["size"]
    
    del user_sessions[user_id]
    await query.edit_message_text("⬇️ Starting download...")
    
    temp_file = tempfile.mktemp(suffix=".mp4")
    
    try:
        success = await download_file_with_retry(download_url, temp_file, query)
        
        if not success:
            raise Exception("Download failed")
        
        await query.edit_message_text("✅ Download complete! Uploading to Telegram...")
        
        file_size = os.path.getsize(temp_file)
        if file_size == 0:
            raise Exception("Downloaded file is empty")
        
        upload_msg = await query.message.reply_text("📤 Uploading to Telegram... 0%")
        
        def upload_progress(current, total):
            percent = int((current / total) * 100)
            if percent % 10 == 0:
                asyncio.create_task(
                    upload_msg.edit_text(f"📤 Uploading to Telegram... {percent}%")
                )
        
        with open(temp_file, "rb") as video_file:
            await context.bot.send_video(
                chat_id=query.message.chat.id,
                video=video_file,
                supports_streaming=True,
                caption=f"✅ {title}\n📦 Size: {size}\n\nCreator: 𝗚𝗲𝗻𝗻𝘆🎀",
                filename=f"{title[:50]}.mp4",
                progress=upload_progress,
                read_timeout=300,
                write_timeout=300,
                connect_timeout=300
            )
        
        await upload_msg.delete()
        await query.message.delete()
        
    except Exception as e:
        await query.edit_message_text(f"❌ Download failed: {str(e)}")
    
    finally:
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except:
                pass

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Error: {context.error}")
    if update and update.message:
        await update.message.reply_text("⚠️ An error occurred. Please try again.")

def main():
    print("🤖 Starting Terabox Bot...")
    print(f"✅ Token loaded: {BOT_TOKEN[:10]}...")
    
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("genny", genny_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_error_handler(error_handler)
    
    print("✅ Bot is running...")
    print("Creator: 𝗚𝗲𝗻𝗻𝘆🎀")
    
    app.run_polling()

if __name__ == "__main__":
    main()