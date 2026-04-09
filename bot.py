import os
import logging
import asyncio
from datetime import datetime, timedelta
from telegram import (
    Update,
    ChatPermissions,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ChatMemberHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ChatMemberStatus
from telegram.error import TelegramError

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ── Config ───────────────────────────────────────────────────────────────────
BOT_TOKEN = os.environ["BOT_TOKEN"]
WELCOME_DELETE_AFTER = int(os.environ.get("WELCOME_DELETE_AFTER", 600))  # 10 min
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")          # e.g. https://your-app.herokuapp.com
PORT = int(os.environ.get("PORT", 8443))

# ── Helpers ───────────────────────────────────────────────────────────────────
ADMIN_STATUSES = {ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER}


async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    try:
        member = await context.bot.get_chat_member(update.effective_chat.id, user_id)
        return member.status in ADMIN_STATUSES
    except TelegramError:
        return False


def escape_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
    )


# ── Welcome ───────────────────────────────────────────────────────────────────
async def delete_message_later(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Job callback: delete a scheduled message."""
    data = context.job.data
    try:
        await context.bot.delete_message(chat_id=data["chat_id"], message_id=data["message_id"])
    except TelegramError as e:
        logger.warning("Could not delete message: %s", e)


async def greet_new_members(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fires when someone joins the group."""
    result = update.chat_member
    if result is None:
        return

    old_status = result.old_chat_member.status
    new_status = result.new_chat_member.status

    # Only handle actual joins (not role changes)
    joined = (
        old_status in {ChatMemberStatus.LEFT, ChatMemberStatus.BANNED}
        and new_status in {ChatMemberStatus.MEMBER, ChatMemberStatus.RESTRICTED}
    )
    if not joined:
        return

    user = result.new_chat_member.user
    chat = result.chat
    first_name = escape_html(user.first_name or "there")
    chat_title = escape_html(chat.title or "this group")

    # Build welcome text
    welcome_text = (
        f"👋 <b>Welcome, <a href='tg://user?id={user.id}'>{first_name}</a>!</b>\n\n"
        f"Glad to have you in <b>{chat_title}</b>. 🎉\n\n"
        f"📜 Please read the group rules and be respectful to everyone.\n"
        f"<i>This message will be removed in {WELCOME_DELETE_AFTER // 60} minutes.</i>"
    )

    button = InlineKeyboardMarkup(
        [[InlineKeyboardButton("👍 Say hi!", callback_data=f"greet_{user.id}")]]
    )

    sent = await update.effective_chat.send_message(
        welcome_text,
        parse_mode="HTML",
        reply_markup=button,
    )

    # Schedule deletion
    run_at = datetime.now() + timedelta(seconds=WELCOME_DELETE_AFTER)
    context.job_queue.run_once(
        delete_message_later,
        when=WELCOME_DELETE_AFTER,
        data={"chat_id": sent.chat_id, "message_id": sent.message_id},
        name=f"del_welcome_{sent.message_id}",
    )
    logger.info("Welcome sent for %s in %s; deletes at %s", user.id, chat.id, run_at)


async def greet_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the 'Say hi!' button press."""
    query = update.callback_query
    await query.answer("Hey! 👋 Welcome to the group!", show_alert=False)


# ── Admin commands ────────────────────────────────────────────────────────────
async def kick_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/kick — remove a user (reply to their message)."""
    if not await is_admin(update, context, update.effective_user.id):
        await update.message.reply_text("⛔ Admins only.")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("↩️ Reply to the user you want to kick.")
        return

    target = update.message.reply_to_message.from_user
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, target.id)
        await context.bot.unban_chat_member(update.effective_chat.id, target.id)  # soft kick
        await update.message.reply_text(f"👢 {escape_html(target.first_name)} was kicked.", parse_mode="HTML")
    except TelegramError as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/ban — permanently ban a user (reply to their message)."""
    if not await is_admin(update, context, update.effective_user.id):
        await update.message.reply_text("⛔ Admins only.")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("↩️ Reply to the user you want to ban.")
        return

    target = update.message.reply_to_message.from_user
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, target.id)
        await update.message.reply_text(f"🔨 {escape_html(target.first_name)} was banned.", parse_mode="HTML")
    except TelegramError as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/mute [minutes] — restrict a user from sending messages."""
    if not await is_admin(update, context, update.effective_user.id):
        await update.message.reply_text("⛔ Admins only.")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("↩️ Reply to the user you want to mute.")
        return

    minutes = 5  # default
    if context.args:
        try:
            minutes = max(1, int(context.args[0]))
        except ValueError:
            pass

    target = update.message.reply_to_message.from_user
    until = datetime.now() + timedelta(minutes=minutes)

    try:
        await context.bot.restrict_chat_member(
            update.effective_chat.id,
            target.id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until,
        )
        await update.message.reply_text(
            f"🔇 {escape_html(target.first_name)} muted for <b>{minutes} minute(s)</b>.",
            parse_mode="HTML",
        )
    except TelegramError as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def unmute_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/unmute — restore a muted user's ability to speak."""
    if not await is_admin(update, context, update.effective_user.id):
        await update.message.reply_text("⛔ Admins only.")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("↩️ Reply to the user you want to unmute.")
        return

    target = update.message.reply_to_message.from_user
    try:
        await context.bot.restrict_chat_member(
            update.effective_chat.id,
            target.id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_polls=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
            ),
        )
        await update.message.reply_text(
            f"🔊 {escape_html(target.first_name)} can speak again.", parse_mode="HTML"
        )
    except TelegramError as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def warn_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/warn — warn a user (tracked in bot_data; 3 warns = auto-ban)."""
    if not await is_admin(update, context, update.effective_user.id):
        await update.message.reply_text("⛔ Admins only.")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("↩️ Reply to the user you want to warn.")
        return

    target = update.message.reply_to_message.from_user
    chat_id = str(update.effective_chat.id)
    user_id = str(target.id)

    warns = context.bot_data.setdefault("warns", {})
    warns.setdefault(chat_id, {})
    warns[chat_id][user_id] = warns[chat_id].get(user_id, 0) + 1
    count = warns[chat_id][user_id]

    if count >= 3:
        try:
            await context.bot.ban_chat_member(update.effective_chat.id, target.id)
            warns[chat_id][user_id] = 0
            await update.message.reply_text(
                f"🔨 {escape_html(target.first_name)} reached <b>3 warnings</b> and was banned.",
                parse_mode="HTML",
            )
        except TelegramError as e:
            await update.message.reply_text(f"❌ Could not ban: {e}")
    else:
        await update.message.reply_text(
            f"⚠️ {escape_html(target.first_name)} warned. "
            f"<b>{count}/3</b> warnings. Next warn at 3 = auto-ban.",
            parse_mode="HTML",
        )


async def pin_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/pin — pin the replied-to message."""
    if not await is_admin(update, context, update.effective_user.id):
        await update.message.reply_text("⛔ Admins only.")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("↩️ Reply to the message you want to pin.")
        return

    try:
        await context.bot.pin_chat_message(
            update.effective_chat.id,
            update.message.reply_to_message.message_id,
            disable_notification=False,
        )
        await update.message.reply_text("📌 Message pinned!")
    except TelegramError as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def unpin_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/unpin — unpin the most recently pinned message."""
    if not await is_admin(update, context, update.effective_user.id):
        await update.message.reply_text("⛔ Admins only.")
        return

    try:
        await context.bot.unpin_chat_message(update.effective_chat.id)
        await update.message.reply_text("📌 Message unpinned.")
    except TelegramError as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def purge_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/purge N — delete the last N messages (max 100)."""
    if not await is_admin(update, context, update.effective_user.id):
        await update.message.reply_text("⛔ Admins only.")
        return

    n = 10
    if context.args:
        try:
            n = min(100, max(1, int(context.args[0])))
        except ValueError:
            pass

    msg_id = update.message.message_id
    ids_to_delete = list(range(msg_id, msg_id - n - 1, -1))

    deleted = 0
    for mid in ids_to_delete:
        try:
            await context.bot.delete_message(update.effective_chat.id, mid)
            deleted += 1
        except TelegramError:
            pass

    notice = await update.effective_chat.send_message(f"🗑 Deleted {deleted} message(s).")
    await asyncio.sleep(5)
    try:
        await notice.delete()
    except TelegramError:
        pass


