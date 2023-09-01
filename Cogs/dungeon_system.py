from os import getenv
from datetime import timedelta
from io import BytesIO

from discord import Interaction, ui, Embed, ButtonStyle, utils, PermissionOverwrite, Forbidden, NotFound, File
from discord.ext import commands, tasks
from chat_exporter import export
from asyncio import sleep
from dotenv import load_dotenv
load_dotenv()


class TranscriptView(ui.View):
    def __init__(self, url: str):
        super().__init__()
        self.add_item(ui.Button(label='Click here to view the transcript', url=url))


class ConfirmButton(ui.Button["ConfirmView"]):
    def __init__(self, label: str, style: ButtonStyle, *, custom_id: str):
        super().__init__(label=label, style=style, custom_id=f"{custom_id}")

    async def callback(self, interaction: Interaction):
        self.view.value = True if self.custom_id == f"confirm_button" else False
        self.view.stop()


class ConfirmView(ui.View):
    def __init__(self):
        super().__init__(timeout=10.0)
        self.value = None
        self.add_item(ConfirmButton("Yes", ButtonStyle.green, custom_id="confirm_button"))
        self.add_item(ConfirmButton("No", ButtonStyle.red, custom_id="decline_button"))


async def channel_creation_embed(interaction, carrying_type, carrying_role_for_ticket, num_carriers):
    ticket_channel = utils.get(interaction.guild.channels, name="🎫make-a-ticket")
    embed = Embed(
        description=
        f"**All carriers for {carrying_role_for_ticket.mention} are pinged, please be patient for a carrier to response!\n**",
        colour=0x89CFF0
    ).set_author(
        name=f"Thanks for creating a carrying ticket for a {carrying_type} carry!"
    ).add_field(
        name="Before the carry",
        value=
        f"> **Pay carrier before carry**, state your `IGN` & `number of carries`.\n"
        f"If carrier takes payment but doesn't provide carry, "
        f"please create a ticket at {ticket_channel.mention} with proof.\n\n",
        inline=False
    ).add_field(
        name="During the carry",
        value="> Only **one redo** is provided if a carry failed due to your fault, this redo policy won't be applied if "
              "you take more than 15 minutes to spawn the boss in a slayer carry.\n\n"
              "> If a carry is failed due to the carrier, a redo must be provided, or a refund, if the carrier doesn't "
              f"comply, please create a ticket at {ticket_channel.mention} with proof.",
        inline=False
    ).add_field(
        name="After the carry",
        value=
        f"> Please close the ticket with `!done` when your carry is finished.\n\n"
        f"> If you are satisfied with the carry, "
        f"leave a honor for the carrier by doing `!honor (carrier's name) (reason)`",
        inline=False
    ).set_footer(
        text=f"{num_carriers} carrier(s) are currently available for a {carrying_type} carry!"
    )
    return embed


async def check_for_duplicate(interaction, carrying_type):
    guild = interaction.guild
    category = utils.get(guild.categories, name="Carrying Tickets")
    for channel in category.channels:
        channel_owner, channel_carrying_type = int(channel.topic.split("|")[0]), channel.topic.split("|")[1]
        if channel_owner == interaction.user.id and channel_carrying_type == carrying_type:
            await interaction.edit_original_response(
                embed=Embed(
                    title=f"You already have a {carrying_type} ticket!",
                    description=f"Please close {channel.mention} with `!done` before creating a new one!",
                    colour=0xCC2222
                )
            )
            return True
    return False


async def check_if_there_carriers(interaction, carrying_role_for_ticket):
    num_of_carriers = len(carrying_role_for_ticket.members)
    if num_of_carriers == 0:
        await interaction.edit_original_response(
            embed=Embed(
                title="No carriers available!",
                description="There are no carriers currently for this carrying type, please recommend skyhub's "
                            " carrying system to your friends capable for this carry!",
                colour=0xCC2222
            )
        )
        return False
    return num_of_carriers


