from os import getenv
from io import BytesIO
from base64 import decodebytes
from re import findall, MULTILINE
from requests import get
from Utilities.perspective_api import perspective_api
from datetime import datetime
from discord import (
    utils,
    Embed,
    File,
    Member,
    channel,
    AllowedMentions,
    ui,
    PartialEmoji,
    Interaction,
    ButtonStyle,
    FFmpegPCMAudio
)

from discord.ext import commands
from aiohttp import ClientSession
from googletrans import Translator, LANGUAGES, LANGCODES
from gtts import gTTS
from dotenv import load_dotenv
from humanfriendly import format_timespan
from pymongo import DESCENDING
from motor.motor_asyncio import AsyncIOMotorClient
cluster = AsyncIOMotorClient(getenv("MongoDbSecretKey"))
ohio_vc_leaderboard_db = cluster["Skyhub"]["OhioVcLeaderboard"]
load_dotenv()


class ImageSwitcher(ui.View):
    def __init__(self, images, original_message_author):
        super().__init__(timeout=120)
        self.images = images
        self.original_message_author = original_message_author
        self.current = 0

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

        await self.original_message.edit(view=self)
        await self.original_message.edit(
            embed=Embed(
                description="This image switcher is timed out",
                colour=0xff0033
            )
        )

    async def interaction_check(self, interaction):
        if self.original_message_author != interaction.user:
            await interaction.response.send_message(
                "You didn't paid Seraphine for this images",
                ephemeral=True
            )
            return
        return True

    @ui.button(emoji=PartialEmoji.from_str("<:backward:1004400601146343535>"), style=ButtonStyle.blurple)
    async def backward(self, interaction: Interaction, button: ui.Button):
        self.current -= 1
        if self.current < 0:
            self.current = len(self.images) - 1
        await interaction.response.edit_message(
            attachments=[
                File(BytesIO(decodebytes(self.images[self.current].encode("utf-8"))), f"image{self.current}.png")
            ]
        )

    @ui.button(emoji=PartialEmoji.from_str("<:forward:1004400629327872020>"), style=ButtonStyle.blurple)
    async def forward(self, interaction: Interaction, button: ui.Button):
        self.current += 1
        if self.current > len(self.images) - 1:
            self.current = 0
        await interaction.response.edit_message(
            attachments=[
                File(BytesIO(decodebytes(self.images[self.current].encode("utf-8"))), f"image{self.current}.png")
            ]
        )


