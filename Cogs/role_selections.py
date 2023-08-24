from discord import ButtonStyle, ui, Interaction, utils, Embed
from discord.ext import commands
from dotenv import load_dotenv
load_dotenv()


async def role_handler(interaction: Interaction, role_name: str, add_message: str, remove_message: str):
    guild = interaction.guild
    role = utils.get(guild.roles, name=role_name)
    if role not in interaction.user.roles:
        await interaction.user.add_roles(role)
        await interaction.response.send_message(
            add_message,
            ephemeral=True
        )

    elif role in interaction.user.roles:
        await interaction.user.remove_roles(role)
        await interaction.response.send_message(
            remove_message,
            ephemeral=True
        )


class SectionSelectionButtons(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(emoji="💰", style=ButtonStyle.green, custom_id='merchants_button')
    async def merchant_button(self, interaction: Interaction, button: ui.Button):
        await role_handler(
            interaction,
            "Not Merchants",
            f"{interaction.user.mention} You have hidden the 💰**Trading**💰 section",
            f"{interaction.user.mention} you have reveled the 💰**Trading**💰 section",
        )

    @ui.button(emoji="🐉", style=ButtonStyle.red, custom_id='dungeoneers_button')
    async def dungeoneers_button(self, interaction: Interaction, button: ui.Button):
        await role_handler(
            interaction,
            "Not Dungeoneers",
            f"{interaction.user.mention} You have hidden the 🐉**Dungeons**🐉 section",
            f"{interaction.user.mention} you have reveled the 🐉**Dungeons**🐉 section",
        )

    @ui.button(emoji="⛏", style=ButtonStyle.gray, custom_id='miners_button')
    async def miners_button(self, interaction: Interaction, button: ui.Button):
        await role_handler(
            interaction,
            "Not Miners",
            f"{interaction.user.mention} You have hidden the ⛏**Mining**⛏ section",
            f"{interaction.user.mention} you have reveled the ⛏**Mining**⛏ section",
        )

    @ui.button(emoji="🎣", style=ButtonStyle.blurple, custom_id='fishers_button')
    async def fishers_button(self, interaction: Interaction, button: ui.Button):
        await role_handler(
            interaction,
            "Not Fishers",
            f"{interaction.user.mention} You have hidden the 🎣**Fishing**🎣 section",
            f"{interaction.user.mention} you have reveled the 🎣**Fishing**🎣 section",
        )


class NotificationSelectionButtons(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(emoji="📢", style=ButtonStyle.red, custom_id='announcement_button')
    async def announcement_button(self, interaction: Interaction, button: ui.Button):
        await role_handler(
            interaction,
            "Announcement",
            f"{interaction.user.mention} You will be pinged when a new 📢**Announcement**📢 is posted",
            f"{interaction.user.mention} You will no longed be pinged when a new 📢**Announcement**📢 is posted"
        )

    @ui.button(emoji="🎁", style=ButtonStyle.green, custom_id='giftaway_button')
    async def giveaway_button(self, interaction: Interaction, button: ui.Button):
        await role_handler(
            interaction,
            "Giveaway",
            f"{interaction.user.mention} You will be pinged when a new 🎁**Giveaway**🎁 is started",
            f"{interaction.user.mention} You will no longed be pinged when a new 🎁**Giveaway**🎁 is started"
        )

    @ui.button(emoji="🤝", style=ButtonStyle.blurple, custom_id='partner_button')
    async def partner_button(self, interaction: Interaction, button: ui.Button):
        await role_handler(
            interaction,
            "Partners",
            f"{interaction.user.mention} You will be pinged when a new 🤝**Partner**🤝 ad is posted",
            f"{interaction.user.mention} You will no longed be pinged when a new 🤝**Partner**🤝 ad is posted"
        )

    @ui.button(emoji="🤔", style=ButtonStyle.grey, custom_id='seraphine_ask_button')
    async def seraphine_ask_button(self, interaction: Interaction, button: ui.Button):
        await role_handler(
            interaction,
            "Seraphine Follower",
            f"{interaction.user.mention} You will be pinged when a new 🤔**Seraphine Question**🤔 is posted",
            f"{interaction.user.mention} You will no longed be pinged when a new 🤔**Seraphine Question**🤔 is posted"
        )

class CarryingPingSelection(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(emoji="⚔", style=ButtonStyle.blurple, custom_id='carrying_ping_button')
    async def carrying_ping_button(self, interaction: Interaction, button: ui.Button):
        await role_handler(
            interaction,
            "⚔️Carrying Ping⚔️",
            f"{interaction.user.mention} You will be pinged when a carrying ticket for your floor(s) is created",
            f"{interaction.user.mention} You will no longer be pinged when a carrying ticket for your floor(s) is created"
        )


class SectionSelectionHandler(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.role_selection_view_added = False

    @commands.command()
    @commands.is_owner()
    async def section_hiding_start(self, ctx):
        start_embed = Embed(
            description="Let us introduce 🤩**_section hiding roles_**🤩, with the roles, you can hide the sections "
                        "you don't want to see!\n"
                        "The sections are explained bellow, to help you decide if you want to hide them or not!!!\n\n"
                        "Click the buttons bellow to hide the sections and click again to reveal them.\n",
            colour=0xfce9ae
        ).set_author(
            name="Skyhub is too clustered for you?",
            icon_url=ctx.guild.icon.url
        ).add_field(
            name="💰 Merchant section 💰",
            value="This section is where you trade, lowball and determining the risk you have when you are trading "
                  "by using our scammer database system and our trading honor system.\n"
                  "You can also get your item to be crafted by someone who have the recipe, and in return, they will gain"
                  "trading honor",
            inline=False
        ).add_field(
            name="🐉 Dungeon section 🐉",
            value="Have you ever wanted a competent team when you are doing dungeons or find carries so you can use your gear?\n"
                  "Wait no more, our dungeon section allows you to do that in no time. \n"
                  "Our dungeon honor system allows you to not be scammed when you are asking for dungeon services too.",
            inline=False
        ).add_field(
            name="⛏ Mining section ⛏",
            value="Mining in general is deemed the most profitable consistence money making method,\n"
                  "if you want to get 30m/h consistently, and the fastest way to do so, mining section is for you.\n"
                  "There will be guides to the best way to grind powder, and the best way to progress your mining gear.\n"
                  "you and other miners can also alert each other of useful mining events and organise propaganda for "
                  "Cole.",
            inline=False
        ).add_field(
            name="🎣 Fishing section 🎣",
            value="Are you early game and want to make some money, or are you going for fishing 60?\n"
                  "From legacy barn fishing, to trophy fishing and xp fishing in the newest crimson isle update,\n"
                  "the experienced fishers will give you advices to how to fish with different method in this section\n"
                  "You can also find fishing loot sharing parties or even hop into the fishing vc to make fishing "
                  "bearable",
            inline=False
        )
        await ctx.send(embed=start_embed, view=SectionSelectionButtons())

    @commands.command()
    @commands.is_owner()
    async def notification_selection_start(self, ctx):
        start_embed = Embed(
            description="🔥**_Fear no more!_**🔥\n"
                        "By clicking those buttons below, you can choose to be pinged when something of your interest "
                        "is happening in skyhub!\n"
                        "Click again to stop being pinged!",
            colour=0xffb52e,
        ).set_author(
            name="Finding it hard to keep track of giveaways and updates in skyhub?",
            icon_url=ctx.guild.icon.url
        ).add_field(
            name="📢 Announcements 📢",
            value="If you want to know the latest news about skyhub, e.g events and announcements, "
                  "this role is perfect for you!",
            inline=False
        ).add_field(
            name="🎁 Giveaways 🎁",
            value="_'Best money making method is to get 1bil from a giftaway'_ ~ one wise person\n"
                  "Do you want to be like that one wise person?\n"
                  "If so, get the giveaway role and get notified when a giftaway starts!",
            inline=False
        ).add_field(
            name="🤝 Partners 🤝",
            value="_Ahh ~~~ discord server partners_, if you own a discord server, "
                  "you will know that it is one of the best ways to get members.\n"
                  "Get this role to support skyhub's partners, and in turn they will support us more, "
                  "which in turn help skyhub to flourish even more! ",
            inline=False
        ).add_field(
            name="💡 Seraphine Follower 💡",
            value="_Are you interested in knowing more about hypixel skyblock?_\n"
                  "I, Seraphine, asks a skyblock question every 2-7 minutes based on the number of members online.\n"
                  "Get notified when new questions are posted, and win 1 skybie for sending the first correct answer!",
            inline=False
        )
        await ctx.send(embed=start_embed, view=NotificationSelectionButtons())

    @commands.command()
    @commands.is_owner()
    async def carrier_ping_selection_start(self, ctx):
        start_embed = Embed(
            description="**Introducing ⚔_Carrier Ping_⚔**\n"
                        "Click the button below to be pinged when you are carrying, click again to stop being pinged",
            colour=0xB24BF3,
        ).set_author(
            name="Don't want to be pinged when you are not carrying?",
            icon_url=ctx.guild.icon.url
        )
        await ctx.send(embed=start_embed, view=CarryingPingSelection())

    async def cog_load(self):
        self.client.add_view(SectionSelectionButtons())
        self.client.add_view(NotificationSelectionButtons())
        self.client.add_view(CarryingPingSelection())


async def setup(client):
    await client.add_cog(SectionSelectionHandler(client))
