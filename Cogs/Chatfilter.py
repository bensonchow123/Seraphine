import asyncio
import os
from re import search, findall

import nextcord
from nextcord.ext import commands

from Utilities.PerspectiveApi import perspective_api


class ChatFilter(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.author_msg_times = {}
        self.just_muted = []

    async def send_logging_message(self, message, reason):
        logging_embed = nextcord.Embed(
            title=f"Message Deleted",
            description=f"From {message.author.mention} in {message.channel.mention}",
            color=0xCC2222,
        )
        logging_embed.add_field(name="For:", value=reason, inline=False)
        if message.content:
            logging_embed.add_field(
                name="Message content:", value=message.content, inline=False
            )
        if message.attachments:
            logging_embed.add_field(
                name="Attachment:", value=message.attachments, inline=False
            )
        await self.staff_logs.send(embed=logging_embed)

    @commands.Cog.listener("on_message")
    async def chat_filter_trigger(self, message):
        if message.author.bot:
            return

        if isinstance(message.channel, nextcord.channel.DMChannel):
            return

        await asyncio.gather(
            self.newline_filter(message),
            self.attachment_filter(message),
            self.bot_channel_filter(message),
            self.discord_filter(message),
            self.ai_chat_filter(message),
        )

    async def newline_filter(self, message: nextcord.Message):
        count = message.content.count("\n")
        if count < 10:
            return

        if count / len(message.content) < 0.25:
            return

        await asyncio.gather(
            message.channel.send(
                f"{message.author.mention} your message has been deleted for having an excessive number of lines.",
                delete_after=10,
            ),
            self.send_logging_message(message, "Too many lines in message"),
            message.delete(),
        )

    async def attachment_filter(self, message):
        if not message.attachments:
            return

        allowed_extensions = {
            ".gif",
            ".png",
            ".jpeg",
            ".jpg",
            ".bmp",
            ".webp",
            ".mp4",
            ".mov",
            ".txt",
            ".ogg",
        }
        for attachment in message.attachments:
            _, extension = os.path.splitext(attachment.filename.lower())
            if extension not in allowed_extensions:
                await asyncio.gather(
                    message.channel.send(
                        embed=nextcord.Embed(
                            title="Your message is deleted because of security reasons",
                            description=f"Your file, {attachment.filename}'s file type is not whitelisted",
                            color=0xCC2222,
                        ).set_footer(
                            text="Contact Hypicksell for whitelisting your file's file type"
                        )
                    ),
                    self.send_logging_message(
                        message, "File's filetype not whitelisted"
                    ),
                    message.delete(),
                )

    async def discord_filter(self, message: nextcord.Message):
        other_discord_links_allowed = [self.self_promotion_channel.id]
        if message.channel.permissions_for(message.author).manage_messages:
            return

        if message.channel.id in other_discord_links_allowed:
            return

        invites = findall(r"discord.gg/[a-z0-9]{8,}", message.content.casefold())
        if invites:
            our_invites = {
                invite.code.casefold() for invite in await message.guild.invites()
            }
            for invite in invites:
                *_, invite_code = invite.split("/")
                if invite_code not in our_invites:
                    break
            else:
                return
            try:
                await message.reply(
                    embed=nextcord.Embed(
                        description=(
                            f"❌ {message.author.mention} you are not allowed to share Discord invites in this channel."
                        ),
                        color=0xAA0000,
                    ),
                    mention_author=True,
                )
            finally:
                await message.delete()
            await self.send_logging_message(
                message,
                reason=f"{message.author} sent {len(invites)} Discord invite{'s' if len(invites) > 1 else ''} in "
                       f"{message.channel.mention}."
            )

    async def ai_chat_filter(self, message: nextcord.Message):
        if message.channel.category_id == 871157014154317854:
            return

        if not message.content:
            return

        response = await perspective_api(message.content)
        if response:
            detected = []
            for category, prediction in response.items():
                if prediction[0] is True:
                    detected.append(
                        f"**{category.casefold()}** with {prediction[1]}% confidence"
                    )
            if detected:
                await asyncio.gather(
                    message.channel.send(
                        message.author.mention,
                        embed=nextcord.Embed(
                            title="Your message was deleted because it is detected to be:",
                            color=0xCC2222,
                            description="\n".join(detected),
                        ),
                    ),
                    self.send_logging_message(message, "\n".join(detected)),
                    message.delete(),
                )

    async def bot_channel_filter(self, message: nextcord.Message):
        lists = [".", "/", "!", "s!", "r!"]
        if message.channel.id != 850027624361230336:
            return
        if message.content.lower().startswith(tuple(lists)):
            return

        await asyncio.gather(
            message.channel.send(
                "Only commands allowed in this channel", delete_after=3
            ),
            message.delete(),
        )

    @commands.Cog.listener("on_message_edit")
    async def bypass_filter_trigger(self, before, after):
        if isinstance(after.channel, nextcord.channel.DMChannel):
            return

        if after.author.bot:
            return

        if not before.content or not after.content:
            return

        if before.content != after.content:
            await asyncio.gather(
                self.chat_filter_bypass(after), self.advert_bypass(after)
            )

    async def chat_filter_bypass(self, after):
        response = await perspective_api(after.content)
        if response:
            detected = []
            for category, prediction in response.items():
                if prediction[0] is True:
                    detected.append(
                        f"**{category.casefold()}** with {prediction[1]}% confidence"
                    )
            if detected:
                await asyncio.gather(
                    after.channel.send(
                        after.author.mention,
                        embed=nextcord.Embed(
                            title="""Do not try to bypass the chat filter, 
                                           your message was deleted because it is detected to be:""",
                            description="\n".join(detected),
                            color=0xCC2222,
                        ),
                    ),
                    self.send_logging_message(after, "\n".join(detected)),
                    after.delete(),
                )

    async def advert_bypass(self, after):
        if "https://discord.gg/" in after.content.lower():
            if after.channel.id != self.self_promotion_channel.id:
                await asyncio.gather(
                    after.channel.send(
                        f"{after.author.mention} don't try to bypass the filter, advertising is only allowed in {self.self_promotion_channel.mention}",
                        delete_after=10,
                    ),
                    self.send_logging_message(after, "Try to bypass advertisement filter"),
                    after.delete(),
                )



    @commands.Cog.listener()
    async def on_ready(self):
        self.guild = self.client.get_guild(844231449014960160)
        self.staffteam = nextcord.utils.get(self.guild.roles, name="Staff-Team")
        self.memberRole = nextcord.utils.get(self.guild.roles, name="Member")
        self.staff_logs = nextcord.utils.get(self.guild.text_channels, name="❗staff-logs")
        self.self_promotion_channel = nextcord.utils.get(self.guild.text_channels, name="📺self-promotion")


def setup(client):
    client.add_cog(ChatFilter(client))
