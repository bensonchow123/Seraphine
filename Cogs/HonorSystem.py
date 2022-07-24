import os
from datetime import datetime, timezone, timedelta

from bson.objectid import ObjectId
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from nextcord import utils, Embed, Member, ui, ButtonStyle, Interaction
from nextcord.ext import commands

load_dotenv()
cluster = AsyncIOMotorClient(os.getenv("MongoDbSecretKey"))
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

    async def _now(self):
        return datetime.now(timezone.utc)

    async def _datetime_to_string(self, datetime_object):
        return datetime_object.strftime("%S:%M:%H:%d:%m:%Y:%z")

    async def _string_to_datetime(self, string):
        return datetime.strptime(string, "%S:%M:%H:%d:%m:%Y:%z")

    async def pural(self, num):
        return "s" if num > 1 else ""

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
        await ctx.reply(embed=honor_status_embed, mention_author=False)

    async def _clear_honor_roles(self, giftee, honor_type):
        for role in list(self.honor_threshold_roles[honor_type].values()):
            if role in giftee.roles:
                await giftee.remove_roles(role)

    async def honor_rewards(self, giftee, honor_type):
        num_honor = await honor_system_db.count_documents({"honor_giftee_id": giftee.id, "honor_type": honor_type})
        if num_honor in self.honor_threshold_roles[honor_type]:
            new_honor_role = self.honor_threshold_roles[honor_type][num_honor]
            skybies_to_give = num_honor // 10
            await self._clear_honor_roles(giftee, honor_type)
            await giftee.add_roles(new_honor_role)
            await self.skybies._give_skybies(giftee, skybies_to_give)
            return new_honor_role, skybies_to_give
        return None, 0

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
            honor_threshold_role, skybie_given = await self.honor_rewards(giftee, honor_type)
            description = f"🎉 You have given a {honor_type} honor to {giftee.display_name}"
            if honor_threshold_role:
                description += (
                    f" and they unlocked the {honor_threshold_role.mention}"
                    f" role with a reward of {skybie_given} skybies 🌟"
                )

            await self._honor_status_embed(
                ctx,
                description,
                True,
                giftee
            )
            await self._honor_staff_logging_embed(ctx, giftee, honor_type, reason, honor_insert_id)

    @commands.group(aliases=["h", "rep", "r", 'honour'], invoke_without_command=True)
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def honor(self, ctx, giftee: Member, *, reason: str):
        if ctx.invoked_subcommand is None:
            if ctx.channel.id not in self.honor_command_channels:
                await ctx.send(
                    f"You can only use this command in {self.trading_honor_commands.mention} or {self.dungeon_honor_commands.mention}"
                )
                return

            if giftee.bot:
                await self._honor_status_embed(
                    ctx,
                    "🛑 You cannot give a honor to a bot",
                    False,
                )

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
            self.honor.reset_cooldown(ctx)
            await self._honor_status_embed(
                ctx,
                f"🛑 Missing required argument: `{error.param.name}`\n"
                f"Use: `!honor (@giftee or giftee id) (reason)`",
                False,
            )
        elif isinstance(error, commands.CommandOnCooldown):
            await self._honor_status_embed(
                ctx,
                f"🛑 Please wait {error.retry_after:.0f} seconds, as there is a cooldown of 30 seconds for each honor",
                False,
            )
        elif isinstance(error, commands.MemberNotFound):
            await self._honor_status_embed(
                ctx,
                f"🛑 Member not found or honor command dont exist\n"
                f"Use: `!honor (@giftee or giftee id) (reason)` or `!help honor`",
                False,
            )

    @honor.command(name="stats", aliases=["s"])
    async def honor_stats(self, ctx, member: Member = None):
        if ctx.channel not in self.honor_command_channels and not ctx.author.guild_permissions.manage_messages:
            await ctx.send(
                f"You can only use this command in {self.trading_honor_commands.mention} or {self.dungeon_honor_commands.mention}"
            )
            return

        you = 'they'
        if not member:
            member = ctx.author
            you = 'you'
        if member.bot:
            await self._honor_status_embed(
                ctx,
                "🛑 Bot have infinite honor, statistics cannot be determined for infinity",
                False,
            )
            return
        total_honor = await honor_system_db.count_documents({"honor_giftee_id": member.id})
        if not total_honor:
            await self._honor_status_embed(
                ctx,
                f"🛑 {member.mention} have no honor yet",
                False,
            )
            return
        member_honor_cursor = honor_system_db.find({"honor_giftee_id": member.id})
        dungeon_honor, trading_honor, today_honor, last_7_days_honor, gifter_id_list = 0, 0, 0, 0, []
        async for insert in member_honor_cursor:
            gifter_id_list.append(insert['honor_giver_id'])
            if insert['honor_type'] == 'dungeon':
                dungeon_honor += 1
            else:
                trading_honor += 1
            insert_date = await self._string_to_datetime(insert['date'])
            now = await self._now()
            if insert_date >= (now - timedelta(days=7)):
                last_7_days_honor += 1
            if insert_date >= (now - timedelta(days=1)):
                today_honor += 1

        trading_embed_field_value = f"***{you.capitalize()} have {trading_honor} trading honor.***"
        dungeon_embed_field_value = f"***{you.capitalize()} have {dungeon_honor} dungeon honor.***"

        trading_honor_away = f"{you.capitalize()} have the maxed trading honor role"
        for key, value in self.honor_threshold_roles["trading"].items():
            if trading_honor < key:
                until_next_trading_role = key - trading_honor
                next_trading_role = value
                trading_honor_away = f"\n {you.capitalize()} are _{until_next_trading_role} honor_ away from the {next_trading_role.mention} role."
                break
        trading_embed_field_value += trading_honor_away

        dungeon_honor_away = f"{you.capitalize()} have the maxed dungeon honor role"
        for key, value in self.honor_threshold_roles["dungeon"].items():
            if dungeon_honor < key:
                until_next_dungeon_role = key - dungeon_honor
                next_dungeon_role = value
                dungeon_honor_away = f"\n {you.capitalize()} are _{until_next_dungeon_role} honor_ away from the {next_dungeon_role.mention} role."
                break
        dungeon_embed_field_value += dungeon_honor_away

        honor_stats_embed = Embed(
            title=f"{member.display_name}'s honor stats",
            description=f"{you.capitalize()} have **{total_honor}** total honor",
            colour=0x003697
        ).add_field(
            name="Trading honor",
            value=trading_embed_field_value,
            inline=False
        ).add_field(
            name="Dungeon honor",
            value=dungeon_embed_field_value,
            inline=False
        ).add_field(
            name="From last 24 hours",
            value=today_honor
        ).add_field(
            name="From last 7 days",
            value=last_7_days_honor
        ).add_field(
            name="Unique gifters %",
            value=f"{round((len(gifter_id_list)-len(set(gifter_id_list))) / len(gifter_id_list) * 100, 2)} %"
        )

        await ctx.reply(embed=honor_stats_embed, mention_author=False)

    async def _sort_honor(self, honor_type):
        honor_cursor = honor_system_db.find({"honor_type": honor_type})
        honor_num_dict = {}
        last_restart_document = await reset_dates_db.find_one({"_id": ObjectId("62b4546da162f9c1a2fbdfe8")})
        last_restart_month = last_restart_document["last_restart_month"]
        async for insert in honor_cursor:
            insert_date = await self._string_to_datetime(insert["date"])
            insert_month = insert_date.month
            insert_giftee_id = insert["honor_giftee_id"]
            if insert_month >= last_restart_month:
                if insert_giftee_id not in honor_num_dict:
                    honor_num_dict[insert_giftee_id] = 1
                else:
                    honor_num_dict[insert_giftee_id] += 1
        sorted_num_list = sorted(honor_num_dict.items(), key=lambda x: x[1], reverse=True)
        return sorted_num_list

    async def _honor_embed(self, sorted_honor_dict, honor_type, member_id):
        emoji_list = ["🥇", "🥈", "🥉"] + (["🎖️"] * 7)
        ranking_list = []
        for ranking in zip(emoji_list, sorted_honor_dict):
            member = self.guild.get_member(ranking[1][0])
            if member.id == member_id:
                ranking_list.append(f"**{ranking[0]}  {member.display_name} has {ranking[1][1]} {honor_type} honor**")
            else:
                ranking_list.append(f"{ranking[0]}  {member.display_name} has {ranking[1][1]} {honor_type} honor")
        joined_ranking_list = '\n'.join(ranking_list)
        profession = "Merchant" if honor_type == "trading" else "Dungeonner"
        honor_ranking_embed = Embed(
            title=f"{honor_type.capitalize()} honor leaderboard",
            description=f"The most honorable {profession} in this server, you can trust your life with them,"
                        f"the leaderboard resets every month. \n\n{joined_ranking_list}",
            colour=0x003697
        ).set_thumbnail(
            url='https://www.pngitem.com/pimgs/m/9-95691_clip-art-medal-vector-cartoon-medal-hd-png.png'
        )
        return honor_ranking_embed

    @honor.command(name="leaderboard", aliases=["l"])
    async def honor_leaderboard(self, ctx, member: Member = None):
        if ctx.channel not in self.honor_command_channels and not ctx.author.guild_permissions.manage_messages:
            await ctx.send(
                f"You can only use this command in {self.trading_honor_commands.mention} or {self.dungeon_honor_commands.mention}"
            )
            return

        if member and member.bot:
            await self._honor_status_embed(
                ctx,
                "🛑 Bots have the unlimited honor, they can't be on the same list as regular members",
                False,
            )

        if not member:
            member = ctx.author

        honor_type = "dungeon" if ctx.channel == self.dungeon_honor_commands else "trading"
        honor_count = await honor_system_db.count_documents({"honor_giftee_id": member.id, "honor_type": honor_type})
        sorted_honor_list = await self._sort_honor(honor_type)
        honor_leaderboard_embed = await self._honor_embed(sorted_honor_list, honor_type, member.id)
        if honor_count:
            member_ranking = sorted_honor_list.index((member.id, honor_count)) + 1
            if member_ranking > 10:
                honor_leaderboard_embed.set_footer(text=f"{member.display_name} is ranked #{member_ranking}")

        await ctx.reply(embed=honor_leaderboard_embed, mention_author=False)

    @honor.command(name="history", aliases=["h"])
    async def honor_history(self, ctx, member: Member = None):
        if ctx.channel not in self.honor_command_channels and not ctx.author.guild_permissions.manage_messages:
            await ctx.send(
                f"You can only use this command in {self.trading_honor_commands.mention} or {self.dungeon_honor_commands.mention}"
            )
            return

        if member and member.bot:
            await self._honor_status_embed(
                ctx,
                "🛑 Bots have the unlimited honor, our severs are not able to track them",
                False,
            )

        if not member:
            member = ctx.author

        now = await self._now()
        member_honor_cursor = honor_system_db.find({"honor_giftee_id": member.id}).sort("_id", -1)
        honor_history_embed_list = []
        current_honor_embed = Embed(
            title=f"{member.display_name}'s honor history",
            colour=0x003697
        )
        async for insert in member_honor_cursor:
            insert_date = await self._string_to_datetime(insert["date"])
            ago = now - insert_date
            seconds_difference = ago.seconds
            ago_message = f"{seconds_difference} second{await self.pural(seconds_difference)} ago"
            if ago.days >= 365:
                years_difference = now.year - insert_date.year
                ago_message = f"{years_difference} year{await self.pural(years_difference)} ago"
            elif now.month != insert_date.month:
                months_difference = (now.year - insert_date.year) * 12 + now.month - insert_date.month
                ago_message = f"{months_difference} month{await self.pural(months_difference)} ago"
            elif ago.days > 0:
                days_difference = ago.days
                ago_message = f"{days_difference} day{await self.pural(days_difference)} ago"
            elif ago.seconds >= 3600:
                hours_difference = ago.seconds // 3600
                ago_message = f"{hours_difference} hour{await self.pural(hours_difference)} ago"
            elif ago.seconds >= 60:
                minutes_difference = ago.seconds // 60
                ago_message = f"{minutes_difference} minute{await self.pural(minutes_difference)} ago"
            elif ago.seconds <= 0:
                ago_message = "just now"

            insert_honor_type = insert["honor_type"]
            insert_honor_giver_id = insert["honor_giver_id"]
            reason = insert["reason"]
            current_honor_embed.add_field(
                name=insert_honor_type,
                value=f"**By**: {self.guild.get_member(insert_honor_giver_id).mention}, {ago_message}\n"
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
            await self._honor_status_embed(ctx, f"{member.display_name} has no honor", False)

        history_view = ButtonedHonorHistory(honor_history_embed_list, ctx.author)
        history_view.view_message = await ctx.send(
            view=history_view,
            embed=honor_history_embed_list[0].set_footer(
                text=f"Page 1/{len(honor_history_embed_list)}"
            )
        )

    async def _find_previous_role_and_skybie_given(self, role, honor_type):
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
            await self._honor_status_embed(
                ctx,
                f"🛑 No honor found with id {honor_insert_id}",
                False,
            )
            return
        description = f"🗑 Honor with id {honor_insert_id} removed"
        giftee = self.guild.get_member(honor_to_delete["honor_giftee_id"])

        if not giftee:
            await self._honor_status_embed(
                ctx,
                f"🛑 This honor's giftee is no longer present the server {giftee.mention}",
                False,
            )
            return
        honor_type = honor_to_delete["honor_type"]
        honor_type_count = await honor_system_db.count_documents({"honor_giftee_id": giftee.id, "honor_type": honor_type})
        if honor_type_count in self.honor_threshold_roles[honor_type]:
            honor_threshold_role = self.honor_threshold_roles[honor_type][honor_type_count]
            previous_role, skybies_to_remove = await self._find_previous_role_and_skybie_given(
                honor_threshold_role,
                honor_type
            )
            description = f"""🛑 You have removed a threshold honor.\n{giftee.mention}'s threshold reward
                          `({honor_threshold_role.mention} role and {skybies_to_remove} skybies)` is removed."""

            if previous_role:
                await giftee.add_roles(previous_role)
                description += f"\nTheir previous role `{previous_role.mention}` is added back."
            await self.skybies._take_skybies(giftee, skybies_to_remove)
            await giftee.remove_roles(honor_threshold_role)

        await honor_system_db.delete_one(honor_to_delete)
        await self._honor_status_embed(
            ctx,
            description,
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
                f"🛑 Missing required argument: `({error.param.name})`"
                f"Use: `!honor remove (honor_insert_id) (honor_threshold_role)`",
                False,
            )

    @honor.command(name="test")
    @commands.is_owner()
    async def honor_test(self, ctx, count: int, giftee: Member):
        for i in range(count):
            honor_insert_id = await self._log_honor(ctx, giftee, "dungeon", "tesing this good")
            honor_threshold_role, skybie_given = await self.honor_rewards(giftee, "dungeon")
            description = f"🎉 You have given a {'dungeon'} honor to {giftee.display_name}"
            if honor_threshold_role:
                description += (
                    f" and they unlocked the {honor_threshold_role.mention}"
                    f" role with a reward of {skybie_given} skybies"
                )

            await self._honor_status_embed(
                ctx,
                description,
                True,
                giftee
            )
            await self._honor_staff_logging_embed(ctx, giftee, "dungeon", "tesing this good", honor_insert_id)

    @commands.Cog.listener()
    async def on_ready(self):
        self.guild = self.client.get_guild(844231449014960160)
        self.dungeon_honor_commands = utils.get(self.guild.text_channels, name="🏅dungeon-honor-commands")
        self.trading_honor_commands = utils.get(self.guild.text_channels, name="🏅trading-honor-commands")
        self.honor_command_channels = [self.trading_honor_commands.id, self.dungeon_honor_commands.id]
        self.staff_honor_logging_channel = utils.get(self.guild.text_channels, name="🏅honor-logging")
        self.skybies = self.client.get_cog("Skybies")
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
                10: utils.get(self.guild.roles, name="decent merchant(10+ trading honor)"),
                25: utils.get(self.guild.roles, name="honest merchant(25+ trading honor)"),
                50: utils.get(self.guild.roles, name="trustworthy merchant(50+ trading honor)"),
                100: utils.get(self.guild.roles, name="respectable merchant(100+ trading honor)"),
                250: utils.get(self.guild.roles, name="admirable merchant(250+ trading honor)"),
                500: utils.get(self.guild.roles, name="exceptional merchant(500+ trading honor)"),
                1000: utils.get(self.guild.roles, name="supreme merchant(1000+ trading honor)"),
            }
        }


def setup(client):
    client.add_cog(HonorSystem(client))