# ── Info commands ─────────────────────────────────────────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "👋 <b>Group Manager Bot is online!</b>\n\n"
        "Add me to a group and make me an admin to get started.\n"
        "Use /help to see all commands.",
        parse_mode="HTML",
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "🤖 <b>Group Manager — Commands</b>\n\n"
        "<b>👑 Admin Commands</b>\n"
        "/kick   – Kick a user (reply)\n"
        "/ban    – Permanently ban (reply)\n"
        "/mute [min] – Mute a user (reply)\n"
        "/unmute – Unmute a user (reply)\n"
        "/warn   – Warn user; 3 warns = auto-ban (reply)\n"
        "/pin    – Pin a message (reply)\n"
        "/unpin  – Unpin last pinned message\n"
        "/purge [n] – Delete last n messages (max 100)\n\n"
        "<b>ℹ️ General</b>\n"
        "/start  – Bot info\n"
        "/help   – This message\n"
        "/rules  – Show group rules\n"
        "/info   – Show your account info\n\n"
        "<i>Welcome messages auto-delete after "
        f"{WELCOME_DELETE_AFTER // 60} minutes.</i>"
    )
    await update.message.reply_text(text, parse_mode="HTML")


async def cmd_rules(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "📜 <b>Group Rules</b>\n\n"
        "1️⃣ Be respectful to all members.\n"
        "2️⃣ No spam or self-promotion.\n"
        "3️⃣ No offensive or NSFW content.\n"
        "4️⃣ Stay on topic.\n"
        "5️⃣ Follow admins' instructions.\n\n"
        "<i>Violations may result in a warning, mute, kick, or ban.</i>",
        parse_mode="HTML",
    )


