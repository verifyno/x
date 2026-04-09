#!/usr/bin/env python3
# ╔══════════════════════════════════════════════════════════════════════════╗
# ║         🍂🥀🍁  AUTUMN MANAGER BOT  🍁🥀🍂                            ║
# ║   Ultra-Advanced Telegram Group Management Bot                          ║
# ║   Features: Group Management • Tic-Tac-Toe • Fancy Text                ║
# ║             X/Twitter Downloader • Image Converter • Tools             ║
# ╚══════════════════════════════════════════════════════════════════════════╝
#
# Requirements:
#   pip install python-telegram-bot~=20.0 Pillow yt-dlp
#
# Environment variables:
#   BOT_TOKEN            — your Telegram bot token (required)
#   WELCOME_DELETE_AFTER — seconds before welcome card is deleted (default 600)
#   WEBHOOK_URL          — set for webhook mode, omit for polling
#   PORT                 — webhook port (default 8443)

import os, io, re, math, logging, asyncio, random, tempfile
from datetime import datetime, timedelta
from pathlib import Path

from telegram import (
    Update, BotCommand, ChatPermissions,
    InlineKeyboardButton, InlineKeyboardMarkup,
)
from telegram.ext import (
    Application, CommandHandler, ChatMemberHandler,
    CallbackQueryHandler, MessageHandler, ContextTypes, filters,
)
from telegram.constants import ChatMemberStatus, ParseMode
from telegram.error import TelegramError

try:
    from PIL import Image
    PIL_OK = True
except ImportError:
    PIL_OK = False

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

VIDEO_CHANNEL = "@sourioo"
VIDEO_MSG_ID  = 2

ADMIN_STATUSES = {ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER}

X_URL_RE = re.compile(
    r'https?://(?:www\.)?(?:twitter\.com|x\.com)/\S+/status/\d+\S*',
    re.IGNORECASE,
)

# ═════════════════════════════════════════════════════════════════════════════
#  FANCY TEXT  ✏️
# ═════════════════════════════════════════════════════════════════════════════

# Pre-validated Unicode math-alphabet character strings (26 letters each)
_BL = "𝐚𝐛𝐜𝐝𝐞𝐟𝐠𝐡𝐢𝐣𝐤𝐥𝐦𝐧𝐨𝐩𝐪𝐫𝐬𝐭𝐮𝐯𝐰𝐱𝐲𝐳"
_BU = "𝐀𝐁𝐂𝐃𝐄𝐅𝐆𝐇𝐈𝐉𝐊𝐋𝐌𝐍𝐎𝐏𝐐𝐑𝐒𝐓𝐔𝐕𝐖𝐗𝐘𝐙"
_BD = "𝟎𝟏𝟐𝟑𝟒𝟓𝟔𝟕𝟖𝟗"

_IL = "𝑎𝑏𝑐𝑑𝑒𝑓𝑔ℎ𝑖𝑗𝑘𝑙𝑚𝑛𝑜𝑝𝑞𝑟𝑠𝑡𝑢𝑣𝑤𝑥𝑦𝑧"
_IU = "𝐴𝐵𝐶𝐷𝐸𝐹𝐺𝐻𝐼𝐽𝐾𝐿𝑀𝑁𝑂𝑃𝑄𝑅𝑆𝑇𝑈𝑉𝑊𝑋𝑌𝑍"

_BIL = "𝒂𝒃𝒄𝒅𝒆𝒇𝒈𝒉𝒊𝒋𝒌𝒍𝒎𝒏𝒐𝒑𝒒𝒓𝒔𝒕𝒖𝒗𝒘𝒙𝒚𝒛"
_BIU = "𝑨𝑩𝑪𝑫𝑬𝑭𝑮𝑯𝑰𝑱𝑲𝑳𝑴𝑵𝑶𝑷𝑸𝑹𝑺𝑻𝑼𝑽𝑾𝑿𝒀𝒁"

_SL = "𝒶𝒷𝒸𝒹ℯ𝒻ℊ𝒽𝒾𝒿𝓀𝓁𝓂𝓃ℴ𝓅𝓆𝓇𝓈𝓉𝓊𝓋𝓌𝓍𝓎𝓏"
_SU = "𝒜ℬ𝒞𝒟ℰℱ𝒢ℋℐ𝒥𝒦ℒℳ𝒩𝒪𝒫𝒬ℛ𝒮𝒯𝒰𝒱𝒲𝒳𝒴𝒵"

_FL = "𝔞𝔟𝔠𝔡𝔢𝔣𝔤𝔥𝔦𝔧𝔨𝔩𝔪𝔫𝔬𝔭𝔮𝔯𝔰𝔱𝔲𝔳𝔴𝔵𝔶𝔷"
_FU = "𝔄𝔅ℭ𝔇𝔈𝔉𝔊ℌℑ𝔍𝔎𝔏𝔐𝔑𝔒𝔓𝔔ℜ𝔖𝔗𝔘𝔙𝔚𝔛𝔜ℨ"

_DL = "𝕒𝕓𝕔𝕕𝕖𝕗𝕘𝕙𝕚𝕛𝕜𝕝𝕞𝕟𝕠𝕡𝕢𝕣𝕤𝕥𝕦𝕧𝕨𝕩𝕪𝕫"
_DU = "𝔸𝔹ℂ𝔻𝔼𝔽𝔾ℍ𝕀𝕁𝕂𝕃𝕄ℕ𝕆ℙℚℝ𝕊𝕋𝕌𝕍𝕎𝕏𝕐ℤ"
_DD = "𝟘𝟙𝟚𝟛𝟜𝟝𝟞𝟟𝟠𝟡"

_ML = "𝚊𝚋𝚌𝚍𝚎𝚏𝚐𝚑𝚒𝚓𝚔𝚕𝚖𝚗𝚘𝚙𝚚𝚛𝚜𝚝𝚞𝚟𝚠𝚡𝚢𝚣"
_MU = "𝙰𝙱𝙲𝙳𝙴𝙵𝙶𝙷𝙸𝙹𝙺𝙻𝙼𝙽𝙾𝙿𝚀𝚁𝚂𝚃𝚄𝚅𝚆𝚇𝚈𝚉"
_MD = "𝟶𝟷𝟸𝟹𝟺𝟻𝟼𝟽𝟾𝟿"

_BBL = "ⓐⓑⓒⓓⓔⓕⓖⓗⓘⓙⓚⓛⓜⓝⓞⓟⓠⓡⓢⓣⓤⓥⓦⓧⓨⓩ"
_BBU = "ⒶⒷⒸⒹⒺⒻⒼⒽⒾⒿⓀⓁⓂⓃⓄⓅⓆⓇⓈⓉⓊⓋⓌⓍⓎⓏ"
_BBD = "⓪①②③④⑤⑥⑦⑧⑨"

_SMALL_CAPS = {
    **{c: t for c, t in zip("abcdefghijklmnopqrstuvwxyz",
                              "ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘQʀsTᴜᴠᴡxʏᴢ")},
    **{c.upper(): t for c, t in zip("abcdefghijklmnopqrstuvwxyz",
                                     "ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘQʀsTᴜᴠᴡxʏᴢ")},
}

