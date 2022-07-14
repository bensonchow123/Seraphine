from nextcord.ext import commands, tasks
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient

from dotenv import load_dotenv
import os

load_dotenv()
cluster = AsyncIOMotorClient(os.getenv("MongoDbSecretKey"))
restart_date_db = cluster["Skyhub"]["ResetDates"]


class ResetDatesHandler(commands.Cog):
    def __init__(self, client):
        self.client = client

    async def _now(self):
        return datetime.now(timezone.utc)

    async def datetime_to_string(self, datetime_object):
        return datetime_object.strftime("%S:%M:%H:%d:%m:%Y:%z")

    @tasks.loop(minutes=1)
    async def reset_weekly(self):
        now = await self._now()
        last_restart_document = await restart_date_db.find_one({"type": "weekly"})
        last_restart_date = datetime.strptime(last_restart_document["last_restart"], "%S:%M:%H:%d:%m:%Y:%z")
        next_reset_date = (last_restart_date + timedelta(days=7))
        if now > next_reset_date:
            next_restart_date_string = await self.datetime_to_string(next_reset_date)
            await restart_date_db.update_one(last_restart_document, {"$set": {"last_restart": next_restart_date_string}})

    @commands.Cog.listener()
    async def on_ready(self):
        self.reset_weekly.start()

def setup(client):
    client.add_cog(ResetDatesHandler(client))