async def cmd_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat = update.effective_chat
    member = await context.bot.get_chat_member(chat.id, user.id)

    status_emoji = {
        ChatMemberStatus.OWNER: "👑 Owner",
        ChatMemberStatus.ADMINISTRATOR: "🛡 Admin",
        ChatMemberStatus.MEMBER: "👤 Member",
        ChatMemberStatus.RESTRICTED: "🔇 Restricted",
        ChatMemberStatus.LEFT: "🚪 Left",
        ChatMemberStatus.BANNED: "🔨 Banned",
    }.get(member.status, member.status)

    await update.message.reply_text(
        f"👤 <b>User Info</b>\n\n"
        f"Name: {escape_html(user.full_name)}\n"
        f"ID: <code>{user.id}</code>\n"
        f"Username: @{user.username or 'N/A'}\n"
        f"Status: {status_emoji}",
        parse_mode="HTML",
    )


# ── App bootstrap ─────────────────────────────────────────────────────────────
def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()

    # Welcome new members
    app.add_handler(ChatMemberHandler(greet_new_members, ChatMemberHandler.CHAT_MEMBER))

    # Button callback
    app.add_handler(CallbackQueryHandler(greet_button_callback, pattern=r"^greet_"))

    # General commands
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("rules", cmd_rules))
    app.add_handler(CommandHandler("info", cmd_info))

    # Admin commands
    app.add_handler(CommandHandler("kick", kick_user))
    app.add_handler(CommandHandler("ban", ban_user))
    app.add_handler(CommandHandler("mute", mute_user))
    app.add_handler(CommandHandler("unmute", unmute_user))
    app.add_handler(CommandHandler("warn", warn_user))
    app.add_handler(CommandHandler("pin", pin_message))
    app.add_handler(CommandHandler("unpin", unpin_message))
    app.add_handler(CommandHandler("purge", purge_messages))

    if WEBHOOK_URL:
        # ── Webhook mode (Heroku) ────────────────────────────────────────────
        webhook_path = f"/webhook/{BOT_TOKEN}"
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=webhook_path,
            webhook_url=f"{WEBHOOK_URL}{webhook_path}",
        )
        logger.info("Running in webhook mode on port %s", PORT)
    else:
        # ── Polling mode (local dev) ─────────────────────────────────────────
        logger.info("Running in polling mode (local dev)")
        app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
