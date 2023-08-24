from os import getenv
from random import choice
from aiohttp import ClientSession
from datetime import datetime, timezone
from minepi import name_to_uuid

from humanfriendly import format_timespan
from pymongo import DESCENDING
from motor.motor_asyncio import AsyncIOMotorClient
from discord import Embed, Interaction, ui, ButtonStyle, utils, AllowedMentions, Forbidden, Member
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()


cluster = AsyncIOMotorClient(getenv("MongoDbSecretKey"))
db = cluster["Skyhub"]
verification_db = db["Verification"]
previous_roles_db = db["Skyhub"]["PreviousRoles"]


async def check_and_add_previous_roles(member):
    have_previous_roles = await previous_roles_db.find_one(
        {"member_id": member.id},
        sort=[('$natural', DESCENDING)]
    )

    if not have_previous_roles:
        return

    async def add_previous_roles():
        previous_roles = have_previous_roles["roles"]
        for role_id in previous_roles:
            role = utils.get(member.guild.roles, id=role_id)
            if role:
                await member.add_roles(role)

    if have_previous_roles:
        await add_previous_roles()

        if member.display_name != have_previous_roles["display_name"]:
            await member.edit(nick=have_previous_roles["display_name"])

        await previous_roles_db.delete_many({"member_id": member.id})
        return True


async def log_verification_data(ign, uuid, member_id):
    await verification_db.insert_one(
        {
            "ign": ign,
            "uuid": uuid,
            "discord_id": member_id,
        }
    )


async def send_welcome_dm(member, rejoining: bool):
    if rejoining:
        explain_message = "rejoining skyhub, hope you enjoy your stay this time!"
    else:
        explain_message = "verifying in skyhub! this is to protect our members."

    welcome_embed = Embed(
        description="**Hii, I am Seraphine, the clerk in the community center!**\n"
                    f"Thanks for {explain_message}\n\n"
                    "My secret hobby is to chat with people who are Skyhub members, "
                    "feel free to chat with me right here in this dm channel! (I am an AI)\n\n"
                    "__Click the button below to start your journey in the skyhub!__",
        color=0x4bb543
    ).set_footer(
        text="Be aware that the skyhub staff team monitors messages send to Seraphine!"
    ).set_author(
        name="Welcome to Skyhub",
        icon_url=member.guild.icon.url
    ).set_thumbnail(
        url=member.guild.icon.url
    )
    try:
        await member.send(embed=welcome_embed, view=StartYourJourneyButton())
    except Forbidden:
        pass


class StartYourJourneyButton(ui.View):
    def __init__(self):
        super().__init__()
        url = "https://discord.gg/GjHSuuAuYB"
        self.add_item(ui.Button(label='Click me!', url=url))


