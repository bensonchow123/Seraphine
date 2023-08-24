from os import getenv
from aiohttp import ClientSession

from discord import Embed, message, DMChannel, utils, channel, AllowedMentions
from dotenv import load_dotenv
from discord.ext import commands
from Utilities.perspective_api import perspective_api

load_dotenv()


class Seraphine(commands.Cog):
    def __init__(self, client):
        self.client = client

    @property
    def guild(self):
        return self.client.get_guild(int(getenv("GUILD_ID")))

    @property
    def seraphine_channel(self):
        return utils.get(self.guild.text_channels, name="👩seraphine-channel")

    async def chat_filter(self, message: message):
        detect = await perspective_api(message.content)
        if detect:
            detected = []
            for category, prediction in detect.items():
                if prediction[0] is True:
                    detected.append(
                        f"**{category.casefold()}** with {prediction[1]}% confidence"
                    )
            if detected:
                await self.staff_logging_embed(message, detected)
                reasons = Embed(
                    title="Your message was not replied by me because it is detected to be:",
                    description="\n".join(detected),
                    color=0xCC2222,
                )
                await message.reply(embed=reasons)
                if not isinstance(message.channel, channel.DMChannel):
                    await message.delete()
            return False

    async def staff_logging_embed(self, message, detected):
        if isinstance(message.channel, DMChannel):
            channel = "DM channel"
        else:
            channel = message.channel.mention

        staff_logs = utils.get(self.guild.text_channels, name="❗staff-logs")
        await staff_logs.send(
            embed=Embed(
                title=f"Message not replied",
                description=f"From {message.author.mention} in {channel}",
                color=0xCC2222,
            ).add_field(
                name="Message content:",
                value=message.content,
                inline=False
            ).add_field(
                name="For:",
                value="\n".join(detected),
                inline=False
            )
        )

    async def get_seraphine_response(self, message: message):
        async with message.channel.typing():
            try:
                async with ClientSession() as session:
                    async with session.get(
                        f"{getenv('BrainShopKeyAndBid')}&uid={str(message.author.id)}&msg={message.content.casefold()}"
                    ) as r:
                        json_response = await r.json()
                        response = json_response["cnt"]
            except Exception as e:
                response = "I am busy, talk to me later"
            return response

    async def dm_monitor_embed(self, message: message, response):
        dm_monitor_channel = utils.get(self.guild.text_channels, name="🕵dm-monitor")
        await dm_monitor_channel.send(
            embed=Embed(
                title=f"New DM From {message.author.display_name}",
                timestamp=message.created_at,
                colour=0xF5E98C,
            ).add_field(
                name="Dm Content:",
                value=message.content,
                inline=False
            ).add_field(name="Bot Response:", value=response, inline=False)
        )

    @commands.Cog.listener("on_message")
    async def ai_trigger(self, message):
        if message.author.bot:
            return
        member = message.author
        if message.channel.id != self.seraphine_channel.id and not isinstance(message.channel, channel.DMChannel):
            return
        if isinstance(message.channel, channel.DMChannel):
            member = await self.guild.fetch_member(message.author.id)

        if self.client.user in message.mentions:
            return

        if not message.content:
            return

        member_role = utils.get(self.guild.roles, name="Member")
        staff_role = utils.get(self.guild.roles, name="Staff-Team")
        verification_channel = utils.get(self.guild.text_channels, name="👁verification")
        if member_role not in member.roles and staff_role not in member.roles:
            await message.reply(
                f"Stranger danger! I do not know who you are, "
                f"please verify in {verification_channel.mention} before chatting with me",
                allowed_mentions=AllowedMentions().none()
            )
            return

        detection = await self.chat_filter(message)
        if not detection:
            response = await self.get_seraphine_response(message)
            if message:
                await message.reply(response, allowed_mentions=AllowedMentions().none())

            if isinstance(message.channel, channel.DMChannel):
                await self.dm_monitor_embed(message, response)


async def setup(client):
    await client.add_cog(Seraphine(client))
