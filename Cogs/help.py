from discord import utils, Embed, ui, PartialEmoji, Colour, ButtonStyle, Interaction
from discord.ext import commands
from dotenv import load_dotenv
load_dotenv()

class HelpButtons(ui.View):
    def __init__(self, embed_list, author):
        super().__init__(timeout=180)
        self.help_embeds_list = embed_list
        self.author = author
        self.footer_list = [
            "Seraphine by Hypicksell • Page 1",
            "Skybie Commands • Page 2",
            "Honor Commands • Page 3",
            "Seraphine Commands • Page 4",
            "Bump Commands • Page 5",
            "Hypixel Commands • Page 6",
            "Scammer Datbase Commands • Page 7",
            "Fun Commands • Page 8",
            "Utility Commands • Page 9",
        ]
        self.current = 0

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        await self.message.edit(view=self)
        await self.message.edit(
            embed=Embed(
                title="This help command is now timed out",
                description="Do `!help` to make a new one",
                colour=0xF9423A,
            )
        )
    async def interaction_check(self, interaction):
        if self.author != interaction.user:
            await interaction.response.send_message(
                "Ey, make your own help command",
                ephemeral=True
            )
            return
        return True

    @ui.button(emoji=PartialEmoji.from_str("<:fast_backward:1015264717570322483>"), style=ButtonStyle.blurple)
    async def fast_backward(self, interaction: Interaction, button: ui.Button):
        self.current = 0
        await interaction.response.edit_message(
            embed=self.help_embeds_list[self.current].set_footer(
                text=self.footer_list[self.current]
            )
        )

    @ui.button(emoji=PartialEmoji.from_str("<:backward:1004400601146343535>"), style=ButtonStyle.blurple)
    async def backward(self, interaction: Interaction, button: ui.Button):
        self.current -= 1
        if self.current < 0:
            self.current = len(self.help_embeds_list) - 1
        await interaction.response.edit_message(
            embed=self.help_embeds_list[self.current].set_footer(
                text=self.footer_list[self.current]
            )
        )

    @ui.button(emoji=PartialEmoji.from_str("<:forward:1004400629327872020>"), style=ButtonStyle.blurple)
    async def forward(self, interaction: Interaction, button: ui.Button):
        self.current += 1
        if self.current > len(self.help_embeds_list) - 1:
            self.current = 0
        await interaction.response.edit_message(
            embed=self.help_embeds_list[self.current].set_footer(
                text=self.footer_list[self.current]
            )
        )

    @ui.button(emoji=PartialEmoji.from_str("<:fast_forward:1015264716072960010>"), style=ButtonStyle.blurple)
    async def fast_forward(self, interaction: Interaction, button: ui.Button):
        self.current = len(self.help_embeds_list) - 1
        await interaction.response.edit_message(
            embed=self.help_embeds_list[self.current].set_footer(
                text=self.footer_list[self.current]
            )
        )


