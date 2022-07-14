import os
import random
from urllib import parse
import io
import re
import requests

import aiohttp
import asyncpraw
import googletrans
from nextcord import utils, Embed, File, Member, channel, AllowedMentions, Colour
from gtts import gTTS
from dotenv import load_dotenv
from nextcord.ext import commands

load_dotenv()


class FunCommands(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.reddit = asyncpraw.Reddit(
            client_id=os.getenv("RedditClientID"),
            client_secret=os.getenv("RedditClientSecret"),
            username=os.getenv("RedditUsername"),
            password=os.getenv("RedditPassword"),
            user_agent=os.getenv("RedditUserAgent"),
        )

    async def get_url_extention(self, url):
        path = parse.urlparse(url).path
        return os.path.splitext(path)[1].casefold()

    async def meme_submissions(self):
        subreddit = await self.reddit.subreddit("mincraftmemes")
        allowed_file_types = [
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".gifv",
            ".webm",
            ".mp4",
            ".wav",
            ".mp3",
            ".ogg",
        ]
        memes_submissions = []
        async for x in subreddit.hot():
            extension = await self.get_url_extention(x.url)
            if not x.stickied:
                if not x.is_self:
                    if not "/gallery/" in x.url:
                        if extension in allowed_file_types:
                            memes_submissions.append(x)
        return memes_submissions

    @commands.command(aliases=["meme"])
    async def memes(self, ctx):
        if (
            ctx.channel.id != self.bot_channel.id
            and not ctx.author.guild_permissions.administrator
        ):
            await ctx.send(
                "Use this command in the <#850027624361230336> channel", delete_after=10
            )
            return
        meme_submission = await self.meme_submissions()
        submission = random.choice(meme_submission)
        reddit_embed = Embed(title=submission.title, colour=0xDCF901)
        reddit_embed.set_image(url=submission.url)
        await ctx.channel.send(embed=reddit_embed)

    @commands.command(aliases=["pr"])
    async def pretend(self, ctx, member: Member, *, content):
        if ctx.channel.id == self.bump_channel.id:
            return

        if isinstance(ctx.message.channel, channel.DMChannel):
            return

        if member.id == self.client.user.id:
            return

        if self.master_of_disguise not in member.roles:
            await ctx.send(
                f"Hey, you are not a {self.master_of_disguise.mention}\n"
                f"Do `!skybies shop` to learn how to to become one"
            )
            return

        user_avatar_image = member.avatar.with_size(512).with_static_format("png").url
        async with aiohttp.ClientSession() as session:
            async with session.get(user_avatar_image) as resp:
                avatar_bytes = bytes(await resp.read())

        webhook = await ctx.channel.create_webhook(
            name=member.display_name, avatar=avatar_bytes
        )
        await webhook.send(
            content=content,
            allowed_mentions=AllowedMentions(everyone=False),
            wait=True,
        )
        await webhook.delete()

    @commands.command(
        aliases=[
            "isrickroll",
            "irr",
        ]
    )
    async def is_rick_roll(self, ctx, url):

        if (
            ctx.channel.id != self.bot_channel.id
            and not ctx.author.guild_permissions.administrator
        ):
            await ctx.send(
                "Use this command in the <#850027624361230336> channel", delete_after=10
            )
            return
        else:
            try:
                source = str(requests.get(url).content).lower()
            except Exception as e:
                print(e)
                await ctx.send("Not a valid link", reference=ctx.message)
            else:
                phrases = [
                    "rickroll",
                    "rick roll",
                    "rick astley",
                    "Rick Astley",
                    "never gonna give you up",
                ]
                rr = bool(re.findall("|".join(phrases), source, re.MULTILINE))
                await ctx.send(
                    "it is a rickroll" if rr else "It is not a rickroll",
                    reference=ctx.message,
                )

    @is_rick_roll.error
    async def is_rick_roll_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("You need to do !is_rick_roll (url) ", delete_after=10)

    @commands.command(aliases=["tr"])
    async def translate(self, ctx, language, *, message):
        if isinstance(ctx.channel, channel.DMChannel):
            return

        lang_to = language.casefold()
        if (
            lang_to not in googletrans.LANGUAGES
            and lang_to not in googletrans.LANGCODES
        ):
            await ctx.send(
                "Not a valid language to translate to", reference=ctx.message
            )

        translator = googletrans.Translator()
        text_translated = translator.translate(message, dest=lang_to).text
        embed = Embed(
            description=f"**{text_translated}**\n[See all supported language here](https://gist.github.com/bensonchow123/459ec905b8ff24a729cf0039f845ffc9)",
            colour=0x0FDBFF,
        )
        embed.set_author(name=f"Translation to {language.capitalize()}:")
        await ctx.send(embed=embed, reference=ctx.message)

    @translate.error
    async def translate_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                "It is !translate (language) (message to translate) ", delete_after=10
            )

    @commands.command(aliases=["domain", "domaininfo"])
    async def ip(self, ctx, *, domain_name):
        import socket

        if (
            ctx.channel.id != self.bot_channel.id
            and not ctx.author.guild_permissions.administrator
        ):
            await ctx.send(
                "Use this command in the <#850027624361230336> channel", delete_after=10
            )
            return
        try:
            ip = socket.gethostbyname(domain_name)
        except socket.gaierror:
            await ctx.send(f"Could not find the domain {domain_name}")
            return

        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://extreme-ip-lookup.com/json/{ip}") as r:
                geo = await r.json()

        em = Embed(
            title=f"About {domain_name} :", colour=Colour.blue()
        )
        fields = [
            {"name": "IP", "value": geo["query"]},
            {"name": "Type", "value": geo["ipType"]},
            {"name": "Country", "value": geo["country"]},
            {"name": "City", "value": geo["city"]},
            {"name": "Continent", "value": geo["continent"]},
            {"name": "Country", "value": geo["country"]},
            {"name": "Hostname", "value": geo["ipName"]},
            {"name": "ISP", "value": geo["isp"]},
            {"name": "Latitute", "value": geo["lat"]},
            {"name": "Longitude", "value": geo["lon"]},
            {"name": "Org", "value": geo["org"]},
            {"name": "Region", "value": geo["region"]},
        ]
        for field in fields:
            if field["value"]:
                em.add_field(name=field["name"], value=field["value"], inline=True)
        return await ctx.send(embed=em)

    @ip.error
    async def Domain_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("It is !ip (Domain)e.g google.com", delete_after=10)

    @commands.command(aliases=["text_to_speech"])
    async def tts(self, ctx, *, message):
        if (
            ctx.channel.id != self.bot_channel.id
            and not ctx.author.guild_permissions.administrator
        ):
            await ctx.send(
                "Use this command in the <#850027624361230336> channel", delete_after=10
            )
            return

        async def do_tts(message):
            f = io.BytesIO()
            tts = gTTS(text=message.casefold(), lang="en")
            tts.write_to_fp(f)
            f.seek(0)
            return f

        buff = await do_tts(message)
        await ctx.send(file=File(buff, f"{str(message)}.wav"))

    @commands.Cog.listener()
    async def on_ready(self):
        self.guild = self.client.get_guild(844231449014960160)
        self.bot_channel = utils.get(self.guild.text_channels, name="👩seraphine-commands")
        self.bump_channel = utils.get(self.guild.text_channels, name="👊bumping")
        self.master_of_disguise = utils.get(self.guild.roles, name="🥸master of disguise🥸")


def setup(client):
    client.add_cog(FunCommands(client))