async def create_channel(interaction, role_name, carrying_type):
    guild = interaction.guild
    carrying_role_for_ticket = utils.get(guild.roles, name=role_name)
    category = utils.get(guild.categories, name="Carrying Tickets")
    is_duplicated = await check_for_duplicate(interaction, carrying_type)
    num_carriers = await check_if_there_carriers(interaction, carrying_role_for_ticket)
    if is_duplicated or not num_carriers:
        return

    label = interaction.user.display_name if len(interaction.user.display_name) < 15 else interaction.user.display_name[
                                                                                          :16]
    carrier_ping_role = utils.get(guild.roles, name="⚔️Carrying Ping⚔️")

    carrying_channel = await guild.create_text_channel(
        name=f"{carrying_type} {label}",
        category=category,
        overwrites={
            carrying_role_for_ticket: PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                read_message_history=True
            ),
            interaction.user: PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                read_message_history=True
            ),
        },
        topic=f"{interaction.user.id}|{carrying_type}",
    )

    await carrying_channel.send(
        f"{interaction.user.mention} {carrier_ping_role.mention}",
        embed=await channel_creation_embed(interaction, carrying_type, carrying_role_for_ticket, num_carriers)
    )

    await interaction.edit_original_response(
        embed=Embed(
            title=f"Thanks for using SkyHub's carrying system 😎",
            description=f"{carrying_channel.mention} has been created for you!\n",
            colour=0x4bb543
        )
    )


async def create_channel_from_button(interaction: Interaction, carrying_type, role_name):
    confirm_view = ConfirmView()

    async def disable_all_buttons():
        for _item in confirm_view.children:
            _item.disabled = True

    await interaction.response.send_message(
        embed=Embed(
            title=f"Are you sure you want to create a {carrying_type} ticket?",
            description="Click the button bellow to confirm!",
            colour=0xffffff
        ),
        ephemeral=True,
        view=confirm_view
    )
    await confirm_view.wait()
    if confirm_view.value is False or confirm_view.value is None:
        await disable_all_buttons()
        title = "Canceled!" if confirm_view.value is False else "Confirmation timed out!"
        await interaction.edit_original_response(
            embed=Embed(
                title=title,
                description="You can create a ticket again by clicking the button bellow!",
                colour=0xCC2222
            ),
            view=None
        )
    else:
        await disable_all_buttons()
        await interaction.edit_original_response(
            embed=Embed(
                title="Creating your ticket...",
                description=f"A {carrying_type} ticket is being created for you... please wait!",
                colour=0xffffff
            ),
            view=None
        )
        await create_channel(interaction, role_name, carrying_type)


class DungeonFloorSelection(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="F1 to F4", style=ButtonStyle.green, custom_id='f1-4_button')
    async def f1_to_f4_button(self, interaction: Interaction, button: ui.Button):
        await create_channel_from_button(interaction, "f1-4", "F1-4")

    @ui.button(label="F5", style=ButtonStyle.green, custom_id='f5_button')
    async def f5_button(self, interaction: Interaction, button: ui.Button):
        await create_channel_from_button(interaction, "f5", "F5")

    @ui.button(label="F6", style=ButtonStyle.green, custom_id='f6_button')
    async def f6_button(self, interaction: Interaction, button: ui.Button):
        await create_channel_from_button(interaction, "f6", "F6")

    @ui.button(label="F7", style=ButtonStyle.green, custom_id='f7_button')
    async def f7_button(self, interaction: Interaction, button: ui.Button):
        await create_channel_from_button(interaction, "f7", "F7")

    @ui.button(label="MM F1", style=ButtonStyle.red, custom_id='mm_f1_button', row=2)
    async def mm_f1_button(self, interaction: Interaction, button: ui.Button):
        await create_channel_from_button(interaction, "mm f1", "MM F1")

    @ui.button(label="MM F2", style=ButtonStyle.red, custom_id='mm_f2_button', row=2)
    async def mm_f2_button(self, interaction: Interaction, button: ui.Button):
        await create_channel_from_button(interaction, "mm f2", "MM F2")

    @ui.button(label="MM F3", style=ButtonStyle.red, custom_id='mm_f3_button', row=2)
    async def mm_f3_button(self, interaction: Interaction, button: ui.Button):
        await create_channel_from_button(interaction, "mm f3", "MM F3")

    @ui.button(label="MM F4", style=ButtonStyle.red, custom_id='mm_f4_button', row=2)
    async def mm_f4_button(self, interaction: Interaction, button: ui.Button):
        await create_channel_from_button(interaction, "mm f4", "MM F4")

    @ui.button(label="MM F5", style=ButtonStyle.red, custom_id='mm_f5_button', row=2)
    async def mm_f5_button(self, interaction: Interaction, button: ui.Button):
        await create_channel_from_button(interaction, "mm f5", "MM F5")

    @ui.button(label="MM F6", style=ButtonStyle.red, custom_id='mm_f6_button', row=3)
    async def mm_f6_button(self, interaction: Interaction, button: ui.Button):
        await create_channel_from_button(interaction, "mm f6", "MM F6")

    @ui.button(label="MM F7", style=ButtonStyle.red, custom_id='mm_f7_button', row=3)
    async def mm_f7_button(self, interaction: Interaction, button: ui.Button):
        await create_channel_from_button(interaction, "mm f7", "MM F7")