class HelpCommand(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.command()
    async def help(self, ctx, *, category=None):
        seraphine_commands_channel = utils.get(ctx.guild.text_channels, name="👩seraphine-commands")
        dungeon_honor_commands = utils.get(ctx.guild.text_channels, name="🏅carrying-honor-commands")
        trading_honor_commands = utils.get(ctx.guild.text_channels, name="🏅trading-honor-commands")

        allowed_channels = [seraphine_commands_channel.id, dungeon_honor_commands.id, trading_honor_commands.id]
        if ctx.channel.id not in allowed_channels and not ctx.author.guild_permissions.administrator:
            await ctx.send(
                f"Use this command in {seraphine_commands_channel.mention}", delete_after=10
            )
            return

        seraphine_channel = utils.get(ctx.guild.text_channels, name="👩seraphine-channel")
        bump_channel = utils.get(ctx.guild.text_channels, name="👊bumping")
        help_embeds_dict = {
            "main": Embed(
                title="Seraphine Commands list",
                description=f"You can use the first two letters of the help command to trigger it,"
                            f"\n for example `!help se` will trigger `!help seraphine`"
                            f"\n[Commands are not CaSe SeNsItiVe](https://youtu.be/dQw4w9WgXcQ)",
                colour=Colour.blue(),
            ).add_field(name="🌟Skybies Commands", value="`!help skybies`")
            .add_field(name="🏅Honor Commands", value="`!help honor`")
            .add_field(name="👩Seraphine Info", value="`!help seraaphine`")
            .add_field(name="👊Bump Commands", value="`!help bump`")
            .add_field(name="⛏Hypixel Commands", value="`!help hypixel`")
            .add_field(name="🕵️Scammer database", value="`!help scammer`")
            .add_field(name="🎲Fun Commands", value="`!help fun`")
            .add_field(name="📋Utilities Commands", value="`!help utilities`")
            .set_footer(text="Made By Hypicksell"),

            "sk": Embed(
                title="skybies Commands",
                description=(
                    "skybies are Skyhub's currency\n"
                    "You get it by welcoming members ,bumping the server, keeping your chat activity streak, "
                    "carrying/ crafting items for others, and answering Seraphine questions!\n"
                    f"Do `!suggest (ideas)` in {seraphine_commands_channel.mention} to give us ideas for how members can obtain and use skybies"
                ),
                colour=0x2E5984,
            ).add_field(
                name="skybies Commands:",
                value="-!skybie\n-!skybie leaderboard\n-!skybie shop",
                inline=False,
            ).add_field(
                name="!skybies",
                value="Get skybies info of a user\n```!skybie or !skybie @user```",
                inline=False,
            ).add_field(
                name="!skybie leaderboard",
                value="Get server ranking of your lifetime skybie count\n```!skybie leaderboard```",
                inline=False,
            ).add_field(
                name="!skybie shop",
                value="purchase roles and server perks with skybies\n```!skybie shop```",
                inline=False,
            ),

            "ho": Embed(
                title="Honor Commands Help",
                colour=0xF1EB9C
            ).set_author(
                name=ctx.author,
                icon_url=ctx.author.avatar.url
            ).add_field(
                name="Honor Commands",
                value="-!Honor\n-!Honor leaderboard\n-!Honor history\n-!Honor stats",
                inline=False,
            ).add_field(
                name="!honor",
                value="Gives a honor point to a user\n```!honor (@user / user id / user#0000)```",
                inline=False,
            ).add_field(
                name="!honor leaderboard",
                value="Honor points leaderboard of last month\n```!honor leaderboard```",
                inline=False,
            ).add_field(
                name="!honor history",
                value="Listing all honor points of a user\n```!honor history or !honour history (@user/ user id/ user#0000)```",
                inline=False,
            ).add_field(
                name="!honor stats",
                value="Show statistics of your honor points\n```!honor stats or !honour stats (@user/ user id/ user#0000)```",
                inline=False
            ),

            "se": Embed(
                title="Seraphine Help",
                description="Seraphine took in the form of a chat bot in our server"
                            "\nYou can suggest topics to be added to seraphine!!!",
                colour=0x6d00c1,
            ).set_thumbnail(
                url=ctx.guild.icon.url
            ).add_field(
                name="Seraphine",
                value=f"Use it in{seraphine_channel.mention} or Dm Seraphine"
                      f"\n```Powered by brainshop ai,you can suggest topics to be added into the bot.```",
                inline=False,
            ),

            "bu": Embed(
                title="Bump Help",
                description=(
                    f"Skyhub disboard bump reminder system in {bump_channel.mention}\n"
                    "Every two hours,disboard will allow us to bump the server and put us on top of disboard\n"
                    f"Do `/bump` in {bump_channel.mention} to bump and support the server!\n"
                    f"For every bump, you get 2 skybies and 1 bump score, if you got the highest bump score,\n"
                    f"you get the bump king role! The bump score resets every week!"
                ),
                colour=0x90EE90,
            ).set_thumbnail(
                url=ctx.guild.icon.url
            ).add_field(
                name="Bump leaderboard",
                value="Skyhub list of Top bumpers! Resets every week"
                      "\n```!bl```",
                inline=False,
            ),

            "hy": Embed(
                title="Hypixel Commands Help",
                colour=0xC4A484
            ).set_thumbnail(
                url=ctx.guild.icon.url
            ).add_field(
                name="Hypixel Commands:",
                value="-!online\n-!mcinfo\n-!wiki",
                inline=False,
            ).add_field(
                name="!online",
                value="Get info of any minecraft server\n```!online (ip) e.g mc.hypixel.net```",
                inline=False,
            ).add_field(
                name="!mcinfo",
                value="Get account information of a Mc Java account\n```!mcinfo (Acoount Username)e.g MetallicWeb7080```",
                inline=False,
            ).add_field(
                name="!wiki",
                value="Search up anything from hypixel wiki\n```!wiki (search term)e.g Seraphine```",
                inline=False,
            ),
            "sc": Embed(
                title="Scammer Database Help",
                colour=0xD3D3D3
            ).set_thumbnail(
                url=ctx.guild.icon.url
            ).add_field(
                name="Scammer Database Commands:",
                value="-/is_scammer\n-!scammer_download",
            ).add_field(
                name="/is_scammer",
                value="Check if a user is a scammer\n```/is_scammer (option: ign, uuid, discord_id)```",
                inline=False,
            ).add_field(
                name="!scammer_download",
                value="Download the scammer database as a single json file\n```!scammer_download```",
            ),
            "fun": Embed(
                title="Fun Commands Help",
                colour=0xFE994A
            ).set_thumbnail(
                url=ctx.guild.icon.url
            ).add_field(
                name="FunCommands:",
                value="-!memes\n-!translate\n-!isrickroll\n-!pretend\n-!paint",
                inline=False,
            ).add_field(
                name="!memes", value="Get Mincraft memes!!!\n```!memes```", inline=False
            ).add_field(
                name="!translate",
                value="Translate a text to a language you like!!!\n```!tr (language) (your text to translate)```",
                inline=False,
            ).add_field(
                name="!isrickroll",
                value="Detect if a webpage's html page have rickroll key words\n```!irr (url)```",
            ).add_field(
                name="!pretend",
                value="Say something pretending to be another user\n```!pr @user message```",
                inline=False,
            ).add_field(
                name="!paint",
                value="Forces Seraphine to paint an image for you, powered by dall-e mini```!paint (prompt)```",
            ),
            "ut": Embed(
                title="Utilities Commands Help",
                colour=0xD3D3D3
            ).set_thumbnail(
                url=ctx.guild.icon.url
            ).add_field(
                name="UtilitiesCommands:",
                value="-!whois\n-!stats\n-!suggest",
                inline=False,
            ).add_field(
                name="!whois",
                value="Get info of a certain user\n```!whois or !whois (@user)```",
                inline=False,
            ).add_field(
                name="!stats",
                value="Get stats of Skyhub discord server\n```!stats```",
                inline=False,
            ).add_field(
                name="!suggest",
                value="Suggest ideas to be added into the bot!!!\n```!suggest (idea)```",
                inline=False,
            )
        }

        help_view = HelpButtons(list(help_embeds_dict.values()), ctx.author)
        if category is None:
            help_view.message = await ctx.send(embed=help_embeds_dict.get("main"), view=help_view)

        else:
            for key in help_embeds_dict.keys():
                if category.casefold().startswith(key):
                    await ctx.send(embed=help_embeds_dict[key])
                    break
            else:
                await ctx.send(f"Your catagory: `{category}` is not found, do `!help` for the main help menu")


async def setup(client):
    await client.add_cog(HelpCommand(client))
