from os import getenv
from typing import List
from re import match
from bson.objectid import ObjectId
from bson.json_util import dumps
from math import ceil

from discord import (
    app_commands,
    Embed,
    Interaction,
    Object,
    ui,
    ButtonStyle,
    TextStyle,
    NotFound,
    HTTPException,
    Colour,
    utils,
    PartialEmoji,
    File
)
from discord.ext import commands
from minepi import name_to_uuid, uuid_to_name
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

cluster = AsyncIOMotorClient(getenv("MongoDbSecretKey"))
scammer_db = cluster["Skyhub"]["ScammerDatabase"]
load_dotenv()

async def offense_display_embed(uuid, reason, evidence_urls, insertion_id, discord_ids=None, alt_uuids=None):
    ign = await uuid_to_name(uuid)
    offense_display_embed = Embed(
        title=f"`{ign}`",
        colour=Colour.random()
    ).add_field(
        name="Reason",
        value=reason
    ).add_field(
        name="Evidences",
        value="\n".join(evidence_urls)
    ).add_field(
        name="NameMC",
        value=f"https://namemc.com/profile/{ign}"
    ).set_footer(
        text=f"To remove this, do !scammer_remove {insertion_id}"
    )
    if alt_uuids:
        offense_display_embed.add_field(
            name="Minecraft alt(s)",
            value="\n".join(alt_uuids)
        )
    if discord_ids:
        offense_display_embed.add_field(
            name="Discord account(s)",
            value="\n".join(discord_ids)
        )
    return offense_display_embed

async def scammer_database_error_embed(interaction, title, message):
    await interaction.response.send_message(
        embed=Embed(
            description=message,
            colour=0xF9423A
        ).set_author(
            name=title
        ),
        ephemeral=True
    )


