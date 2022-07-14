from collections import deque
from datetime import datetime, timedelta
from typing import Optional
from asyncio import gather
from os import getenv

import nextcord
from nextcord import Guild, Member, Message, Role, utils, Embed
from nextcord.ext import commands
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
load_dotenv()

cluster = AsyncIOMotorClient(getenv("MongoDbSecretKey"))
anti_mute_bypass_db = cluster["Skyhub"]["PreviouslyMuted"]

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

    async def _send_muted_embed(self, message, member, reason):
        try:
            await member.send(
                embed=nextcord.Embed(
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

        if isinstance(message.channel, nextcord.channel.DMChannel):
            return

        if message.channel.permissions_for(message.author).manage_messages:
            return

        if (
                message.author.id in self._muting
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
        ) = self._metrics_on_messages_from_member(member, last_warned)

        too_many_messages = num_messages_last_five_seconds > 5
        too_many_mentions = num_mentions_last_twenty_seconds > 5
        too_many_channels = num_channels_last_fifteen_seconds > 3
        too_many_duplicates = num_duplicate_messages > 1

        if not too_many_messages and not too_many_mentions and not too_many_channels and not too_many_duplicates:
            return

        staff_role = await self._staff_role(message.guild)
        action_description = []
        if should_mute:
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

        else:
            if too_many_messages:
                action_description.append(" spamming messages")
            if too_many_mentions:
                action_description.append(" spamming mentions")
            if too_many_channels:
                action_description.append(" messaging in so many channels")
            if too_many_duplicates:
                action_description.append(" sending duplicate messages")

            if len(action_description) > 1:
                action_description[-1] = f" and{action_description[-1]}"
            if len(action_description) > 2:
                action_description = [",".join(action_description)]

            action_description.insert(0, f"{member.mention} please stop")

        if should_mute:
            self._muting.add(member.id)
            await member.add_roles(await self._mute_role(member.guild))
            self._muting.remove(member.id)

        m: Message = await message.channel.send("".join(action_description))
        if should_mute:
            await gather(
                self._send_muted_embed(message, member, action_description),
                self.client.get_channel(844291279622111253).send(
                    staff_role.mention,
                    embed=Embed(
                        title="User muted!!!",
                        description=f"Please review {member.mention}'s behavior in {message.channel.mention}"
                                f" [To the message]({m.jump_url}).\nUse `!unmute` to remove their mute.",
                        color=0xCC2222
                    )
                )
            )
        self._warned[member.id] = utils.utcnow()

    def _metrics_on_messages_from_member(
            self, member: Member, oldest: Optional[datetime] = None
    ) -> tuple[int, int, int, int]:
        num_messages_checked = 0
        num_recent_messages = 0
        num_recent_mention = 0
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

            if len(message.content) > 15:
                messages_last_minute.add(message.content)
                num_messages_checked += 1

        return (
            num_recent_messages,
            num_recent_mention,
            len(recent_channels),
            num_messages_checked - len(messages_last_minute),
        )

    @commands.Cog.listener("on_member_remove")
    async def anti_mute_bypass(self, member):
        if await self._mute_role(member.guild) in member.roles:
            muted_member = {"member_id": member.id}
            await anti_mute_bypass_db.insert_one(muted_member)

    @commands.Cog.listener("on_member_join")
    async def add_mute_role_as_muted_member_rejoins(self, member):
        insert = {"member_id": member.id}
        if_member_in_anti_mute_bypass_database = await anti_mute_bypass_db.count_documents(insert)
        if if_member_in_anti_mute_bypass_database:
            await anti_mute_bypass_db.remove(insert)
            await member.add_roles(await self._mute_role(member.guild))
            try:
                member.send(
                    embed=Embed(
                        description="Your shenanigans is ineffective, you are still muted, I am 2 steps ahead of you",
                        colour=0xCC2222
                    )
                )
            except:
                return


def setup(client):
    client.add_cog(AutoMod(client))