class VerificationModal(ui.Modal):
    def __init__(self, cog, verification_method):
        super().__init__(
            title="Welcome to skyhub!",
            timeout=None,
        )
        self.cog = cog
        self.verification_method = verification_method
        self.welcome_message_templates = [
            "{} have docked in skyhub!",
            "The myth, the legend, {} is now in the skyhub!",
            "Roses are red, violets are blue, {} is now in the skyhub!",
            "The sky is falling, {} is now in skyhub!",
            "{} has landed in the skyhub!"
            "The prophecy has came true, {} is now in the skyhub!",
        ]
        self.user_detail_message = "Input your API key" if self.verification_method == "hypixel_api_key" else "Input your IGN"
        self.user_details = ui.TextInput(
            label=self.user_detail_message,
            min_length=2,
            max_length=50,
        )
        self.add_item(self.user_details)

    async def send_verification_status_embed(self, interaction: Interaction, successful: bool, ign=None, reason=None):
        if successful:
            verification_status_embed = Embed(
                description=f"You have been verified as **{ign}**, enjoy your stay!\n"
                            f"If you want to unverify, do `!unverify`",
                color=0x4bb543
            ).set_author(
                name=f"Verification successful",
            ).set_thumbnail(
                url=interaction.guild.icon.url
            )
        else:
            verification_status_embed = Embed(
                description=reason,
                color=0xff0033
            ).set_author(
                name="Verification failed",
            ).set_thumbnail(
                url=interaction.guild.icon.url
            )
        await interaction.response.send_message(embed=verification_status_embed, ephemeral=True)

    async def check_if_account_taken(self, interaction: Interaction, uuid: id, ign: str):
        mc_account = await verification_db.find_one({"uuid": uuid})
        if mc_account:
            member_id = mc_account["discord_id"]
            user = await interaction.client.fetch_user(member_id)
            if user:
                verification_help_channel = utils.get(interaction.guild.channels, name="❓verification-help")
                await self.send_verification_status_embed(
                    interaction,
                    False,
                    reason=f"This mc account `{ign}` is verified to `{user}`, please log into that discord account"
                           f" and do `!unverify` in order to verify with this discord account.\n"
                           f"If you have lost that account, please open a ticket in {verification_help_channel.mention}\n"
                           f"Be aware that if you just unverified, it may take up to 5 minutes everything to update."
                )
                return True
            if not user:
                await verification_db.delete_one(mc_account)

        return False

    async def verify(self, interaction: Interaction):
        member = interaction.user
        if self.verification_method == "hypixel_social_menu":
            ign = self.user_details.value
            uuid = await name_to_uuid(ign)
            async with ClientSession() as session:
                async with session.get(
                    f"https://api.hypixel.net/player?uuid={uuid}",
                    headers={"API-Key": getenv("HYPIXEL_API_KEY")},
                ) as hypixel_api_response:
                    if hypixel_api_response.status == 200:
                        hypixel_api_response = await hypixel_api_response.json()
                        linked_discord_tag = hypixel_api_response['player']["socialMedia"]["links"]["DISCORD"]
                        if not linked_discord_tag:
                            await self.send_verification_status_embed(
                                interaction,
                                False,
                                reason="Your hypixel profile is not linked to a discord account,"
                                       "please follow the instructions above to verify with hypixel social menu"
                            )
                        elif linked_discord_tag == str(member):
                            account_taken = await self.check_if_account_taken(interaction, uuid, ign)
                            if not account_taken:
                                await log_verification_data(ign, uuid, member.id)
                                await self.send_verification_status_embed(interaction, True, ign)
                                return ign
                        else:
                            await self.send_verification_status_embed(
                                interaction,
                                False,
                                reason=f"Your mc account is linked to {linked_discord_tag} instead of {str(member)}"
                            )
                    else:
                        await self.send_verification_status_embed(
                            interaction,
                            False,
                            reason=f"Hypixel api is not returning information of {self.user_details.value.strip()}"
                        )

    async def on_submit(self, interaction: Interaction) -> None:
        ign = await self.verify(interaction)
        member = interaction.user
        if ign:
            verifying_role = utils.get(interaction.guild.roles, name="Verifying")
            have_previous_roles = await check_and_add_previous_roles(member)
            is_rejoining = True

            if verifying_role in member.roles:
                await member.remove_roles(verifying_role)

            if not have_previous_roles:
                await member.add_roles(utils.get(interaction.guild.roles, name="Member"))
                welcome_channel = utils.get(interaction.guild.channels, name="👋🏻welcome")
                await welcome_channel.send(
                    choice(self.welcome_message_templates).format(member.mention),
                    allowed_mentions=AllowedMentions().none()
                )
                self.cog.unwelcomed_new_members.append(member.id)
                is_rejoining = False

            try:
                await send_welcome_dm(interaction.user, rejoining=is_rejoining)
            except Forbidden:
                pass
            if member.display_name != ign:
                await member.edit(nick=ign)

