import os

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import DESCENDING
from nextcord import Embed, utils
from nextcord.ext import commands, tasks
from dotenv import load_dotenv
from datetime import datetime
load_dotenv()
cluster = AsyncIOMotorClient(os.getenv("MongoDbSecretKey"))
bump_db = cluster["Skyhub"]["BumpRecord"]
restart_date_db = cluster["Skyhub"]["ResetDates"]

class Bumpleaderboard(commands.Cog):
    def __init__(self, client):
        self.client = client


    async def _find_weekly_restart_date(self):
        last_restart = await restart_date_db.find_one({"type": "weekly"})
        last_restart = last_restart["last_restart"]
        last_restart_date = datetime.strptime(last_restart, "%S:%M:%H:%d:%m:%Y:%z")
        return last_restart_date

    async def _last_bump_id(self):
        last_bump = await bump_db.find_one(sort=[('$natural', DESCENDING)])
        last_bump_id = last_bump["_id"]
        return last_bump_id

    async def _get_bump_king(self):
        bump_ranking_list = await self._bump_sort()
        if bump_ranking_list:
            return self.guild.get_member(bump_ranking_list[0][0])

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

    async def _bump_leaderboard_embed(self,ctx):
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
            ctx.channel.id != self.bot_channel.id
            and not ctx.author.guild_permissions.administrator
        ):
            await ctx.send("Use this command in the <#850027624361230336> channel", delete_after=10)
            return
        bump_leaderboard_embed = await self._bump_leaderboard_embed(ctx)
        await ctx.channel.send(embed=bump_leaderboard_embed)

    async def _remove_all_bump_king(self):
        for user in self.guild.members:
            await user.remove_roles(self.bump_king_role)

    async def _find_previous_bump_king(self):
        for member in self.guild.members:
            if self.bump_king_role in member.roles:
                return member

    async def _crown_bump_king(self,member):
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

    @tasks.loop(minutes=1)
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
    async def on_ready(self):
        self.guild = self.client.get_guild(844231449014960160)
        self.bot_channel = utils.get(self.guild.text_channels, name="👩seraphine-commands")
        self.general = utils.get(self.guild.text_channels, name="💭general")
        self.bump_king_role = utils.get(self.guild.roles, name="BumpKing")
        self._bump_king_updater.start()
def setup(client):
    client.add_cog(Bumpleaderboard(client))