_UPSIDE_DOWN = {
    **{c: t for c, t in zip(
        "abcdefghijklmnopqrstuvwxyz",
        "ɐqɔpǝɟƃɥᴉɾʞlɯuopdqɹsʇnʌʍxʎz")},
    **{c: t for c, t in zip(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "∀qƆpƎℲפHIɾʞ˥WNOԀQɹS┴∩ΛMX⅄Z")},
    **{c: t for c, t in zip("0123456789", "0ƖᄅƐㄣϛ9ㄥ86")},
    **{"!": "¡", "?": "¿", ".": "˙", ",": "'"},
}


def _str_font(text: str, lower_s: str, upper_s: str, digit_s: str = "") -> str:
    lm = {chr(ord('a') + i): c for i, c in enumerate(lower_s)}
    um = {chr(ord('A') + i): c for i, c in enumerate(upper_s)}
    dm = {str(i): c for i, c in enumerate(digit_s)} if digit_s else {}
    return "".join(lm.get(c) or um.get(c) or dm.get(c) or c for c in text)


def _map_font(text: str, mapping: dict) -> str:
    return "".join(mapping.get(c, c) for c in text)


def _strikethrough(text: str) -> str:
    return "".join(c + "\u0336" for c in text)


def _fullwidth(text: str) -> str:
    result = []
    for c in text:
        cp = ord(c)
        if ord('A') <= cp <= ord('Z'):
            result.append(chr(cp - ord('A') + 0xFF21))
        elif ord('a') <= cp <= ord('z'):
            result.append(chr(cp - ord('a') + 0xFF41))
        elif ord('0') <= cp <= ord('9'):
            result.append(chr(cp - ord('0') + 0xFF10))
        elif c == ' ':
            result.append('\u3000')
        else:
            result.append(c)
    return "".join(result)


def _wavy(text: str) -> str:
    """Alternating UPPER/lower"""
    return "".join(c.upper() if i % 2 == 0 else c.lower() for i, c in enumerate(text))


# Ordered dict of style name → transform function
FONT_STYLES: dict = {
    "𝗕𝗼𝗹𝗱":           lambda t: _str_font(t, _BL, _BU, _BD),
    "𝘐𝘵𝘢𝘭𝘪𝘤":         lambda t: _str_font(t, _IL, _IU),
    "𝑩𝒐𝒍𝒅 𝑰𝒕𝒂𝒍𝒊𝒄":   lambda t: _str_font(t, _BIL, _BIU),
    "𝒮𝒸𝓇𝒾𝓅𝓉":         lambda t: _str_font(t, _SL, _SU),
    "𝔉𝔯𝔞𝔨𝔱𝔲𝔯":       lambda t: _str_font(t, _FL, _FU),
    "𝔻𝕠𝕦𝕓𝕝𝕖":         lambda t: _str_font(t, _DL, _DU, _DD),
    "𝙼𝚘𝚗𝚘":            lambda t: _str_font(t, _ML, _MU, _MD),
    "Ⓑⓤⓑⓑⓛⓔ":        lambda t: _str_font(t, _BBL, _BBU, _BBD),
    "Sᴍᴀʟʟ Cᴀᴘs":      lambda t: _map_font(t, _SMALL_CAPS),
    "ʍʌʇʇʎ":            lambda t: _map_font(t, _UPSIDE_DOWN)[::-1],
    "Ｗｉｄｅ":           _fullwidth,
    "WaVy TeXt":        _wavy,
    "S̶t̶r̶i̶k̶e̶t̶h̶r̶o̶u̶g̶h̶":  _strikethrough,
}

# ═════════════════════════════════════════════════════════════════════════════
#  TIC-TAC-TOE  🎮
# ═════════════════════════════════════════════════════════════════════════════

_CELL = {"X": "❌", "O": "⭕", " ": "⬜"}


def ttt_keyboard(board: list, game_id: str) -> InlineKeyboardMarkup:
    rows = []
    for r in range(3):
        row = []
        for c in range(3):
            row.append(InlineKeyboardButton(
                _CELL[board[r][c]],
                callback_data=f"ttt_{game_id}_{r}_{c}",
            ))
        rows.append(row)
    rows.append([InlineKeyboardButton("🏳️ Surrender", callback_data=f"tttsur_{game_id}")])
    return InlineKeyboardMarkup(rows)


def ttt_check_winner(board: list):
    """Returns 'X', 'O', 'draw', or None."""
    lines = [
        [(0,0),(0,1),(0,2)], [(1,0),(1,1),(1,2)], [(2,0),(2,1),(2,2)],
        [(0,0),(1,0),(2,0)], [(0,1),(1,1),(2,1)], [(0,2),(1,2),(2,2)],
        [(0,0),(1,1),(2,2)], [(0,2),(1,1),(2,0)],
    ]
    for line in lines:
        vals = [board[r][c] for r, c in line]
        if vals[0] != " " and all(v == vals[0] for v in vals):
            return vals[0]
    if all(board[r][c] != " " for r in range(3) for c in range(3)):
        return "draw"
    return None


def ttt_render(game: dict) -> str:
    x_name = esc(game["names"]["X"])
    o_name = esc(game["names"]["O"])
    cur    = game["current"]
    turn   = esc(game["names"][cur])
    icon   = "❌" if cur == "X" else "⭕"
    return (
        f"🎮 <b>Tic-Tac-Toe</b> 🍂\n"
        f"❌ <b>{x_name}</b>  vs  ⭕ <b>{o_name}</b>\n\n"
        f"{icon} <b>{turn}'s turn!</b>"
    )


def ttt_board_str(board: list) -> str:
    return "\n".join(" ".join(_CELL[board[r][c]] for c in range(3)) for r in range(3))

# ═════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ═════════════════════════════════════════════════════════════════════════════

def esc(text: str) -> str:
    if not text:
        return ""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


async def is_admin(chat_id: int, user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        m = await context.bot.get_chat_member(chat_id, user_id)
        return m.status in ADMIN_STATUSES
    except TelegramError:
        return False


async def admin_guard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not await is_admin(update.effective_chat.id, update.effective_user.id, context):
        await update.message.reply_text("⛔ <b>Admins only.</b>", parse_mode=ParseMode.HTML)
        return False
    return True


async def reply_guard(update: Update, noun: str = "user") -> bool:
    if not update.message.reply_to_message:
        await update.message.reply_text(f"↩️ Reply to the {noun} you want to target.")
        return False
    return True


async def send_video_with_caption(
    chat_id: int, caption: str,
    reply_markup: InlineKeyboardMarkup,
    context: ContextTypes.DEFAULT_TYPE,
):
    try:
        msg = await context.bot.copy_message(
            chat_id=chat_id, from_chat_id=VIDEO_CHANNEL,
            message_id=VIDEO_MSG_ID, caption=caption,
            parse_mode=ParseMode.HTML, reply_markup=reply_markup,
        )
        return msg.message_id
    except TelegramError as e:
        logger.warning("copy_message failed: %s", e)
        return None


async def edit_text_or_caption(q, text: str, reply_markup=None):
    """Edit caption if it's a media message, else edit text."""
    kw = dict(parse_mode=ParseMode.HTML, reply_markup=reply_markup)
    try:
        await q.edit_message_caption(caption=text, **kw)
    except TelegramError:
        try:
            await q.edit_message_text(text=text, **kw)
        except TelegramError:
            pass

# ═════════════════════════════════════════════════════════════════════════════
#  KEYBOARD BUILDERS
# ═════════════════════════════════════════════════════════════════════════════

def start_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📜 Rules",        callback_data="menu_rules"),
            InlineKeyboardButton("ℹ️ My Info",       callback_data="menu_info"),
        ],
        [
            InlineKeyboardButton("👑 Admin Help",    callback_data="menu_admin"),
            InlineKeyboardButton("🎮 Games",         callback_data="menu_games"),
        ],
        [
            InlineKeyboardButton("✏️ Fancy Text",    callback_data="menu_fancy"),
            InlineKeyboardButton("🛠 Tools",         callback_data="menu_tools"),
        ],
        [
            InlineKeyboardButton("📥 X Downloader", callback_data="menu_xdl"),
            InlineKeyboardButton("🆘 Support",       url="https://t.me/sourioo"),
        ],
    ])


