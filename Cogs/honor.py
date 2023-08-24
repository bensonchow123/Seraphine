from os import getenv
from datetime import datetime, timezone, timedelta

from humanfriendly import format_timespan
from bson.objectid import ObjectId
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from discord import utils, Embed, Member, ui, ButtonStyle, Interaction
from discord.ext import commands

load_dotenv()
cluster = AsyncIOMotorClient(getenv("MongoDbSecretKey"))
honor_system_db = cluster["Skyhub"]["HonorSystem"]
reset_dates_db = cluster["Skyhub"]["ResetDates"]


class ButtonedHonorHistory(ui.View):
    def __init__(self, embed_list, original_message_author):
        super().__init__(timeout=60)
        self.embed_list = embed_list
        self.original_message_author = original_message_author
        self.current = 0

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        await self.view_message.edit(view=self)
        await self.view_message.edit(
            embed=Embed(
                description="This honor history embed is timed out",
                colour=0xff0033
            )
        )

    async def interaction_check(self, interaction):
        if self.original_message_author != interaction.user:
            await interaction.response.send_message(
                "This embed ain't not yours",
                ephemeral=True
            )
            return
        return True

    @ui.button(emoji="⏪", style=ButtonStyle.blurple)
    async def fast_backwards(self, button: ui.Button, interaction: Interaction):
        self.current = 0
        await interaction.response.edit_message(
            embed=self.embed_list[self.current].set_footer(
                text=f"Page {self.current + 1}/{len(self.embed_list)}"
            )
        )

    @ui.button(emoji="◀", style=ButtonStyle.blurple)
    async def backwards(self, button: ui.Button, interaction: Interaction):
        self.current -= 1
        if self.current < 0:
            self.current = len(self.embed_list) - 1
        await interaction.response.edit_message(
            embed=self.embed_list[self.current].set_footer(
                text=f"Page {self.current + 1}/{len(self.embed_list)}"
            )
        )

    @ui.button(emoji="▶", style=ButtonStyle.blurple)
    async def forward(self, button: ui.Button, interaction: Interaction):
        self.current += 1
        if self.current > len(self.embed_list) - 1:
            self.current = 0
        await interaction.response.edit_message(
            embed=self.embed_list[self.current].set_footer(
                text=f"Page {self.current + 1}/{len(self.embed_list)}"
            )
        )

    @ui.button(emoji="⏩", style=ButtonStyle.blurple)
    async def fast_forward(self, button: ui.Button, interaction: Interaction):
        self.current = len(self.embed_list) - 1
        await interaction.response.edit_message(
            embed=self.embed_list[self.current].set_footer(
                text=f"Page {self.current + 1}/{len(self.embed_list)}"
            )
        )


