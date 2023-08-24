from os import getenv
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from discord import utils, Embed, Colour, Member
from discord.ext import commands

load_dotenv()
cluster = AsyncIOMotorClient(getenv("MongoDbSecretKey"))
skybiedb = cluster["Skyhub"]["Skybies"]


class Skybies(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.item_cost = {
            "angel": 70,
            "weekly_giveaway": 5,
            "sky_promoter": 30,
            "master_of_disguise": 50,
            "skybies_baiter": 100,
        }

    @property
    def guild(self):
        return self.client.get_guild(int(getenv("GUILD_ID")))

    @property
    def angel(self): return utils.get(self.guild.roles, name="😎Angels😎")

    @property
    def sky_promoter(self): return utils.get(self.guild.roles, name="📢Sky Promoter📢")

    @property
    def master_of_disguise(self): return utils.get(self.guild.roles, name="🥸master of disguise🥸")

    @property
    def skybies_baiter(self): return utils.get(self.guild.roles, name="🤑Skybies Baiter🤑")

    @property
    def weekly_giveaway(self): return utils.get(self.guild.roles, name="📅Weekly giveaway📅")

    @property
    def seraphine_commands(self): return utils.get(self.guild.text_channels, name="👩seraphine-commands")

    @property
    def angel_channel(self): return utils.get(self.guild.text_channels, name="😎angels-chat")

    @property
    def self_promotion_channel(self): return utils.get(self.guild.text_channels, name="📺self-promotion")

    @property
    def weekly_giveaway_channel(self): return utils.get(self.guild.text_channels, name="🎉weekly-giveaways")

    async def skybies_log_embed(self, member, count, start_of_title, reason=None):
        skybies_logs_channel = utils.get(self.guild.text_channels, name="🌟skybies-logs")
        skybies_embed = Embed(
            title=f"{start_of_title} {count} Skybies",
            description=reason,
            colour=Colour.blue()
        ).set_footer(
            text="!skybie | !skybie @user | !skybie leaderboard | !skybie shop | !help skybies"
        )
        if member.avatar:
            skybies_embed.set_thumbnail(url=member.avatar.url)
        await skybies_logs_channel.send(embed=skybies_embed)

    async def give_skybies(self, member, count, reason=None):
        if reason:
            await self.skybies_log_embed(member, count, "Give", reason)
        stats = await skybiedb.find_one({"member_id": member.id})
        if stats is None:
            new_member = {"member_id": member.id, "skybies": count, "lifetime_skybies": count}
            await skybiedb.insert_one(new_member)
        else:
            new_skybies_count = stats["skybies"] + count
            await skybiedb.update_one({"member_id": member.id}, {"$set": {"skybies": new_skybies_count}})
            new_lifetime_skybies_count = stats["lifetime_skybies"] + count
            await skybiedb.update_one({"member_id": member.id},
                                      {"$set": {"lifetime_skybies": new_lifetime_skybies_count}})

    async def take_skybies(self, member, count, reason=None):
        if reason:
            await self.skybies_log_embed(member, count, "Took", reason)
        stats = await skybiedb.find_one({"member_id": member.id})
        if stats is None:
            newuser = {"member_id": member.id, "skybies": abs(count)}
            await skybiedb.insert_one(newuser)
        else:
            new_skybies_count = stats["skybies"] - count
            await skybiedb.update_one({"member_id": member.id}, {"$set": {"skybies": new_skybies_count}})

    async def get_top_skybies(self):
        rankings = skybiedb.find().sort("lifetime_skybies", -1)
        return [x async for x in rankings]

    async def get_skybies(self, member):
        stats = await skybiedb.find_one({"member_id": member.id})
        if stats is None:
            return 0, 0
        else:
            return stats["skybies"], stats["lifetime_skybies"]

    async def skybies_stats_embed(self, member, self_lookup):
        lookup_member = member
        activity_streak_cog = self.client.get_cog("ActivityStreak")
        current_streak = await activity_streak_cog.get_data(lookup_member, "current_streak")
        best_streak = await activity_streak_cog.get_data(lookup_member, "best_streak")
        last_active_date = await activity_streak_cog.get_data(lookup_member, "last_active_date")
        next_day = (
            last_active_date + timedelta(hours=23, minutes=30)
            if last_active_date
            else datetime.utcnow()
        )
        your = "Your" if self_lookup else "Their"
        you = "You" if self_lookup else "They"
        plural = lambda num: "s" * (num != 1)
        streak = (
            f"{your} current activity streak is {current_streak} day{plural(current_streak)}, and {your.lower()} best "
            f"ever streak is {best_streak} day{plural(best_streak)}."
        )
        if current_streak == best_streak:
            streak = f"{your} current and best ever streak is {current_streak} day{plural(current_streak)}!!!"
        thats_in = next_day - datetime.utcnow()
        thats_in_msg = f"{thats_in.total_seconds()} seconds"
        if thats_in < timedelta(seconds=0):
            thats_in_msg = "the past!"
        elif thats_in > timedelta(hours=1):
            thats_in_msg = f"{thats_in // timedelta(hours=1)} hours"
        elif thats_in > timedelta(minutes=1):
            thats_in_msg = f"{thats_in // timedelta(minutes=1)} minutes"
        streak = (
            f"{streak}\n*To maintain {your.lower()} streak be sure to send a message sometime around "
            f"<t:{int(next_day.replace(tzinfo=timezone.utc).timestamp())}:t>. That's in approximately {thats_in_msg}.*")

        skybies, lifetime_skybies = await self.get_skybies(lookup_member)
        skybies_stats_embed = Embed(
            title="Skybies stats",
            description=f"{lookup_member.mention} have {lifetime_skybies} lifetime skybies and {int(skybies)} skybies",
            colour=0x007bff
        )
        skybies_stats_embed.add_field(
            name="Activity Streak",
            value=streak
        )
        purchaseable_roles = [self.sky_promoter, self.master_of_disguise, self.angel, self.skybies_baiter, self.weekly_giveaway]
        if any([role for role in lookup_member.roles if role in purchaseable_roles]):
            skybies_stats_embed.add_field(
                name="Skybies role purchases",
                value=f"Roles that {you.lower()} have purchased 😊\n"
                      f"{'Thanks for supporting the server!!!' if self_lookup else 'Learn more skybies purchases in `!skybies shop`'}",
                inline=False
            )

        if self.weekly_giveaway in lookup_member.roles:
            skybies_stats_embed.add_field(
                name="📅 Weekly giveaway 📅",
                value=(
                    "*5 skybies for a one time ticket!*\n"
                    "With 5 skybies, you can join the weekly giveaway, where you can win up to 20mil coins!"
                ),
                inline=False
            )

        if self.sky_promoter in lookup_member.roles:
            skybies_stats_embed.add_field(
                name="📢 Sky Promoter 📢",
                value=(
                    "*30 Skybies to purchase*\n"
                    f"Sky promoters have bought deep connections from Seraphine to access "
                    f"{self.self_promotion_channel.mention}"
                    f"\nWith that, they got to promote their own goals with the price of skybies in that channel."
                ),
                inline=False
            )

        if self.master_of_disguise in lookup_member.roles:
            skybies_stats_embed.add_field(
                name="🥸 Master of disguise 🥸",
                value=(
                    "*50 skybies to purchase*\n"
                    "Master of disguise have mastered the ancient craft of shape shifting,\n"
                    "They can pretend to be anyone with the `!pr (@user or id) (message)` command"
                ),
                inline=False
            )

        if self.angel in lookup_member.roles:
            skybies_stats_embed.add_field(
                name="😎 Angels 😎",
                value=(
                    "*70 Skybies to purchase*\n"
                    "Angles are the cool people in skyhub.\n"
                    "They have their own private channel where they can talk cool stuff to each other"
                ),
                inline=False
            )
        if self.skybies_baiter in lookup_member.roles:
            skybies_stats_embed.add_field(
                name="🤑 Skybies baiter 🤑",
                value=(
                    "*Takes 100 skybies to bribe Seraphine*\n"
                    "With 100 skybies, you manage to bribe Seraphine to let you enter giftaways twice, as that's her"
                    "annual salary."
                ),
                inline=False
            )

        skybies_stats_embed.set_thumbnail(url="https://i.imgur.com/wVQj5O1.jpg")
        skybies_stats_embed.set_footer(
            text="!skybie | !skybie @user | !skybie leaderboard | !skybie shop | !help skybies")
        return skybies_stats_embed

    async def leaderboard_embed(self, requester):
        rankings = await self.get_top_skybies()
        leaderboard_list = []
        indexes = ["🥇", "🥈", "🥉", *(f"{count}." for count in range(4, 11))]
        for count, x in zip(indexes, rankings):
            member = requester.guild.get_member(x['member_id'])
            if member and member.id == requester.id:
                leaderboard_list.append(
                    f"**{count}{member.display_name} has {x['lifetime_skybies']} lifetime skybies**"
                )
            else:
                leaderboard_list.append(
                    f"{count}{member.display_name if member else 'Unknown'} has {x['lifetime_skybies']} lifetime skybies"
                )
        rank = 0
        skybies_count = 0
        for x in rankings:
            rank += 1
            if requester.id == x["member_id"]:
                skybies_count = x["lifetime_skybies"]
                break
        if rank > 10:
            leaderboard_list.append("...")
            leaderboard_list.append(f"**{rank}.You have {skybies_count} lifetime skybies**")

        skybies_leaderboard_embed = Embed(
            title="Skybies Leaderboard",
            description="\n".join(leaderboard_list),
            colour=0x007bff
        ).set_thumbnail(
            url="https://i.imgur.com/wVQj5O1.jpg"
        ).set_footer(
            text="!skybie | !skybie @user | !skybie leaderboard | !skybie shop | !help skybies"
        )
        return skybies_leaderboard_embed

    async def skybies_shop_embed(self):
        skybies_shop_embed = Embed(
            title="Skybies shop",
            description=(
                "🤩 You can purchase items with skybies 🤩\n"
                "Don't worry for your skybies leaderboard positon, as your lifetime skybies won't be deducted.\n"
                "Currently I only sells 5 items, which is explained below!"
            ),
            colour=0x007bff
        ).add_field(
            name="📅 Weekly giveaway 📅",
            value=(
                f"For 5 skybies, you will be given a one time ticket to participate in the weekly giveaway in "
                f"{self.weekly_giveaway_channel.mention}!\n"
                f"Purchase it with:\n"
                f"`!skybies shop weekly_giveaway`"
            ),
        ).add_field(
            name="📢 Sky Promoter 📢",
            value=(
                f"For 30 skybies, I will grant you access to the {self.self_promotion_channel.mention} channel\n"
                f"Purchase it with:\n"
                f"`!skybies shop sky_promoter`"
            ),
            inline=False
        ).add_field(
            name="🥸 Master of disguise 🥸",
            value=(
                f"For 50 skybies, I will sell you the {self.master_of_disguise.mention} role\n"
                f"You will be able to access the `!pr (@user or id) (message)` command, "
                f"allowing you to disguise as that person and send a message.\n"
                f"Purchase it with:\n"
                f"`!skybie shop master_of_disguise`"
            ),
            inline=False
        ).add_field(
            name="😎 Angels 😎",
            value=(
                f"For 70 skybies, I will sell you the {self.angel.mention} role\n"
                f"You will be able to access {self.angel_channel.mention} channel and "
                f"be displayed separately from other members\n"
                f"Purchase it with:\n"
                f"`!skybies shop angel`"
            ),
            inline=False
        ).add_field(
            name="🤑 Skybies baiter 🤑",
            value=(
                f"For 100 skybies, I will sell my soul to you, and let you enter giftaway twice.\n"
                f"Purchase it with:\n"
                f"`!skybies shop skybies_baiter`"
            )
        ).set_footer(
            text="!skybie | !skybie @user | !skybie leaderboard | !skybie shop | !help skybies"
        )
        return skybies_shop_embed

    async def purchase_status_embed(self, reason, successful):
        colour = 0x4bb543 if successful else 0xff0033
        end_of_title = "successful!" if successful else "unsuccessful :("
        purchase_status_embed = Embed(
            title=f"Your item purchase is {end_of_title}",
            description=reason,
            colour=colour,
        ).set_thumbnail(
            url="https://i.imgur.com/wVQj5O1.jpg"
        ).set_footer(text="!skybie | !skybie @user | !skybie leaderboard | !skybie shop | !help skybies")
        return purchase_status_embed

    async def has_role(self, ctx, role):
        if role in ctx.author.roles:
            return True

    async def role_purchase_handler(self, ctx, item):
        roles_and_pivilages = {
            "angel": {
                "role": self.angel,
                "privilege": f"you now unlocked the {self.angel_channel.mention} channel,\n"
                             f"and be displayed separately from other members"
            },
            "sky_promoter": {
                "role": self.sky_promoter,
                "privilege": f"you now unlocked the {self.self_promotion_channel.mention} channel,\n"
                             f"and be able to send ads in that channel"
            },
            "master_of_disguise": {
                "role": self.master_of_disguise,
                "privilege": f"you will now be able to use the `!pr (@member or id) (message)` command!\n"
                             f"To be able to disguise as that member"
            },
            "skybies_baiter": {
                "role": self.skybies_baiter,
                "privilege": f"you will now be able to enter giftaways twice!"
            },
            "weekly_giveaway": {
                "role": self.weekly_giveaway,
                "privilege": f"you will now be able to enter weekly giftaways in{self.weekly_giveaway_channel.mention}!"
            }
        }
        role = roles_and_pivilages[item]["role"]
        privilege = roles_and_pivilages[item]["privilege"]
        skybie_cost = self.item_cost[item]
        skybies_aquired, _ = await self.get_skybies(ctx.author)
        if await self.has_role(ctx, role):
            purchase_description = (
                f"You already have the {role.mention} role, why do you want to buy it again?"
            )
            successful = False
        elif (skybies_aquired - skybie_cost) < 0:
            purchase_description = (
                f"You cannot afford the {role.mention} role, you only have {int(skybies_aquired)} skybies\n"
                f"You need {skybie_cost} to purchase the {role.mention} role"
            )
            successful = False
        else:
            await self.take_skybies(ctx.author, skybie_cost, f"{ctx.author.mention} bought the {role.mention} role")
            await ctx.author.add_roles(role)
            purchase_description = (
                f"You have purchased the {role.mention} role, {privilege}\n"
                f"You now have {int(skybies_aquired - skybie_cost)} skybies left"
            )
            successful = True
        purchase_embed = await self.purchase_status_embed(purchase_description, successful)
        await ctx.send(embed=purchase_embed)

    @commands.group(aliases=["skybie", "s"], invoke_without_command=True)
    async def skybies(self, ctx, member: Member = None):
        if ctx.channel.id != self.seraphine_commands.id and not ctx.author.guild_permissions.administrator:
            await ctx.send(f"Use this command in the {self.seraphine_commands.mention} channel", delete_after=10)
            return

        if ctx.invoked_subcommand is None:
            if not member:
                member = ctx.author
            await ctx.send(embed=await self.skybies_stats_embed(member, True))

    @skybies.error
    async def skybies_error(self, ctx, error):
        if isinstance(error, commands.MemberNotFound):
            option_not_exist_embed = Embed(
                title="Skybie command or member don't exist",
                description="Do `!help skybie` to get a list of skybie commands",
                colour=0xff0033
            ).set_footer(
                text="!skybie | !skybie @user | !skybie leaderboard | !skybie shop | !help skybies"
            )
            await ctx.send(embed=option_not_exist_embed)

    @skybies.command(name="leaderboard", aliases=['l', 'lb'])
    async def skybies_leaderboard(self, ctx):
        if ctx.channel.id != self.seraphine_commands.id and not ctx.author.guild_permissions.administrator:
            await ctx.send(f"Use this command in the {self.seraphine_commands.mention} channel", delete_after=10)
            return
        leaderboard_embed = await self.leaderboard_embed(ctx.author)
        await ctx.send(embed=leaderboard_embed)

    @commands.cooldown(1, 1, commands.BucketType.user)
    @skybies.command(name="shop", aliases=['s', 'sh', 'store'])
    async def skybies_shop(self, ctx, item=None):
        if ctx.channel.id != self.seraphine_commands.id and not ctx.author.guild_permissions.administrator:
            await ctx.send(f"Use this command in the {self.seraphine_commands.mention} channel", delete_after=10)
            return
        if not item:
            skybie_shop_embed = await self.skybies_shop_embed()
            await ctx.send(embed=skybie_shop_embed)

        if item and item not in self.item_cost:
            item_do_not_exist_embed = await self.purchase_status_embed(
                reason=(
                    "I don't sell the item you are requesting,\n"
                    "Do `!skybies shop` to see what items you can purchase from me"
                ),
                successful=False
            )
            await ctx.send(embed=item_do_not_exist_embed)

        if item and item in self.item_cost:
            await self.role_purchase_handler(ctx, item)

    @skybies_shop.error
    async def skybie_shop_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(
                self.purchase_status_embed(
                    reason="You are on cooldown, please wait 1 second before trying to purchase again",
                    successful=False
                )
            )

async def setup(client):
    await client.add_cog(Skybies(client))
