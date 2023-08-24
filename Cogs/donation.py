from discord.ext import commands
from discord.utils import get
from discord import Member, AllowedMentions, Embed
from pymongo import DESCENDING
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from os import getenv
load_dotenv()

cluster = AsyncIOMotorClient(getenv("MongoDbSecretKey"))
donation_db = cluster["Skyhub"]["Donation"]
verification_db = cluster["Skyhub"]["Verification"]


class Donation(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.donation_roles = {
            10: "Novice(10m donated)",
            25: "Supporter(25m donated)",
            50: "Benefactor(50m donated)",
            100: "Magnate(100m donated)",
            250: "Mogul(250m donated)",
            500: "Tycoon(500m donated)",
            1000: "Baron(1b donated)",
            2500: "Legend(2.5b donated)",
            5000: "Demigod(5b donated)",
            10000: "God(10b+ donated)",
        }

    async def get_uuid_and_name_from_member(self, member):
        member_minecraft_info_insert = await verification_db.find_one({"discord_id": member.id})
        if member_minecraft_info_insert:
            uuid = member_minecraft_info_insert["uuid"]
            ign = member_minecraft_info_insert["ign"]
            return uuid, ign
        return None, None

    async def handle_donations(self, uuid, ign, amount):
        member_previous_donations = await donation_db.find_one({"uuid": uuid})
        previously_donated = 0
        if member_previous_donations:
            previously_donated = int(member_previous_donations["amount"])
            total_donated = previously_donated + amount
            await donation_db.update_one({"uuid": uuid}, {"$set": {"amount": total_donated}})
        else:
            total_donated = amount
            await donation_db.insert_one({"uuid": uuid, "ign": ign, "amount": amount})

        return previously_donated, total_donated

    async def get_top_donation_role(self, guild, amount):
        top_role = None
        for donation_amount, role_name in self.donation_roles.items():
            role = get(guild.roles, name=role_name)
            if role and amount >= donation_amount:
                top_role = role
            else:
                break
        return top_role

    async def get_next_donation_role_and_remaining(self, guild, amount):
        for donation_amount, donation_role_name in self.donation_roles.items():
            if amount < donation_amount:
                donation_role = get(guild.roles, name=donation_role_name)
                if donation_role:
                    remaining_amount = donation_amount - amount
                    return donation_role, remaining_amount
                else:
                    return None, None
        return None, None

    async def handle_donation_roles(self, member, amount):
        top_role = await self.get_top_donation_role(member.guild, amount)

        next_role, remaining_amount = await self.get_next_donation_role_and_remaining(member.guild, amount)
        for donation_role_name in self.donation_roles.values():
            donation_role = get(member.guild.roles, name=donation_role_name)
            if donation_role and donation_role != top_role and donation_role in member.roles:
                await member.remove_roles(donation_role)

        if next_role:
            remaining_amount_str = str(remaining_amount / 1000) + " bil" if remaining_amount > 1000 else str(
                remaining_amount) + " mil"

        amount_str = str(amount / 1000) + " bil" if amount > 1000 else str(amount) + " mil"
        donation_embed = Embed(
            title=f"🎉Thanks {member.display_name} for your donation🎉",
            description=f"{member.mention} has donated **{amount_str}** in total!\n",
            colour=0xffea6c
        )
        if not top_role:
            donation_embed.description += f"**{remaining_amount_str}** is needed to unlock the {next_role.mention} role."
            return False, None, None, False, None, donation_embed

        if top_role not in member.roles:
            await member.add_roles(top_role)
            if not next_role:
                donation_embed.description += f"They have unlocked the max donation role!"
                return True, top_role, next_role, True, None, donation_embed
            else:
                donation_embed.description += f"{remaining_amount_str} is needed to unlock the next role, {next_role.mention}!"
                return True, top_role, next_role, False, remaining_amount, donation_embed
        else:
            if not next_role:
                donation_embed.description += f"They already unlocked the max donation role!"
                return False, top_role, next_role, False, None, donation_embed
            else:
                donation_embed.description += f"{remaining_amount_str} is needed to unlock the {next_role.mention} role."
                return False, top_role, next_role, False, remaining_amount, donation_embed

    @commands.command(aliases=["donate"])
    @commands.has_permissions(administrator=True)
    async def donation(self, ctx, member: Member, amount: int, proof_link: str, *, donation_items: str):
        amount = int(amount)
        uuid, ign = await self.get_uuid_and_name_from_member(member)
        if not uuid:
            await ctx.send(f"{member.mention} is not in the verification database.")
            return
        previously_donated, total_donated = await self.handle_donations(uuid, ign, amount)
        unlocked, top_role, next_role, unlocked_max_role, remaining_amount, donation_embed = await self.handle_donation_roles(member, total_donated)

        give_away_contribution_channel = get(ctx.guild.channels, name="💸giveaway-contributions")
        if give_away_contribution_channel:
            previously_donated_str = str(previously_donated / 1000) + " bil" if previously_donated > 1000 else \
                str(previously_donated) + " mil"
            total_donated_str = str(total_donated / 1000) + " bil" if total_donated > 1000 else str(total_donated) + " mil"
            amount_str = str(amount / 1000) + " bil" if amount > 1000 else str(amount) + " mil"
            contribution_embed = Embed(
                title=f"🎉Thanks {member.display_name} for your donation🎉",
                description=f"{member.mention} donated **{donation_items}**, which is worth **{amount_str}**!\n"
                            f"Increasing their total donated amount from **{previously_donated_str}** to **{total_donated_str}**\n\n",
                colour=0xffea6c
            )
            if unlocked:
                if unlocked_max_role:
                    contribution_embed.description += f"**{member.mention} has unlocked the max donation role, " \
                                                      f"{top_role.mention}, becoming a 🔱god🔱**\n"
                else:
                    contribution_embed.description += f"**Unlocking the {top_role.mention} role!**\n"

            if next_role:
                remaining_amount_str = str(remaining_amount / 1000) + " bil" if remaining_amount > 1000 else str(
                    remaining_amount) + " mil"
                contribution_embed.description += f"**{remaining_amount_str}** is needed to unlock the {next_role.mention} role."

            contribution_embed.set_image(url=proof_link)
            contribution_prove_msg = await give_away_contribution_channel.send(embed=contribution_embed)
            donation_embed.description += f"\n[Click here to see your donation record!]({contribution_prove_msg.jump_url})"
            await ctx.send(embed=donation_embed, allowed_mentions=AllowedMentions.none())

    @donation.error
    async def donation_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.reply(
                "You need to be at least an admain to use this command",
                delete_after=10,
                mention_author=False
            )
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.reply(
                f" `{error.param}` is missing!\n"
                f"Please use the command like this:\n"
                f"```!donation (member:<@member><member><member#1234) "
                f"(amount:<123>) (proof_url:<image url>) (donation_items_names: <hyperion>)```",
                mention_author=False
            )
        elif isinstance(error, commands.BadArgument):
            await ctx.reply(
                f"Invalid argument in `{error.args}`\n"
                f"Please use the command like this:\n"
                f"```!donation (member:<@member><member><member#1234) "
                f"(amount:<123>) (proof_url:<image url>) (donation_items_names: <hyperion>)```",
                mention_author=False
            )
        else:
            print(error)
            await ctx.reply(
                f"Please use the command like this:\n"
                f"```!donation (member:<@member><member><member#1234) "
                f"(amount:<123>) (proof_url:<image url>) (donation_items_names: <hyperion>)```",
                mention_author=False
            )

    async def get_member_from_uuid(self, uuid):
        member_minecraft_info_insert = await verification_db.find_one({"uuid": uuid})
        if member_minecraft_info_insert:
            member = self.client.get_user(member_minecraft_info_insert["discord_id"])
            return member
        return None

    @commands.command(aliases=["dl"])
    async def donation_leaderboard(self, ctx):
        donation_cursor = donation_db.find({}).sort("amount", DESCENDING).limit(10)
        donation_leaderboard = []
        donation_list = await donation_cursor.to_list(length=10)
        for ranking, donation_document in enumerate(donation_list, start=1):
            member = await self.get_member_from_uuid(donation_document["uuid"])
            if member:
                name = member.display_name
            else:
                name = donation_document["ign"]
            donation_amount = donation_document["amount"]
            donation_str = str(donation_amount / 1000) + " bil" if donation_amount > 1000 else str(donation_amount) + " mil"
            donation_leaderboard.append(f"**{ranking}**. **{name}** - **{donation_str}**")

        donation_leaderboard_embed = Embed(
            title="Donation Leaderboard",
            description="The most generous people in the servers are bellow!\n"
                        "Helping to keep our server alive and running!\n",
            colour=0xffea6c
        )
        donation_leaderboard_embed.add_field(name="Top 10 Donators", value="\n".join(donation_leaderboard))
        await ctx.send(embed=donation_leaderboard_embed)


async def setup(client):
    await client.add_cog(Donation(client))


