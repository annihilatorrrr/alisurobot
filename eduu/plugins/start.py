from typing import Union

from pyrogram import Client, filters
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

import eduu
from eduu.config import prefix
from eduu.utils import commands
from eduu.utils.localization import use_chat_lang


bot_repo_link = "https://github.com/iiiiii1wepfj/test-eduu-based-bot"

# Using a low priority group so deeplinks will run before this and stop the propagation.
@Client.on_message(filters.command("start", prefix), group=2)
@Client.on_callback_query(filters.regex("^start_back$"))
@use_chat_lang()
async def start(c: Client, m: Union[Message, CallbackQuery], strings):
    if isinstance(m, CallbackQuery):
        msg = m.message
        method = msg.edit_text
    else:
        msg = m
        method = msg.reply_text

    if msg.chat.type == "private":
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        strings("commands_btn"), callback_data="commands"
                    ),
                    InlineKeyboardButton(strings("infos_btn"), callback_data="infos"),
                ],
                [
                    InlineKeyboardButton(
                        strings("language_btn"), callback_data="chlang"
                    ),
                    InlineKeyboardButton(
                        strings("add_chat_btn"),
                        url=f"https://t.me/{c.me.username}?startgroup=new",
                    ),
                ],
            ]
        )
        await method(
            strings("private").format(myname=c.me.first_name), reply_markup=keyboard
        )
    else:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        strings("start_chat"),
                        url=f"https://t.me/{c.me.username}?start=start",
                    )
                ]
            ]
        )
        await method(
            strings("group").format(myname=c.me.first_name), reply_markup=keyboard
        )


@Client.on_callback_query(filters.regex("^infos$"))
@use_chat_lang()
async def infos(c: Client, m: CallbackQuery, strings):
    res = strings("info_page").format(
        myname=c.me.first_name,
        version=eduu.__version__,
        version_code=c.version_code,
        codelink=bot_repo_link,
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    strings("back_btn", context="general"), callback_data="start_back"
                )
            ]
        ]
    )
    await m.message.edit_text(res, reply_markup=keyboard, disable_web_page_preview=True)


commands.add_command("start", "general")
