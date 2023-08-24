from collections import deque
from datetime import datetime, timedelta
from typing import Optional
from asyncio import gather
from re import findall, sub

from discord import Guild, Member, Message, Role, utils, Embed, channel
from discord.ext import commands


class AutoMod(commands.Cog):
    def __init__(self, client):
        super().__init__()
        self.client = client
        self._message_buffer = deque(maxlen=1000)
        self._warned = {}
        self._muting = set()

    async def _mute_role(self, guild: Guild) -> Role:
        return utils.get(guild.roles, name="Muted")

    async def _staff_role(self, guild: Guild) -> Role:
        return utils.get(guild.roles, name="Staff-Team")

    async def _member_role(self, guild: Guild) -> Role:
        return utils.get(guild.roles, name="Member")

    async def _verification_role(self, guild: Guild) -> Role:
        return utils.get(guild.roles, name="Verifying")

    async def _staff_chat(self, guild: Guild) -> channel:
        return utils.get(guild.channels, name="🗒staff-chat")

    async def _staff_logs(self, guild: Guild, message: channel) -> channel:
        return utils.get(guild.channels, name="❗staff-logs")

    async def _send_muted_embed(self, message, member, reason):
        try:
            await member.send(
                embed=Embed(
                    description=f"A staff member will evaluate your action and decide a action,\n"
                                f"dm a staff member if no action have been done in an hour",
                    color=0xCC2222).set_author(
                                        name="You have been muted",
                                        icon_url=message.guild.icon.url
                ).add_field(name="For:",
                            value="".join(reason[1:]),
                            inline=False
                            ).set_footer(
                                text=member.display_name,
                                icon_url=member.avatar.url
                )
            )
        except:
            return

    @commands.Cog.listener("on_message")
    async def _auto_mod_trigger(self, message: Message):
        if message.author.bot:
            return

        if isinstance(message.channel, channel.DMChannel):
            return

        if message.channel.permissions_for(message.author).manage_messages:
            return

        if (
                message.author.id in self._muting
                or message.author.timed_out_until
                or await self._mute_role(message.guild) in message.author.roles
        ):
            return
        self._message_buffer.appendleft(message)
        await self._handle_spamming_violations(message, message.author)

    async def _handle_spamming_violations(self, message: Message, member: Member):
        last_warned = self._warned[member.id] if member.id in self._warned else None
        should_mute = last_warned and utils.utcnow() - last_warned <= timedelta(
            minutes=2
        )

        (
            num_messages_last_five_seconds,
            num_mentions_last_twenty_seconds,
            num_channels_last_fifteen_seconds,
            num_duplicate_messages,
            num_everyone_mentions,
            num_everyone_mentions_with_nitro,
            num_scam_links,
        ) = self._metrics_on_messages_from_member(member, last_warned)

        content = self.escape_links(message.clean_content)
        too_many_messages = num_messages_last_five_seconds > 3
        too_many_mentions = num_mentions_last_twenty_seconds > 5
        too_many_channels = num_channels_last_fifteen_seconds > 3
        too_many_duplicates = num_duplicate_messages > 1
        too_many_everyone_mentions = num_everyone_mentions > 0
        too_many_everyone_mentions_with_nitro = num_everyone_mentions_with_nitro > 0
        too_many_scam_links = num_scam_links > 0

        if (
                not too_many_messages
                and not too_many_mentions
                and not too_many_channels
                and not too_many_duplicates
                and not too_many_everyone_mentions
                and not too_many_everyone_mentions_with_nitro
                and not too_many_scam_links
        ):
            return

        should_mute = (
                should_mute or too_many_everyone_mentions_with_nitro or too_many_scam_links
        )

        action_description = []
        if should_mute:
            if await self._verification_role(member.guild) in member.roles:
                action_description.append(
                    f"{member.mention} you're muted for 20 minutes or until a staff member reviews your behaviour:\n"
                )
            else:
                action_description.append(
                    f"{member.mention} you're being muted until the staff team can review your behavior:\n"

                )
            if too_many_messages:
                action_description.append("- Message spamming\n")
            if too_many_mentions:
                action_description.append("- Spamming mentions\n")
            if too_many_channels:
                action_description.append("- Spamming in multiple channels\n")
            if too_many_duplicates:
                action_description.append("- Sending duplicate messages\n")
            if too_many_everyone_mentions or too_many_everyone_mentions_with_nitro:
                action_description.append("- Spamming mentions to everyone\n")
            if too_many_everyone_mentions_with_nitro or too_many_scam_links:
                action_description.append("- Nitro scamming\n")

        else:
            if too_many_messages:
                action_description.append(" spamming messages")
            if too_many_mentions:
                action_description.append(" spamming mentions")
            if too_many_channels:
                action_description.append(" messaging in so many channels")
            if too_many_duplicates:
                action_description.append(" sending duplicate messages")
            if too_many_everyone_mentions or too_many_everyone_mentions_with_nitro:
                action_description.append(" mentioning everyone")
            if too_many_everyone_mentions_with_nitro or too_many_scam_links:
                action_description.append(" nitro scamming")

            if len(action_description) > 1:
                action_description[-1] = f" and{action_description[-1]}"
            if len(action_description) > 2:
                action_description = [",".join(action_description)]

            action_description.insert(0, f"{member.mention} please stop")

        if should_mute:
            if await self._verification_role(member.guild) in member.roles:
                self._muting.add(member.id)
                await member.edit(timed_out_until=utils.utcnow() + timedelta(minutes=20))
                self._muting.remove(member.id)
            else:
                self._muting.add(member.id)
                await member.remove_roles(await self._member_role(member.guild))
                await member.add_roles(await self._mute_role(member.guild))
                self._muting.remove(member.id)

        if (
                num_everyone_mentions > 0
                or num_scam_links > 0
                or num_everyone_mentions_with_nitro > 0
        ):
            staff_logs = await self._staff_logs(message.guild, message.channel)
            scam_links = self.get_all_sanitized_links(content)
            for link in scam_links:
                await staff_logs.send(
                    embed=Embed(
                        description=f"{member.mention} has sent a message detected with a scam link: \n{link}",
                    ).set_author(
                        name="Scam link detected",
                    )
                )
            await message.delete()
            action_description.append("\n**⚠️ Your message has been deleted ⚠️**")

        if too_many_everyone_mentions_with_nitro or too_many_scam_links:
            m: Message = [message async for message in message.channel.history(limit=1)][0]
            await message.channel.send(
                f"{member.mention} you've been muted for possibly sharing scams.",
                delete_after=5,
            )
        else:
            m: Message = await message.channel.send("".join(action_description))

        staff_chat = await self._staff_chat(message.guild)
        staff_role = await self._staff_role(message.guild)
        if should_mute:
            await gather(
                self._send_muted_embed(message, member, action_description),
                staff_chat.send(
                    staff_role.mention,
                    embed=Embed(
                        title="User muted!!!",
                        description=f"Please review {member.mention}'s behavior in {message.channel.mention} "
                                    f"[To the message]({m.jump_url}).\nUse `!unmute` to remove their mute.",
                        color=0xCC2222
                    )
                )
            )
        self._warned[member.id] = utils.utcnow()

    def _metrics_on_messages_from_member(
            self, member: Member, oldest: Optional[datetime] = None
    ) -> tuple[int, ...]:
        num_messages_checked = 0
        num_recent_messages = 0
        num_recent_mention = 0
        num_everyone_mentions = 0
        num_everyone_mentions_with_nitro = 0
        num_scam_links = 0
        recent_channels = set()
        messages_last_minute = set()


        now = utils.utcnow()
        since = min(oldest or now, now - timedelta(minutes=1))
        for message in (
                message for message in self._message_buffer if message.author == member
        ):
            if since > message.created_at:
                break

            if now - timedelta(seconds=5) <= message.created_at:
                num_recent_messages += 1

            if now - timedelta(seconds=20) <= message.created_at:
                if len(message.mentions):
                    num_recent_mention += 1

            if now - timedelta(seconds=15) <= message.created_at:
                recent_channels.add(message.channel.id)
                content = message.content
                links = self.get_scam_links(content)
                if links:
                    num_scam_links += len(links)

                if "@everyone" in content or "@here" in content:
                    num_everyone_mentions += 1

                    if "nitro" in content or "gift" in content:
                        num_everyone_mentions_with_nitro += 1

            if len(message.content) > 15:
                messages_last_minute.add(message.content)
                num_messages_checked += 1

        return (
            num_recent_messages,
            num_recent_mention,
            len(recent_channels),
            num_messages_checked - len(messages_last_minute),
            num_everyone_mentions,
            num_everyone_mentions_with_nitro,
            num_scam_links,
        )

    def get_scam_links(self, content: str) -> set[str]:
        return {
            link
            for link in findall(
                r"http[s]?://(?:d.+?\.gift|t\.me)/[^\s]+", content.casefold()
            )
            if not link.startswith("https://discord.gift/")
        }

    def get_all_sanitized_links(self, content: str) -> set[str]:
        return {
            " ".join(parts)
            for parts in findall(
                r"(http[s]?://)(.+?\..+?)(/[^\s]*|$)", content.casefold()
            )
        }

    def escape_links(self, content: str) -> str:
        return sub(r"(http[s]?://)(.+?)(\s|/|$)", r"\1 \2 \3", content)


async def setup(client):
    await client.add_cog(AutoMod(client))