class HonorSystem(commands.Cog):
    def __init__(self, client):
        self.client = client

    @property
    def skybies(self):
        return self.client.get_cog("Skybies")

    @property
    def guild(self):
        return self.client.get_guild(int(getenv("GUILD_ID")))

    @property
    def carrying_honor_commands(self):
        return utils.get(self.guild.text_channels, name="🏅carrying-honor-commands")

    @property
    def trading_honor_commands(self):
        return utils.get(self.guild.text_channels, name="🏅trading-honor-commands")

    @property
    def honor_threshold_roles(self):
        return {
            "carrying": {
                10: utils.get(self.guild.roles, name="decent carrier(10+ carrying honor)"),
                25: utils.get(self.guild.roles, name="honorable carrier(25+ carrying honor)"),
                50: utils.get(self.guild.roles, name="trustworthy carrier(50+ carrying honor)"),
                100: utils.get(self.guild.roles, name="famous carrier(100+ carrying honor)"),
                250: utils.get(self.guild.roles, name="legendary carrier(250+ carrying honor)"),
                500: utils.get(self.guild.roles, name="mythical carrier(500+ carrying honor)"),
                1000: utils.get(self.guild.roles, name="deity carrier(1000+ carrying honor)"),
            },
            "trading": {
                10: utils.get(self.guild.roles, name="decent merchant(10+ trading honor)"),
                25: utils.get(self.guild.roles, name="honest merchant(25+ trading honor)"),
                50: utils.get(self.guild.roles, name="trustworthy merchant(50+ trading honor)"),
                100: utils.get(self.guild.roles, name="respectable merchant(100+ trading honor)"),
                250: utils.get(self.guild.roles, name="admirable merchant(250+ trading honor)"),
                500: utils.get(self.guild.roles, name="exceptional merchant(500+ trading honor)"),
                1000: utils.get(self.guild.roles, name="supreme merchant(1000+ trading honor)"),
            }
        }

    async def now(self):
        return datetime.now(timezone.utc)

    async def datetime_to_string(self, datetime_object):
        return datetime_object.strftime("%S:%M:%H:%d:%m:%Y:%z")

    async def string_to_datetime(self, string):
        return datetime.strptime(string, "%S:%M:%H:%d:%m:%Y:%z")

    async def pural(self, num):
        return "s" if num > 1 else ""

    async def log_honor(self, ctx, giftee, honor_type, reason):
        now = await self.now()
        insert = await honor_system_db.insert_one(
            {
                "honor_giftee_id": giftee.id,
                "honor_giver_id": ctx.author.id,
                "date": await self.datetime_to_string(now),
                "honor_type": honor_type,
                "reason": reason,
            }
        )
        return insert.inserted_id

    async def check_if_same_gifter_cooldown_in_process(self, ctx, giftee: Member, honor_type: str):
        giftee_query = {
            "honor_giftee_id": giftee.id,
            "honor_giver_id": ctx.author.id,
            "honor_type": honor_type,
        }
        giftee_previous_honor_from_same_gifter = await honor_system_db.count_documents(giftee_query)
        if giftee_previous_honor_from_same_gifter:
            now = await self.now()
            honor_from_same_author_in_30min_cooldown = []
            async for insert in honor_system_db.find(giftee_query):
                date = await self.string_to_datetime(insert["date"])
                if (date + timedelta(minutes=30)) > now:
                    honor_from_same_author_in_30min_cooldown.append(date)
            if honor_from_same_author_in_30min_cooldown:
                lastest_honor_from_same_author_in_30min_cooldown = max(honor_from_same_author_in_30min_cooldown)
                return lastest_honor_from_same_author_in_30min_cooldown

    async def honor_staff_logging_embed(self, ctx, giftee: Member, honor_type: str, reason: str, honor_insert_id):
        staff_honor_logs_channel = utils.get(self.guild.text_channels, name="🏅honor-logs")
        give_honor_status_and_logging_embed = Embed(
            description=f"If you believe this honor's reason is unreasonable, or it's abuse to the honor system.\n"
                        f"Please do `!honor remove {honor_insert_id}` to remove this honor",
            colour=0xff0033
        ).set_author(
            name=f"From {ctx.author.display_name} to {giftee.display_name}",
        ).add_field(
            name="Reason",
            value=reason,
        ).set_footer(
            text=f"gifter id: {ctx.author.id} | giftee id: {giftee.id} | honor type: {honor_type}"
        )
        await staff_honor_logs_channel.send(embed=give_honor_status_and_logging_embed)

    async def honor_status_embed(self, ctx, reason: str, sucessful: bool, giftee: Member = None):
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
        await ctx.reply(embed=honor_status_embed, mention_author=False)

    async def clear_honor_roles(self, giftee: Member, honor_type: str):
        for role in list(self.honor_threshold_roles[honor_type].values()):
            if role in giftee.roles:
                await giftee.remove_roles(role)

    async def honor_rewards(self, giftee: Member, honor_type: str):
        num_honor = await honor_system_db.count_documents({"honor_giftee_id": giftee.id, "honor_type": honor_type})
        if num_honor in self.honor_threshold_roles[honor_type]:
            new_honor_role = self.honor_threshold_roles[honor_type][num_honor]
            skybies_to_give = num_honor // 10
            await self.clear_honor_roles(giftee, honor_type)
            await giftee.add_roles(new_honor_role)
            await self.skybies.give_skybies(giftee, skybies_to_give)
            return num_honor, new_honor_role, skybies_to_give
        return num_honor, None, 0

    async def honor_handler(self, ctx, giftee: Member, honor_type: str, reason: str):
        same_gifter_cooldown_in_process = await self.check_if_same_gifter_cooldown_in_process(ctx, giftee, honor_type)
        if same_gifter_cooldown_in_process:
            cooldown_expires = same_gifter_cooldown_in_process + timedelta(minutes=30)
            please_wait = cooldown_expires - await self.now()
            wait_msg = f"{please_wait.total_seconds()} seconds"
            if please_wait < timedelta(seconds=0):
                wait_msg = "0 seconds, contact hypicksell as this is broken,"
            elif please_wait > timedelta(minutes=1):
                wait_msg = f"{please_wait // timedelta(minutes=1)} minutes"

            await self.honor_status_embed(
                ctx,
                f"🛑 You have given a {honor_type} honor to {giftee.display_name} at "
                f"<t:{int(same_gifter_cooldown_in_process.replace(tzinfo=timezone.utc).timestamp())}:t>, \n"
                f"please wait {wait_msg} as there is a cooldown of 30 minutes to the same giftee",
                False,
                giftee
            )
        else:
            honor_insert_id = await self.log_honor(ctx, giftee, honor_type, reason)
            num_honor, honor_threshold_role, skybie_given = await self.honor_rewards(giftee, honor_type)
            description = f"🎉 You have given a {honor_type} honor to {giftee.display_name}"
            if honor_threshold_role:
                description += (
                    f" \nThey unlocked the {honor_threshold_role.mention}"
                    f" role with a reward of {skybie_given} skybies 🌟"
                )
            else:
                carrying_honor_away, next_carrying_role = await self.num_to_and_role_of_next_honor_threshold(
                    num_honor,
                    honor_type
                )
                if carrying_honor_away:
                    description += (
                        f"\n They are _{carrying_honor_away} honor_ "
                        f"away from the {next_carrying_role.mention} role."
                    )
            await self.honor_status_embed(
                ctx,
                description,
                True,
                giftee
            )
            await self.honor_staff_logging_embed(ctx, giftee, honor_type, reason, honor_insert_id)

    async def num_to_and_role_of_next_honor_threshold(self, num_honor: int, honor_type: str):
        num_till_next_honor_role, next_honor_role = None, None
        for key, value in self.honor_threshold_roles[honor_type].items():
            if num_honor < key:
                num_till_next_honor_role = key - num_honor
                next_honor_role = value
                break
        return num_till_next_honor_role, next_honor_role

    @commands.group(aliases=["h", "rep", "r", 'honour'], invoke_without_command=True)
    @commands.cooldown(2, 30, commands.BucketType.user)
    async def honor(self, ctx, giftee: Member, *, reason: str):
        if ctx.invoked_subcommand is None:
            if ctx.channel.id not in [self.trading_honor_commands.id, self.carrying_honor_commands.id] and not ctx.channel.category.name == "Carrying Tickets":
                await ctx.send(
                    f"You can only use this command in {self.trading_honor_commands.mention},"
                    f" {self.carrying_honor_commands.mention} or in a carrying ticket"
                )
                return

            if giftee.bot:
                await self.honor_status_embed(
                    ctx,
                    "🛑 You cannot give a honor to a bot",
                    False,
                )
            if ctx.channel == self.carrying_honor_commands or ctx.channel.category.name == "Carrying Tickets":
                honor_type = "carrying"
            else:
                honor_type = "trading"

            if ctx.author.id == giftee.id:
                await self.honor_status_embed(
                    ctx,
                    f"🛑 You can't give honor to yourself",
                    False,
                    giftee
                )
                return

            if (reason and len(reason.split()) < 3) or (reason and len(reason.split()) > 20):
                await self.honor_status_embed(
                    ctx,
                    f"🛑 Reason must be at most 20 words and more than 3 words\n"
                    "Use: `!honor (@member or id) (reason)`",
                    False,
                    giftee
                )
                return

            await self.honor_handler(ctx, giftee, honor_type, reason)

    @honor.error
    async def honor_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await self.honor_status_embed(
                ctx,
                f"🛑 Missing required argument: `{error.param.name}`\n"
                f"Use: `!honor (@giftee or giftee id) (reason)`",
                False,
            )
        elif isinstance(error, commands.CommandOnCooldown):
            await self.honor_status_embed(
                ctx,
                f"🛑 Please wait {error.retry_after:.0f} seconds, "
                f"as there is a limit of 2 honor commands every 30 seconds ",
                False,
            )
        elif isinstance(error, commands.MemberNotFound):
            await self.honor_status_embed(
                ctx,
                f"🛑 Member not found or honor command dont exist\n"
                f"Use: `!honor (@giftee or giftee id) (reason)` or `!help honor`",
                False,
            )

    @honor.command(name="stats", aliases=["s"])
    async def honor_stats(self, ctx, member: Member = None):
        if ctx.channel not in [self.trading_honor_commands.id, self.carrying_honor_commands.id] and not ctx.author.guild_permissions.manage_messages:
            await ctx.send(
                f"You can only use this command in {self.trading_honor_commands.mention} or {self.carrying_honor_commands.mention}"
            )
            return

        you = 'they'
        if not member:
            member = ctx.author
            you = 'you'
        if member.bot:
            await self.honor_status_embed(
                ctx,
                "🛑 Bot have infinite honor, statistics cannot be determined for infinity",
                False,
            )
            return
        total_honor = await honor_system_db.count_documents({"honor_giftee_id": member.id})
        if not total_honor:
            await self.honor_status_embed(
                ctx,
                f"🛑 {member.mention} have no honor yet",
                False,
            )
            return
        member_honor_cursor = honor_system_db.find({"honor_giftee_id": member.id})
        carrying_honor, trading_honor, today_honor, last_7_days_honor, gifter_id_list = 0, 0, 0, 0, []
        async for insert in member_honor_cursor:
            gifter_id_list.append(insert['honor_giver_id'])
            if insert['honor_type'] == 'carrying':
                carrying_honor += 1
            else:
                trading_honor += 1
            insert_date = await self.string_to_datetime(insert['date'])
            now = await self.now()
            if insert_date >= (now - timedelta(days=7)):
                last_7_days_honor += 1
            if insert_date >= (now - timedelta(days=1)):
                today_honor += 1

        trading_embed_field_value = f"***{you.capitalize()} have {trading_honor} trading honor.***"
        carrying_embed_field_value = f"***{you.capitalize()} have {carrying_honor} carrying honor.***"

        trading_honor_away, next_trading_role= await self.num_to_and_role_of_next_honor_threshold(
            trading_honor,
            "trading"
        )
        if not trading_honor_away:
            trading_honor_away_message = f"{you.capitalize()} have reached the maximum trading honor role."
        else:
            trading_honor_away_message = (
                f"\n {you.capitalize()} are _{trading_honor_away} honor_ "
                f"away from the {next_trading_role.mention} role."
            )
        trading_embed_field_value += trading_honor_away_message

        carrying_honor_away, next_carrying_role = await self.num_to_and_role_of_next_honor_threshold(
            carrying_honor,
            "carrying"
        )
        if not carrying_honor_away:
            carrying_honor_away_message = f"{you.capitalize()} have reached the maximum carrying honor role."
        else:
            carrying_honor_away_message = (
                f"\n {you.capitalize()} are _{carrying_honor_away} honor_ "
                f"away from the {next_carrying_role.mention} role."
            )
        carrying_embed_field_value += carrying_honor_away_message

        honor_stats_embed = Embed(
            title=f"{member.display_name}'s honor stats",
            description=f"{you.capitalize()} have **{total_honor}** total honor",
            colour=0x003697
        ).add_field(
            name="Trading honor",
            value=trading_embed_field_value,
            inline=False
        ).add_field(
            name="Carrying honor",
            value=carrying_embed_field_value,
            inline=False
        ).add_field(
            name="From last 24 hours",
            value=today_honor
        ).add_field(
            name="From last 7 days",
            value=last_7_days_honor
        ).add_field(
            name="Unique gifters %",
            value=f"{round(len(set(gifter_id_list)) / len(gifter_id_list) * 100, 2)}%"
        )

        await ctx.reply(embed=honor_stats_embed, mention_author=False)

    async def sort_honor(self, honor_type: str):
        honor_cursor = honor_system_db.find({"honor_type": honor_type})
        honor_num_dict = {}
        last_restart_document = await reset_dates_db.find_one({"_id": ObjectId("62b4546da162f9c1a2fbdfe8")})
        last_restart_month = last_restart_document["last_restart_month"]
        async for insert in honor_cursor:
            insert_date = await self.string_to_datetime(insert["date"])
            insert_month = insert_date.month
            insert_giftee_id = insert["honor_giftee_id"]
            if insert_month >= last_restart_month:
                if insert_giftee_id not in honor_num_dict:
                    honor_num_dict[insert_giftee_id] = 1
                else:
                    honor_num_dict[insert_giftee_id] += 1
        sorted_num_list = sorted(honor_num_dict.items(), key=lambda x: x[1], reverse=True)
        return sorted_num_list

    async def honor_embed(self, sorted_honor_dict, honor_type, member_id):
        emoji_list = ["🥇", "🥈", "🥉"] + (["🎖️"] * 7)
        ranking_list = []
        for ranking in zip(emoji_list, sorted_honor_dict):
            member = self.guild.get_member(ranking[1][0])
            if not member:
                continue
            elif member.id == member_id:
                ranking_list.append(f"**{ranking[0]}  {member.display_name} has {ranking[1][1]} {honor_type} honor**")
            else:
                ranking_list.append(f"{ranking[0]}  {member.display_name} has {ranking[1][1]} {honor_type} honor")
        joined_ranking_list = '\n'.join(ranking_list)
        profession = "Merchant" if honor_type == "trading" else "Carrier"
        honor_ranking_embed = Embed(
            title=f"{honor_type.capitalize()} honor leaderboard",
            description=f"The most honorable {profession} in this server, you can trust your life with them,"
                        f"the leaderboard resets every month. \n\n{joined_ranking_list}",
            colour=0x003697
        ).set_thumbnail(
            url='https://i.imgur.com/yi6sTso.png'
        )
        return honor_ranking_embed

    @honor.command(name="leaderboard")
    async def honor_leaderboard(self, ctx, member: Member = None):
        if ctx.channel.id not in [self.trading_honor_commands.id, self.carrying_honor_commands.id] and not ctx.author.guild_permissions.manage_messages:
            await ctx.send(
                f"You can only use this command in {self.trading_honor_commands.mention} or {self.carrying_honor_commands.mention}"
            )
            return

        if member and member.bot:
            await self.honor_status_embed(
                ctx,
                "🛑 Bots have the unlimited honor, they can't be on the same list as regular members",
                False,
            )

        if not member:
            member = ctx.author

        honor_type = "carrying" if ctx.channel == self.carrying_honor_commands else "trading"
        honor_count = await honor_system_db.count_documents({"honor_giftee_id": member.id, "honor_type": honor_type})
        sorted_honor_list = await self.sort_honor(honor_type)
        honor_leaderboard_embed = await self.honor_embed(sorted_honor_list, honor_type, member.id)
        if honor_count:
            member_ranking = sorted_honor_list.index((member.id, honor_count)) + 1
            if member_ranking > 10:
                honor_leaderboard_embed.set_footer(text=f"{member.display_name} is ranked #{member_ranking}")

        await ctx.reply(embed=honor_leaderboard_embed, mention_author=False)

    @honor.command(name="history", aliases=["h", "list"])
    async def honor_history(self, ctx, member: Member = None):
        if ctx.channel not in [self.trading_honor_commands.id, self.carrying_honor_commands.id] and not ctx.author.guild_permissions.manage_messages:
            await ctx.send(
                f"You can only use this command in {self.trading_honor_commands.mention} or {self.carrying_honor_commands.mention}"
            )
            return

        if member and member.bot:
            await self.honor_status_embed(
                ctx,
                "🛑 Bots have the unlimited honor, our severs are not able to track them",
                False,
            )

        if not member:
            member = ctx.author

        now = await self.now()
        member_honor_cursor = honor_system_db.find({"honor_giftee_id": member.id}).sort("_id", -1)
        honor_history_embed_list = []
        current_honor_embed = Embed(
            title=f"{member.display_name}'s honor history",
            colour=0x003697
        )
        async for insert in member_honor_cursor:
            insert_date = await self.string_to_datetime(insert["date"])
            ago = now - insert_date
            ago_message = f"{format_timespan(ago, max_units=2)} ago"

            insert_honor_type = insert["honor_type"]
            insert_honor_giver_id = insert["honor_giver_id"]
            reason = insert["reason"]
            insert_honor_giver = self.guild.get_member(insert_honor_giver_id)
            current_honor_embed.add_field(
                name=insert_honor_type,
                value=f"**By**: {insert_honor_giver.mention if insert_honor_giver else 'Unknown'}, {ago_message}\n"
                      f"**Reason**: {reason}\n"
                      f"**id**: ```{insert['_id']}```",
                inline=False
            )
            if len(current_honor_embed.fields) >= 5:
                honor_history_embed_list.append(current_honor_embed)
                current_honor_embed = Embed(
                    title=f"{member.display_name}'s honor history",
                    colour=0x003697
                )
        if len(current_honor_embed.fields):
            honor_history_embed_list.append(current_honor_embed)

        if not honor_history_embed_list:
            await self.honor_status_embed(ctx, f"{member.display_name} has no honor", False)

        history_view = ButtonedHonorHistory(honor_history_embed_list, ctx.author)
        history_view.view_message = await ctx.send(
            view=history_view,
            embed=honor_history_embed_list[0].set_footer(
                text=f"Page 1/{len(honor_history_embed_list)}"
            )
        )

    async def find_previous_role_and_skybie_given(self, role, honor_type):
        list_of_honor_threshold_roles = list(self.honor_threshold_roles[honor_type].values())
        list_of_honor_threshold = list(self.honor_threshold_roles[honor_type].keys())
        position_of_role = list_of_honor_threshold_roles.index(role)
        try:
            previous_role = list_of_honor_threshold_roles[position_of_role - 1]
        except IndexError:
            previous_role = None
        honor_threshold = list_of_honor_threshold[position_of_role]
        skybie_to_remove = honor_threshold // 10
        return previous_role, skybie_to_remove


    @honor.command(name="remove", aliases=["r"])
    @commands.has_permissions(manage_messages=True)
    async def honor_remove(self, ctx, honor_insert_id):
        honor_to_delete = await honor_system_db.find_one({"_id": ObjectId(honor_insert_id)})
        if not honor_to_delete:
            await self.honor_status_embed(
                ctx,
                f"🛑 No honor found with id {honor_insert_id}",
                False,
            )
            return
        description = f"🗑 Honor with id {honor_insert_id} removed"
        giftee = self.guild.get_member(honor_to_delete["honor_giftee_id"])

        if not giftee:
            await self.honor_status_embed(
                ctx,
                f"🛑 This honor's giftee is no longer present the server {giftee.mention}",
                False,
            )
            return
        honor_type = honor_to_delete["honor_type"]
        honor_type_count = await honor_system_db.count_documents({"honor_giftee_id": giftee.id, "honor_type": honor_type})
        if honor_type_count in self.honor_threshold_roles[honor_type]:
            honor_threshold_role = self.honor_threshold_roles[honor_type][honor_type_count]
            previous_role, skybies_to_remove = await self.find_previous_role_and_skybie_given(
                honor_threshold_role,
                honor_type
            )
            description = f"""🛑 You have removed a threshold honor.\n{giftee.mention}'s threshold reward
                          `({honor_threshold_role.mention} role and {skybies_to_remove} skybies)` is removed."""

            if previous_role:
                await giftee.add_roles(previous_role)
                description += f"\nTheir previous role `{previous_role.mention}` is added back."
            await self.skybies.take_skybies(giftee, skybies_to_remove)
            await giftee.remove_roles(honor_threshold_role)

        await honor_system_db.delete_one(honor_to_delete)
        await self.honor_status_embed(
            ctx,
            description,
            True,
        )

    @honor_remove.error
    async def honor_remove_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await self.honor_status_embed(
                ctx,
                f"🛑 You don't have permission to use this command",
                False,
            )
        elif isinstance(error, commands.MissingRequiredArgument):
            await self.honor_status_embed(
                ctx,
                f"🛑 Missing required argument: `({error.param.name})`"
                f"Use: `!honor remove (honor_insert_id) (honor_threshold_role)`",
                False,
            )

    @honor.command(name="test")
    @commands.is_owner()
    async def honor_test(self, ctx, count: int, giftee: Member):
        for i in range(count):
            honor_insert_id = await self.log_honor(ctx, giftee, "carrying", "tesing this good")
            num_honor, honor_threshold_role, skybie_given = await self.honor_rewards(giftee, "carrying")
            description = f"🎉 You have given a carrying honor to {giftee.display_name}"
            if honor_threshold_role:
                description += (
                    f" and they unlocked the {honor_threshold_role.mention}"
                    f" role with a reward of {skybie_given} skybies"
                )

            await self.honor_status_embed(
                ctx,
                description,
                True,
                giftee
            )
            await self.honor_staff_logging_embed(ctx, giftee, "carrying", "tesing this good", honor_insert_id)


async def setup(client):
    await client.add_cog(HonorSystem(client))
