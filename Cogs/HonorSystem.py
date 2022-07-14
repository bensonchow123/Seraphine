import os
from datetime import datetime, timezone, timedelta

from nextcord import utils, Embed, Member
from nextcord.ext import commands
from bson.objectid import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()
cluster = AsyncIOMotorClient(os.getenv("MongoDbSecretKey"))
honor_system_db = cluster["Skyhub"]["HonorSystem"]
class HonorSystem(commands.Cog):
    def __init__(self, client):
        self.client = client

    async def _now(self):
        return datetime.now(timezone.utc)

    async def _datetime_to_string(self, datetime_object):
        return datetime_object.strftime("%S:%M:%H:%d:%m:%Y:%z")

    async def _string_to_datetime(self, string):
        return datetime.strptime(string, "%S:%M:%H:%d:%m:%Y:%z")

    async def _log_honor(self, ctx, giftee, honor_type, reason):
        now = await self._now()
        insert = await honor_system_db.insert_one(
            {
                "honor_giftee_id": giftee.id,
                "honor_giver_id": ctx.author.id,
                "date": await self._datetime_to_string(now),
                "honor_type": honor_type,
                "reason": reason,
            }
        )
        return insert.inserted_id

    async def _check_if_same_gifter_cooldown_in_process(self, ctx, giftee, honor_type):
        giftee_query = {
                "honor_giftee_id": giftee.id,
                "honor_giver_id": ctx.author.id,
                "honor_type": honor_type,
            }
        giftee_previous_honor_from_same_gifter = await honor_system_db.count_documents(giftee_query)
        if giftee_previous_honor_from_same_gifter:
            now = await self._now()
            honor_from_same_author_in_30min_cooldown = []
            async for insert in honor_system_db.find(giftee_query):
                date = await self._string_to_datetime(insert["date"])
                if (date + timedelta(minutes=30)) > now:
                    honor_from_same_author_in_30min_cooldown.append(date)
            if honor_from_same_author_in_30min_cooldown:
                lastest_honor_from_same_author_in_30min_cooldown = max(honor_from_same_author_in_30min_cooldown)
                return lastest_honor_from_same_author_in_30min_cooldown

    async def _honor_staff_logging_embed(self, ctx, giftee, honor_type, reason, honor_insert_id):
        give_honor_status_and_logging_embed = Embed(
            description="If you believe this honor's reason is unreasonable, or it's abuse to the honor system.\n"
                        f"Please do `!honor remove {honor_insert_id}` to remove this honor",
            colour=0xff0033
        ).set_author(
            name=f"From {ctx.author.display_name} to {giftee.display_name}",
        ).add_field(
            name="Reason",
            value=reason,
        ).set_footer(
            text=f"gifter id {ctx.author.id} | giftee id {giftee.id} | honor type: {honor_type}"
        )
        await self.staff_honor_logging_channel.send(embed=give_honor_status_and_logging_embed)

    async def _honor_status_embed(self, ctx, reason, sucessful, giftee=None):
        honor_status_embed = Embed(
            description=reason,
            colour=0x4bb543 if sucessful else 0xff0033
        ).set_author(
            name="Honor action logged" if sucessful else "Honor action not logged",
            icon_url=self.guild.icon.url
        )
        if giftee:
            honor_status_embed.set_footer(
                text=f"From {ctx.author.display_name} to {giftee.display_name}"
            )
        await ctx.reply(embed=honor_status_embed)

    async def _honor_handler(self, ctx, giftee, honor_type, reason):
        same_gifter_cooldown_in_process = await self._check_if_same_gifter_cooldown_in_process(ctx, giftee, honor_type)
        if same_gifter_cooldown_in_process:
            cooldown_expires = same_gifter_cooldown_in_process + timedelta(minutes=30)
            please_wait = cooldown_expires - await self._now()
            wait_msg = f"{please_wait.total_seconds()} seconds"
            if please_wait < timedelta(seconds=0):
                wait_msg = "0 seconds, contact hypicksell as this is broken,"
            elif please_wait > timedelta(minutes=1):
                wait_msg = f"{please_wait // timedelta(minutes=1)} minutes"

            await self._honor_status_embed(
                ctx,
                f"🛑 You have given a {honor_type} honor to {giftee.display_name} at "
                f"<t:{int(same_gifter_cooldown_in_process.replace(tzinfo=timezone.utc).timestamp())}:t>, \n"
                f"please wait {wait_msg} as there is a cooldown of 30 minutes to the same giftee",
                False,
                giftee
            )
        else:
            honor_insert_id = await self._log_honor(ctx, giftee, honor_type, reason)
            await self._honor_status_embed(
                ctx,
                f"🎉 You have given a {honor_type} honor to {giftee.display_name}",
                True,
                giftee
            )
            await self._honor_staff_logging_embed(ctx, giftee, honor_type, reason, honor_insert_id)

    @commands.group(aliases=["h","rep", "r", 'honour'], invoke_without_command=True)
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def honor(self, ctx, giftee: Member, *, reason: str):
        if ctx.invoked_subcommand is None:
            if ctx.channel.id != self.dungeon_honor_commands.id and ctx.channel.id != self.trading_honor_commands.id:
                await ctx.send(
                    f"You can only use this command in {self.trading_honor_commands.mention} or {self.dungeon_honor_commands.mention}"
                )
                return
            honor_type = "dungeon" if ctx.channel == self.dungeon_honor_commands else "trading"

            if ctx.author.id == giftee.id:
                await self._honor_status_embed(
                    ctx,
                    f"🛑 You can't give honor to yourself",
                    False,
                    giftee
                )
                return

            if (reason and len(reason.split()) < 3) or (reason and len(reason.split()) > 10):
                await self._honor_status_embed(
                    ctx,
                    f"🛑 Reason must be at most 10 words and more than 3 words\n"
                    "Use: `!honor (@member or id) (reason)`",
                    False,
                    giftee
                )
                return

            await self._honor_handler(ctx, giftee, honor_type, reason)

    @honor.error
    async def honor_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await self._honor_status_embed(
                ctx,
                f"🛑 Missing required argument: {error.param.name}",
                False,
            )
        elif isinstance(error, commands.CommandOnCooldown):
            await self._honor_status_embed(
                ctx,
                f"🛑 Please wait {error.retry_after:.0f} seconds, as there is a cooldown of 30 seconds for each honor",
                False,
            )

    @honor.command(name="remove")
    @commands.has_permissions(manage_messages=True)
    async def honor_remove(self, ctx, *, honor_insert_id):
        honor_to_remove_query = {'_id': ObjectId(honor_insert_id)}
        deleted = await honor_system_db.delete_one(honor_to_remove_query)
        if not deleted.deleted_count:
            await self._honor_status_embed(
                ctx,
                f"🛑 Honor with id {honor_insert_id} not found",
                False,
            )
            return
        await self._honor_status_embed(
            ctx,
            f"🗑 Honor with id {honor_insert_id} removed",
            True,
        )

    @honor_remove.error
    async def honor_remove_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await self._honor_status_embed(
                ctx,
                f"🛑 You don't have permission to use this command",
                False,
            )
        elif isinstance(error, commands.MissingRequiredArgument):
            await self._honor_status_embed(
                ctx,
                f"🛑 Missing required argument: {error.param.name}",
                False,
            )


    @commands.Cog.listener()
    async def on_ready(self):
        self.guild = self.client.get_guild(844231449014960160)
        self.dungeon_honor_commands = utils.get(self.guild.text_channels, name="🏅dungeon-honor-commands")
        self.trading_honor_commands = utils.get(self.guild.text_channels, name="🏅trading-honor-commands")
        self.staff_honor_logging_channel = utils.get(self.guild.text_channels, name="🏅honor-logging")
        self.honor_threshold_roles = {
            "dungeon": {
                10: utils.get(self.guild.roles, name="dungeon guide(10+ dungeon honor)"),
                25: utils.get(self.guild.roles, name="trustworthy dungeon guide(25+ dungeon honor)"),
                50: utils.get(self.guild.roles, name="honorable dungeon guide(50+ dungeon honor)"),
                100: utils.get(self.guild.roles, name="dungeon carrier(100+ dungeon honor)"),
                250: utils.get(self.guild.roles, name="legendary carrier(250+ dungeon honor)"),
                500: utils.get(self.guild.roles, name="mythical carrier(500+ dungeon honor)"),
                1000: utils.get(self.guild.roles, name="deity carrier(1000+ dungeon honor)"),
            },
            "trading": {
                10: utils.get(self.guild.roles, name="trading guide(10+ trading honor)"),
                }
        }


def setup(client):
    client.add_cog(HonorSystem(client))
