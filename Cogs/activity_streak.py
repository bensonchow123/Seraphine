from os import getenv
from datetime import datetime, timedelta

from discord import utils, TextChannel
from dotenv import load_dotenv
from discord.ext import commands
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv()
cluster = AsyncIOMotorClient(getenv("MongoDbSecretKey"))
ActiveStreakdb = cluster["Skyhub"]["ActivityStreak"]

FIRST_TIME_BONUS = 2
DAILY_MESSAGE_BONUS = 2
WEEKLY_STREAK_BONUS = 4

class ActivityStreak(commands.Cog):
    def __init__(self, client):
        self.client = client

    async def now(self):
        return datetime.utcnow()

    async def get_data(self, member, type):
        now = await self.now()
        stats = await ActiveStreakdb.find_one({"member_id": member.id})
        if stats is None:
            new_user = {"member_id": member.id, "last_active_date": now, "current_streak": 1, "best_streak": 1}
            await ActiveStreakdb.insert_one(new_user)
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
        ):
            return
        member_role = utils.get(message.guild.roles, name="Member")
        staff_role = utils.get(message.guild.roles, name="Staff-Team")
        if member_role not in message.author.roles and staff_role not in message.author.roles:
            return

        last_active_date = await self.get_data(message.author, "last_active_date")
        current_date = await self.now()

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
            section_selection_channel = utils.get(message.guild.channels, name="🔘section-hiding-selection")
            notification = (
                f"Gave {message.author.display_name} {skybies} skybies for sending their first message.\n"
                f"You can purchase roles and perks with skybies, `!help skybies` to learn more!\n"
                f"Hide sections you don't want to see in {section_selection_channel.mention} !"
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
            reason = f"{message.author.display_name} has begun a new activity streak!!!  [See Message]({message.jump_url})"
            await self.update_database(message.author, "current_streak", current_streak)

        if current_streak > best_streak:
            await self.update_database(message.author, "best_streak", current_streak)

        skybies_cog = self.client.get_cog("Skybies")
        await self.update_database(message.author, "last_active_date", await self.now())
        await skybies_cog.give_skybies(message.author, skybies, reason)
        try:
            await message.reply(notification, delete_after=15, mention_author=False)
        except:
            pass


async def setup(client):
    await client.add_cog(ActivityStreak(client))

