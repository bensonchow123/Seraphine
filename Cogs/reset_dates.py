from datetime import datetime, timezone, timedelta
from bson.objectid import ObjectId
from os import getenv

from discord.ext import commands, tasks
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()
cluster = AsyncIOMotorClient(getenv("MongoDbSecretKey"))
restart_date_db = cluster["Skyhub"]["ResetDates"]


class ResetDatesHandler(commands.Cog):
    def __init__(self, client):
        self.client = client

    async def now(self):
        return datetime.now(timezone.utc)

    async def datetime_to_string(self, datetime_object):
        return datetime_object.strftime("%S:%M:%H:%d:%m:%Y:%z")

    @tasks.loop(minutes=1)
    async def update_reset_dates(self):
        now = await self.now()
        last_restart_document = await restart_date_db.find_one({"_id": ObjectId("62b4546da162f9c1a2fbdfe8")})
        last_weekly_restart_date = datetime.strptime(last_restart_document["last_weekly_restart"], "%S:%M:%H:%d:%m:%Y:%z")
        next_weekly_reset_date = (last_weekly_restart_date + timedelta(days=7))
        last_restart_month = last_restart_document["last_restart_month"]

        if now > next_weekly_reset_date:
            next_restart_date_string = await self.datetime_to_string(next_weekly_reset_date)
            await restart_date_db.update_one(
                last_restart_document,
                {"$set": {"last_weekly_restart": next_restart_date_string}}
            )

        if now.month != last_restart_month:
            await restart_date_db.update_one(last_restart_document, {"$set": {"last_restart_month": now.month}})

    async def cog_load(self):
        self.update_reset_dates.start()


async def setup(client):
    await client.add_cog(ResetDatesHandler(client))