def rules_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ I Agree", callback_data="rules_agree"),
            InlineKeyboardButton("🔙 Back",    callback_data="menu_start"),
        ],
    ])


def back_keyboard(target: str = "menu_start") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data=target)]])

# ═════════════════════════════════════════════════════════════════════════════
#  MESSAGE TEMPLATES
# ═════════════════════════════════════════════════════════════════════════════

START_TEXT = (
    "🍂 <b>AUTUMN MANAGER BOT</b> 🍁\n"
    "┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n"
    "✨ <i>The most powerful group manager — with autumn vibes!</i>\n\n"
    "🛡️ <b>Management</b>  — Kick, Ban, Mute, Warn, Purge\n"
    "🎮 <b>Games</b>        — Tic-Tac-Toe for groups\n"
    "✏️ <b>Fancy Text</b>   — 13 Unicode font styles\n"
    "📥 <b>X Downloader</b> — Download Twitter / X media\n"
    "🛠️ <b>Tools</b>        — Image converter, dice, calc & more\n\n"
    "🥀 <i>Add me as Admin in your group to unlock everything!</i>\n"
    "┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄"
)

RULES_TEXT = (
    "📜 <b>Group Rules</b> 🍂\n"
    "┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n\n"
    "1️⃣  Be respectful to every member.\n"
    "2️⃣  No spam, ads, or self-promotion.\n"
    "3️⃣  No offensive or NSFW content.\n"
    "4️⃣  Stay on topic.\n"
    "5️⃣  Follow admins' instructions.\n\n"
    "⚠️ <i>Violations → warning → mute → kick → ban</i>\n"
    "┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄"
)

HELP_TEXT = (
    "🍁 <b>AUTUMN MANAGER — Full Command List</b> 🍂\n"
    "┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n\n"
    "👑 <b>Admin Commands</b>\n"
    "┣ /kick            — Kick a user <i>(reply)</i>\n"
    "┣ /ban             — Permanently ban <i>(reply)</i>\n"
    "┣ /tban 1d|2h|30m  — Temp-ban <i>(reply)</i>\n"
    "┣ /mute [minutes]  — Mute <i>(reply)</i>\n"
    "┣ /unmute          — Restore voice <i>(reply)</i>\n"
    "┣ /warn            — Warn; 3 warnings = auto-ban <i>(reply)</i>\n"
    "┣ /warns           — Check user warn count <i>(reply)</i>\n"
    "┣ /clearwarn       — Clear all warns <i>(reply)</i>\n"
    "┣ /pin             — Pin replied message\n"
    "┣ /unpin           — Unpin latest pinned message\n"
    "┣ /purge [n]       — Delete last N messages (max 100)\n"
    "┣ /promote         — Promote to admin <i>(reply)</i>\n"
    "┣ /demote          — Revoke admin rights <i>(reply)</i>\n"
    "┗ /admins          — List all group admins\n\n"
    "🎮 <b>Games</b>\n"
    "┣ /ttt             — Tic-Tac-Toe <i>(reply to challenge)</i>\n"
    "┗ /endgame         — End current game\n\n"
    "✏️ <b>Fancy Text</b>\n"
    "┗ /fancy [text]    — Generate text in 13 font styles\n\n"
    "📥 <b>X / Twitter Downloader</b>\n"
    "┗ /xdl [link]      — Download media from X/Twitter\n\n"
    "🛠️ <b>Tools</b>\n"
    "┣ /imgconvert      — Convert image format (send photo)\n"
    "┣ /roll [max]      — Roll a dice\n"
    "┣ /flip            — Flip a coin\n"
    "┣ /calc [expr]     — Safe calculator\n"
    "┣ /id              — Get user / chat ID\n"
    "┗ /stats           — Group statistics\n\n"
    "ℹ️ <b>General</b>\n"
    "┣ /start  — Main menu\n"
    "┣ /help   — This command list\n"
    "┣ /rules  — Group rules\n"
    "┗ /info   — Your account info\n"
    "┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄"
)

ADMIN_HELP_TEXT = (
    "👑 <b>Admin Quick Reference</b> 🍁\n"
    "┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n\n"
    "All mod commands work by <b>replying</b> to the target message.\n\n"
    "<b>🔨 Moderation</b>\n"
    "<code>/kick</code>         — Remove (can rejoin)\n"
    "<code>/ban</code>          — Permanent ban\n"
    "<code>/tban 1d</code>      — Ban for 1 day\n"
    "<code>/mute 30</code>      — Mute for 30 min\n"
    "<code>/warn</code>         — Issue warning (3 = auto-ban)\n\n"
    "<b>📌 Content</b>\n"
    "<code>/pin</code>          — Pin replied message\n"
    "<code>/purge 20</code>     — Delete last 20 messages\n\n"
    "<b>⚙️ Access</b>\n"
    "<code>/promote</code>      — Grant admin rights\n"
    "<code>/demote</code>       — Revoke admin rights\n"
    "<code>/admins</code>       — List all admins\n"
    "┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄"
)

GAMES_TEXT = (
    "🎮 <b>Games Available</b> 🍂\n"
    "┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n\n"
    "🎯 <b>Tic-Tac-Toe</b>\n"
    "Challenge someone by <b>replying to their message</b> with:\n"
    "<code>/ttt</code>\n\n"
    "• Both players click the board to make moves\n"
    "• First to get 3 in a row wins ❌⭕\n"
    "• Use /endgame to abandon a running match\n\n"
    "🌱 <i>More games coming soon…</i>\n"
    "┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄"
)

TOOLS_TEXT = (
    "🛠️ <b>Available Tools</b> 🍁\n"
    "┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n\n"
    "🎲 <code>/roll [max]</code>      — Roll a dice\n"
    "🪙 <code>/flip</code>            — Flip a coin\n"
    "🧮 <code>/calc 2+2*3</code>      — Calculator\n"
    "🆔 <code>/id</code>              — Your / target user ID\n"
    "📊 <code>/stats</code>           — Group member count & info\n"
    "🖼️ <code>/imgconvert</code>      — Convert image to PNG/JPEG/WebP/BMP\n"
    "   <i>Send a photo after the command!</i>\n"
    "┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄"
)

FANCY_INFO_TEXT = (
    "✏️ <b>Fancy Text Generator</b> 🥀\n"
    "┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n\n"
    "Generate your text in <b>13 unique Unicode font styles!</b>\n\n"
    "📌 Usage:\n"
    "<code>/fancy Hello World</code>\n\n"
    "✅ Styles include Bold, Italic, Script, Fraktur,\n"
    "   Double-struck, Mono, Bubble, Small Caps,\n"
    "   Upside Down, Wide, Wavy, Strikethrough\n"
    "┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄"
)