class ScammerAddModal(ui.Modal):
    def __init__(self):
        super().__init__(
            title="Scammer Database",
            timeout=None,
        )
        self.ign = ui.TextInput(
            label="Mincraft IGN",
            min_length=3,
            max_length=48,
        )
        self.add_item(self.ign)
        self.reason = ui.TextInput(
            label='Reason',
            style=TextStyle.paragraph,
        )
        self.add_item(self.reason)
        self.evidence = ui.TextInput(
            label="Proof (Imgur/ discord, separate by new line)",
            style=TextStyle.paragraph,
        )
        self.add_item(self.evidence)
        self.discord_account_ids = ui.TextInput(
            label="Discord account ids (separate by new line)",
            style=TextStyle.paragraph,
            required=False
        )
        self.add_item(self.discord_account_ids)
        self.alt_igns = ui.TextInput(
            label="Minecraft alts (separate by new line)",
            style=TextStyle.paragraph,
            required=False
        )
        self.add_item(self.alt_igns)

    async def get_uuid(self, ign):
        try:
            uuid = await name_to_uuid(ign)
            return uuid

        except ValueError:
            return

    async def handle_discord_ids(self, client, discord_ids):
        discord_ids = discord_ids.split("\n")
        failed_discord_ids = []
        filtered_discord_ids = []
        for discord_id in discord_ids:
            if discord_id:
                try:
                    await client.fetch_user(discord_id)
                    filtered_discord_ids.append(discord_id)

                except NotFound:
                    failed_discord_ids.append(discord_id)

                except HTTPException:
                    failed_discord_ids.append(discord_id)

        if failed_discord_ids:
            return [False, failed_discord_ids]

        if filtered_discord_ids:
            return [True, filtered_discord_ids]

        return [False, None]

    async def handle_minecraft_alts(self, igns):
        igns = igns.split("\n")
        failed_igns = []
        filtered_uuids = []
        for ign in igns:
            if ign:
                try:
                    uuid = await name_to_uuid(ign)
                    filtered_uuids.append(uuid)
                except ValueError:
                    failed_igns.append(ign)
        if failed_igns:
            return [False, failed_igns]

        if filtered_uuids:
            return [True, filtered_uuids]

        return [False, None]

    async def handle_evidence(self, evidence):
        evidences = evidence.split("\n")
        not_allowed_evidences = []
        filtered_evidence = []
        for evidence in evidences:
            if evidence:
                if match(
                    "(https://|http://)?(cdn\.|media\.)discord(app)?\.(com|net)/attachments/[0-9]{17,19}/[0-9]{17,19}/(?P<filename>.{1,256})\.(?P<mime>[0-9a-zA-Z]{2,4})(\?size=[0-9]{1,4})?",
                    evidence
                ) or match(
                    "(^(http|https)://)?(i\.)?imgur.com/((?P<gallery>gallery/)(?P<galleryid>\w+)|(?P<album>a/)(?P<albumid>\w+)#?)?(?P<imgid>\w*)",
                    evidence
                ):
                    filtered_evidence.append(evidence)
                else:
                    not_allowed_evidences.append(evidence)

        if not_allowed_evidences:
            return [False, not_allowed_evidences]

        if filtered_evidence:
            return [True, filtered_evidence]

        return [False, None]

    async def log_offense(self, uuid, reason, evidence_urls, discord_ids=None, alt_uuids=None):
        offense = await scammer_db.insert_one(
            {
                "offender_uuid": uuid,
                "reason": reason,
                "evidence_urls": evidence_urls,
                "discord_ids": discord_ids,
                "alt_uuids": alt_uuids
            }
        )
        offense_insert_id = offense.inserted_id
        return offense_insert_id

    async def on_submit(self, interaction: Interaction) -> None:
        uuid = await self.get_uuid(self.ign.value.strip())
        if not uuid:
            await scammer_database_error_embed(
                interaction,
                "Scammer database append unsuccessful",
                f"`{self.ign.value.strip()}` is not a valid mc account, please check for typos"
                )
            return
        reason = self.reason.value.strip()
        evidence_urls = None
        evidence_handler_response = await self.handle_evidence(self.evidence.value.strip())
        if not evidence_handler_response[0] and evidence_handler_response[1]:
            formatted_not_allowed_evidences = "\n".join(evidence_handler_response[1])
            await scammer_database_error_embed(
                interaction,
                "Scammer database append unsuccessful",
                f"In evidence field, the evidence at:\n"
                f"```\n{formatted_not_allowed_evidences}```\n"
                f"Are not Imgur or discord attachment links, please make sure the images or videos will not be deleted."
            )
            return
        if not evidence_handler_response[0]:
            await scammer_database_error_embed(
                interaction,
                "Scammer database append unsuccessful",
                "In evidence field, something seems to have gone wrong, please submit again"
            )
            return
        if evidence_handler_response[0] and evidence_handler_response[1]:
            evidence_urls = evidence_handler_response[1]
        discord_ids = None
        if self.discord_account_ids.value.strip():
            discord_id_handler_response = await self.handle_discord_ids(interaction.client, self.discord_account_ids.value.strip())
            if not discord_id_handler_response[0] and discord_id_handler_response[1]:
                formatted_failed_discord_ids = "\n".join(discord_id_handler_response[1])
                await scammer_database_error_embed(
                    interaction,
                    "Scammer database append unsuccessful",
                    f"In discord id field, the id(s):\n"
                    f"```\n{formatted_failed_discord_ids}```\n"
                    f"Does not seem to belong to any discord account(s)"
                )
                return
            if not discord_id_handler_response[0]:
                await scammer_database_error_embed(
                    interaction,
                    "Scammer database append unsuccessful",
                    "In discord id field, something seems to have gone wrong, please submit again"
                    )
                return
            if discord_id_handler_response[0] and discord_id_handler_response[1]:
                discord_ids = discord_id_handler_response[1]

        alt_uuids = None
        if self.alt_igns.value.strip():
            alt_handler_response = await self.handle_minecraft_alts(self.alt_igns.value.strip())
            if not alt_handler_response[0] and alt_handler_response[1]:
                formatted_failed_igns = '\n'.join(alt_handler_response[1])
                await scammer_database_error_embed(
                    interaction,
                    "Scammer database append unsuccessful",
                    f"In alts field, the minecraft ign(s):\n"
                    f"```\n{formatted_failed_igns}```\n"
                    f"Does not seem to belong to any minecraft account(s)"
                )
                return

            if not alt_handler_response[0]:
                await scammer_database_error_embed(
                    interaction,
                    "Scammer database append unsuccessful",
                    "In alts field, something seems to have gone wrong, please submit again",
                )
                return

            if alt_handler_response[0] and alt_handler_response[1]:
                alt_uuids = alt_handler_response[1]

        offense_insert_id = await self.log_offense(uuid, reason, evidence_urls, discord_ids, alt_uuids)
        if offense_insert_id:
            scammer_log_channel = utils.get(
                interaction.guild.text_channels,
                name="🕵scammer-logs"
            )
            new_offense_embed = await offense_display_embed(uuid, reason, evidence_urls, offense_insert_id, discord_ids, alt_uuids)
            await interaction.response.send_message(
                embed=new_offense_embed
            )
            await scammer_log_channel.send(
                embed=new_offense_embed
            )
        else:
            await scammer_database_error_embed(
                interaction,
                "Scammer database append unsuccessful",
                "Something unknown have gone wrong, please try again, if this continues to happen, contact hypicksell"
            )


