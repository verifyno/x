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
    ChatMemberHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from telegram.constants import ChatMemberStatus
from telegram.error import TelegramError

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
BOT_TOKEN            = os.environ["BOT_TOKEN"]
WELCOME_DELETE_AFTER = int(os.environ.get("WELCOME_DELETE_AFTER", 600))
WEBHOOK_URL          = os.environ.get("WEBHOOK_URL", "")
PORT                 = int(os.environ.get("PORT", 8443))

# Video source: https://t.me/sourioo/2
VIDEO_CHANNEL = "sourioo"
VIDEO_MSG_ID  = 2

ADMIN_STATUSES = {ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER}


# ── Helpers ───────────────────────────────────────────────────────────────────
def escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    try:
        member = await context.bot.get_chat_member(update.effective_chat.id, user_id)
        return member.status in ADMIN_STATUSES
    except TelegramError:
        return False


# ── Inline menus ──────────────────────────────────────────────────────────────
def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Professional main menu shown on /start."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📋 Commands",  callback_data="menu_commands"),
            InlineKeyboardButton("📜 Rules",     callback_data="menu_rules"),
        ],
        [
            InlineKeyboardButton("👤 My Info",   callback_data="menu_info"),
            InlineKeyboardButton("❓ Help",      callback_data="menu_help"),
        ],
        [
            InlineKeyboardButton("➕ Add me to your group",
                                 url="https://t.me/YourBotUsername?startgroup=true"),
        ],
    ])


def rules_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Main Menu", callback_data="menu_main")],
    ])


def back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("« Back", callback_data="menu_main")],
    ])


# ── Send video with caption (no "Forwarded from" tag) ────────────────────────
async def send_video_with_caption(
    chat_id: int,
    caption: str,
    reply_markup: InlineKeyboardMarkup,
    context: ContextTypes.DEFAULT_TYPE,
) -> int | None:
    """
    Copy the video from @sourioo (message 2) into chat_id,
    replacing its caption with our own text and attaching a keyboard.
    Returns the sent message_id, or None on failure.
    """
    try:
        sent = await context.bot.copy_message(
            chat_id=chat_id,
            from_chat_id=f"@{VIDEO_CHANNEL}",
            message_id=VIDEO_MSG_ID,
            caption=caption,
            parse_mode="HTML",
            reply_markup=reply_markup,
        )
        return sent.message_id
    except TelegramError as e:
        logger.warning("copy_message failed: %s", e)
        return None


# ── Welcome new members ───────────────────────────────────────────────────────
async def delete_message_later(context: ContextTypes.DEFAULT_TYPE) -> None:
    data = context.job.data
    try:
        await context.bot.delete_message(chat_id=data["chat_id"], message_id=data["message_id"])
    except TelegramError as e:
        logger.warning("Could not delete message: %s", e)


async def greet_new_members(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    result = update.chat_member
    if result is None:
        return

    old_status = result.old_chat_member.status
    new_status  = result.new_chat_member.status

    joined = (
        old_status in {ChatMemberStatus.LEFT, ChatMemberStatus.BANNED}
        and new_status in {ChatMemberStatus.MEMBER, ChatMemberStatus.RESTRICTED}
    )
    if not joined:
        return

    user       = result.new_chat_member.user
    chat       = result.chat
    first_name = escape_html(user.first_name or "there")
    chat_title = escape_html(chat.title or "this group")

    caption = (
        f"👋 <b>Welcome, <a href='tg://user?id={user.id}'>{first_name}</a>!</b>\n\n"
        f"We're glad to have you in <b>{chat_title}</b>! 🎉\n\n"
        f"• Read the /rules before chatting\n"
        f"• Be respectful to everyone\n"
        f"• Have fun and enjoy your stay!\n\n"
        f"<i>⏳ This message disappears in {WELCOME_DELETE_AFTER // 60} min.</i>"
    )

    welcome_keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📜 Read Rules", callback_data="menu_rules"),
            InlineKeyboardButton("👋 Say Hi!",    callback_data=f"greet_{user.id}"),
        ]
    ])

    msg_id = await send_video_with_caption(chat.id, caption, welcome_keyboard, context)

    if msg_id:
        context.job_queue.run_once(
            delete_message_later,
            when=WELCOME_DELETE_AFTER,
            data={"chat_id": chat.id, "message_id": msg_id},
            name=f"del_welcome_{msg_id}",
        )
        logger.info("Welcome sent for %s in %s", user.id, chat.id)


