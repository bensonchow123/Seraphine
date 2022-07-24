import os
import aiohttp
from datetime import datetime, timezone, timedelta

from nextcord import Message, utils, ui, ButtonStyle, Interaction, Embed
from nextcord.ext import commands, tasks
from dotenv import load_dotenv
from bson.objectid import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import DESCENDING
load_dotenv()
cluster = AsyncIOMotorClient(os.getenv("MongoDbSecretKey"))
bump_db = cluster["Skyhub"]["BumpRecord"]
restart_date_db = cluster["Skyhub"]["ResetDates"]


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
        await self._bump_king_updater()
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

    @tasks.loop(seconds=5)
    async def _bump_reminder(self):
        if not self.waiting_bump:
            bump_now = await self._check_bump()
            if bump_now:
                await self._send_reminder_message()

    async def _remove_all_bump_king(self):
        for user in self.guild.members:
            await user.remove_roles(self.bump_king_role)

    async def _find_previous_bump_king(self):
        for member in self.guild.members:
            if self.bump_king_role in member.roles:
                return member

    async def _remove_all_crowining_message(self):
        bump_channel_messages = await self.bump_channel.history(limit=500).flatten()
        for message in bump_channel_messages:
            if message.author.id == self.client.user.id and message.embeds:
                if "👑 All Hail The Bump King 👊" in message.embeds[0].title.casefold():
                    await message.delete()

    async def _crown_bump_king(self, member):
        await self._remove_all_crowining_message()
        crowing_embed = Embed(
            color=0xFFCC00,
            title="👑 All Hail The Bump King 👊",
            description=(
                f"All hail {member.mention}, our new 🍕 *Bump King* 🍕!!!\n\n*Any who is valiant enough may "
                f"someday become our Bump King! All one must do is bump the server more than any other!*"
            ),
        )
        await self.general.send(embed=crowing_embed)
        await member.add_roles(self.bump_king_role)

    async def _get_bump_king(self):
        bump_ranking_list = await self._bump_sort()
        if bump_ranking_list:
            return self.guild.get_member(bump_ranking_list[0][0])

    async def _bump_king_updater(self):
        bump_king = await self._get_bump_king()
        if not bump_king:
            return

        previous_bump_king = await self._find_previous_bump_king()
        if not previous_bump_king:
            await self._crown_bump_king(bump_king)

        if previous_bump_king and bump_king.id != previous_bump_king.id:
            await self._remove_all_bump_king()
            await self._crown_bump_king(bump_king)

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

    async def _find_weekly_restart_date(self):
        last_restart = await restart_date_db.find_one({"_id": ObjectId("62b4546da162f9c1a2fbdfe8")})
        last_restart = last_restart["last_weekly_restart"]
        last_restart_date = datetime.strptime(last_restart, "%S:%M:%H:%d:%m:%Y:%z")
        return last_restart_date

    async def _last_bump_id(self):
        last_bump = await bump_db.find_one(sort=[('$natural', DESCENDING)])
        last_bump_id = last_bump["_id"]
        return last_bump_id

    async def _bump_sort(self):
        last_restart = await self._find_weekly_restart_date()
        last_bump_id = await self._last_bump_id()
        filtered = {}
        cursor = bump_db.find({})
        async for insert in cursor:
            date_string = insert["date"]
            date = datetime.strptime(date_string, "%S:%M:%H:%d:%m:%Y:%z")
            bumper_id = insert["bumper_id"]
            insert_id = insert["_id"]
            if date >= last_restart:
                if bumper_id not in filtered:
                    filtered[bumper_id] = 1
                else:
                    filtered[bumper_id] += 1
            if date < last_restart and insert_id != last_bump_id:
                await bump_db.delete_one(insert)

        sorted_bump = sorted(filtered.items(), key=lambda x: x[1], reverse=True)
        return sorted_bump

    async def _bump_leaderboard_embed(self, ctx):
        bump_ranking_list = await self._bump_sort()
        emojis = ["🥇", "🥈", "🥉"]
        if len(bump_ranking_list) > 3:
            star = ["✨"] * (min(len(bump_ranking_list), 10) - 3)
            emojis += star
        runner_up_list = []
        for ranking in range(1, len(bump_ranking_list)):
            bump_leaderboard_member = ctx.guild.get_member(bump_ranking_list[ranking][0])
            bump_count = bump_ranking_list[ranking][1]
            runner_up_list.append(
                f"{emojis[ranking]}{bump_leaderboard_member.mention if bump_leaderboard_member else '*Unknown*'} with **{bump_count}** bumps")
        bump_leaderboard_embed = Embed(
            title="Skyhub Bump Leaderboard",
            description="People that wasted their sweat and tears to bump the server, resets every week",
            colour=0x94fffd
        ).add_field(
            name=":crown: Bump King :crown:",
            value=f"{emojis[0]}{self.guild.get_member(bump_ranking_list[0][0]).mention} is our Bump King with {bump_ranking_list[0][1]} bumps!"
        ).add_field(
            name="RunnerUps",
            value="\n".join(runner_up_list),
            inline=False
        ).set_thumbnail(
            url=self.guild.icon.url
        )

        return bump_leaderboard_embed

    @commands.command(aliases=["bl"])
    async def bump_leaderboard(self, ctx):
        if (
                ctx.channel.id != self.seraphine_commands.id
                and not ctx.author.guild_permissions.administrator
        ):
            await ctx.send(f"Use this command in the {self.seraphine_commands.mention} channel", delete_after=10)
            return
        bump_leaderboard_embed = await self._bump_leaderboard_embed(ctx)
        await ctx.channel.send(embed=bump_leaderboard_embed)

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
        self.seraphine_commands = utils.get(self.guild.text_channels, name="👩seraphine-commands")
        self.bump_king_role = utils.get(self.guild.roles, name="BumpKing")
        self.bumper_role = utils.get(self.guild.roles, name="Bumpers")
        self.general = utils.get(self.guild.text_channels, name="💭general")
        self.skybies = self.client.get_cog("Skybies")
        if not self.bump_button_added:
            self.client.add_view(BumpButton())
            self.bump_button_added = True
        self._bump_reminder.start()


def setup(client):
    client.add_cog(BumpReminder(client))