XDL_TEXT = (
    "📥 <b>X / Twitter Media Downloader</b> 🍁\n"
    "┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n\n"
    "Download videos, GIFs and images from X (Twitter)!\n\n"
    "📌 Usage:\n"
    "<code>/xdl https://x.com/user/status/123...</code>\n\n"
    "✅ <b>Supported:</b> Videos • GIFs • Images\n"
    "⚠️ Max file size: 50 MB\n\n"
    "💡 <i>You can also just send the X link directly in chat\n"
    "and I'll offer to download it for you!</i>\n"
    "┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄"
)

# ═════════════════════════════════════════════════════════════════════════════
#  WELCOME HANDLER
# ═════════════════════════════════════════════════════════════════════════════

async def greet_new_members(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    result = update.chat_member
    if result is None or result.new_chat_member is None:
        return
    old_s = result.old_chat_member.status
    new_s = result.new_chat_member.status
    if old_s in (ChatMemberStatus.LEFT, ChatMemberStatus.BANNED) \
            and new_s == ChatMemberStatus.MEMBER:
        user = result.new_chat_member.user
        chat = update.effective_chat
        text = (
            f"🍂 <b>Welcome to {esc(chat.title)}!</b> 🍁\n\n"
            f"Hey <b>{esc(user.first_name)}</b>, glad you joined! 👋\n"
            f"Please read the /rules and enjoy your stay. 🥀\n\n"
            f"<i>This card will self-destruct in "
            f"{WELCOME_DELETE_AFTER // 60} minutes.</i>"
        )
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("📜 Read Rules", callback_data="menu_rules"),
            InlineKeyboardButton("👋 Say Hi!", url=f"tg://user?id={user.id}"),
        ]])
        msg_id = await send_video_with_caption(chat.id, text, kb, context)
        if msg_id is None:
            m = await chat.send_message(text, parse_mode=ParseMode.HTML, reply_markup=kb)
            msg_id = m.message_id

        async def _autodelete():
            await asyncio.sleep(WELCOME_DELETE_AFTER)
            try:
                await context.bot.delete_message(chat.id, msg_id)
            except TelegramError:
                pass

        asyncio.create_task(_autodelete())

# ═════════════════════════════════════════════════════════════════════════════
#  CALLBACK QUERY ROUTER
# ═════════════════════════════════════════════════════════════════════════════

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q   = update.callback_query
    await q.answer()
    data = q.data or ""

    # ── Menu navigation ───────────────────────────────────────────────────────
    if data == "menu_start":
        await edit_text_or_caption(q, START_TEXT, start_keyboard())
        return

    if data == "menu_rules":
        await edit_text_or_caption(q, RULES_TEXT, rules_keyboard())
        return

    if data == "menu_admin":
        await edit_text_or_caption(q, ADMIN_HELP_TEXT, back_keyboard())
        return

    if data == "menu_games":
        await edit_text_or_caption(q, GAMES_TEXT, back_keyboard())
        return

    if data == "menu_fancy":
        await edit_text_or_caption(q, FANCY_INFO_TEXT, back_keyboard())
        return

    if data == "menu_tools":
        await edit_text_or_caption(q, TOOLS_TEXT, back_keyboard())
        return

    if data == "menu_xdl":
        await edit_text_or_caption(q, XDL_TEXT, back_keyboard())
        return

    if data == "menu_info":
        user = q.from_user
        chat = q.message.chat
        try:
            member = await context.bot.get_chat_member(chat.id, user.id)
            role = {
                ChatMemberStatus.OWNER:         "👑 Owner",
                ChatMemberStatus.ADMINISTRATOR: "🛡️ Admin",
                ChatMemberStatus.MEMBER:        "👤 Member",
                ChatMemberStatus.RESTRICTED:    "🔇 Restricted",
            }.get(member.status, "👤 Member")
        except Exception:
            role = "👤 Member"
        info_text = (
            f"👤 <b>Your Info</b> 🍂\n"
            f"┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n"
            f"<b>Name:</b>     {esc(user.full_name)}\n"
            f"<b>ID:</b>       <code>{user.id}</code>\n"
            f"<b>Username:</b> @{user.username or 'N/A'}\n"
            f"<b>Role:</b>     {role}"
        )
        await edit_text_or_caption(q, info_text, back_keyboard())
        return

    if data == "rules_agree":
        await q.answer("✅ Thanks for agreeing to the rules!", show_alert=True)
        return

    # ── Image format conversion ───────────────────────────────────────────────
    if data.startswith("imgconv_"):
        # format: "imgconv_{fmt}"  (file_id stored in user_data)
        fmt = data[8:]
        file_id = context.user_data.get("imgconv_file_id")
        if not file_id:
            await q.answer("⚠️ Session expired. Please send the image again.", show_alert=True)
            return
        await q.answer(f"⏳ Converting to {fmt.upper()}…")
        await _do_image_convert(q.message, context, file_id, fmt)
        return

    # ── Tic-Tac-Toe surrender ─────────────────────────────────────────────────
    if data.startswith("tttsur_"):
        game_id = data[7:]
        games = context.bot_data.setdefault("ttt_games", {})
        game   = games.get(game_id)
        if game:
            # Only a player can surrender
            if q.from_user.id not in game["players"].values():
                await q.answer("❌ You're not in this game!", show_alert=True)
                return
            loser_name = esc(q.from_user.first_name)
            board_str  = ttt_board_str(game["board"])
            del games[game_id]
            await q.edit_message_text(
                f"🏳️ <b>{loser_name}</b> surrendered!\n\n{board_str}",
                parse_mode=ParseMode.HTML,
            )
        return

    # ── Tic-Tac-Toe move ──────────────────────────────────────────────────────
    if data.startswith("ttt_"):
        await _ttt_move(update, context, q, data)
        return

    # ── Generic noop ─────────────────────────────────────────────────────────
    # (handles "noop" or any unrecognised callback)

# ═════════════════════════════════════════════════════════════════════════════
#  TIC-TAC-TOE COMMAND & MOVE LOGIC
# ═════════════════════════════════════════════════════════════════════════════

async def cmd_ttt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    user = update.effective_user

    if chat.type == "private":
        await update.message.reply_text(
            "🎮 Tic-Tac-Toe is a group game!\n"
            "Add me to a group and reply to someone's message with /ttt"
        )
        return

    if not update.message.reply_to_message:
        await update.message.reply_text(
            "🎮 <b>How to play:</b> Reply to another member's message with "
            "<code>/ttt</code> to challenge them!",
            parse_mode=ParseMode.HTML,
        )
        return

    opponent = update.message.reply_to_message.from_user
    if opponent.id == user.id:
        await update.message.reply_text("🤔 You can't challenge yourself!")
        return
    if opponent.is_bot:
        await update.message.reply_text("🤖 You can't challenge a bot!")
        return

    game_id = str(chat.id)
    games   = context.bot_data.setdefault("ttt_games", {})

    if game_id in games and games[game_id]["status"] == "active":
        await update.message.reply_text(
            "♟ A game is already running here! Use /endgame to end it first."
        )
        return

    board = [[" "] * 3 for _ in range(3)]
    games[game_id] = {
        "board":   board,
        "players": {"X": user.id, "O": opponent.id},
        "names":   {"X": user.first_name, "O": opponent.first_name},
        "current": "X",
        "status":  "active",
    }

    await update.message.reply_text(
        ttt_render(games[game_id]),
        parse_mode=ParseMode.HTML,
        reply_markup=ttt_keyboard(board, game_id),
    )


