from nextcord.ext import commands
import nextcord
import asyncio


class GitHubButton(nextcord.ui.View):
    def __init__(self):
        super().__init__()
        url = "https://github.com/bensonchow123/Seraphine"
        self.add_item(nextcord.ui.Button(label='GitHub link for bot', url=url))


class InformationCommands(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.command()
    async def whois(self, ctx, member: nextcord.Member = None):
        if ctx.channel.id != self.bot_channel.id and not ctx.author.guild_permissions.administrator:
            await ctx.send("Use this command in the <#850027624361230336> channel", delete_after=10)
            return
        else:
            if not member:
                member = ctx.message.author
            roles = [role for role in member.roles]
            embed = nextcord.Embed(colour=nextcord.Colour.green(), timestamp=ctx.message.created_at,
                                   title=f"User Info of {member} in Skyhub")
            embed.set_thumbnail(url=member.avatar.url)
            embed.set_footer(text=f"Requested by {ctx.author}")
            embed.add_field(name="ID:", value=member.id)
            embed.add_field(name="Display Name:", value=member.display_name)

            embed.add_field(name="Created Account On:", value=member.created_at.strftime("%a, %#d %B %Y, %I:%M %p UTC"))
            embed.add_field(name="Joined Server On:", value=member.joined_at.strftime("%a, %#d %B %Y, %I:%M %p UTC"))

            embed.add_field(name="Roles:", value="\n".join([role.mention for role in roles][1:]))
            embed.add_field(name="Highest Role:", value=member.top_role.mention)
            await ctx.send(embed=embed)

    @commands.command()
    async def stats(self, ctx):
        embed = nextcord.Embed(title="Server information", colour=nextcord.Colour.green(),
                               timestamp=ctx.message.created_at)

        embed.set_thumbnail(url=ctx.guild.icon.url)
        true_member_count = [m for m in ctx.guild.members if not m.bot]

        statuses = [len(list(filter(lambda m: str(m.status) == "online", true_member_count))),
                    len(list(filter(lambda m: str(m.status) == "idle", true_member_count))),
                    len(list(filter(lambda m: str(m.status) == "dnd", true_member_count))),
                    len(list(filter(lambda m: str(m.status) == "offline", true_member_count)))]
        fields = [("ID", ctx.guild.id, True),
                  ("Owner", ctx.guild.owner, True),
                  ("Region", "United Kingdom", True),
                  ("Created at", ctx.guild.created_at.strftime("%d/%m/%Y %H:%M:%S"), True),
                  ("TotalMembers", len(ctx.guild.members), True),
                  ("Members", len(list(filter(lambda m: not m.bot, ctx.guild.members))), True),
                  ("Bots", len(list(filter(lambda m: m.bot, ctx.guild.members))), True),
                  ("Banned members", len(await ctx.guild.bans()), True),
                  ("Statuses", f"🟢 {statuses[0]} 🟠 {statuses[1]}\n 🔴 {statuses[2]} ⚪ {statuses[3]}", True),
                  ("Text channels", len(ctx.guild.text_channels), True),
                  ("Voice channels", len(ctx.guild.voice_channels), True),
                  ("Categories", len(ctx.guild.categories), True),
                  ("Roles", len(ctx.guild.roles), True),
                  ("Invites", len(await ctx.guild.invites()), True),
                  ("\u200b", "\u200b", True)]
        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)
            embed.set_footer(text=f"Requested by {ctx.author}")
        if ctx.channel.id != self.bot_channel.id and not ctx.author.guild_permissions.administrator:
            await ctx.send("Use this command in the <#850027624361230336> channel", delete_after=10)
            return
        else:
            await ctx.send(embed=embed)

    @commands.Cog.listener("on_message")
    async def discord_bot_introduction(self, message: nextcord.Message):
        if message.author.bot:
            return
        if message.channel.id == self.bump_channel.id:
            return
        if self.client.user not in message.mentions:
            return
        if message.reference:
            return
        file = nextcord.File(r"./Utilities/seraphine.mp3")
        await message.reply(file=file,
                            content="Play the audio file below to know more about me!",
                            view=GitHubButton())

    @commands.command()
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def suggest(self, ctx, *, suggestion):
        channel = nextcord.utils.get(ctx.guild.text_channels, name='💡suggestions')
        if ctx.channel.id != self.bot_channel.id and not ctx.author.guild_permissions.administrator:
            await ctx.channel.send("Use this command in the #🤖〢bot-commands channel", delete_after=20)
            await ctx.message.delete()
        else:
            await ctx.message.add_reaction("✅")
            suggest_embed = nextcord.Embed(colour=0xFF0000, timestamp=ctx.message.created_at)
            suggest_embed.set_thumbnail(url=f"{ctx.author.avatar.url}")
            suggest_embed.add_field(name='Submitter:', value=f'{ctx.author}', inline=False)
            suggest_embed.add_field(name='Suggestion:', value=f"```{suggestion}```", inline=False)
            suggest_embed.set_footer(text=f"UserID:{ctx.author.id}", icon_url=ctx.guild.icon.url)
            message = await channel.send(embed=suggest_embed)
            await message.add_reaction('✅')
            await message.add_reaction('❌')
            await asyncio.sleep(2)
            await ctx.message.delete()

    @suggest.error
    async def suggest_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("you need an idea to use the command , use <!suggest (idea)> in <#850027624361230336>",
                           delete_after=10)
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send("You can only suggest an idea every one minute")

    @commands.Cog.listener()
    async def on_ready(self):
        self.guild = self.client.get_guild(844231449014960160)
        self.bot_channel = nextcord.utils.get(self.guild.text_channels, name="👩seraphine-commands")
        self.bump_channel = nextcord.utils.get(self.guild.text_channels, name="👊bumping")


def setup(client):
    client.add_cog(InformationCommands(client))
