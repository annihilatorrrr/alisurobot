import datetime
import io
import os
import re
import shutil
import tempfile

import yt_dlp
from pyrogram import Client, filters
from pyrogram.errors import BadRequest
from pyromod.helpers import ikb
from pyrogram.types import CallbackQuery, Message

from alisu.config import prefix
from alisu.utils import aiowrap, pretty_size
from alisu.utils.consts import http
from alisu.utils.localization import use_chat_lang
from alisu.utils.bot_error_log import logging_errors


@aiowrap
def extract_info(instance, url, download=True):
    return instance.extract_info(url, download)


async def search_yt(query):
    page = (
        await http.get(
            "https://www.youtube.com/results",
            params=dict(search_query=query, pbj="1"),
            headers={
                "x-youtube-client-name": "1",
                "x-youtube-client-version": "2.20200827",
            },
        )
    ).json()
    list_videos = []
    for video in page[1]["response"]["contents"]["twoColumnSearchResultsRenderer"][
        "primaryContents"
    ]["sectionListRenderer"]["contents"][0]["itemSectionRenderer"]["contents"]:
        if video.get("videoRenderer"):
            dic = {
                "title": video["videoRenderer"]["title"]["runs"][0]["text"],
                "url": "https://www.youtube.com/watch?v="
                + video["videoRenderer"]["videoId"],
            }
            list_videos.append(dic)
    return list_videos


@Client.on_message(filters.command("yt", prefix))
@use_chat_lang()
@logging_errors
async def yt_search_cmd(c: Client, m: Message, strings):
    if len(m.text.split()) > 1:
        vids = [
            '{}: <a href="{}">{}</a>'.format(num + 1, i["url"], i["title"])
            for num, i in enumerate(await search_yt(m.text.split(None, 1)[1]))
        ]
        await m.reply_text(
            "\n".join(vids) if vids else strings("no_results", context="general"),
            disable_web_page_preview=True,
        )
    else:
        await m.reply_text(strings("no_results", context="general"))


@Client.on_message(filters.command("ytdl", prefix))
@use_chat_lang()
@logging_errors
async def ytdlcmd(c: Client, m: Message, strings):
    if not m.from_user:
        return
    user = m.from_user.id

    if m.reply_to_message and m.reply_to_message.text:
        url = m.reply_to_message.text
    elif len(m.command) > 1:
        url = m.text.split(None, 1)[1]
    else:
        await m.reply_text(strings("ytdl_missing_argument"))
        return

    ydl = yt_dlp.YoutubeDL(
        {"outtmpl": "dls/%(title)s-%(id)s.%(ext)s", "format": "mp4", "noplaylist": True}
    )
    rege = re.match(
        r"http(?:s?):\/\/(?:www\.)?youtu(?:be\.com\/watch\?v=|\.be\/)([\w\-\_]*)(&(amp;)?‌​[\w\?‌​=]*)?",
        url,
        re.M,
    )
    temp = 0
    if "t=" in url:
        temp = url.split("t=")[1].split("&")[0]

    if not rege:
        yt = await extract_info(ydl, "ytsearch:" + url, download=False)
        yt = yt["entries"][0]
    else:
        yt = await extract_info(ydl, rege.group(), download=False)

    for f in yt["formats"]:
        if f["format_id"] == "140":
            afsize = f["filesize"] or 0
        if f["ext"] == "mp4" and f["filesize"] is not None:
            vfsize = f["filesize"] or 0
            vformat = f["format_id"]

    keyboard = [
        [
            (
                strings("ytdl_audio_button"),
                f'_aud.{yt["id"]}|{afsize}|{temp}|{vformat}|{m.chat.id}|{user}|{m.id}',
            ),
            (
                strings("ytdl_video_button"),
                f'_vid.{yt["id"]}|{vfsize}|{temp}|{vformat}|{m.chat.id}|{user}|{m.id}',
            ),
        ]
    ]

    if " - " in yt["title"]:
        performer, title = yt["title"].rsplit(" - ", 1)
    else:
        performer = yt.get("creator") or yt.get("uploader")
        title = yt["title"]

    text = f"🎧 <b>{performer}</b> - <i>{title}</i>\n"
    text += f"💾 <code>{pretty_size(afsize)}</code> (audio) / <code>{pretty_size(int(vfsize))}</code> (video)\n"
    text += f"⏳ <code>{datetime.timedelta(seconds=yt.get('duration'))}</code>"

    await m.reply_text(text, reply_markup=ikb(keyboard))


@Client.on_callback_query(filters.regex("^(_(vid|aud))"))
@use_chat_lang()
async def cli_ytdl(
    c: Client,
    cq: CallbackQuery,
    strings,
):
    data, fsize, temp, vformat, cid, userid, mid = cq.data.split("|")
    if not cq.from_user.id == int(userid):
        return await cq.answer(strings("ytdl_button_denied"), cache_time=60)
    if int(fsize) > 200000000:
        return await cq.answer(
            strings("ytdl_file_too_big"),
            show_alert=True,
            cache_time=60,
        )
    vid = re.sub(r"^\_(vid|aud)\.", "", data)
    url = f"https://www.youtube.com/watch?v={vid}"
    await cq.message.edit(strings("ytdl_downloading"))
    with tempfile.TemporaryDirectory() as tempdir:
        path = os.path.join(tempdir, "ytdl")

    ttemp = ""
    if int(temp):
        ttemp = f"⏰ {datetime.timedelta(seconds=int(temp))} | "

    if "vid" in data:
        ydl = yt_dlp.YoutubeDL(
            {
                "outtmpl": f"{path}/%(title)s-%(id)s.%(ext)s",
                "format": vformat,
                "noplaylist": True,
            }
        )
    else:
        ydl = yt_dlp.YoutubeDL(
            {
                "outtmpl": f"{path}/%(title)s-%(id)s.%(ext)s",
                "format": "140",
                "extractaudio": True,
                "noplaylist": True,
            }
        )
    try:
        yt = await extract_info(ydl, url, download=True)
    except BaseException as e:
        await cq.message.edit(strings("ytdl_send_error").format(errmsg=e))
        return
    await cq.message.edit(strings("ytdl_sending"))
    filename = ydl.prepare_filename(yt)
    thumb = io.BytesIO((await http.get(yt["thumbnail"])).content)
    thumb.name: str = "thumbnail.png"
    if "vid" in data:
        try:
            await c.send_video(
                int(cid),
                filename,
                width=1920,
                height=1080,
                caption=ttemp + yt["title"],
                duration=yt["duration"],
                thumb=thumb,
                reply_to_message_id=int(mid),
            )
        except BadRequest as e:
            await c.send_message(
                chat_id=int(cid),
                text=strings("ytdl_send_error").format(errmsg=e),
                reply_to_message_id=int(mid),
            )
    else:
        if " - " in yt["title"]:
            performer, title = yt["title"].rsplit(" - ", 1)
        else:
            performer = yt.get("creator") or yt.get("uploader")
            title = yt["title"]
        try:
            await c.send_audio(
                int(cid),
                filename,
                title=title,
                performer=performer,
                caption=ttemp[:-2],
                duration=yt["duration"],
                thumb=thumb,
                reply_to_message_id=int(mid),
            )
        except BadRequest as e:
            await c.send_message(
                chat_id=int(cid),
                text=strings("ytdl_send_error").format(errmsg=e),
                reply_to_message_id=int(mid),
            )
    await cq.message.delete()

    shutil.rmtree(tempdir, ignore_errors=True)