class VerificationButtons(ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @ui.button(label="Verify by social menu", style=ButtonStyle.blurple, custom_id='verification_buttons:social menu')
    async def verify_by_social_menu_button(self, interaction: Interaction, button: ui.Button):
        verification_modal = VerificationModal(self.cog, "hypixel_social_menu")
        await interaction.response.send_modal(verification_modal)

class JoinAndLeave(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.persistent_views_added = False
        self.persistent_modals_added = False
        self.verifying_welcome_message = False
        self.unwelcomed_new_members = []

    @property
    def guild(self):
        return self.client.get_guild(int(getenv("GUILD_ID")))

    @property
    def server_logs(self):
        return utils.get(self.guild.channels, name="👥server-logs")

    @property
    def verification_role(self):
        return utils.get(self.guild.roles, name="Verifying")

    async def pural(self, num):
        return "s" if num > 1 else ""

    async def check_if_verified(self, member):
        member = await verification_db.find_one(
            {
                "discord_id": member.id,
            }
        )
        return member

    async def find_same_invite_after_join(self, invite_list, invite_to_find):
        for invite in invite_list:
            if invite.code == invite_to_find:
                return invite

    async def invite_tracking(self, member, joined_before):
        invites_before_join = self.guild_invites
        invites_after_join = await member.guild.invites()
        used_invites = []
        same_invite_after_join = None
        for invite in invites_before_join:
            same_invite_after_join = await self.find_same_invite_after_join(invites_after_join, invite.code)
            if invite.uses < same_invite_after_join.uses:
                if member not in [x.inviter for x in used_invites]:
                    used_invites.append(invite)
                else:
                    continue
        if used_invites:
            creation_date = member.created_at
            now = datetime.now(timezone.utc)
            account_age = now - creation_date
            account_age_message = format_timespan(account_age, max_units=2)
            invite_description = "\n".join(
                [
                   f"Invite `{invite.code}` by {invite.inviter} and is used {same_invite_after_join.uses} time{await self.pural(same_invite_after_join.uses)}."
                   for invite in used_invites
                ]
            )
            member_invite_logging = Embed(
                description=f"{member.mention} {member}",
                color=0x4bb543
            ).add_field(
                name="Account age",
                value=account_age_message,
                inline=False
            ).add_field(
                name="Invite used by member",
                value=invite_description[:4096],
                inline=False
            ).set_author(
                url=member.avatar.url if member.avatar else member.default_avatar.url,
                name="Member rejoined" if joined_before else "Member joined",
            ).set_footer(
                text=f"Member ID: {member.id} | Inviter IDs: {', '.join([str(x.inviter.id) for x in used_invites])}"[:2048]
            )
            await self.server_logs.send(embed=member_invite_logging)

    @commands.Cog.listener("on_member_join")
    async def verification_start(self, member):
        if member.bot:
            return
        is_member_verified = await self.check_if_verified(member)
        if is_member_verified:
            # If member unverified and leave, roles will be saved, but they are still unverified
            # So we need to check if they are verified or not before adding roles
            has_previous_roles = await check_and_add_previous_roles(member)
            if not has_previous_roles:
                await member.add_roles(utils.get(member.guild.roles, name="Member"))
            await member.edit(nick=is_member_verified["ign"])
            await send_welcome_dm(member, rejoining=True)

        if not is_member_verified:
            await member.add_roles(utils.get(member.guild.roles, name="Verifying"))

        await self.invite_tracking(member, is_member_verified)

    async def save_member_roles(self, member):
        if member.roles:  # member role not saved to determine if they are rejoining or not
            member_role_ids = [role.id for role in member.roles if role.name != '@everyone' and role.name != 'Verifying']

            if not member_role_ids:  # to remove people with only verifying role
                return

            if member_role_ids:
                await previous_roles_db.insert_one(
                    {
                        "member_id": member.id,
                        "roles": member_role_ids,
                        "display_name": member.display_name
                    }
                )

    @commands.Cog.listener("on_member_remove")
    async def saving_member_roles(self, member):
        self.guild_invites = await member.guild.invites()
        await self.save_member_roles(member)
        await self.server_logs.send(
            embed=Embed(
                description=f"{member.mention} had left the server",
                colour=0xff0033,
            ).set_author(
                name=f"Member left",
                url=member.avatar.url if member.avatar else member.default_avatar.url,
            )
        )

    @commands.command(aliases=["reverify", "deverify"])
    @commands.cooldown(1, 300, commands.BucketType.user)
    async def unverify(self, ctx, member: Member = None):
        to_unverify = ctx.author
        if member:
            if not ctx.author.guild_permissions.manage_messages:
                ctx.command.reset_cooldown(ctx)
                return await ctx.reply("You do not have permission to unverify other members, do !unverify.")
            to_unverify = member

        verifying_role = utils.get(to_unverify.guild.roles, name="Verifying")
        if verifying_role not in to_unverify.roles:
            seraphine_channel = utils.get(ctx.guild.text_channels, name="👩seraphine-commands")
            if ctx.channel.id != seraphine_channel.id:
                ctx.command.reset_cooldown(ctx)
                await ctx.reply(
                    f"Use this command in the {seraphine_channel.mention} channel",
                    delete_after=10,
                    mention_author=False
                )
                return

        unverify = await verification_db.delete_many({"discord_id": to_unverify.id})
        if unverify.deleted_count == 0:
            ctx.command.reset_cooldown(ctx)
            return await ctx.reply(f"{to_unverify.mention} is not verified.")

        await previous_roles_db.delete_many({"member_id": to_unverify.id})
        await self.save_member_roles(to_unverify)
        for role in to_unverify.roles:
            if role.name != '@everyone':
                await to_unverify.remove_roles(role)
        await to_unverify.add_roles(self.verification_role)
        await ctx.reply(
            f"{to_unverify.mention} has been unverified"
        )

    @unverify.error
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(
                f"You can only use this command once every 5 minutes, please try again in {error.retry_after:.0f} seconds"
            )

    @commands.command()
    @commands.is_owner()
    async def verification_instruction(self, ctx):
        verification_help_channel = utils.get(ctx.guild.text_channels, name="❓verification-help")
        verification_embed = Embed(
            description="Verification process is very simple!\n"
                        "You just need to verify yourself by linking your Discord account with Hypixel's social menu!\n"
                        f"If you have any problems with verifying, please open a ticket in {verification_help_channel.mention}\n",
            colour=0x003697
        ).add_field(
            name="Verify by hypixel social menu",
            value="To verify with Hypixel Social Menu\n"
                  "> **1:** Log onto hypixel and select `hotbar slot 2` for the `My profile` icon\n"
                  "> **2:** Right click to go into `My profile` and click the `Social Media` icon\n"
                  "> **3:** Click the `Discord`icon and input your discord tag (e.g name#1234) in chat, it's case sensitive.\n"
                  "> **4:** Click the `Verify by social menu` button bellow, and input your minecraft IGN in the input field.\n"
                 "A gif below demonstrates the process.",
            inline=False,
        ).set_image(
            url="https://i.imgur.com/vHQx0WA.gif"
        ).set_author(
            name="Welcome to skyhub!"
        ).set_footer(
            text="If the button below don't work, please restart your discord client and try again."
        )
        await ctx.send(embed=verification_embed, view=VerificationButtons(self))

    @commands.Cog.listener("on_message")
    async def welcoming_rewards(self, message):
        if message.author.bot:
            return

        if not self.unwelcomed_new_members:
            return

        welcome_channel = utils.get(self.guild.text_channels, name="👋🏻welcome")

        if message.channel.id != welcome_channel.id:
            return

        if message.author.id in self.unwelcomed_new_members:
            return

        if self.verifying_welcome_message:
            return

        skybies = self.client.get_cog("Skybies")
        self.verifying_welcome_message = True
        welcomed_members = []
        for members in self.unwelcomed_new_members:
            member = message.guild.get_member(members)
            welcomed_members.append(member.mention if member else "Unknown")
        await skybies.give_skybies(
            message.author, 1,
            f"{message.author.display_name} had welcomed {','.join(welcomed_members)} to Skyhub!!!"
        )
        await message.reply(
            f"{message.author.display_name} have been given 1 skybie for welcoming {len(welcomed_members)} "
            f"member{await self.pural(len(welcomed_members))} to Skyhub!!!",
            delete_after=7,
            mention_author=False
        )

        self.unwelcomed_new_members.clear()
        self.verifying_welcome_message = False

    async def get_invites(self):
        await self.client.wait_until_ready()
        self.guild_invites = await self.guild.invites()

    async def cog_load(self):
        self.client.add_view(VerificationButtons(self))
        self.client.loop.create_task(self.get_invites())


async def setup(client):
    await client.add_cog(JoinAndLeave(client))