class SlayerCarriesSelection(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="Rev T1-4", style=ButtonStyle.green, custom_id='rev_t4_button')
    async def rev_t1_4_button(self, interaction: Interaction, button: ui.Button):
        await create_channel_from_button(interaction, "rev-t1-4", "T1-4 Rev")

    @ui.button(label="Rev T5", style=ButtonStyle.green, custom_id='rev_t5_button')
    async def rev_t5_button(self, interaction: Interaction, button: ui.Button):
        await create_channel_from_button(interaction, "rev-t5", "T5 Rev")

    @ui.button(label="Tarantula T1-3", style=ButtonStyle.red, custom_id='tarantula_1_3_button', row=2)
    async def tarantula_t1_3_button(self, interaction: Interaction, button: ui.Button):
        await create_channel_from_button(interaction, "tarantula-t1-3", "T1-3 Tarantula")

    @ui.button(label="Tarantula T4", style=ButtonStyle.red, custom_id='tarantula_t4_button', row=2)
    async def tarantula_t4_button(self, interaction: Interaction, button: ui.Button):
        await create_channel_from_button(interaction, "tarantula-t4", "T4 Tarantula")

    @ui.button(label="Sven T1-3", style=ButtonStyle.grey, custom_id='sven_t1_3_button', row=3)
    async def sven_t1_3_button(self, interaction: Interaction, button: ui.Button):
        await create_channel_from_button(interaction, "sven-t1-3", "T1-3 Sven")

    @ui.button(label="Sven T4", style=ButtonStyle.grey, custom_id='sven_t4_button', row=3)
    async def sven_t4_button(self, interaction: Interaction, button: ui.Button):
        await create_channel_from_button(interaction, "sven-t4", "T4 Sven")

    @ui.button(label="Void T1", style=ButtonStyle.blurple, custom_id='void_t1_button', row=4)
    async def void_t1_button(self, interaction: Interaction, button: ui.Button):
        await create_channel_from_button(interaction, "void-t1", "T1 Voidgloom")

    @ui.button(label="Void T2", style=ButtonStyle.blurple, custom_id='void_t2_button', row=4)
    async def void_t2_button(self, interaction: Interaction, button: ui.Button):
        await create_channel_from_button(interaction, "void-t2", "T2 Voidgloom")

    @ui.button(label="Void T3", style=ButtonStyle.blurple, custom_id='void_t3_button', row=4)
    async def void_t3_button(self, interaction: Interaction, button: ui.Button):
        await create_channel_from_button(interaction, "void-t3", "T3 Voidgloom")

    @ui.button(label="Void T4", style=ButtonStyle.blurple, custom_id='void_t4_button', row=4)
    async def void_t4_button(self, interaction: Interaction, button: ui.Button):
        await create_channel_from_button(interaction, "void-t4", "T4 Voidgloom")


class CrimsonCarriesSelection(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="Magma boss", style=ButtonStyle.red, custom_id='magma_boss_button')
    async def magma_boss_button(self, interaction: Interaction, button: ui.Button):
        await create_channel_from_button(interaction, "magma-boss", "Magma Boss")

    @ui.button(label="Ashfang", style=ButtonStyle.red, custom_id='ashfang_button')
    async def ashfang_button(self, interaction: Interaction, button: ui.Button):
        await create_channel_from_button(interaction, "ashfang", "Ashfang")

    @ui.button(label="Basic Kuudra", style=ButtonStyle.red, custom_id='basic_kuudra_button')
    async def basic_kuudra_button(self, interaction: Interaction, button: ui.Button):
        await create_channel_from_button(interaction, "basic_kuudra", "Basic Kuudra")

    @ui.button(label="Hot Kuudra", style=ButtonStyle.red, custom_id='hot_kuudra_button')
    async def hot_kuudra_button(self, interaction: Interaction, button: ui.Button):
        await create_channel_from_button(interaction, "hot_kuudra", "Hot Kuudra")