class ScammerAddButton(ui.View):
    def __init__(self, scammer_add_response, author):
        super().__init__(timeout=300)
        self.scammer_add_response = scammer_add_response
        self.author = author
        self.current = 0

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        await self.scammer_add_response.edit(view=self)
        await self.scammer_add_response.edit(
            embed=Embed(
                description="Do `!scammer_add` to make a new one",
                colour=0xF9423A,
            ).set_author(
                name="This scammer_add command is timed out"
            )
        )
    async def interaction_check(self, interaction):
        if self.author != interaction.user:
            await interaction.response.send_message(
                f"hey! this is for {self.author.mention}",
                ephemeral=True
            )
            return
        return True

    @ui.button(label="click to add scammer to database", style=ButtonStyle.blurple)
    async def verify_by_api_key_button(self, interaction: Interaction, button: ui.button):
        await interaction.response.send_modal(ScammerAddModal())

class OffensesViewButtons(ui.View):
    def __init__(self, offense_embeds_list):
        super().__init__(timeout=180)
        self.offense_embed_list = offense_embeds_list
        self.current = 0


    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        await self.is_scammer_message.edit(view=self)
        await self.is_scammer_message.edit(
            embed=Embed(
                description="Do `/is_scammer` to make a new one",
                colour=0xF9423A,
            ).set_author(
                name="This is_scammer command is timed out"
            )
        )

    @ui.button(emoji=PartialEmoji.from_str("<:fast_backward:1015264717570322483>"), style=ButtonStyle.blurple)
    async def fast_backward(self, interaction: Interaction, button: ui.Button):
        self.current = 0
        await interaction.response.edit_message(
            embed=self.offense_embed_list[self.current]
        )

    @ui.button(emoji=PartialEmoji.from_str("<:backward:1004400601146343535>"), style=ButtonStyle.blurple)
    async def backward(self, interaction: Interaction, button: ui.Button):
        self.current -= 1
        if self.current < 0:
            self.current = len(self.offense_embed_list) - 1
        await interaction.response.edit_message(
            embed=self.offense_embed_list[self.current]
        )

    @ui.button(emoji=PartialEmoji.from_str("<:forward:1004400629327872020>"), style=ButtonStyle.blurple)
    async def forward(self, interaction: Interaction, button: ui.Button):
        self.current += 1
        if self.current > len(self.offense_embed_list) - 1:
            self.current = 0
        await interaction.response.edit_message(
            embed=self.offense_embed_list[self.current]
        )

    @ui.button(emoji=PartialEmoji.from_str("<:fast_forward:1015264716072960010>"), style=ButtonStyle.blurple)
    async def fast_forward(self, interaction: Interaction, button: ui.Button):
        self.current = len(self.offense_embed_list) - 1
        await interaction.response.edit_message(
            embed=self.offense_embed_list[self.current]
        )


