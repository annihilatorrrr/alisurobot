from pyrogram import Client, filters
from pyrogram.types import Message

from alisu.config import prefix
from alisu.utils import commands
from alisu.utils.consts import http
from alisu.utils.localization import use_chat_lang
from alisu.utils.bot_error_log import logging_errors


@Client.on_message(filters.command("hastebin", prefix) & ~filters.edited)
@use_chat_lang(context="pastes")
@logging_errors
async def hastebin(c: Client, m: Message, strings):
    if m.reply_to_message:
        if m.reply_to_message.document:
            tfile = m.reply_to_message
            to_file = await tfile.download()
            with open(to_file, "rb") as fd:
                mean = fd.read().decode("UTF-8")
        if m.reply_to_message.text:
            mean = m.reply_to_message.text

        url: str = "https://hastebin.com/documents"
        r = await http.post(url, data=mean.encode("UTF-8"))
        url: str = f"https://hastebin.com/{r.json()['key']}"
        await m.reply_text(url, disable_web_page_preview=True)
    else:
        await m.reply_text(strings("reply_to_document_or_text"))


commands.add_command(
    "hastebin", "tools", "hastebin_description", context_location="pastes"
)