async def cmd_endgame(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    game_id = str(update.effective_chat.id)
    games   = context.bot_data.setdefault("ttt_games", {})
    if game_id not in games:
        await update.message.reply_text("❌ No game is running in this chat.")
        return
    del games[game_id]
    await update.message.reply_text("🏳️ Game ended. 🍂")


async def _ttt_move(update, context, q, data: str) -> None:
    # data = "ttt_{game_id}_{r}_{c}"
    # game_id is a signed integer (can be negative for groups), no underscores
    parts = data.split("_")         # ["ttt", maybe-negative-game_id, r, c]
    if len(parts) != 4:
        return
    _, game_id, r_str, c_str = parts
    r, c = int(r_str), int(c_str)
    user  = q.from_user
    games = context.bot_data.setdefault("ttt_games", {})
    game  = games.get(game_id)

    if not game or game["status"] != "active":
        await q.answer("❌ No active game here.", show_alert=True)
        return

    current_sym = game["current"]
    current_uid = game["players"][current_sym]
    other_sym   = "O" if current_sym == "X" else "X"

    if user.id != current_uid:
        if user.id == game["players"][other_sym]:
            await q.answer(
                f"⏳ It's {game['names'][current_sym]}'s turn!", show_alert=True
            )
        else:
            await q.answer("❌ You're not in this game!", show_alert=True)
        return

    board = game["board"]
    if board[r][c] != " ":
        await q.answer("❌ That cell is already taken!", show_alert=True)
        return

    board[r][c] = current_sym
    winner      = ttt_check_winner(board)
    board_txt   = ttt_board_str(board)

    if winner:
        game["status"] = "done"
        if winner == "draw":
            result_text = f"🤝 <b>It's a draw!</b>\n\n{board_txt}"
        else:
            winner_name = esc(game["names"][winner])
            emoji       = "❌" if winner == "X" else "⭕"
            result_text = f"🎉 {emoji} <b>{winner_name} wins!</b>\n\n{board_txt}"
        await q.edit_message_text(result_text, parse_mode=ParseMode.HTML)
        del games[game_id]
    else:
        game["current"] = other_sym
        await q.edit_message_text(
            ttt_render(game),
            parse_mode=ParseMode.HTML,
            reply_markup=ttt_keyboard(board, game_id),
        )

# ═════════════════════════════════════════════════════════════════════════════
#  FANCY TEXT
# ═════════════════════════════════════════════════════════════════════════════

async def cmd_fancy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text(
            "✏️ Usage: <code>/fancy your text here</code>\n"
            "Example: <code>/fancy Hello World</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    text = " ".join(context.args)
    if len(text) > 80:
        await update.message.reply_text("⚠️ Text must be 80 characters or fewer.")
        return

    lines = [f"✏️ <b>Fancy Text Generator</b> 🥀\n<i>Input: {esc(text)}</i>\n"]
    for name, fn in FONT_STYLES.items():
        try:
            styled = fn(text)
            lines.append(f"<b>{name}</b>\n{styled}")
        except Exception:
            pass

    output = "\n\n".join(lines)
    # Telegram message max is 4096 chars; truncate gracefully
    if len(output) > 4000:
        output = output[:4000] + "\n…"
    await update.message.reply_text(output, parse_mode=ParseMode.HTML)

# ═════════════════════════════════════════════════════════════════════════════
#  X / TWITTER DOWNLOADER
# ═════════════════════════════════════════════════════════════════════════════

async def cmd_xdl(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.args:
        url = context.args[0]
        if X_URL_RE.search(url):
            await _download_x(update.message, context, url)
        else:
            await update.message.reply_text(
                "❓ That doesn't look like a valid X/Twitter link.\n"
                "Expected: <code>https://x.com/user/status/...</code>",
                parse_mode=ParseMode.HTML,
            )
    else:
        context.user_data["awaiting_xdl"] = True
        await update.message.reply_text(
            XDL_TEXT + "\n\n📨 <i>Now send me the X / Twitter link!</i>",
            parse_mode=ParseMode.HTML,
        )


async def _download_x(message, context: ContextTypes.DEFAULT_TYPE, url: str) -> None:
    status = await message.reply_text("⏳ Fetching media from X… 🍂")

    with tempfile.TemporaryDirectory() as tmpdir:
        output_tpl = os.path.join(tmpdir, "%(id)s.%(ext)s")
        cmd = [
            "yt-dlp",
            "--no-playlist",
            "--format", "best[filesize<50M]/best",
            "--output", output_tpl,
            "--no-warnings",
            "--quiet",
            url,
        ]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        except FileNotFoundError:
            await status.edit_text(
                "❌ <b>yt-dlp is not installed on this server.</b>\n"
                "Admin: <code>pip install yt-dlp</code>",
                parse_mode=ParseMode.HTML,
            )
            return
        except asyncio.TimeoutError:
            await status.edit_text("❌ Download timed out (> 2 minutes).")
            return

        if proc.returncode != 0:
            err = (stderr or b"").decode(errors="ignore")[:300]
            await status.edit_text(
                f"❌ Download failed.\n<code>{esc(err)}</code>",
                parse_mode=ParseMode.HTML,
            )
            return

        files = list(Path(tmpdir).iterdir())
        if not files:
            await status.edit_text("❌ No file was downloaded.")
            return

        filepath = max(files, key=lambda p: p.stat().st_size)
        ext      = filepath.suffix.lower()
        caption  = "📥 Downloaded from X 🍂"

        try:
            await status.edit_text("📤 Uploading… 🍁")
            with open(filepath, "rb") as fh:
                if ext in (".mp4", ".mkv", ".webm", ".mov", ".avi"):
                    await message.reply_video(video=fh, caption=caption, supports_streaming=True)
                elif ext == ".gif":
                    await message.reply_animation(animation=fh, caption=caption)
                elif ext in (".jpg", ".jpeg", ".png", ".webp"):
                    await message.reply_photo(photo=fh, caption=caption)
                else:
                    await message.reply_document(document=fh, caption=caption)
            await status.delete()
        except TelegramError as e:
            await status.edit_text(f"❌ Upload failed: {esc(str(e))}", parse_mode=ParseMode.HTML)

# ═════════════════════════════════════════════════════════════════════════════
#  IMAGE FORMAT CONVERTER  🖼️
# ═════════════════════════════════════════════════════════════════════════════

_IMG_FORMAT_KB = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("🟢 PNG",  callback_data="imgconv_PNG"),
        InlineKeyboardButton("🔵 JPEG", callback_data="imgconv_JPEG"),
    ],
    [
        InlineKeyboardButton("🟣 WebP", callback_data="imgconv_WEBP"),
        InlineKeyboardButton("🔴 BMP",  callback_data="imgconv_BMP"),
    ],
    [
        InlineKeyboardButton("🟡 TIFF", callback_data="imgconv_TIFF"),
        InlineKeyboardButton("⚫ ICO",  callback_data="imgconv_ICO"),
    ],
])