class DungeonSystem(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.is_owner()
    @commands.command()
    async def dungeon_carrying_start(self, ctx):
        explain_embed = Embed(
            description="This is the baseline for the prices of each carry, negotiate with the carrier if you want to!",
            colour=0x8155BA
        ).add_field(
            name="Floor 1 (Bonzo)",
            value=
            "**Completion -** `10k`\n"
            "**S rating -** `80k`\n"
        ).add_field(
            name="__Floor 2: (scarf)__",
            value=
            "**Completion -** `50k`\n"
            "**S rating -** `100k`\n"
        ).add_field(
            name="__Floor 3: (Professor)__",
            value=
            "**Completion -** `80k`\n"
            "**S rating -** `150k`\n"
        ).add_field(
            name="__Floor 4: (Thorn)__",
            value=
            "**Completion -** `250k`\n"
            "**S rating -** `300k`\n"
        ).add_field(
            name="__Floor 5: (Livid)__",
            value=
            "**Completion -** `200k`\n"
            "**S rating -** `250k`\n"
            "**S+ rating -** `400K`\n"
        ).add_field(
            name="__Floor 6: (Sadan)__",
            value=
            "**Completion -** `500k`\n"
            "**S rating -** `600k`\n"
            "**S+ rating -** `800k`\n"
        ).add_field(
            name="__Floor 7: (Necron, Storm, Goldor, Maxor)__",
            value=
            "**Completion -** `3m`\n"
            "**S rating -** `4.5m`\n"
            "**S+ rating -** `6m`\n",
            inline=False
        ).add_field(
            name="__MM F1: (Bonzo)__",
            value=
            "**Completion -** `500k`\n"
            "**S rating -** `750k`\n"
            "**S+ rating -** `1.2m`\n",
        ).add_field(
            name="__MM F2: (scarf)__",
            value=
            "**Completion -** `1.5m`\n"
            "**S rating -** `2m`\n"
            "**S+ rating -** `3m`\n"
        ).add_field(
            name="__MM F3: (Professor)__",
            value=
            "**Completion -** `1m`\n"
            "**S rating -** `1.5m`\n"
            "**S+ rating -** `2.5m`\n"
        ).add_field(
            name="__MM F4: (Thorn)__",
            value=
            "**Completion -** `7m`\n"
            "**S rating -** `10m`\n"
            "**S+ rating -** `13m`\n"
        ).add_field(
            name="__MM F5: (Livid)__",
            value=
            "**Completion -** `3m`\n"
            "**S rating -** `3.5m`\n"
            "**S+ rating -** `4.5m`\n"
        ).add_field(
            name="__MM F6: (Sadan)__",
            value=
            "**Completion -** `5m`\n"
            "**S rating -** `6.5m`\n"
            "**S+ rating -** `8m`\n"
        ).add_field(
            name="__MM F7: (Necron, Storm, Goldor, Maxor)__",
            value=
            "**Completion -** `10m`\n"
            "**S rating -** `13m`\n"
            "**S+ rating -** `16m`\n"
        ).set_author(
            name="Dungeon Carry Prices:",
            icon_url=ctx.guild.icon.url
        )
        await ctx.send(embed=explain_embed, view=DungeonFloorSelection())

    @commands.is_owner()
    @commands.command()
    async def slayer_carrying_start(self, ctx):
        explain_embed = Embed(
            description="This is the baseline for the prices of each carry, negotiate with the carrier if you want to!",
            colour=0xCD5C5C
        ).add_field(
            name="__Reverent Horror__",
            value=
            "**T1-4 -** `50k`\n"
            "**T5 -** `150k`\n",
            inline=False
        ).add_field(
            name="__Tarantula Broodfather__",
            value=
            "**T1-3 -** `70k`\n"
            "**T4 -** `170k`\n",
            inline=False
        ).add_field(
            name="__Sven Packmaster__",
            value=
            "**T1-3 -** `80k`\n"
            "**T4 -** `150k`\n",
            inline=False
        ).add_field(
            name="__Voidgloom Seraph__",
            value=
            "**T1/ T2-** `250k`\n"
            "**T3 -** `500k`\n"
            "**T4 -**  `1.5m`\n",
            inline=False
        ).set_author(
            name="Slayer Carry Prices:",
            icon_url=ctx.guild.icon.url
        )
        await ctx.send(embed=explain_embed, view=SlayerCarriesSelection())

    @commands.is_owner()
    @commands.command()
    async def crimson_carrying_start(self, ctx):
        explain_embed = Embed(
            description="This is the baseline for the prices of each carry, negotiate with the carrier if you want to!",
            colour=0xFFD580
        ).add_field(
            name="__Bosses__",
            value=
            "**Magma boss -** `750k`\n"
            "**Ashfang -** `2m`\n",
            inline=False
        ).add_field(
            name="__Kuudra__",
            value=
            "**Basic -** `6m`\n"
            "**Hot -** `9m`\n",
            inline=False
        ).set_author(
            name="Crimson Carry Prices:",
            icon_url=ctx.guild.icon.url
        )
        await ctx.send(embed=explain_embed, view=CrimsonCarriesSelection())

    async def send_carrying_logs_embed(self, channel, title, description):
        carrier_logs_channel = utils.get(channel.guild.channels, name="📜carrier-logs")
        transcript = await export(
            channel,
            limit=100,
            tz_info="UTC",
            military_time=True,
            bot=self.client,
        )

        transcript_file = File(
            BytesIO(transcript.encode()),
            filename=f"transcript-{channel.name}.html",
        )
        carrying_logs_embed = Embed(
            title=title,
            description=description,
            colour=0x00FF00
        )
        if not transcript:
            return await channel.send(embed=carrying_logs_embed)
        transcript_html_dump_channel = utils.get(channel.guild.channels, name="📁transcript-html-files")
        transcript_file_message = await transcript_html_dump_channel.send(file=transcript_file)
        await carrier_logs_channel.send(
            embed=carrying_logs_embed,
            view=TranscriptView(
                f"https://bensonchow.cf/chat-exporter?url={transcript_file_message.attachments[0].url}"
                )
        )

    async def is_ticket_owner(self, ctx):
        owner_id = int(ctx.channel.topic.split("|")[0])
        if owner_id == ctx.author.id:
            return True

    @commands.command(aliases=["close"])
    async def done(self, ctx):
        if not ctx.channel.category.name == "Carrying Tickets":
            return

        is_owner = await self.is_ticket_owner(ctx)
        logging_title = f"Ticket closed by the ticket creator"
        if not is_owner:
            carrier_role = utils.get(ctx.guild.roles, name="Carrier")
            if ctx.channel.permissions_for(ctx.author).manage_messages:
                if carrier_role in ctx.author.roles:
                    logging_title = "Ticket closed by a staff member"
            elif carrier_role in ctx.author.roles:
                logging_title = "Ticket closed by a carrier"
            else:
                await ctx.send(
                    embed=Embed(
                        description="You are not the owner of this ticket!\n"
                                    "Only carrier/staff members can close other's ticket!",
                        color=0xCC2222
                    )
                )
                return

        await self.send_carrying_logs_embed(
            ctx.channel,
            logging_title,
            f"{ctx.author.mention} closed {ctx.channel.name}"
        )

        await ctx.channel.send(
            embed=Embed(
                description=f"{ctx.author.mention} has closed the ticket, the channel will be deleted in 5 seconds!",
                color=0xCC2222
            )
        )
        await sleep(5)
        await ctx.channel.delete()

    @tasks.loop(minutes=10)
    async def remove_old_tickets(self):
        guild = self.client.get_guild(int(getenv("GUILD_ID")))
        for channel in guild.text_channels:
            if channel.category.name == "Carrying Tickets":
                try:
                    last_message = await channel.fetch_message(channel.last_message_id)
                except NotFound:
                    continue
                if last_message.created_at < (utils.utcnow() - timedelta(hours=48)):
                    try:
                        owner = self.client.get_user(int(channel.topic.split("|")[0]))
                        if owner:
                            await owner.send(
                                embed=Embed(
                                    description=f"Create another ticket in skyhub if you still need a carry!",
                                    color=0xCC2222
                                ).set_author(
                                    name=f"Your ticket has been deleted due to inactivity for 48 hours!",
                                )
                            )
                    except:
                        pass
                    await self.send_carrying_logs_embed(
                        channel, "Ticket deleted due to inactivity",
                        f"{channel.name} has been deleted due to inactivity"
                    )
                    await channel.delete()

    async def remove_old_tickets_starter(self):
        await self.client.wait_until_ready()
        self.remove_old_tickets.start()

    async def cog_load(self):
        self.client.add_view(DungeonFloorSelection())
        self.client.add_view(SlayerCarriesSelection())
        self.client.add_view(CrimsonCarriesSelection())
        self.client.loop.create_task(self.remove_old_tickets_starter())


async def setup(client):
    await client.add_cog(DungeonSystem(client))