# ── Callback query handler (all inline buttons) ───────────────────────────────
COMMANDS_TEXT = (
    "🤖 <b>Available Commands</b>\n\n"
    "<b>👑 Admin Only</b>\n"
    "/kick — Kick a member <i>(reply)</i>\n"
    "/ban — Permanently ban <i>(reply)</i>\n"
    "/mute [min] — Mute a member <i>(reply)</i>\n"
    "/unmute — Restore voice <i>(reply)</i>\n"
    "/warn — Warn member; 3 = auto-ban <i>(reply)</i>\n"
    "/pin — Pin a message <i>(reply)</i>\n"
    "/unpin — Unpin latest\n"
    "/purge [n] — Delete last n messages\n\n"
    "<b>ℹ️ General</b>\n"
    "/start — Welcome screen\n"
    "/rules — Group rules\n"
    "/info — Your account info\n"
    "/help — This command list"
)

RULES_TEXT = (
    "📜 <b>Group Rules</b>\n\n"
    "1️⃣  <b>Respect everyone</b> — no insults or harassment.\n"
    "2️⃣  <b>No spam</b> — no repeated messages or self-promo.\n"
    "3️⃣  <b>No NSFW content</b> — keep it clean.\n"
    "4️⃣  <b>Stay on topic</b> — relevant posts only.\n"
    "5️⃣  <b>Follow admins</b> — their word is final.\n\n"
    "<i>⚠️ Breaking rules leads to warn → mute → ban.</i>"
)


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    data  = query.data
    user  = query.from_user

    # ── greet button ──────────────────────────────────────────────────────────
    if data.startswith("greet_"):
        await query.answer("Hey! 👋 Welcome aboard!", show_alert=False)
        return

    await query.answer()

    # ── main menu ─────────────────────────────────────────────────────────────
    if data == "menu_main":
        caption = (
            "🤖 <b>Group Manager Bot</b>\n\n"
            "I keep your group safe and organised.\n"
            "Choose an option below to get started."
        )
        try:
            await query.edit_message_caption(
                caption=caption,
                parse_mode="HTML",
                reply_markup=main_menu_keyboard(),
            )
        except TelegramError:
            pass

    # ── commands ──────────────────────────────────────────────────────────────
    elif data == "menu_commands":
        try:
            await query.edit_message_caption(
                caption=COMMANDS_TEXT,
                parse_mode="HTML",
                reply_markup=back_keyboard(),
            )
        except TelegramError:
            pass

    # ── rules ─────────────────────────────────────────────────────────────────
    elif data == "menu_rules":
        try:
            await query.edit_message_caption(
                caption=RULES_TEXT,
                parse_mode="HTML",
                reply_markup=rules_keyboard(),
            )
        except TelegramError:
            pass

    # ── my info ───────────────────────────────────────────────────────────────
    elif data == "menu_info":
        try:
            chat_id = query.message.chat_id
            member  = await context.bot.get_chat_member(chat_id, user.id)
            status_label = {
                ChatMemberStatus.OWNER:         "👑 Owner",
                ChatMemberStatus.ADMINISTRATOR: "🛡 Admin",
                ChatMemberStatus.MEMBER:        "👤 Member",
                ChatMemberStatus.RESTRICTED:    "🔇 Restricted",
                ChatMemberStatus.LEFT:          "🚪 Left",
                ChatMemberStatus.BANNED:        "🔨 Banned",
            }.get(member.status, member.status)

            info_text = (
                f"👤 <b>Your Info</b>\n\n"
                f"Name: {escape_html(user.full_name)}\n"
                f"ID: <code>{user.id}</code>\n"
                f"Username: @{user.username or 'N/A'}\n"
                f"Status: {status_label}"
            )
            await query.edit_message_caption(
                caption=info_text,
                parse_mode="HTML",
                reply_markup=back_keyboard(),
            )
        except TelegramError:
            pass

    # ── help ──────────────────────────────────────────────────────────────────
    elif data == "menu_help":
        help_text = (
            "❓ <b>How to use this bot</b>\n\n"
            "1. Add me to your Telegram group.\n"
            "2. Promote me to <b>Admin</b> with these rights:\n"
            "   • Delete messages\n"
            "   • Ban &amp; restrict members\n"
            "   • Pin messages\n\n"
            "3. I will automatically:\n"
            "   • Welcome new members 👋\n"
            "   • Delete welcome after 10 min ⏳\n"
            "   • Handle admin commands ⚙️\n\n"
            "Use /start to return to the main screen."
        )
        try:
            await query.edit_message_caption(
                caption=help_text,
                parse_mode="HTML",
                reply_markup=back_keyboard(),
            )
        except TelegramError:
            pass


