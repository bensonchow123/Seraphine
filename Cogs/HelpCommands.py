from nextcord import utils, Embed, ui, PartialEmoji, Colour, ButtonStyle, Interaction
from nextcord.ext import commands


class ButtonHelp(ui.View):
    def __init__(self, embed_list, author):
        super().__init__(timeout=180)
        self.embed_list = embed_list
        self.author = author
        self.footer_list = [
            "Seraphine by Hypicksell • Page 1",
            "Skybie Commands • Page 2",
            "Honor Commands • Page 3",
            "Seraphine Commands • Page 4",
            "Bump Commands • Page 5",
            "Hypixel Commands • Page 6",
            "Fun Commands • Page 7",
            "Utility Commands • Page 8",
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

    @ui.button(
        emoji=PartialEmoji.from_str("<:backward:886268967944073236>"),
        label="Prior Page",
        style=ButtonStyle.danger,
    )
    async def backward(
        self, button: ui.Button, interaction: Interaction
    ):
        self.current -= 1
        if self.current < 0:
            self.current = len(self.embed_list) - 1
        await interaction.response.edit_message(
            embed=self.embed_list[self.current].set_footer(
                text=self.footer_list[self.current]
            )
        )

    @ui.button(
        emoji=PartialEmoji.from_str("<:forward:886268968032149534>"),
        label="Next Page ",
        style=ButtonStyle.green,
    )
    async def forward(
        self, button: ui.Button, interaction: Interaction
    ):
        self.current += 1
        if self.current > len(self.embed_list) - 1:
            self.current = 0
        await interaction.response.edit_message(
            embed=self.embed_list[self.current].set_footer(
                text=self.footer_list[self.current]
            )
        )


class HelpCommand(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def help(self, ctx, *, category=None):
        allowed_channels = [self.seraphine_commands_channel.id, self.dungeon_honor_commands.id, self.trading_honor_commands.id]
        if ctx.channel.id not in allowed_channels and not ctx.author.guild_permissions.administrator:
            await ctx.send(
                f"Use this command in {'or'.join(allowed_channels)}", delete_after=10

            )
            return

        self.main_help_command = (
            Embed(
                title="Seraphine Command list:",
                description=f"You can use the first letter of the help command to trigger it, for example `!help s`"
                            f"\n[Commands are not CaSe SeNsItiVe](https://youtu.be/dQw4w9WgXcQ)",
                colour=Colour.blue(),
            )
            .add_field(name="🌟Skybies Commands", value="`!Help Skybies`")
            .add_field(name="🏅Honor Commands", value="`!Help Honor`")
            .add_field(name="👩Seraphine Info", value="`!Help Seraphine`")
            .add_field(name="👊Bump Commands", value="`!Help Bump`")
            .add_field(name="⛏Hypixel Commands", value="`!Help Hypixel`")
            .add_field(name="🎲Fun Commands", value="`!Help Fun`")
            .add_field(name="📋Utilities Commands", value="`!Help Ut`")
            .set_footer(text="Made By Hypicksell")
        )

        self.skybies_embed = (
            Embed(
                description=(
                    "Skybies are Skyhub's currency\n"
                    "You get it by welcoming members ,bumping the server and keeping your chat activity streak\n"
                    f"Do `!suggest (ideas)` in {self.seraphine_commands_channel.mention} to give us ideas for how members can obtain and use skybies"
                ),
                colour=0x2E5984,
            ).set_author(
                name=ctx.author,
                icon_url=ctx.author.avatar.url
            ).add_field(
                name="Skybies Commands:",
                value="-!Skybie\n-!Skybie leaderboard\n-!Skybie shop\n-!giftcards",
                inline=False,
            ).add_field(
                name="!Skybies",
                value="Get skybies info of a user\n```!skybie or !skybie @user```",
                inline=False,
            ).add_field(
                name="!Skybie leaderboard",
                value="Get server ranking of your lifetime skybie count\n```!skybie leaderboard```",
                inline=False,
            ).add_field(
                name="!Skybie shop",
                value="purchase skyblock coins and server perks with skybies\n```!skybie shop```",
                inline=False,
            ).add_field(
                name="!giftcards",
                value="Checking the giftcards that you own\n```!giftcards```",
            )
        )

        self.honor_embed = (
            Embed(
                title="Honor Commands Help",
                colour=0xF1EB9C
            )
        ).set_author(
                name=ctx.author,
                icon_url=ctx.author.avatar.url
        ).add_field(
            name="Honor Commands",
            value="-!Honor\n-!Honor leaderboard\n-!Honor history\n-!Honor stats",
            inline=False,
        ).add_field(
            name="!Honor",
            value="Gives a honor point to a user\n```!honor (@user / user id / user#0000)",
            inline=False,
        ).add_field(
            name="!Honor leaderboard",
            value="Honor points leaderboard of last month\n```!honor leaderboard```",
            inline=False,
        ).add_field(
            name="!Honor history",
            value="Listing all honor points of a user\n```!honor history or !honour history (@user/ user id/ user#0000)```",
            inline=False,
        ).add_field(
            name="!Honor stats",
            value="Show statistics of your honor points\n```!honor stats or !honour stats (@user/ user id/ user#0000)```",
            inline=False,
        )

        self.seraphine_embed = (
            Embed(
                title="Seraphine Help",
                description="Seraphine took in the form of a chat bot in our server"
                            "\nYou can suggest topics to be added to seraphine!!!",
                colour=0x6d00c1,
            ).set_author(
                name=ctx.author,
                icon_url=ctx.author.avatar.url
            ).set_thumbnail(
                url=ctx.guild.icon.url
            ).add_field(
                name="Seraphine",
                value=f"Use it in{self.seraphine.mention} or Dm Seraphine"
                      f"\n```Powered by brainshop ai,you can suggest topics to be added into the bot.```",
                inline=False,
            )
        )

        self.bump_embed = (
            Embed(
                title="Bump Help",
                description=(
                    f"Skyhub disboard bump reminder system in {self.bump_channel.mention}\n"
                    "Every two hours,disboard will allow us to bump the server and put us on top of disboard\n"
                    f"Do `/bump` in {self.bump_channel.mention} to bump and support the server!\n"
                    f"For every bump, you get 2  and 1 bump score, if you got the highest bump score,\n"
                    f"you get the bump king role! The bump score resets every week!"
                ),
                colour=0x90EE90,
            ).set_author(
                name=ctx.author,
                icon_url=ctx.author.avatar.url
            ).set_thumbnail(
                url=ctx.guild.icon.url
            ).add_field(
                name="Bump leaderboard",
                value="Skyhub list of Top bumpers! Resets every week"
                      "\n```!bl```",
                inline=False,
            )
        )

        self.hypixel_embed = (
            Embed(
                title="Hypixel Commands Help",
                colour=0xC4A484
            ).set_author(
                name=ctx.author,
                icon_url=ctx.author.avatar.url
            ).set_thumbnail(
                url=ctx.guild.icon.url
            ).add_field(
                name="Hypixel Commands:",
                value="-!online\n-!mcinfo\n-!mcwiki",
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
                value="Search up anything from hypixel wiki\n```!mcwiki (search term)e.g Seraphine```",
                inline=False,
            )
        )

        self.funcommands_embed = (
            Embed(
                title="Fun Commands Help",
                colour=0xFE994A
            ).set_author(
                name=ctx.author,
                icon_url=ctx.author.avatar.url
            ).set_thumbnail(
                url=ctx.guild.icon.url
            ).add_field(
                name="FunCommands:",
                value="-!memes\n-!translate\n-!isrickroll\n-!ip\n-!pretend",
                inline=False,
            ).add_field(
                name="!memes", value="Get Mincraft memes!!!\n```!memes```", inline=False
            ).add_field(
                name="!translate",
                value="Translate a text to a language you like!!!\n```!tr (language) (your text to translate)```",
                inline=False,
            ).add_field(
                name="!isrickroll",
                value="Detect if a webpage's html page have rick roll key words\n```!irr (url)```",
            ).add_field(
                name="!ip",
                value="Get ip info of a domain e.g google.com\n```!ip (e.g google.com)```",
                inline=False,
            ).add_field(
                name="!text_to_speach",
                value="Make your message into a sound file\n```!tts(message)```",
                inline=False,
            ).add_field(
                name="!pretend",
                value="Say something pretending to be another user\n```!pr @user message```",
                inline=False,
            )
        )

        self.utilities_embed = (
            Embed(
                title="Utilities Commands Help",
                colour=0xD3D3D3
            ).set_author(
                name=ctx.author,
                icon_url=ctx.author.avatar.url
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
        )
        embed_list = [
            self.main_help_command,
            self.skybies_embed,
            self.honor_embed,
            self.seraphine_embed,
            self.bump_embed,
            self.hypixel_embed,
            self.funcommands_embed,
            self.utilities_embed,
        ]
        view = ButtonHelp(embed_list, ctx.author)
        if category is None:
            view.message = await ctx.send(embed=self.main_help_command, view=view)

        elif str(category).casefold() in {"skybies", "skybie"}:
            await ctx.send(embed=self.skybies_embed)

        elif str(category).casefold() in {"h","honor", "honorboard"}:
            await ctx.send(embed=self.honor_embed)

        elif str(category).casefold() in {"seraphine", "s"}:
            await ctx.send(embed=self.seraphine_embed)

        elif str(category).casefold() in {"bump", "bumps"}:
            await ctx.send(embed=self.bump_embed)

        elif str(category).casefold() in {"hypixel", "hypixel"}:
            await ctx.send(embed=self.hypixel_embed)

        elif str(category).casefold() in {"fun", "funcommands", "funcommand"}:
            await ctx.send(embed=self.funcommands_embed)

        elif str(category).casefold() in {"u", "ut", "utilitiescommand",}:
            await ctx.send(embed=self.utilities_embed)

    @help.error
    async def help_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(
                "Hey, use yo help command that you just made instead of making a new one"
            )

    @commands.Cog.listener()
    async def on_ready(self):
        self.guild = self.client.get_guild(844231449014960160)
        self.seraphine_commands_channel = utils.get(self.guild.text_channels, name="👩seraphine-commands")
        self.dungeon_honor_commands = utils.get(self.guild.text_channels, name="🏅dungeon-honor-commands")
        self.trading_honor_commands = utils.get(self.guild.text_channels, name="🏅trading-honor-commands")
        self.seraphine = utils.get(self.guild.text_channels, name="👩seraphine-channel")
        self.bump_channel = utils.get(self.guild.text_channels, name="👊bumping")


def setup(client):
    client.add_cog(HelpCommand(client))
