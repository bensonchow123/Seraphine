import os
from datetime import datetime, timedelta

from nextcord import utils, TextChannel, MessageType
from dotenv import load_dotenv
from nextcord.ext import commands
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv()
cluster = AsyncIOMotorClient(os.getenv("MongoDbSecretKey"))
ActiveStreakdb = cluster["Skyhub"]["ActivityStreak"]

FIRST_TIME_BONUS = 2
DAILY_MESSAGE_BONUS = 2
WEEKLY_STREAK_BONUS = 4

class ActivityStreak(commands.Cog):
    def __init__(self, client):
        self.client = client

    async def _now(self):
        return datetime.utcnow()

    async def _get_data(self, member, type):
        now = await self._now()
        stats = await ActiveStreakdb.find_one({"member_id": member.id})
        if stats is None:
            newuser = {"member_id": member.id, "last_active_date": now, "current_streak": 0, "best_streak": 0}
            await ActiveStreakdb.insert_one(newuser)
            return None
        return stats[type]

    async def update_database(self, member, field, new_value):
        await ActiveStreakdb.update_one({"member_id": member.id}, {"$set": {field: new_value}})

    async def get_streak(self, member):
        stats = await ActiveStreakdb.find_one({"member_id": member.id})
        if not stats:
            return 0, 0
        return stats["current_streak"], stats["best_streak"]

    @commands.Cog.listener("on_message")
    async def activity_streak_handler(self, message):
        if (
                message.author.bot
                or not isinstance(message.channel, TextChannel)
                or message.type == MessageType.new_member
        ):
            return
        last_active_date = await self._get_data(message.author, "last_active_date")
        current_date = await self._now()

        if (
                last_active_date
                and timedelta(hours=23, minutes=30) >= (current_date - last_active_date)
        ):
            return
        current_streak, best_streak = await self.get_streak(message.author)
        reason = (
            f"{message.author.mention} has continued their {current_streak + 1} day activity streak! "
            f"[See Message]({message.jump_url})"
        )
        skybies = DAILY_MESSAGE_BONUS
        notification = (
            f"Gave {message.author.display_name} their daily {skybies} skybies bonus! Their current activity streak is "
            f"{current_streak + 1} day{'s' * (current_streak > 0)}!"
        )

        if not last_active_date:
            skybies = FIRST_TIME_BONUS
            current_streak = 1
            reason = f"{message.author.mention} has sent their first [message]({message.jump_url})!!!"
            await self.update_database(message.author, "current_streak", current_streak)
            notification = (
                f"Gave {message.author.display_name} {skybies} skybies for sending their first message,\n"
                f"You can purchase roles and skyblock coins with skybies, `!help skybies` to learn more!"
            )

        elif current_date - last_active_date < timedelta(days=2):
            current_streak += 1
            await self.update_database(message.author, "current_streak", current_streak)

            if current_streak % 7 == 0:
                skybies = WEEKLY_STREAK_BONUS
                weeks = current_streak // 7
                reason = (
                    f"{message.author.mention} has messaged every day for {weeks} week{'s' * (weeks > 1)}! "
                    f"[See Message]({message.jump_url})"
                )

                notification = (
                    f"Gave {message.author.display_name} {skybies} skybies for their {weeks} week{'s' * (weeks > 1)} activity streak!!!"
                )
        else:
            current_streak = 1
            reason = f"{message.author.mention.display_name} has begun a new activity streak!!!  [See Message]({message.jump_url})"
            await self.update_database(message.author, "current_streak", current_streak)

        if current_streak > best_streak:
            await self.update_database(message.author, "best_streak", current_streak)
        await self.update_database(message.author, "last_active_date", await self._now())
        await self.skybies._give_skybies(message.author, skybies, reason)
        await message.channel.send(notification, delete_after=10)

    @commands.Cog.listener()
    async def on_ready(self):
        self.guild = self.client.get_guild(844231449014960160)
        self.skybies_logs = utils.get(self.guild.text_channels, name="🌟skybies-logs")
        self.skybies = self.client.get_cog("Skybies")

def setup(client):
    client.add_cog(ActivityStreak(client))