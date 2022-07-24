import os
from datetime import datetime, timedelta, timezone
from random import uniform

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from nextcord import utils, Embed, Colour, Member
from nextcord.ext import commands

load_dotenv()
cluster = AsyncIOMotorClient(os.getenv("MongoDbSecretKey"))
skybiedb = cluster["Skyhub"]["Skybies"]
giftcards_db = cluster["Skyhub"]["Giftcards"]


class Skybies(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.item_cost = {
            "angel": 70,
            "sky_promoter": 30,
            "master_of_disguise": 50,
            "greater_giftcard": 40,
            "lesser_giftcard": 20
        }

    async def _skybies_log_embed(self, member, count, start_of_title, reason=None):
        skybies_embed = Embed(
            title=f"{start_of_title} {count} Skybies",
            description=reason,
            colour=Colour.blue()
        ).set_footer(
            text="!skybie | !skybie @user | !skybie leaderboard | !skybie shop | !help skybies"
        )
        if member.avatar:
            skybies_embed.set_thumbnail(url=member.avatar.url)
        await self.skybies_logs_channel.send(embed=skybies_embed)

    async def _give_skybies(self, member, count, reason=None):
        if reason:
            await self._skybies_log_embed(member, count, "Give", reason)
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

    async def _take_skybies(self, member, count, reason=None):
        if reason:
            await self._skybies_log_embed(member, count, "Took", reason)
        stats = await skybiedb.find_one({"member_id": member.id})
        if stats is None:
            newuser = {"member_id": member.id, "skybies": abs(count)}
            await skybiedb.insert_one(newuser)
        else:
            new_skybies_count = stats["skybies"] - count
            await skybiedb.update_one({"member_id": member.id}, {"$set": {"skybies": new_skybies_count}})

    async def _get_top_skybies(self):
        rankings = skybiedb.find().sort("lifetime_skybies", -1)
        return [x async for x in rankings]

    async def _get_skybies(self, member):
        stats = await skybiedb.find_one({"member_id": member.id})
        if stats is None:
            return 0, 0
        else:
            return stats["skybies"], stats["lifetime_skybies"]

    async def _skybies_stats_embed(self, member, self_lookup):
        lookup_member = member
        current_streak = await self.activitystreak._get_data(lookup_member, "current_streak")
        best_streak = await self.activitystreak._get_data(lookup_member, "best_streak")
        last_active_date = await self.activitystreak._get_data(lookup_member, "last_active_date")
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

        skybies, lifetime_skybies = await self._get_skybies(lookup_member)
        skybies_stats_embed = Embed(
            title="Skybies stats",
            description=f"{lookup_member.mention} have {lifetime_skybies} lifetime skybies and {skybies} skybies",
            colour=0x007bff
        )
        skybies_stats_embed.add_field(
            name="Activity Streak",
            value=streak
        )
        if self.angel in lookup_member.roles:
            skybies_stats_embed.add_field(
                name="Skybies role purchases",
                value=f"Roles that {you.lower()} have purchased 😊\n"
                      f"{'Thanks for supporting the server!!!' if self_lookup else 'Learn more skybies purchases in `!skybies shop`'}",
                inline=False
            )
        if self.master_of_disguise in lookup_member.roles:
            skybies_stats_embed.add_field(
                name="🥸 Master of disguise 🥸",
                value=(
                    "*30 skybies to purchase*\n"
                    "Master if disguise have mastered the ancient craft of shapeshift,\n"
                    "They can pretend to be anyone with the `!pr (@user or id) (message)` command"
                ),
                inline=False
            )
        if self.sky_promoter in lookup_member.roles:
            skybies_stats_embed.add_field(
                name="📢 Sky Promoter 📢",
                value=(
                    "*50 Skybies to purchase*\n"
                    f"Sky promoters have deep connection that allows them access {self.self_promotion_channel.mention}\n"
                    "With that, they decided to promote their own goals in that channel."
                ),
                inline=False
            )
        if self.angel in lookup_member.roles:
            skybies_stats_embed.add_field(
                name="😎 Angels 😎",
                value=(
                    "*70 Skybies to purchase*\n"
                    "Angles are the cool people in the server.\n"
                    "They have their own private channel where they can talk cool stuff to each other"
                ),
                inline=False
            )

        skybies_stats_embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/669941420454576131.png?v=1")
        skybies_stats_embed.set_footer(
            text="!skybie | !skybie @user | !skybie leaderboard | !skybie shop | !help skybies")
        return skybies_stats_embed

    async def _leaderboard_embed(self, requester):
        rankings = await self._get_top_skybies()
        leaderboard_list = []
        indexes = ["🥇", "🥈", "🥉", *(f"{count}." for count in range(4, 11))]
        for count, x in zip(indexes, rankings):
            member = self.guild.get_member(x['member_id'])
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
            url="https://cdn.discordapp.com/emojis/669941420454576131.png?v=1"
        ).set_footer(
            text="!skybie | !skybie @user | !skybie leaderboard | !skybie shop | !help skybies"
        )
        return skybies_leaderboard_embed

    async def _skybies_shop_embed(self):
        skybies_shop_embed = Embed(
            title="Skybies shop",
            description=(
                "🤩 You can purchase items with skybies 🤩\n"
                "Don't worry for your skybies leaderboard positon, as your lifetime skybies won't be deducted.\n"
                "Currently I only sells 5 items, which is explained below!"
            ),
            colour=0x007bff
        ).add_field(
            name="Lesser giftcard",
            value=(
                "For 20 skybies, I will sell you a giftcard that contains 0m to 1m skyblock coins\n"
                f"Open a ticket in {self.ticket_channel.mention} to claim your coins\n"
                "Purchase it with:\n"
                "`!skybies shop lesser_giftcard`"
            ),
            inline=False
        ).add_field(
            name="Greater giftcard",
            value=(
                "For 40 skybies, I will sell you an giftcard that contains 500k to 2m skyblock coins\n"
                f"Open a ticket in {self.ticket_channel.mention} to claim your coins\n"
                "Purchase it with:\n"
                "`!skybies shop greater_giftcard`"
            ),
            inline=False
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
                f"You will be able to access the `pr (@user or id) (message)` command,"
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
        )
        return skybies_shop_embed

    async def _purchase_status_embed(self, reason, successful):
        colour = 0x4bb543 if successful else 0xff0033
        end_of_title = "successful!" if successful else "unsuccessful :("
        purchase_status_embed = Embed(
            title=f"Your item purchase is {end_of_title}",
            description=reason,
            colour=colour,
        ).set_thumbnail(
            url="https://cdn.discordapp.com/attachments/850019796014858280/991334099161727016/skybies.jpg"
        ).set_footer(text="!skybie | !skybie @user | !skybie leaderboard | !skybie shop | !help skybies")
        return purchase_status_embed

    async def _roll_sb_coins(self, type):
        upper_bound = 2 if type == "greater" else 1.0
        lower_bound = 0.5 if type == "greater" else 0.0
        return round(uniform(lower_bound, upper_bound), 2)

    async def _giftcards_generator(self, member, type):
        coins = await self._roll_sb_coins(type)
        new_giftcard = {"member_id": member.id, "coins": coins, "type": type}
        await giftcards_db.insert_one(new_giftcard)
        return coins

    async def _giftcard_handler(self, ctx, type):
        skybie_cost = self.item_cost[f"{type}_giftcard"]
        skybies_aquired, _ = await self._get_skybies(ctx.author)
        if (skybies_aquired - skybie_cost) < 0:
            purchase_description = (
                f"You cannot afford a {type} giftcard, you only have {skybies_aquired} skybies,\n"
                f"You need {skybie_cost} skybies to purchase a {type} giftcard"
            )
            successful = False
        else:
            await self._take_skybies(ctx.author, skybie_cost, f"{ctx.author.mention} brought a {type} giftcard!")
            coins = await self._giftcards_generator(ctx.author, type)
            purchase_description = (
                f"You have purchased a {type} giftcard, it contains **{coins}m** sb coins\n"
                f"You have {skybies_aquired - skybie_cost} skybies left, do !giftcard to check your unredeemed giftcards\n"
                f"Open a ticket at {self.ticket_channel.mention} to redeem your giftcards"
            )
            successful = True
        purchase_embed = await self._purchase_status_embed(purchase_description, successful)
        await ctx.send(embed=purchase_embed)

    async def _has_role(self, ctx, role):
        if role in ctx.author.roles:
            return True

    async def _role_purchase_handler(self, ctx, item):
        roles_and_pivilages = {
            "angel": {
                "role": self.angel,
                "privilege": f"you now unlocked the {self.angel_channel.mention} channel,\n"
                             f"and be displayed separately from other members"
            },
            "sky_promoter": {
                "role": self.sky_promoter,
                "privilege": f"you now unlocked the {self.self_promotion_channel} channel,\n"
                             f"and be able to send ads in that channel"
            },
            "master_of_disguise": {
                "role": self.master_of_disguise,
                "privilege": f"you will now be able to use the `!pr (@member or id) (message)` command!\n"
                             f"To be able to disguise as that member"
            }
        }
        role = roles_and_pivilages[item]["role"]
        privilege = roles_and_pivilages[item]["privilege"]
        skybie_cost = self.item_cost[item]
        skybies_aquired, _ = await self._get_skybies(ctx.author)
        if await self._has_role(ctx, role):
            purchase_description = (
                f"You already have the {role.mention} role, why do you want to buy it again?"
            )
            successful = False
        elif (skybies_aquired - skybie_cost) < 0:
            purchase_description = (
                f"You cannot afford the {role.mention} role, you only have {skybies_aquired} skybies"
                f"You need {skybie_cost} to purchase the {role.mention} role"
            )
            successful = False
        else:
            await self._take_skybies(ctx.author, skybie_cost, f"{ctx.author.mention} brought the {role.mention} role")
            await ctx.author.add_roles(role)
            purchase_description = (
                f"You have purchased the {role.mention} role, {privilege}\n"
                f"You now have {skybies_aquired - skybie_cost} skybies left"
            )
            successful = True
        purchase_embed = await self._purchase_status_embed(purchase_description, successful)
        await ctx.send(embed=purchase_embed)

    @commands.group(aliases=["skybie", "s"], invoke_without_command=True)
    async def skybies(self, ctx, member: Member = None):
        if ctx.invoked_subcommand is None:
            if ctx.channel.id != self.seraphine_commands.id and not ctx.author.guild_permissions.administrator:
                await ctx.send(f"Use this command in the {self.seraphine_commands.mention} channel", delete_after=10)

            if not member:
                member = ctx.author
            await ctx.send(embed=await self._skybies_stats_embed(member, True))

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
        leaderboard_embed = await self._leaderboard_embed(ctx.author)
        await ctx.send(embed=leaderboard_embed)

    @commands.cooldown(1, 1, commands.BucketType.user)
    @skybies.command(name="shop", aliases=['s', 'sh', 'store'])
    async def skybies_shop(self, ctx, item=None):
        if ctx.channel.id != self.seraphine_commands.id and not ctx.author.guild_permissions.administrator:
            await ctx.send(f"Use this command in the {self.seraphine_commands.mention} channel", delete_after=10)
        if not item:
            skybie_shop_embed = await self._skybies_shop_embed()
            await ctx.send(embed=skybie_shop_embed)

        if item and item not in self.item_cost:
            item_do_not_exist_embed = await self._purchase_status_embed(
                reason=(
                    "I don't sell the item you are requesting,\n"
                    "Do `!skybies shop` to see what items you can purchase from me"
                ),
                successful=False
            )
            await ctx.send(embed=item_do_not_exist_embed)

        if item and item in self.item_cost:
            item = item.casefold().strip()
            if "giftcard" in item:
                type = item.split("_")[0]
                if type == "lesser" or type == "greater":
                    await self._giftcard_handler(ctx, type)
            if "angel" in item or "sky_promoter" in item or "master_of_disguise" in item:
                await self._role_purchase_handler(ctx, item)

    @skybies_shop.error
    async def skybie_shop_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(
                self._purchase_status_embed(
                    reason="You are on cooldown, please wait 1 second before trying to purchase again",
                    successful=False
                )
            )

    async def _giftcards_embed(self, giftcard_list):
        if giftcard_list:
            colour = 0xf4e98c
            title = "You have unredeemed giftcards"
            description = (
                f"Open a ticket at {self.ticket_channel.mention}to redeem your giftcards,\n"
                f" all your giftcards will be redeemed at once as a staff member redeems your giftcards"
            )
        else:
            colour = 0xf942a
            title = "You do not have any unredeemed giftcards"
            description = (
                "You can buy giftcards containing skyblock coins with skybies,\n "
                "do `!skybies shop` to learn more"
            )
        giftcards_embed = Embed(
            title=title,
            description=description,
            colour=colour,
        ).set_thumbnail(
            url="https://cdn.discordapp.com/attachments/850019796014858280/991724049422098472/red_gift.png"
        ).set_footer(
            text="!skybie | !skybie @user | !skybie leaderboard | !skybie shop | !help skybies"
        )
        if giftcard_list:
            giftcards_embed.add_field(
                name="Your unredeemed giftcards",
                value="\n".join(giftcard_list),
            )
        return giftcards_embed

    @commands.command(aliases=["giftcard"])
    async def giftcards(self, ctx, member: Member = None):
        if ctx.channel.id != self.seraphine_commands.id and not ctx.author.guild_permissions.administrator:
            await ctx.send(f"Use this command in the {self.seraphine_commands.mention} channel", delete_after=10)
            return

        if not member:
            member = ctx.author
        cursor = giftcards_db.find(({"member_id": member.id}))
        giftcard_list = []
        async for insert in cursor:
            giftcard_list.append(f"{insert['type']} giftcard: containing {insert['coins']}m coins")
        giftcard_embed = await self._giftcards_embed(giftcard_list)
        await ctx.send(embed=giftcard_embed)

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def redeem(self, ctx, member: Member):
        member_id = member.id
        cursor = giftcards_db.find(({"member_id": member_id}))
        total_coins_in_minion = 0.0
        num_giftcards = 0
        async for insert in cursor:
            total_coins_in_minion += insert["coins"]
            num_giftcards += 1
            await giftcards_db.delete_one(insert)

        title = f"{member.display_name} have redeemed {num_giftcards} giftcard"
        colour = 0xf4e98c
        description = (
            f"All giftcards of {member.mention} is redeemed,\n"
            f"totaling {total_coins_in_minion}m worth of skyblock coins.\n"
            f"🔫 now give them their coins 🔫"
        )

        if not total_coins_in_minion:
            title = f"{member.display_name} have no unredeemed giftcards"
            colour = 0xf942a
            description = (
                "This member have no giftcards to redeem,"
                "You are bamboozled"
            )
        redeem_embed = Embed(
            title=title,
            description=description,
            colour=colour
        ).set_thumbnail(
            url="https://cdn.discordapp.com/attachments/850019796014858280/992017061083631687/unknown.png"
        )
        await ctx.send(embed=redeem_embed)

    @redeem.error
    async def redeem_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("you need to be an staff member to use this command", delete_after=10)
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("It is !redeem (@member) (1 or -1)", delete_after=10)

    @commands.Cog.listener()
    async def on_ready(self):
        self.guild = self.client.get_guild(844231449014960160)

        self.angel = utils.get(self.guild.roles, name="😎Angels😎")
        self.sky_promoter = utils.get(self.guild.roles, name="📢Sky Promoter📢")
        self.master_of_disguise = utils.get(self.guild.roles, name="🥸master of disguise🥸")

        self.seraphine_commands = utils.get(self.guild.text_channels, name="👩seraphine-commands")
        self.ticket_channel = self.angel_channel = utils.get(self.guild.text_channels, name="🎫make-a-ticket")
        self.angel_channel = utils.get(self.guild.text_channels, name="😎angels-chat")
        self.skybies_logs_channel = utils.get(self.guild.text_channels, name="🌟skybies-logs")
        self.self_promotion_channel = utils.get(self.guild.text_channels, name="📺self-promotion")
        self.activitystreak = self.client.get_cog("ActivityStreak")


def setup(client):
    client.add_cog(Skybies(client))
