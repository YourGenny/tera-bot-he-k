# TERABOX GROUP BOT - FIXED VERSION FOR TERMUX

import asyncio
import aiohttp
import time
import os
import tempfile
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# Bot Configuration
BOT_TOKEN = "BOT_TOKEN"
API_BASE = "https://teradl.tiiny.io/"
ALLOWED_GROUPS = {
    -1003284051384: "Team Fx Main Group",
    -1002473112174: "Group One",
    -1003199415158: "Group Two"
}

# Storage
user_sessions = {}
user_cooldown = {}
COOLDOWN_TIME = 30  # seconds

# Progress Bar Function
def create_progress_bar(percent, length=10):
    filled = int(length * percent / 100)
    return "▓" * filled + "░" * (length - filled)

# Terabox API Function
async def get_terabox_link(link):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
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

# Start Command
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

# Main Command
async def genny_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Check if in group
    if update.message.chat.type == "private":
        return
    
    # Check group authorization
    chat_id = update.message.chat.id
    if chat_id not in ALLOWED_GROUPS:
        return
    
    user_id = update.effective_user.id
    
    # Check cooldown
    current_time = time.time()
    if user_id in user_cooldown:
        time_left = COOLDOWN_TIME - (current_time - user_cooldown[user_id])
        if time_left > 0:
            await update.message.reply_text(f"⏳ Please wait {int(time_left)} seconds!")
            return
    
    # Check for link
    if not context.args:
        await update.message.reply_text("📝 Usage: /genny <terabox-link>")
        return
    
    link = context.args[0]
    
    # Validate link
    if "terabox" not in link and "1024tera" not in link:
        await update.message.reply_text("❌ Invalid Terabox link!")
        return
    
    # Update cooldown
    user_cooldown[user_id] = current_time
    
    # Send processing message
    msg = await update.message.reply_text("🔄 Processing your request...")
    
    try:
        # Show progress
        for progress in [10, 25, 50, 75, 90, 100]:
            bar = create_progress_bar(progress)
            await msg.edit_text(f"🔍 Getting download link...\n{bar} {progress}%")
            await asyncio.sleep(0.3)
        
        # Get download link
        download_url, title, size, duration = await get_terabox_link(link)
        
        # Store in session
        user_sessions[user_id] = {
            "url": download_url,
            "title": title,
            "size": size,
            "duration": duration
        }
        
        # Create buttons
        keyboard = [
            [InlineKeyboardButton("📥 Direct Download", url=download_url)],
            [InlineKeyboardButton("📲 Telegram Download", callback_data=f"telegram_{user_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Send final message
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

# Download file with retry mechanism
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
                        async for chunk in response.content.iter_chunked(1024 * 64):  # 64KB chunks
                            if chunk:
                                file.write(chunk)
                                downloaded += len(chunk)
                                
                                # Update progress every 5% or 5 seconds
                                current_time = time.time()
                                if total_size > 0 and (current_time - last_update > 5 or 
                                                     downloaded == total_size):
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
                await asyncio.sleep(2)  # Wait before retry
                continue
            else:
                raise Exception(f"Download failed after {max_retries} attempts: {str(e)}")
    
    return False

# Button Callback Handler
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Get user ID from callback data
    data_parts = query.data.split("_")
    if len(data_parts) != 2:
        await query.edit_message_text("❌ Invalid request!")
        return
    
    user_id = int(data_parts[1])
    
    # Check session
    if user_id not in user_sessions:
        await query.edit_message_text("❌ Session expired! Please try again.")
        return
    
    session_data = user_sessions[user_id]
    download_url = session_data["url"]
    title = session_data["title"]
    size = session_data["size"]
    
    # Delete session to prevent reuse
    del user_sessions[user_id]
    
    # Start download process
    await query.edit_message_text("⬇️ Starting download...")
    
    # Create temporary file
    temp_file = tempfile.mktemp(suffix=".mp4")
    
    try:
        # Download file with retry mechanism
        success = await download_file_with_retry(download_url, temp_file, query)
        
        if not success:
            raise Exception("Download failed")
        
        # Download complete
        await query.edit_message_text("✅ Download complete! Uploading to Telegram...")
        
        # Check file size
        file_size = os.path.getsize(temp_file)
        if file_size == 0:
            raise Exception("Downloaded file is empty")
        
        # Upload to Telegram with progress
        upload_msg = await query.message.reply_text("📤 Uploading to Telegram... 0%")
        
        def upload_progress(current, total):
            percent = int((current / total) * 100)
            if percent % 10 == 0:  # Update every 10%
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
        
        # Clean up
        await upload_msg.delete()
        await query.message.delete()
        
    except Exception as e:
        await query.edit_message_text(f"❌ Download failed: {str(e)}")
    
    finally:
        # Delete temp file
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except:
                pass

# Error Handler
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Error: {context.error}")
    if update and update.message:
        await update.message.reply_text("⚠️ An error occurred. Please try again.")

# Cleanup old sessions
async def cleanup_sessions():
    while True:
        await asyncio.sleep(300)  # Run every 5 minutes
        current_time = time.time()
        
        # Clean old user sessions (older than 10 minutes)
        expired_users = [
            user_id for user_id, timestamp in user_cooldown.items()
            if current_time - timestamp > 600
        ]
        for user_id in expired_users:
            user_cooldown.pop(user_id, None)
            user_sessions.pop(user_id, None)

# Main Function
def main():
    print("🤖 Starting Terabox Bot...")
    
    # Create application
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("genny", genny_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    # Add error handler
    app.add_error_handler(error_handler)
    
    print("✅ Bot is running...")
    print("Creator: 𝗚𝗲𝗻𝗻𝘆🎀")
    
    # Start session cleanup task
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.create_task(cleanup_sessions())
    
    # Start polling
    app.run_polling()

if __name__ == "__main__":
    main()