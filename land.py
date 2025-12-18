import asyncio
import aiohttp
import time
import os
import tempfile
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_BASE = "https://teradl.tiiny.io/"

ALLOWED_GROUPS = {
    -1003284051384: "Team Fx Main Group",
    -1002473112174: "Group One",
    -1003199415158: "Group Two"
}

COOLDOWN_TIME = 30
MAX_FILE_SIZE = 1900 * 1024 * 1024  # ~1.9GB Telegram safe
# =========================================

user_sessions = {}
user_cooldown = {}

def create_progress_bar(p, l=10):
    f = int(l * p / 100)
    return "▓" * f + "░" * (l - f)

async def get_terabox_link(link):
    headers = {'User-Agent': 'Mozilla/5.0'}
    async with aiohttp.ClientSession(headers=headers) as s:
        url = f"{API_BASE}?key=RushVx&link={link}"
        async with s.get(url, timeout=60) as r:
            d = await r.json()
            v = d["data"][0]
            return v["download"], v.get("title","Video"), v.get("size","?")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type == "private":
        return
    if update.message.chat.id not in ALLOWED_GROUPS:
        return
    await update.message.reply_text(
        "🤖 Terabox Downloader Bot\n\n"
        "Use: /genny <link>\n\n"
        "Creator: 𝗚𝗲𝗻𝗻𝘆🎀"
    )

async def genny_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.id not in ALLOWED_GROUPS:
        return

    user_id = update.effective_user.id
    now = time.time()

    if user_id in user_cooldown and now - user_cooldown[user_id] < COOLDOWN_TIME:
        await update.message.reply_text("⏳ Wait karo babu 😘")
        return

    if not context.args:
        await update.message.reply_text("📝 /genny <terabox-link>")
        return

    link = context.args[0]
    user_cooldown[user_id] = now

    msg = await update.message.reply_text("🔄 Processing...")

    try:
        url, title, size = await get_terabox_link(link)
        user_sessions[user_id] = url

        kb = [
            [InlineKeyboardButton("📥 Direct Download", url=url)],
            [InlineKeyboardButton("📲 Telegram Download", callback_data=f"tg_{user_id}")]
        ]

        await msg.edit_text(
            f"✅ Ready!\n\n🎬 {title}\n📦 {size}\n\nChoose:",
            reply_markup=InlineKeyboardMarkup(kb)
        )

    except Exception as e:
        await msg.edit_text(f"❌ Error: {e}")

async def download_and_upload(query, context, url):
    temp = tempfile.mktemp(suffix=".mp4")
    await query.edit_message_text("⬇️ Downloading...")

    async with aiohttp.ClientSession() as s:
        async with s.get(url, timeout=300) as r:
            size = int(r.headers.get("Content-Length", 0))
            if size > MAX_FILE_SIZE:
                await query.edit_message_text("❌ File too large for Telegram")
                return

            with open(temp, "wb") as f:
                async for chunk in r.content.iter_chunked(1024 * 64):
                    f.write(chunk)

    await query.edit_message_text("📤 Uploading to Telegram...")

    with open(temp, "rb") as v:
        await context.bot.send_video(
            chat_id=query.message.chat.id,
            video=v,
            supports_streaming=True,
            caption="✅ Uploaded\n\nCreator: 𝗚𝗲𝗻𝗻𝘆🎀",
            read_timeout=300,
            write_timeout=300
        )

    os.remove(temp)
    await query.message.delete()

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data.split("_")
    if len(data) != 2:
        return

    user_id = int(data[1])
    if user_id not in user_sessions:
        await query.edit_message_text("❌ Session expired")
        return

    url = user_sessions.pop(user_id)
    await download_and_upload(query, context, url)

def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN missing")

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("genny", genny_command))
    app.add_handler(CallbackQueryHandler(button_callback))

    print("🤖 Bot running (Telegram Download Enabled)")
    app.run_polling()

if __name__ == "__main__":
    main()