async def cmd_imgconvert(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.message
    if msg.photo or (msg.document and msg.document.mime_type
                     and msg.document.mime_type.startswith("image")):
        await _prompt_img_format(msg, context)
    else:
        context.user_data["awaiting_imgconv"] = True
        await msg.reply_text(
            "🖼️ <b>Image Converter</b>\n\n"
            "Send me a photo or image file to convert!\n"
            "Supported outputs: <b>PNG • JPEG • WebP • BMP • TIFF • ICO</b>",
            parse_mode=ParseMode.HTML,
        )


async def _prompt_img_format(message, context: ContextTypes.DEFAULT_TYPE) -> None:
    if message.photo:
        file_id = message.photo[-1].file_id
    elif message.document:
        file_id = message.document.file_id
    else:
        return

    # Store file_id in user_data (avoids 64-byte callback_data limit)
    context.user_data["imgconv_file_id"] = file_id
    await message.reply_text(
        "🖼️ <b>Choose the output format:</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=_IMG_FORMAT_KB,
    )


async def _do_image_convert(
    message, context: ContextTypes.DEFAULT_TYPE,
    file_id: str, fmt: str,
) -> None:
    if not PIL_OK:
        await message.reply_text(
            "❌ Pillow is not installed.\n"
            "Admin: <code>pip install Pillow</code>",
            parse_mode=ParseMode.HTML,
        )
        return
    try:
        tg_file = await context.bot.get_file(file_id)
        raw     = io.BytesIO()
        await tg_file.download_to_memory(raw)
        raw.seek(0)

        img = Image.open(raw)
        out = io.BytesIO()

        # Formats that don't support RGBA / P modes
        if fmt in ("JPEG", "BMP", "ICO") and img.mode in ("RGBA", "P", "LA"):
            img = img.convert("RGB")

        # ICO wants small sizes
        if fmt == "ICO":
            img = img.resize((256, 256), Image.LANCZOS)

        img.save(out, format=fmt)
        out.seek(0)

        ext = fmt.lower().replace("jpeg", "jpg")
        await message.reply_document(
            document=out,
            filename=f"converted.{ext}",
            caption=f"✅ Converted to <b>{fmt}</b> 🍂",
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:
        await message.reply_text(
            f"❌ Conversion failed: {esc(str(e))}", parse_mode=ParseMode.HTML
        )

# ═════════════════════════════════════════════════════════════════════════════
#  GENERIC MESSAGE HANDLER  (X link detection + conversation flows)
# ═════════════════════════════════════════════════════════════════════════════

async def generic_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.message
    if not msg:
        return

    # ── X downloader conversation flow
    if context.user_data.get("awaiting_xdl"):
        text  = msg.text or msg.caption or ""
        match = X_URL_RE.search(text)
        if match:
            context.user_data.pop("awaiting_xdl", None)
            await _download_x(msg, context, match.group())
        else:
            await msg.reply_text(
                "❓ That doesn't look like an X/Twitter link.\n"
                "Example: <code>https://x.com/user/status/1234567890</code>",
                parse_mode=ParseMode.HTML,
            )
        return

    # ── Image convert conversation flow
    if context.user_data.get("awaiting_imgconv"):
        if msg.photo or (msg.document and msg.document.mime_type
                         and msg.document.mime_type.startswith("image")):
            context.user_data.pop("awaiting_imgconv", None)
            await _prompt_img_format(msg, context)
            return

    # ── Auto-detect X URLs posted in group
    text = msg.text or ""
    match = X_URL_RE.search(text)
    if match:
        url = match.group()
        await msg.reply_text(
            f"🍁 <b>X link detected!</b>\n"
            f"Use <code>/xdl {url}</code> to download the media. 📥",
            parse_mode=ParseMode.HTML,
        )

# ═════════════════════════════════════════════════════════════════════════════
#  TOOL COMMANDS
# ═════════════════════════════════════════════════════════════════════════════

async def cmd_roll(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    max_val = 6
    if context.args:
        try:
            max_val = max(2, min(int(context.args[0]), 100_000))
        except ValueError:
            pass
    result = random.randint(1, max_val)
    bar    = "█" * int(result / max_val * 10) + "░" * (10 - int(result / max_val * 10))
    await update.message.reply_text(
        f"🎲 <b>Dice Roll</b> (1–{max_val})\n\n"
        f"<code>[{bar}]</code>\n"
        f"Result: <b>{result}</b>",
        parse_mode=ParseMode.HTML,
    )


async def cmd_flip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    side = random.choice(["Heads 🌕", "Tails 🌑"])
    await update.message.reply_text(
        f"🪙 <b>Coin Flip</b>\n\n<b>{side}!</b>",
        parse_mode=ParseMode.HTML,
    )


async def cmd_calc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text(
            "🧮 Usage: <code>/calc 2+2*3</code>\n"
            "Supports: + − × ÷ % ( ) ** and math functions.",
            parse_mode=ParseMode.HTML,
        )
        return
    expr = " ".join(context.args)
    # Strip anything that isn't a safe math expression
    safe = re.sub(r"[^0-9+\-*/().%^ eE]", "", expr).strip()
    safe = safe.replace("^", "**")        # convenience
    if not safe:
        await update.message.reply_text("❌ Invalid expression.")
        return
    try:
        result = eval(safe, {"__builtins__": {}, "math": math}, {})  # noqa: S307
        if isinstance(result, float) and result.is_integer():
            result = int(result)
        await update.message.reply_text(
            f"🧮 <code>{esc(expr)}</code>\n= <b>{result}</b>",
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:
        await update.message.reply_text(
            f"❌ Error: <code>{esc(str(e))}</code>", parse_mode=ParseMode.HTML
        )


async def cmd_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.message
    if msg.reply_to_message:
        u = msg.reply_to_message.from_user
        await msg.reply_text(
            f"🆔 <b>User ID</b>\n"
            f"<b>Name:</b> {esc(u.full_name)}\n"
            f"<b>ID:</b>   <code>{u.id}</code>",
            parse_mode=ParseMode.HTML,
        )
    else:
        await msg.reply_text(
            f"🆔 <b>IDs</b>\n"
            f"<b>Your ID:</b>  <code>{msg.from_user.id}</code>\n"
            f"<b>Chat ID:</b>  <code>{msg.chat_id}</code>",
            parse_mode=ParseMode.HTML,
        )


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    try:
        count = await context.bot.get_chat_member_count(chat.id)
    except TelegramError:
        count = "?"
    await update.message.reply_text(
        f"📊 <b>Group Statistics</b> 🍂\n"
        f"┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n"
        f"<b>Name:</b>    {esc(chat.title or 'N/A')}\n"
        f"<b>ID:</b>      <code>{chat.id}</code>\n"
        f"<b>Members:</b> {count}\n"
        f"<b>Type:</b>    {(chat.type or '').capitalize()}",
        parse_mode=ParseMode.HTML,
    )

# ═════════════════════════════════════════════════════════════════════════════
#  GENERAL COMMANDS
# ═════════════════════════════════════════════════════════════════════════════

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    sent = await send_video_with_caption(
        update.effective_chat.id, START_TEXT, start_keyboard(), context
    )
    if sent is None:
        await update.message.reply_text(
            START_TEXT, parse_mode=ParseMode.HTML, reply_markup=start_keyboard()
        )


async def cmd_rules(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    sent = await send_video_with_caption(
        update.effective_chat.id, RULES_TEXT, rules_keyboard(), context
    )
    if sent is None:
        await update.message.reply_text(
            RULES_TEXT, parse_mode=ParseMode.HTML, reply_markup=rules_keyboard()
        )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(HELP_TEXT, parse_mode=ParseMode.HTML)


async def cmd_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user   = update.effective_user
    chat   = update.effective_chat
    member = await context.bot.get_chat_member(chat.id, user.id)
    role   = {
        ChatMemberStatus.OWNER:         "👑 Owner",
        ChatMemberStatus.ADMINISTRATOR: "🛡️ Admin",
        ChatMemberStatus.MEMBER:        "👤 Member",
        ChatMemberStatus.RESTRICTED:    "🔇 Restricted",
        ChatMemberStatus.LEFT:          "🚪 Left",
        ChatMemberStatus.BANNED:        "🔨 Banned",
    }.get(member.status, member.status)
    await update.message.reply_text(
        f"👤 <b>User Info</b> 🍂\n"
        f"┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n"
        f"<b>Name:</b>     {esc(user.full_name)}\n"
        f"<b>ID:</b>       <code>{user.id}</code>\n"
        f"<b>Username:</b> @{user.username or 'N/A'}\n"
        f"<b>Role:</b>     {role}",
        parse_mode=ParseMode.HTML,
    )

# ═════════════════════════════════════════════════════════════════════════════
#  ADMIN / MODERATION COMMANDS
# ═════════════════════════════════════════════════════════════════════════════

async def cmd_kick(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await admin_guard(update, context): return
    if not await reply_guard(update):          return
    t = update.message.reply_to_message.from_user
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, t.id)
        await context.bot.unban_chat_member(update.effective_chat.id, t.id)
        await update.message.reply_text(
            f"👢 <b>{esc(t.first_name)}</b> was kicked from the group. 🍂",
            parse_mode=ParseMode.HTML,
        )
    except TelegramError as e:
        await update.message.reply_text(f"❌ {e}")


async def cmd_ban(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await admin_guard(update, context): return
    if not await reply_guard(update):          return
    t = update.message.reply_to_message.from_user
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, t.id)
        await update.message.reply_text(
            f"🔨 <b>{esc(t.first_name)}</b> was permanently banned. 🥀",
            parse_mode=ParseMode.HTML,
        )
    except TelegramError as e:
        await update.message.reply_text(f"❌ {e}")


async def cmd_tban(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Temporary ban. /tban 1d | 2h | 30m (reply)"""
    if not await admin_guard(update, context): return
    if not await reply_guard(update):          return

    raw = (context.args[0] if context.args else "1d").lower()
    match = re.fullmatch(r"(\d+)([dhm])", raw)
    if not match:
        await update.message.reply_text(
            "⚠️ Format: <code>/tban 1d</code>  |  <code>2h</code>  |  <code>30m</code>",
            parse_mode=ParseMode.HTML,
        )
        return
    value, unit = int(match.group(1)), match.group(2)
    delta = {"d": timedelta(days=value),
             "h": timedelta(hours=value),
             "m": timedelta(minutes=value)}[unit]
    until = datetime.now() + delta
    t     = update.message.reply_to_message.from_user
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, t.id, until_date=until)
        await update.message.reply_text(
            f"⏳ <b>{esc(t.first_name)}</b> banned for <b>{value}{unit}</b>. 🍁",
            parse_mode=ParseMode.HTML,
        )
    except TelegramError as e:
        await update.message.reply_text(f"❌ {e}")


async def cmd_mute(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await admin_guard(update, context): return
    if not await reply_guard(update):          return
    minutes = 5
    if context.args:
        try:
            minutes = max(1, int(context.args[0]))
        except ValueError:
            pass
    t     = update.message.reply_to_message.from_user
    until = datetime.now() + timedelta(minutes=minutes)
    try:
        await context.bot.restrict_chat_member(
            update.effective_chat.id, t.id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until,
        )
        await update.message.reply_text(
            f"🔇 <b>{esc(t.first_name)}</b> muted for <b>{minutes} min</b>. 🥀",
            parse_mode=ParseMode.HTML,
        )
    except TelegramError as e:
        await update.message.reply_text(f"❌ {e}")


async def cmd_unmute(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await admin_guard(update, context): return
    if not await reply_guard(update):          return
    t = update.message.reply_to_message.from_user
    try:
        await context.bot.restrict_chat_member(
            update.effective_chat.id, t.id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_polls=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
            ),
        )
        await update.message.reply_text(
            f"🔊 <b>{esc(t.first_name)}</b> can speak again! 🍂",
            parse_mode=ParseMode.HTML,
        )
    except TelegramError as e:
        await update.message.reply_text(f"❌ {e}")


async def cmd_warn(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await admin_guard(update, context): return
    if not await reply_guard(update):          return
    t     = update.message.reply_to_message.from_user
    cid   = str(update.effective_chat.id)
    uid   = str(t.id)
    warns = context.bot_data.setdefault("warns", {})
    warns.setdefault(cid, {})
    warns[cid][uid] = warns[cid].get(uid, 0) + 1
    count = warns[cid][uid]
    if count >= 3:
        try:
            await context.bot.ban_chat_member(update.effective_chat.id, t.id)
            warns[cid][uid] = 0
            await update.message.reply_text(
                f"🔨 <b>{esc(t.first_name)}</b> accumulated <b>3 warnings</b> "
                f"and was auto-banned! 🥀",
                parse_mode=ParseMode.HTML,
            )
        except TelegramError as e:
            await update.message.reply_text(f"❌ {e}")
    else:
        progress = "🟥" * count + "⬛" * (3 - count)
        await update.message.reply_text(
            f"⚠️ <b>{esc(t.first_name)}</b> warned — <b>{count}/3</b>\n"
            f"{progress}  ← 3 = auto-ban 🍁",
            parse_mode=ParseMode.HTML,
        )


async def cmd_warns(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await reply_guard(update): return
    t     = update.message.reply_to_message.from_user
    cid   = str(update.effective_chat.id)
    uid   = str(t.id)
    warns = context.bot_data.get("warns", {})
    count = warns.get(cid, {}).get(uid, 0)
    progress = "🟥" * count + "⬛" * (3 - count)
    await update.message.reply_text(
        f"⚠️ <b>{esc(t.first_name)}</b> has <b>{count}/3</b> warnings\n{progress}",
        parse_mode=ParseMode.HTML,
    )


async def cmd_clearwarn(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await admin_guard(update, context): return
    if not await reply_guard(update):          return
    t   = update.message.reply_to_message.from_user
    cid = str(update.effective_chat.id)
    uid = str(t.id)
    context.bot_data.setdefault("warns", {}).setdefault(cid, {})[uid] = 0
    await update.message.reply_text(
        f"✅ Warnings cleared for <b>{esc(t.first_name)}</b>. 🍂",
        parse_mode=ParseMode.HTML,
    )


async def cmd_pin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await admin_guard(update, context):       return
    if not await reply_guard(update, "message"):     return
    try:
        await context.bot.pin_chat_message(
            update.effective_chat.id,
            update.message.reply_to_message.message_id,
        )
        await update.message.reply_text("📌 Message pinned! 🍁")
    except TelegramError as e:
        await update.message.reply_text(f"❌ {e}")


async def cmd_unpin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await admin_guard(update, context): return
    try:
        await context.bot.unpin_chat_message(update.effective_chat.id)
        await update.message.reply_text("📌 Message unpinned. 🍂")
    except TelegramError as e:
        await update.message.reply_text(f"❌ {e}")


async def cmd_purge(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await admin_guard(update, context): return
    n = 10
    if context.args:
        try:
            n = min(100, max(1, int(context.args[0])))
        except ValueError:
            pass
    base    = update.message.message_id
    deleted = 0
    for mid in range(base, base - n - 1, -1):
        try:
            await context.bot.delete_message(update.effective_chat.id, mid)
            deleted += 1
        except TelegramError:
            pass
    notice = await update.effective_chat.send_message(
        f"🗑 Purged <b>{deleted}</b> message(s). 🍂", parse_mode=ParseMode.HTML
    )
    await asyncio.sleep(4)
    try:
        await notice.delete()
    except TelegramError:
        pass


async def cmd_promote(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await admin_guard(update, context): return
    if not await reply_guard(update):          return
    t = update.message.reply_to_message.from_user
    try:
        await context.bot.promote_chat_member(
            update.effective_chat.id, t.id,
            can_manage_chat=True,
            can_delete_messages=True,
            can_restrict_members=True,
            can_pin_messages=True,
            can_change_info=True,
            can_invite_users=True,
        )
        await update.message.reply_text(
            f"⬆️ <b>{esc(t.first_name)}</b> promoted to admin! 👑🍁",
            parse_mode=ParseMode.HTML,
        )
    except TelegramError as e:
        await update.message.reply_text(f"❌ {e}")


async def cmd_demote(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await admin_guard(update, context): return
    if not await reply_guard(update):          return
    t = update.message.reply_to_message.from_user
    try:
        await context.bot.promote_chat_member(
            update.effective_chat.id, t.id,
            can_manage_chat=False,
            can_delete_messages=False,
            can_restrict_members=False,
            can_pin_messages=False,
            can_change_info=False,
            can_invite_users=False,
        )
        await update.message.reply_text(
            f"⬇️ <b>{esc(t.first_name)}</b> was demoted. 🍂",
            parse_mode=ParseMode.HTML,
        )
    except TelegramError as e:
        await update.message.reply_text(f"❌ {e}")


async def cmd_admins(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        admins = await context.bot.get_chat_administrators(update.effective_chat.id)
        lines  = ["👑 <b>Group Admins</b> 🍁\n┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n"]
        for a in admins:
            icon     = "👑" if a.status == ChatMemberStatus.OWNER else "🛡️"
            name     = esc(a.user.full_name)
            uname    = f" (@{a.user.username})" if a.user.username else ""
            lines.append(f"{icon} {name}{uname}")
        await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)
    except TelegramError as e:
        await update.message.reply_text(f"❌ {e}")

# ═════════════════════════════════════════════════════════════════════════════
#  POST-INIT  (registers Telegram's "/" menu)
# ═════════════════════════════════════════════════════════════════════════════

async def post_init(application: Application) -> None:
    await application.bot.set_my_commands([
        BotCommand("start",       "🍂 Introduction & main menu"),
        BotCommand("help",        "📋 Full command list"),
        BotCommand("rules",       "📜 Group rules"),
        BotCommand("info",        "👤 Your account info"),
        BotCommand("fancy",       "✏️ Fancy text generator"),
        BotCommand("xdl",         "📥 Download X / Twitter media"),
        BotCommand("ttt",         "🎮 Tic-Tac-Toe (reply to challenge)"),
        BotCommand("endgame",     "🏳️ End current Tic-Tac-Toe game"),
        BotCommand("imgconvert",  "🖼️ Convert image format"),
        BotCommand("roll",        "🎲 Roll a dice"),
        BotCommand("flip",        "🪙 Flip a coin"),
        BotCommand("calc",        "🧮 Calculator"),
        BotCommand("id",          "🆔 Get user / chat ID"),
        BotCommand("stats",       "📊 Group statistics"),
        BotCommand("kick",        "👢 Kick a user (reply)"),
        BotCommand("ban",         "🔨 Ban a user (reply)"),
        BotCommand("tban",        "⏳ Temp-ban (reply) [1d/2h/30m]"),
        BotCommand("mute",        "🔇 Mute (reply) [minutes]"),
        BotCommand("unmute",      "🔊 Unmute (reply)"),
        BotCommand("warn",        "⚠️ Warn a user (reply)"),
        BotCommand("warns",       "📋 Check warn count (reply)"),
        BotCommand("clearwarn",   "✅ Clear all warns (reply)"),
        BotCommand("pin",         "📌 Pin a message (reply)"),
        BotCommand("unpin",       "📌 Unpin latest message"),
        BotCommand("purge",       "🗑 Delete last N messages"),
        BotCommand("promote",     "⬆️ Promote to admin (reply)"),
        BotCommand("demote",      "⬇️ Demote admin (reply)"),
        BotCommand("admins",      "👑 List all group admins"),
    ])

# ═════════════════════════════════════════════════════════════════════════════
#  MAIN
# ═════════════════════════════════════════════════════════════════════════════

def main() -> None:
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # ── Event handlers
    app.add_handler(ChatMemberHandler(greet_new_members, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(CallbackQueryHandler(button_handler))

    # ── General
    app.add_handler(CommandHandler("start",      cmd_start))
    app.add_handler(CommandHandler("help",       cmd_help))
    app.add_handler(CommandHandler("rules",      cmd_rules))
    app.add_handler(CommandHandler("info",       cmd_info))

    # ── Fancy Text
    app.add_handler(CommandHandler("fancy",      cmd_fancy))

    # ── X Downloader
    app.add_handler(CommandHandler("xdl",        cmd_xdl))

    # ── Games
    app.add_handler(CommandHandler("ttt",        cmd_ttt))
    app.add_handler(CommandHandler("endgame",    cmd_endgame))

    # ── Tools
    app.add_handler(CommandHandler("imgconvert", cmd_imgconvert))
    app.add_handler(CommandHandler("roll",       cmd_roll))
    app.add_handler(CommandHandler("flip",       cmd_flip))
    app.add_handler(CommandHandler("calc",       cmd_calc))
    app.add_handler(CommandHandler("id",         cmd_id))
    app.add_handler(CommandHandler("stats",      cmd_stats))

    # ── Moderation
    app.add_handler(CommandHandler("kick",       cmd_kick))
    app.add_handler(CommandHandler("ban",        cmd_ban))
    app.add_handler(CommandHandler("tban",       cmd_tban))
    app.add_handler(CommandHandler("mute",       cmd_mute))
    app.add_handler(CommandHandler("unmute",     cmd_unmute))
    app.add_handler(CommandHandler("warn",       cmd_warn))
    app.add_handler(CommandHandler("warns",      cmd_warns))
    app.add_handler(CommandHandler("clearwarn",  cmd_clearwarn))
    app.add_handler(CommandHandler("pin",        cmd_pin))
    app.add_handler(CommandHandler("unpin",      cmd_unpin))
    app.add_handler(CommandHandler("purge",      cmd_purge))
    app.add_handler(CommandHandler("promote",    cmd_promote))
    app.add_handler(CommandHandler("demote",     cmd_demote))
    app.add_handler(CommandHandler("admins",     cmd_admins))

    # ── Generic message handler (X-link detection + conversation flows)
    #    Must be registered LAST so commands take priority
    app.add_handler(MessageHandler(
        (filters.TEXT | filters.PHOTO | filters.Document.IMAGE) & ~filters.COMMAND,
        generic_message_handler,
    ))

    if WEBHOOK_URL:
        webhook_path = f"/webhook/{BOT_TOKEN}"
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=webhook_path,
            webhook_url=f"{WEBHOOK_URL}{webhook_path}",
        )
        logger.info("🍁 Webhook mode — port %s", PORT)
    else:
        logger.info("🍂 Polling mode (local dev)")
        app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