# ── /start ────────────────────────────────────────────────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    caption = (
        "🤖 <b>Group Manager Bot</b>\n\n"
        "I keep your group safe and organised.\n"
        "Choose an option below to get started."
    )
    await send_video_with_caption(
        update.effective_chat.id, caption, main_menu_keyboard(), context
    )


# ── /rules ────────────────────────────────────────────────────────────────────
async def cmd_rules(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await send_video_with_caption(
        update.effective_chat.id, RULES_TEXT, rules_keyboard(), context
    )


# ── /help ─────────────────────────────────────────────────────────────────────
async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(COMMANDS_TEXT, parse_mode="HTML")


# ── /info ─────────────────────────────────────────────────────────────────────
async def cmd_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user   = update.effective_user
    chat   = update.effective_chat
    member = await context.bot.get_chat_member(chat.id, user.id)

    status_label = {
        ChatMemberStatus.OWNER:         "👑 Owner",
        ChatMemberStatus.ADMINISTRATOR: "🛡 Admin",
        ChatMemberStatus.MEMBER:        "👤 Member",
        ChatMemberStatus.RESTRICTED:    "🔇 Restricted",
        ChatMemberStatus.LEFT:          "🚪 Left",
        ChatMemberStatus.BANNED:        "🔨 Banned",
    }.get(member.status, member.status)

    await update.message.reply_text(
        f"👤 <b>User Info</b>\n\n"
        f"Name: {escape_html(user.full_name)}\n"
        f"ID: <code>{user.id}</code>\n"
        f"Username: @{user.username or 'N/A'}\n"
        f"Status: {status_label}",
        parse_mode="HTML",
    )


# ── Admin commands ────────────────────────────────────────────────────────────
async def kick_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await is_admin(update, context, update.effective_user.id):
        await update.message.reply_text("⛔ Admins only.")
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("↩️ Reply to the user you want to kick.")
        return
    target = update.message.reply_to_message.from_user
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, target.id)
        await context.bot.unban_chat_member(update.effective_chat.id, target.id)
        await update.message.reply_text(f"👢 <b>{escape_html(target.first_name)}</b> was kicked.", parse_mode="HTML")
    except TelegramError as e:
        await update.message.reply_text(f"❌ {e}")


async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await is_admin(update, context, update.effective_user.id):
        await update.message.reply_text("⛔ Admins only.")
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("↩️ Reply to the user you want to ban.")
        return
    target = update.message.reply_to_message.from_user
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, target.id)
        await update.message.reply_text(f"🔨 <b>{escape_html(target.first_name)}</b> was banned.", parse_mode="HTML")
    except TelegramError as e:
        await update.message.reply_text(f"❌ {e}")