class ScammerDatabase(commands.Cog):
    def __init__(self, client):
        self.client = client

    @property
    def guild(self):
        return Object(id=int(getenv("GUILD_ID")))

    @commands.command(aliases=["add_scammer"])
    @commands.has_permissions(manage_messages=True)
    async def scammer_add(self, ctx):
        to_do_before_adding_embed = Embed(
            description="**1.** Do `/is_scammer` to check if the same offence is recorded already or if they have alts.\n"
                        "**2.** Upload the evidence of scamming to [Imgur](https://imgur.com/upload) "
                        "or as an discord attachment that you know will not be deleted."
                        "**3.** For every alt the offender have, please append the same info to the alt in the scammer database"
            ,
            colour=0x4bb543
        ).set_author(
            name="Please do the bellow 3 steps when appending to scammer database"
        )
        scammer_add_button = ScammerAddButton(ctx.message,ctx.author)
        scammer_add_button.scammer_add_message = await ctx.reply(embed=to_do_before_adding_embed, view=scammer_add_button)

    @scammer_add.error
    async def scammer_add_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("you need to be at least a helper to use this command", delete_after=10)

    @commands.command()
    async def is_scammer_notification(self, ctx):
        await ctx.reply(
            embed=Embed(
                description=f"Please use /is_scammer to check by ign or discord id",
                colour=0xf9423a
            )
        )

    async def get_previous_offenses(self, uuid=None, discord_id=None):
        all_offenses = None
        if uuid:
            if not discord_id:
                all_offenses = scammer_db.find({"offender_uuid": uuid})
            if discord_id:
                all_offenses = scammer_db.find({"offender_uuid": uuid, "discord_ids": discord_id})

        if not uuid and discord_id:
            all_offenses = scammer_db.find({"discord_ids": discord_id})
        if all_offenses is not None:
            async for document in all_offenses:
                return all_offenses
        return None

    async def format_offenses(self, offenses_list):
        offense_embeds_list = []
        for offense in offenses_list:
            offense_embed = await offense_display_embed(
                offense["offender_uuid"],
                offense["reason"],
                offense["evidence_urls"],
                str(offense["_id"]),
                offense["discord_ids"],
                offense["alt_uuids"]
            )
            offense_embeds_list.append(offense_embed)
        return offense_embeds_list

    @app_commands.command(name="is_scammer", description="check the skyhub scammer database by discord id or ign")
    @app_commands.describe(
        ign="Minecraft IGN",
        uuid="Minecraft account uuid",
        discord_id="Discord user id",
    )
    async def is_scammer(self, interaction: Interaction, ign: str = None, uuid: str = None, discord_id: str = None):
        if not any([ign, uuid, discord_id]):
            await interaction.response.send_message(
                "Please choose the filter(s) you using for searching the scammer database"
            )

        offenses = None
        if not uuid and not ign and discord_id:
            offenses = await self.get_previous_offenses(discord_id=discord_id)

        if uuid or ign:
            if not uuid and ign:
                try:
                    uuid = await name_to_uuid(ign)
                except ValueError:
                    await scammer_database_error_embed(
                        interaction,
                        "Ign not exist",
                        f"No current mc accounts have the ign `{ign}`, try find your target's current IGN or uuid at"
                        "[namemc](https://namemc.com/)"
                    )
                    return
            if uuid and not ign:
                try:
                    ign = await uuid_to_name(uuid)
                except ValueError:
                    await scammer_database_error_embed(
                        interaction,
                        "UUID not exist",
                        f"No current mc accounts have the uuid `{uuid}`, check for typos"
                    )
                    return
            if discord_id:
                offenses = await self.get_previous_offenses(uuid, discord_id)

            if not discord_id:
                offenses = await self.get_previous_offenses(uuid)

        offense_list = [x async for x in offenses]

        if not offense_list:
            verification_help_channel = utils.get(interaction.guild.channels, name="❓verification-help")
            scammer_info_channel = utils.get(interaction.guild.channels, name="📝trading-section-info")
            if ign:
                not_found_message = f"Minecraft account `{ign}` is not found in the scammer database."
            elif uuid:
                not_found_message = f"Minecraft account with uuid `{uuid}` is not found in the scammer database."
            else:
                not_found_message = f"Discord account with id {discord_id} is not found in the scammer database."

            await interaction.response.send_message(
                embed=Embed(
                    description=f"{not_found_message}\n\n"
                                f"This does not mean they are not a scammer, be aware of scammers and educate yourself "
                                f"about common scams at [the wiki](https://hypixel-skyblock.fandom.com/wiki/Scams).\n"
                                f"Also, collect evidence if you have been scammed, so you can open an ticket"
                                f"at {verification_help_channel.mention} to add the scammer to the database, learn more"
                                f"about the criteria of evidences that we accept at {scammer_info_channel.mention}",
                    colour=0x4bb543
                ).set_author(
                    name=f"This {'mc account' if ign else 'discord id'} is not within the database"
                )
            )
        if offense_list:
            offense_embeds_list = await self.format_offenses(offense_list)
            if len(offense_embeds_list) > 1:
                offenses_view = OffensesViewButtons(offense_embeds_list)
                offenses_view.is_scammer_message = await interaction.response.send_message(
                    embed=offense_embeds_list[0],
                    view=offenses_view,
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    embed=offense_embeds_list[0],
                    ephemeral=True
                )

    @is_scammer.autocomplete("ign")
    async def is_scammer_autocomplete(self, interaction: Interaction, current: str) -> List[app_commands.Choice[str]]:
        placeholder_igns = ['RogueStab', "ItsModern"]
        return [
            app_commands.Choice(name=ign, value=ign)
            for ign in placeholder_igns if current.lower() in ign.lower()
        ]

    @is_scammer.autocomplete("uuid")
    async def is_scammer_autocomplete(self, interaction: Interaction, current: str) -> List[app_commands.Choice[str]]:
        placeholder_uuids = []
        return [
            app_commands.Choice(name=ign, value=ign)
            for ign in placeholder_uuids if current.lower() in ign.lower()
        ]

    @is_scammer.autocomplete("discord_id")
    async def is_scammer_autocomplete(self, interaction: Interaction, current: str) -> List[app_commands.Choice[str]]:
        placeholder_discord_ids = ['1234456789']
        return [
            app_commands.Choice(name=discord_id, value=discord_id)
            for discord_id in placeholder_discord_ids if current.lower() in id
        ]

    @commands.command()
    @commands.cooldown(1, 600, commands.BucketType.user)
    async def scammer_download(self, ctx):
        all_inserts_list = [offense async for offense in scammer_db.find({}, {'_id': False})]
        json_data = dumps(all_inserts_list, indent=2)
        with open('scammer_database.json', 'w') as file:
            file.write(json_data)
        await ctx.reply(
            file=File("scammer_database.json"),
            mention_author=False
        )

    @scammer_download.error
    async def scammer_download_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            cooldown = ceil(error.retry_after//60)
            await ctx.send(
                f"This command is on cooldown for {cooldown} minute{'s' * (cooldown != 1)}"
            )

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def scammer_remove(self, ctx, insert_id: str):
        result = await scammer_db.delete_one({"_id": ObjectId(insert_id)})
        if not result.deleted_count:
            await ctx.reply(
                Embed(
                    description=f"Offense with insert id {insert_id} not found",
                    colour=0xF9423A
                ).set_author(
                    name="Insert id not found"
                ),
                mention_author=False
            )


async def setup(client):
    await client.add_cog(ScammerDatabase(client))
