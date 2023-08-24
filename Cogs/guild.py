from os import getenv
from aiohttp import ClientSession

from discord import utils, Embed
from discord.ext import commands, tasks
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

cluster = AsyncIOMotorClient(getenv("MongoDbSecretKey"))
verification_db = cluster["Skyhub"]["Verification"]
load_dotenv()


class Guild(commands.Cog):
    def __init__(self, client):
        self.client = client

    @property
    def guild(self):
        return self.client.get_guild(int(getenv("GUILD_ID")))

    @property
    def gexp_threshold_roles(self):
        return {
            20000: utils.get(self.guild.roles, name="Barely playing (20k gxp)"),
            50000: utils.get(self.guild.roles, name="Casual (50k gxp)"),
            100000: utils.get(self.guild.roles, name="Active (100k gxp)"),
            200000: utils.get(self.guild.roles, name="Hyper active (200k gxp)"),
            400000: utils.get(self.guild.roles, name="Sweaty (400k gxp)"),
        }

    @property
    def guild_logging_channel(self):
        return utils.get(self.guild.text_channels, name="📜guild-logs")

    async def get_guild_info(self):
        async with ClientSession() as session:
            async with session.get(
                    'https://api.hypixel.net/guild?name=Skyhub Official',
                    headers={"API-Key": getenv("HYPIXEL_API_KEY")},
            ) as response:
                if response.status == 200:
                    return await response.json()

    async def get_uuid_and_name_from_member(self, member):
        member_minecraft_info_insert = await verification_db.find_one({"discord_id": member.id})
        if member_minecraft_info_insert:
            uuid = member_minecraft_info_insert["uuid"]
            ign = member_minecraft_info_insert["ign"]
            return uuid, ign
        return None, None

    async def calculate_member_gexp(self, member, guild_info):
        uuid, ign = await self.get_uuid_and_name_from_member(member)
        if uuid:
            guild_members = guild_info["guild"]["members"]
            for guild_member in guild_members: # need to check if member in guild
                if guild_member["uuid"] == uuid:
                    return True, sum(guild_member["expHistory"].values())
            return False, f"**{member.display_name}** with uuid:`{uuid}` and ign:`{ign}` is not in guild."
        return False, f"**{member.display_name}** is not in the verification database."

    @tasks.loop(hours=1)
    async def update_gexp_roles(self):
        guild_info = await self.get_guild_info()
        if not guild_info:
            return await self.guild_logging_channel.send(
                embed=Embed(
                    description="Failed to get guild info from hypixel api.",
                    colour=0xff0033
                )
            )
        member_statuses = []
        failed_statuses = []
        guild_member_role = utils.get(self.guild.roles, name="Guild Member")
        for member in self.guild.members:
            if guild_member_role not in member.roles:
                continue
            successful, information = await self.calculate_member_gexp(member, guild_info)
            if successful:
                current_roles = member.roles
                highest_role = None
                for exp_threshold, role in self.gexp_threshold_roles.items():
                    if information >= exp_threshold:
                        highest_role = role
                    elif role in current_roles:
                        await member.remove_roles(role)
                if highest_role is None:
                    member_statuses.append(
                        (f"**{member.display_name}** literally only got `{information}` gexp in 7 days.", information))
                if highest_role is not None:
                    await member.add_roles(highest_role)
                    member_statuses.append(
                        (
                            f"**{member.display_name}** got `{information}` gexp unlocking the role {highest_role.mention}.",
                            information
                        )
                    )
            else:
                failed_statuses.append(information)
        sorted_member_statuses = sorted(member_statuses, key=lambda x: x[1], reverse=True)
        member_statues = [status[0] for status in sorted_member_statuses]

        member_status_logging_embed = Embed(
            title="Member status logging",
            description="I, Seraphine, has checked the gexp gain of everyone from the past 7 days!",
            colour=0x26457a
        )
        num_fields = 1
        member_status_chunks = []
        current_chunk = ""
        for status in member_statues:
            if len(current_chunk) + len(status) > 1024:  # Discord embed field character limit
                member_status_chunks.append(current_chunk)
                current_chunk = ""
                num_fields += 1
            current_chunk += f"\n{status}"
        member_status_chunks.append(current_chunk)

        # Add the member statuses to multiple fields in the embed
        for i, chunk in enumerate(member_status_chunks):
            if i == 0:
                member_status_logging_embed.add_field(
                    name="Skyhub gexp status:",
                    value=f"{chunk}",
                    inline=False
                )
            else:
                member_status_logging_embed.add_field(
                    name=f"continued",
                    value=f"{chunk}",
                    inline=False
                )

        if failed_statuses:
            member_status_logging_embed.add_field(
                name="I couldn't get:",
                value="\n".join(failed_statuses),
                inline=False
            )
        await self.guild_logging_channel.send(embed=member_status_logging_embed)

    async def update_gxp_roles_starter(self):
        await self.client.wait_until_ready()
        await self.update_gexp_roles.start()

    async def cog_load(self):
        self.client.loop.create_task(self.update_gxp_roles_starter())


async def setup(client):
    await client.add_cog(Guild(client))