async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await is_admin(update, context, update.effective_user.id):
        await update.message.reply_text("⛔ Admins only.")
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("↩️ Reply to the user you want to mute.")
        return
    minutes = 5
    if context.args:
        try:
            minutes = max(1, int(context.args[0]))
        except ValueError:
            pass
    target = update.message.reply_to_message.from_user
    until  = datetime.now() + timedelta(minutes=minutes)
    try:
        await context.bot.restrict_chat_member(
            update.effective_chat.id,
            target.id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until,
        )
        await update.message.reply_text(
            f"🔇 <b>{escape_html(target.first_name)}</b> muted for <b>{minutes} min</b>.",
            parse_mode="HTML",
        )
    except TelegramError as e:
        await update.message.reply_text(f"❌ {e}")


async def unmute_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
            f"🔊 <b>{escape_html(target.first_name)}</b> can speak again.",
            parse_mode="HTML",
        )
    except TelegramError as e:
        await update.message.reply_text(f"❌ {e}")


async def warn_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await is_admin(update, context, update.effective_user.id):
        await update.message.reply_text("⛔ Admins only.")
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("↩️ Reply to the user you want to warn.")
        return
    target  = update.message.reply_to_message.from_user
    chat_id = str(update.effective_chat.id)
    user_id = str(target.id)
    warns   = context.bot_data.setdefault("warns", {})
    warns.setdefault(chat_id, {})
    warns[chat_id][user_id] = warns[chat_id].get(user_id, 0) + 1
    count = warns[chat_id][user_id]
    if count >= 3:
        try:
            await context.bot.ban_chat_member(update.effective_chat.id, target.id)
            warns[chat_id][user_id] = 0
            await update.message.reply_text(
                f"🔨 <b>{escape_html(target.first_name)}</b> reached 3 warnings and was banned.",
                parse_mode="HTML",
            )
        except TelegramError as e:
            await update.message.reply_text(f"❌ {e}")
    else:
        await update.message.reply_text(
            f"⚠️ <b>{escape_html(target.first_name)}</b> warned — <b>{count}/3</b>. "
            f"At 3 warnings: auto-ban.",
            parse_mode="HTML",
        )


async def pin_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
        )
        await update.message.reply_text("📌 Message pinned!")
    except TelegramError as e:
        await update.message.reply_text(f"❌ {e}")


async def unpin_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await is_admin(update, context, update.effective_user.id):
        await update.message.reply_text("⛔ Admins only.")
        return
    try:
        await context.bot.unpin_chat_message(update.effective_chat.id)
        await update.message.reply_text("📌 Message unpinned.")
    except TelegramError as e:
        await update.message.reply_text(f"❌ {e}")


async def purge_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
    deleted = 0
    for mid in range(msg_id, msg_id - n - 1, -1):
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


# ── Bootstrap ─────────────────────────────────────────────────────────────────
def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()

    # Chat member updates (welcome)
    app.add_handler(ChatMemberHandler(greet_new_members, ChatMemberHandler.CHAT_MEMBER))

    # All inline button callbacks
    app.add_handler(CallbackQueryHandler(button_callback))

    # General commands
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help",  cmd_help))
    app.add_handler(CommandHandler("rules", cmd_rules))
    app.add_handler(CommandHandler("info",  cmd_info))

    # Admin commands
    app.add_handler(CommandHandler("kick",   kick_user))
    app.add_handler(CommandHandler("ban",    ban_user))
    app.add_handler(CommandHandler("mute",   mute_user))
    app.add_handler(CommandHandler("unmute", unmute_user))
    app.add_handler(CommandHandler("warn",   warn_user))
    app.add_handler(CommandHandler("pin",    pin_message))
    app.add_handler(CommandHandler("unpin",  unpin_message))
    app.add_handler(CommandHandler("purge",  purge_messages))

    if WEBHOOK_URL:
        webhook_path = f"/webhook/{BOT_TOKEN}"
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=webhook_path,
            webhook_url=f"{WEBHOOK_URL}{webhook_path}",
        )
        logger.info("Webhook mode — port %s", PORT)
    else:
        logger.info("Polling mode (local dev)")
        app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
