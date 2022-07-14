from nextcord import ButtonStyle, ui, Interaction, utils, Embed
from nextcord.ext import commands

class SectionSelectionButtons(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(emoji="💰", style=ButtonStyle.green, custom_id='MerchantsButton')
    async def merchant_button(self, button: ui.Button, interaction: Interaction):
        guild = interaction.guild
        merchant_role = utils.get(guild.roles, name="Merchants")
        if merchant_role in interaction.user.roles:
            await interaction.user.remove_roles(merchant_role)
            await interaction.response.send_message(
                f"{interaction.user.mention} You have hidden the 💰**Trading**💰 section",
                ephemeral=True
            )
        elif merchant_role not in interaction.user.roles:
            await interaction.user.add_roles(merchant_role)
            await interaction.response.send_message(
                f"{interaction.user.mention} you have reveled the 💰**Trading**💰 section ",
                ephemeral=True
            )

    @ui.button(emoji="🐉", style=ButtonStyle.red, custom_id='DungeoneersButton')
    async def dungeoneers_button(self, button: ui.Button, interaction: Interaction):
        guild = interaction.guild
        Dungeoneers_role = utils.get(guild.roles, name="Dungeoneers")
        if Dungeoneers_role in interaction.user.roles:
            await interaction.user.remove_roles(Dungeoneers_role)
            await interaction.response.send_message(
                f"{interaction.user.mention} You have hidden the 🐉**Dungeons**🐉 section",
                ephemeral=True
            )
        elif Dungeoneers_role not in interaction.user.roles:
            await interaction.user.add_roles(Dungeoneers_role)
            await interaction.response.send_message(
                f"{interaction.user.mention} you have reveled the 🐉**Dungeons**🐉 section ",
                ephemeral=True
            )

    @ui.button(emoji="⛏", style=ButtonStyle.gray, custom_id='MinersButton')
    async def miners_button(self, button: ui.Button, interaction: Interaction):
        guild = interaction.guild
        miners_role = utils.get(guild.roles, name="Miners")
        if miners_role in interaction.user.roles:
            await interaction.user.remove_roles(miners_role)
            await interaction.response.send_message(
                f"{interaction.user.mention} You have hidden the ⛏**Mineing**⛏ section",
                ephemeral=True
            )
        elif miners_role not in interaction.user.roles:
            await interaction.user.add_roles(miners_role)
            await interaction.response.send_message(
                f"{interaction.user.mention} you have reveled the ⛏**Mineing**⛏ section ",
                ephemeral=True
            )

    @ui.button(emoji="🎣", style=ButtonStyle.blurple, custom_id='FishersButton')
    async def fishers_button(self, button: ui.Button, interaction: Interaction):
        guild = interaction.guild
        fishers_role = utils.get(guild.roles, name="Fishers")
        if fishers_role in interaction.user.roles:
            await interaction.user.remove_roles(fishers_role)
            await interaction.response.send_message(
                f"{interaction.user.mention} You have hidden the 🎣**Fishing**🎣 section",
                ephemeral=True
            )
        elif fishers_role not in interaction.user.roles:
            await interaction.user.add_roles(fishers_role)
            await interaction.response.send_message(
                f"{interaction.user.mention} you have reveled the 🎣**Fishing**🎣 section ",
                ephemeral=True
            )
    @ui.button(emoji="🎁", style=ButtonStyle.green, custom_id='GiftteeButton')
    async def gifttee_button(self, button: ui.Button, interaction: Interaction):
        guild = interaction.guild
        giftee_role = utils.get(guild.roles, name="Giftee")
        if giftee_role in interaction.user.roles:
            await interaction.user.remove_roles(giftee_role)
            await interaction.response.send_message(
                f"{interaction.user.mention} You have hidden the 🎁**Giveaway**🎁 section",
                ephemeral=True
            )
        elif giftee_role not in interaction.user.roles:
            await interaction.user.add_roles(giftee_role)
            await interaction.response.send_message(
                f"{interaction.user.mention} you have reveled the 🎁**Giveaway**🎁 section ",
                ephemeral=True
            )


class SectionSelectionHandler(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.role_selection_view_added = False

    @commands.Cog.listener()
    async def on_ready(self):
        self.guild = self.client.get_guild(844231449014960160)
        if not self.role_selection_view_added:
            self.client.add_view(SectionSelectionButtons())
            self.role_selection_view_added = True

    @commands.command()
    @commands.is_owner()
    async def section_selection_start(self, ctx):
        start_embed = Embed(
            description="There are 5 hidden section in skyhub, this is to improve your experience "
                        "by not filling up your discord with channel you will never use.\n"
                        "Click the buttons bellow to reveal the different sections, and click again to hide them.\n"
                        ,
            colour=0xfce9ae
        ).set_author(
            name="Thanks for joining Skyhub!"
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
        ).add_field(
            name="🎁 Giveaway section 🎁",
            value="If you want to get millions of coins or discord nitro, just by clicking a button, this section is "
                  "for you, you can also gain skybies and special roles by contributing to giveaways.",
            inline=False
        )
        await ctx.send(embed=start_embed, view=SectionSelectionButtons())

def setup(client):
    client.add_cog(SectionSelectionHandler(client))
