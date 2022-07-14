import os
import aiohttp
from datetime import datetime, timezone, timedelta

from nextcord import Message, utils, ui, ButtonStyle, Interaction, Embed
from dotenv import load_dotenv
from nextcord.ext import commands, tasks
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import DESCENDING
load_dotenv()
cluster = AsyncIOMotorClient(os.getenv("MongoDbSecretKey"))
bump_db = cluster["Skyhub"]["BumpRecord"]


class BumpButton(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(emoji="🔔", style=ButtonStyle.blurple, custom_id='BumpButton')
    async def button_pressed(self, button: ui.Button, interaction: Interaction):
        guild = interaction.guild
        bump_role = utils.get(guild.roles, name="Bumpers")
        if bump_role in interaction.user.roles:
            await interaction.user.remove_roles(bump_role)
            await interaction.response.send_message(f"{interaction.user.mention} you will no longer be tagged by bump reminders",ephemeral=True)
        elif bump_role not in interaction.user.roles:
            await interaction.user.add_roles(bump_role)
            await interaction.response.send_message(f"{interaction.user.mention} you will be tagged by bump reminders",ephemeral=True)

class BumpReminder(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.bump_button_added = False
        self.waiting_bump = False

    async def _now(self):
        return datetime.now(timezone.utc)

    async def _last_bump_time(self):
        last_bump = await bump_db.find_one(sort=[('$natural', DESCENDING)])
        last_bump = last_bump["date"]
        return datetime.strptime(last_bump,"%S:%M:%H:%d:%m:%Y:%z")

    async def _get_bumper_id(self,message):
        url = f"https://discord.com/api/v9/channels/{message.channel.id}/messages/{message.id}"
        headers = {"Authorization": f"Bot {self.client.http.token}"}
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url) as response:
                data = await response.json()
                return int(data["interaction"]["user"]["id"])

    async def _log_successful_bump(self, bumper_id):
        now = await self._now()
        bumper = {"bumper_id": bumper_id, "date": now.strftime("%S:%M:%H:%d:%m:%Y:%z")}
        await bump_db.insert_one(bumper)

    async def _handle_disboard_message(self, message):
        if not message.embeds:
            return

        if "bump done!" not in message.embeds[0].description.casefold():
            return
        await self._clean_channel(ignore=message)
        bumper_id = await self._get_bumper_id(message)
        bumper = self.guild.get_member(bumper_id)
        await self._log_successful_bump(bumper_id)
        if not self.waiting_bump or (not bumper_id and message.channel == self.bump_channel):
            await message.delete()
            return
        await self.skybies._give_skybies(bumper, 2, reason=f"{bumper.mention} had bumped the server")
        self.waiting_bump = False

    async def _clean_channel(self, ignore=None):
        def check(message: Message):
            if ignore and message.id == ignore.id:
                return False
            if message.id == 996009949257801759:
                return False
            return True

        await self.bump_channel.purge(check=check)

    async def _send_reminder_message(self):
        if not self.waiting_bump:
            await self._clean_channel()
            await self.logging.send(embed=Embed(description="An reminder message is sent", colour=0x4bb543))
            await self.bump_channel.send(
                f"{self.bumper_role.mention} It's been 2hrs since the last bump!\n*Use the `/bump` command now!*"
            )
            self.waiting_bump = True

    async def _check_bump(self):
        now = await self._now()
        last_bump_time = await self._last_bump_time()
        if now >= (last_bump_time + timedelta(hours=2)):
            return True
        return False

    @tasks.loop(seconds=10)
    async def _bump_reminder(self):
        if not self.waiting_bump:
            bump_now = await self._check_bump()
            if bump_now:
                await self._send_reminder_message()

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        if message.author.id == self.disboard.id:
            await self._handle_disboard_message(message)
            return

        if message.channel != self.bump_channel:
            return

        if message.author.id == self.client.user.id and not self.waiting_bump:
            return

        await message.delete()

    @commands.command()
    @commands.is_owner()
    async def bump_start(self, ctx):
        await self.bump_channel.send(
            embed=Embed(
                description=(
                    f"To help us stay at the top of Disboard join the _Bump Squad_ by hitting the button to be notified when it's time to bump."
                    f" Hit the button again at anytime to turn off the bump reminder notifications."
                ),
                color=0x306998,
            ).set_author(name="Skyhub Bump Squad",
                         icon_url=self.guild.icon.url),
            view=BumpButton()
        )



    @commands.Cog.listener()
    async def on_ready(self):
        self.guild = self.client.get_guild(844231449014960160)
        self.disboard = self.guild.get_member(302050872383242240)
        self.logging = utils.get(self.guild.text_channels, name="❗staff-logs")
        self.bump_channel = utils.get(self.guild.text_channels, name="👊bumping")
        self.bumper_role = utils.get(self.guild.roles, name="Bumpers")
        self.skybies = self.client.get_cog("Skybies")
        if not self.bump_button_added:
            self.client.add_view(BumpButton())
            self.bump_button_added = True
        self._bump_reminder.start()


def setup(client):
    client.add_cog(BumpReminder(client))