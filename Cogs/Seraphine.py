import os

import aiohttp
import nextcord
from dotenv import load_dotenv
from nextcord.ext import commands
from Utilities.PerspectiveApi import perspective_api

load_dotenv()


class Seraphine(commands.Cog):
    def __init__(self, client):
        self.client = client

    async def ai_monitor(self, message: nextcord.message):
        detect = await perspective_api(message.content)
        if detect:
            detected = []
            for category, prediction in detect.items():
                if prediction[0] is True:
                    detected.append(
                        f"**{category.casefold()}** with {prediction[1]}% confidence"
                    )
            if detected:
                await self.staff_logging_message(message, detected)
                reasons = nextcord.Embed(
                    title="Your message was not replied by me because it is detected to be:",
                    description="\n".join(detected),
                    color=0xCC2222,
                )
                await message.reply(embed=reasons)
                if not isinstance(message.channel, nextcord.channel.DMChannel):
                    await message.delete()
            return False

    async def staff_logging_message(self, message, detected):
        channel = message.channel.mention
        if isinstance(message.channel, nextcord.channel.DMChannel):
            channel = "DM channel"

        await self.staff_logs.send(
            embed=nextcord.Embed(
                title=f"Message not replied",
                description=f"From {message.author.mention} in {channel}",
                color=0xCC2222,
            )
            .add_field(name="Message content:", value=message.content, inline=False)
            .add_field(name="For:", value="\n".join(detected), inline=False)
        )

    async def get_chat_ai_response(self, message: nextcord.message):
        async with message.channel.typing():
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"{os.getenv('BrainShopKeyAndBid')}&uid={str(message.author.id)}&msg={message.content.casefold()}"
                    ) as r:
                        json_response = await r.json()
                        response = json_response["cnt"]
            except Exception as e:
                print(e)
                response = "I am busy, talk to me later"
            return response

    async def dm_monitor_embed(self, message: nextcord.message, response):
        await self.dm_conitor.send(
            embed=nextcord.Embed(
                title=f"New DM From {message.author.display_name}",
                timestamp=message.created_at,
                colour=0xF5E98C,
            )
            .add_field(name="Dm Content:", value=message.content, inline=False)
            .add_field(name="Bot Response:", value=response, inline=False)
        )

    @commands.Cog.listener("on_message")
    async def ai_trigger(self, message):
        if message.channel.id != self.seraphine_channel.id and not isinstance(message.channel, nextcord.channel.DMChannel):
            return

        if message.author.bot:
            return

        if self.client.user in message.mentions:
            return

        if not message.content:
            return

        detection = await self.ai_monitor(message)
        if not detection:
            await self.chat_bot(message)


    async def chat_bot(self, message: nextcord.message):
        if message.channel.id != self.seraphine_channel.id and not isinstance(
            message.channel, nextcord.channel.DMChannel
        ):
            return

        response = await self.get_chat_ai_response(message)
        await message.reply(response, mention_author=False)

        if isinstance(message.channel, nextcord.channel.DMChannel):
            await self.dm_monitor_embed(message, response)

    @commands.Cog.listener()
    async def on_ready(self):
        self.guild = self.client.get_guild(844231449014960160)
        self.seraphine_channel = nextcord.utils.get(self.guild.text_channels, name="👩seraphine-channel")
        self.dm_conitor = nextcord.utils.get(self.guild.text_channels, name="🕵dm-monitor")
        self.staff_logs = nextcord.utils.get(self.guild.text_channels, name="❗staff-logs")


def setup(client):
    client.add_cog(Seraphine(client))