class FunCommands(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.lol_counts = {}
        self.voice_channel_times = {}

    @property
    def guild(self):
        return self.client.get_guild(int(getenv("GUILD_ID")))

    @property
    def seraphine_commands(self):
        return utils.get(self.guild.text_channels, name="👩seraphine-commands")

    async def prompt_filter(self, message):
        detect = await perspective_api(message.content)
        if detect:
            detected = []
            for category, prediction in detect.items():
                if prediction[0] is True:
                    detected.append(
                        f"**{category.casefold()}** with {prediction[1]}% confidence"
                    )
            if detected:
                return detected
        return False

    @commands.command(aliases=["pr"])
    async def pretend(self, ctx, member: Member, *, content: str):
        if isinstance(ctx.channel, channel.DMChannel):
            return

        if member.id == self.client.user.id:
            await ctx.send("Master, you can't pretend to be a bot")
            return

        master_of_disguise = utils.get(ctx.guild.roles, name="🥸master of disguise🥸")
        if master_of_disguise not in ctx.author.roles and not ctx.author.guild_permissions.administrator:
            await ctx.send(
                f"Hey, you are not a {master_of_disguise.mention}\n"
                f"Do `!skybies shop` to learn how to to become one",
                allowed_mentions=AllowedMentions.none(),
            )
            return

        detected = await self.prompt_filter(ctx.message)
        if not detected:
            user_avatar_image = member.avatar.with_size(512).with_static_format("png").url
            async with ClientSession() as session:
                async with session.get(user_avatar_image) as resp:
                    avatar_bytes = bytes(await resp.read())

            webhook = await ctx.channel.create_webhook(
                name=member.display_name, avatar=avatar_bytes
            )
            await ctx.message.delete()
            await webhook.send(
                content=content,
                allowed_mentions=AllowedMentions(everyone=False),
                wait=True,
            )
            await webhook.delete()

    @pretend.error
    async def pretend_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Its !pr (member_id or @member 0r member#1234) (message)", delete_after=10)
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send("You can't pretend to be a member that don't exist", delete_after=10)

    @commands.command(
        aliases=[
            "isrickroll",
            "irr",
        ]
    )
    async def is_rick_roll(self, ctx, url :str):

        if (
            ctx.channel.id != self.seraphine_commands.id
            and not ctx.author.guild_permissions.administrator
        ):
            await ctx.send(
                f"Use this command in the {self.seraphine_commands} channel", delete_after=10
            )
            return
        else:
            try:
                source = str(get(url).content).lower()
            except Exception as e:
                await ctx.send("Not a valid link", reference=ctx.message)
            else:
                phrases = [
                    "rick"
                    "roll",
                    "rickroll",
                    "rick roll",
                    "rick astley",
                    "Rick Astley",
                    "never gonna give you up",
                ]
                rr = bool(findall("|".join(phrases), source, MULTILINE))
                await ctx.send(
                    "it is a rickroll" if rr else "It is not a rickroll",
                    reference=ctx.message,
                )

    @is_rick_roll.error
    async def is_rick_roll_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("You need to do !is_rick_roll (url) ", delete_after=10)

    @commands.command(aliases=["tr"])
    async def translate(self, ctx, language: str, *, message: str):
        if isinstance(ctx.channel, channel.DMChannel):
            return

        detected = await self.prompt_filter(ctx.message)
        if not detected:
            lang_to = language.casefold()
            if (
                lang_to not in LANGUAGES
                and lang_to not in LANGCODES
            ):
                await ctx.send(
                    "Not a valid language to translate to", reference=ctx.message
                )

            translator = Translator()
            text_translated = translator.translate(message, dest=lang_to).text
            embed = Embed(
                description=f"**{text_translated}**\n"
                            f"[See all supported language here]"
                            f"(https://gist.github.com/bensonchow123/459ec905b8ff24a729cf0039f845ffc9)",
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

    @commands.command(aliases=["text_to_speech"])
    async def tts(self, ctx, *, message):
        if (
            ctx.channel.id != self.seraphine_commands.id
            and not ctx.author.guild_permissions.administrator
        ):
            await ctx.send(
                f"Use this command in the {self.seraphine_commands} channel", delete_after=10
            )
            return
        detected = await self.prompt_filter(ctx.message)
        if not detected:
            async def do_tts(msg):
                f = BytesIO()
                tts = gTTS(text=msg.casefold(), lang="en")
                tts.write_to_fp(f)
                f.seek(0)
                return f

            message_wav = await do_tts(message)
            await ctx.send(file=File(message_wav, f"{str(message)}.wav"))

    async def generate_image(self, tokens: str):
        url = "https://backend.craiyon.com" + "/generate"
        async with ClientSession() as sess:
            async with sess.post(url, json={"prompt": tokens}) as resp:
                resp = await resp.json()
                return resp['images']

    @commands.cooldown(1, 60, commands.BucketType.user)
    @commands.command(aliases=["draw"])
    async def paint(self, ctx, *, prompt: str):
        if (
            ctx.channel.id != self.seraphine_commands.id
            and not ctx.author.guild_permissions.administrator
        ):
            await ctx.send(
                f"Use this command in the {self.seraphine_commands.mention} channel", delete_after=10
            )
            return
        detected = await self.prompt_filter(ctx.message)
        if not detected:
            skybies_cog = self.client.get_cog("Skybies")
            skybies_count, _ = await skybies_cog.get_skybies(ctx.author)

            if skybies_count < 1:
                return await ctx.send(
                    "You don't have enough skybies to buy paintings from me!\n"
                    f"You have {skybies_count} skybies and you need 4 to buy a painting"
                )
            loading_emoji = utils.get(self.client.emojis, name="loading")
            loading_message = await ctx.reply(
                embed=Embed(
                    title=f"Painting {prompt}",
                    description=f"I usually take up to 2 minutes {loading_emoji}",
                    colour=0xffffff
                )
            )
            try:
                images = await self.generate_image(prompt)
            except:
                return await ctx.send("I ran out of paint, try again later")

            image_switcher = ImageSwitcher(images, ctx.author)
            image_switcher.original_message = loading_message
            await loading_message.edit(
                content=f"You have now have {skybies_count - 2} skybies left",
                embed=None,
                attachments=[File(BytesIO(decodebytes(images[0].encode("utf-8"))), "image0.png")],
                view=image_switcher
            )
            await skybies_cog.take_skybies(ctx.author, 2, reason="Paid Seraphine to paint a picture")

    @paint.error
    async def paint_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.reply(
                content=f"Please wait {int(error.retry_after)} seconds before using this command again,"
                f" as there is a cooldown of 1 minutes",
                delete_after=10
            )

        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                "It is !paint (prompt) ", delete_after=10
            )

    async def play_source(self, voice_client):
        source = FFmpegPCMAudio('./Utilities/ohio.mp3')
        voice_client.play(
            source,
            after=lambda e: print(f"Ohio playing error: {e}") if e else self.client.loop.create_task(
                self.play_source(
                    voice_client
                )
            )
        )

    async def save_vc_time(self, member, seconds):
        await ohio_vc_leaderboard_db.update_one(
            {"member_id": member.id},
            {"$set": {"seconds": seconds}},
            upsert=True
        )

    async def find_member_top_time(self, member):
        member_top_time = await ohio_vc_leaderboard_db.find_one({"member_id": member.id})
        try:
            return member_top_time["seconds"]
        except (TypeError, KeyError) as e:
            return None

    @commands.Cog.listener("on_voice_state_update")
    async def ohio_vc_trigger(self, member, before, after):
        if member.id == self.client.user.id:
            return

        ohio_vc = utils.get(self.guild.channels, name='💀 Ohio VC 💀')
        ohio_vc_gang_channel = utils.get(self.guild.channels, name='😈ohio-vc-gang')

        if before.channel is None and after.channel is not None and after.channel == ohio_vc:
            guild = member.guild
            voice_client = guild.voice_client
            if voice_client is None:
                voice_client = await ohio_vc.connect()
                self.client.loop.create_task(self.play_source(voice_client))
            self.voice_channel_times[member.id] = datetime.utcnow()

        elif before.channel is not None and after.channel is None and before.channel == ohio_vc:
            if len(before.channel.members) - 1 == 0:
                await member.guild.voice_client.disconnect()

            if member.id in self.voice_channel_times:
                time_spent = datetime.utcnow() - self.voice_channel_times[member.id]
                on_vc_leave_embed = Embed(
                        description=f"🎉 {member.mention} joined and left the ohio vc after "
                                    f"{format_timespan(time_spent.total_seconds())} 🎉",
                        colour=0x0FDBFF,
                    ).set_footer(text="If you deafen yourself in ohio vc, you will be disconnected from it.")

                previous_top_time = await self.find_member_top_time(member)
                if not previous_top_time or time_spent.total_seconds() > previous_top_time:
                    await self.save_vc_time(member, time_spent.total_seconds())
                    on_vc_leave_embed.description += "\n**🏆It is their new top time!🏆**"

                await ohio_vc_gang_channel.send(embed=on_vc_leave_embed)
                del self.voice_channel_times[member.id]

        if (before.channel == ohio_vc or after.channel == ohio_vc) and (before.self_deaf or after.self_deaf):
            await member.move_to(None)

    @commands.command(aliases=["ol"])
    async def ohio_leaderboard(self, ctx):
        emoji_list = ["🥇", "🥈", "🥉"] + (["💀"] * 7)
        cursor = ohio_vc_leaderboard_db.find().sort("seconds", DESCENDING).limit(10)
        leaderboard = await cursor.to_list(length=10)
        ohio_leaderboard_list = []
        for index, document in enumerate(leaderboard):
            member = self.guild.get_member(document["member_id"])
            ohio_leaderboard_list.append(
                f"{emoji_list[index]} {member.mention if member else 'unknown'} with **{format_timespan(document['seconds'])}**"
            )
        leaderboard_string = "\n".join(ohio_leaderboard_list)
        leaderboard_embed = Embed(
            title="😈 Ohio VC Leaderboard 😈",
            description=f"__**The people bellow are clinically insane:**__\n{leaderboard_string}",
            colour=0x0FDBFF,
        )
        await ctx.send(embed=leaderboard_embed)

    async def get_count(self, channel) -> int:
        return self.lol_counts.get(channel.id, 0)

    async def set_count(self, channel, count: int):
        self.lol_counts[channel.id] = count

    @commands.Cog.listener("on_message")
    async def lol_streak_listerner(self, message):
        if message.author.bot:
            return

        lol_count = await self.get_count(message.channel)
        if message.content.casefold().strip() == "lol":
            await self.set_count(message.channel, lol_count + 1)
            return

        if lol_count > 0:
            await self.set_count(message.channel, 0)

        if lol_count > 1:
            await message.channel.send(
                f"{message.author.mention} has broken the {lol_count} LOL streak 😟",
                allowed_mentions=AllowedMentions(users=False),
            )


async def setup(client):
    await client.add_cog(FunCommands(client))
