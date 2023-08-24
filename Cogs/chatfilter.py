import asyncio
from os import path
from re import findall

from discord import utils, Embed, channel, Message
from discord.ext import commands

from Utilities.perspective_api import perspective_api


class ChatFilter(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.author_msg_times = {}
        self.just_muted = []

    async def send_logging_message(self, message: Message, reason: str):
        staff_logs = utils.get(message.guild.text_channels, name="❗staff-logs")
        logging_embed = Embed(
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
        await staff_logs.send(embed=logging_embed)

    async def newline_filter(self, message: Message):
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

    async def attachment_filter(self, message: Message):
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
            ".json"
        }
        for attachment in message.attachments:
            _, extension = path.splitext(attachment.filename.lower())
            if extension not in allowed_extensions:
                await asyncio.gather(
                    message.channel.send(
                        embed=Embed(
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

    async def discord_invites_filter(self, message: Message):
        other_discord_links_allowed = [1004284081556693093]
        if message.channel.permissions_for(message.author).manage_messages:
            return

        if message.channel.id in other_discord_links_allowed:
            return

        invites = findall(r"discord.gg/[a-z\d]+", message.content.casefold())
        if not invites:
            return

        our_invites = {
            invite.code.casefold() for invite in await message.guild.invites()
        }
        for invite in invites:
            *_, invite_code = invite.split("/")
            if invite_code not in our_invites:
                break
            else:
                await message.reply(
                    "Thanks for sharing skyhub's invite link!",
                    mention_author=False,
                    delete_after=5
                )
                return
        try:
            await message.reply(
                embeds=[
                    Embed(
                        description=(
                            f"❌ {message.author.mention} you are not allowed to share other discord invites in this "
                            f"channel."
                        ),
                        color=0xAA0000,
                    )
                ],
                mention_author=True,
            )
        finally:
            await message.delete()

        formatted_links = "\n- ".join(invites)
        await self.send_logging_message(
            message,
            reason=f"{message.author.mention} sent {len(invites)} discord invite{'s' if len(invites) > 1 else ''} in "
                   f"{message.channel.mention}.\n"
                   f"**Invite links detected:**\n"
                   f"- {formatted_links}",
        )

    async def ai_chat_filter(self, message: Message):
        if message.channel.id == 1004284081556693096:
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
                        embed=Embed(
                            title="Your message was deleted because it is detected to be:",
                            color=0xCC2222,
                            description="\n".join(detected),
                        ),
                    ),
                    self.send_logging_message(message, "\n".join(detected)),
                    message.delete(),
                )

    @commands.Cog.listener("on_message")
    async def chat_filter_trigger(self, message: Message):
        if message.author.bot:
            return

        if isinstance(message.channel, channel.DMChannel):
            return

        await asyncio.gather(
            self.newline_filter(message),
            self.attachment_filter(message),
            self.discord_invites_filter(message),
            self.ai_chat_filter(message),
        )

    @commands.Cog.listener("on_message_edit")
    async def bypass_filter_trigger(self, before, after: Message):
        if isinstance(after.channel, channel.DMChannel):
            return

        if after.author.bot:
            return

        if not before.content or not after.content:
            return

        if before.content != after.content:
            await asyncio.gather(
                self.ai_chat_filter(after),
                self.discord_invites_filter(after),
                self.newline_filter(after),
            )


async def setup(client):
    await client.add_cog(ChatFilter(client))

