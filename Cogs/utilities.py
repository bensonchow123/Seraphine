from os import getenv

from discord.ext import commands
from discord import ui, Colour, Embed, Message, utils, File, Member
from motor.motor_asyncio import AsyncIOMotorClient
cluster = AsyncIOMotorClient(getenv("MongoDbSecretKey"))
verification_db = cluster["Skyhub"]["Verification"]

class GitHubButton(ui.View):
    def __init__(self):
        super().__init__()
        url = "https://github.com/bensonchow123/Seraphine"
        self.add_item(ui.Button(label='GitHub link for bot', url=url))


class InformationCommands(commands.Cog):
    def __init__(self, client):
        self.client = client

    @property
    def guild(self):
        return self.client.get_guild(int(getenv("GUILD_ID")))

    @property
    def seraphine_commands(self):
        return utils.get(self.guild.text_channels, name="👩seraphine-commands")

    @commands.command(alises=['info'])
    async def whois(self, ctx, member: Member = None):
        if ctx.channel.id != self.seraphine_commands.id and not ctx.author.guild_permissions.administrator:
            await ctx.send(f"Use this command in the {self.seraphine_commands} channel", delete_after=10)
            return

        if not member:
            member = ctx.message.author

        minecraft_cog = self.client.get_cog("Minecraft")

        whois_embed = Embed(
            colour=Colour.green(),
            description=
            f"**Created account on:** \n<t:{int(member.created_at.timestamp())}:f>\n"
            f"**Joined server on:** \n<t:{int(member.joined_at.timestamp())}:f>\n",
            title=f"User Info of {member.display_name}"
        ).set_thumbnail(
            url=member.avatar.url
        ).set_footer(
            text=f"Requested by {ctx.author}"
        )
        member_minecraft_info_insert = await verification_db.find_one({"discord_id": member.id})
        if member_minecraft_info_insert:
            ign = member_minecraft_info_insert["ign"]
            uuid = member_minecraft_info_insert["uuid"]
            whois_embed.add_field(
                name="MC account info:",
                value=f"IGN: `{ign}`\nUUID: `{uuid}`\n [Skycrypt](https://sky.shiiyu.moe/stats/{ign})",
                inline=False
            )

            skin_url, cape_url = await minecraft_cog.get_appearance(uuid)
            if skin_url:
                url_message = f"Skin texture: [Click here to download]({skin_url})\n"
                whois_embed.set_thumbnail(url=skin_url)
                cape_url_message = f"Cape Texture: {ign.capitalize()} have no capes"
                if cape_url:
                    cape_url_message = f"Cape texture: [Click here to download]({cape_url})"
                    whois_embed.set_thumbnail(url=cape_url)
                url_message += cape_url_message
                whois_embed.add_field(
                    name=f"Links for skin and cape (if any):",
                    value=url_message,
                    inline=False
                )

            member_hypixel_online_status = await minecraft_cog.get_hypixel_online_status(ign)
            hypixel_online_status_message = f"{member.mention} is not online on hypixel right now"
            if member_hypixel_online_status and member_hypixel_online_status["session"]["online"]:
                hypixel_online_status_message = (
                    f"{member.mention} is online on hypixel right now, "
                    f"playing {member_hypixel_online_status['game']['type']}"
                )
            whois_embed.description += f"{hypixel_online_status_message}\n"

        await ctx.send(embed=whois_embed)

    @whois.error
    async def whois_error(self, ctx, error):
        if isinstance(error, commands.MemberNotFound):
            await ctx.send(f"Member `{error.argument}` not found")
        else:
            await ctx.send(f"An error occurred, please try again")

    @commands.command()
    async def stats(self, ctx):
        embed = Embed(title="Server information", colour=Colour.green(),
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
                  ("Banned members", len([x async for x in ctx.guild.bans()]), True),
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
        if ctx.channel.id != self.seraphine_commands.id and not ctx.author.guild_permissions.administrator:
            await ctx.send(f"Use this command in the {self.seraphine_commands.mention} channel", delete_after=10)
            return
        else:
            await ctx.send(embed=embed)

    @commands.Cog.listener("on_message")
    async def discord_bot_introduction(self, message: Message):
        if message.author.bot:
            return

        if self.client.user not in message.mentions:
            return

        if message.reference:
            return

        file = File(r"./Utilities/seraphine.mp3")
        await message.reply(file=file,
                            content="Play the audio file below to know more about me!",
                            view=GitHubButton())

    @commands.command()
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def suggest(self, ctx, *, suggestion):
        channel = utils.get(ctx.guild.text_channels, name='💡suggestions')
        if ctx.channel.id != self.seraphine_commands.id and not ctx.author.guild_permissions.administrator:
            await ctx.channel.send(f"Use this command in the {self.seraphine_commands.mention}", delete_after=20)
            await ctx.message.delete()
        else:
            suggest_embed = Embed(colour=0xFF0000, timestamp=ctx.message.created_at)
            suggest_embed.set_thumbnail(url=f"{ctx.author.avatar.url}")
            suggest_embed.add_field(name='Submitter:', value=f'{ctx.author}', inline=False)
            suggest_embed.add_field(name='Suggestion:', value=f"```{suggestion}```", inline=False)
            suggest_embed.set_footer(text=f"UserID:{ctx.author.id}", icon_url=ctx.guild.icon.url)
            await channel.send(embed=suggest_embed)
            await ctx.message.delete()

    @suggest.error
    async def suggest_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                f"you need an idea to use the command , use <!suggest (idea)> in {self.seraphine_commands.mention}",
                delete_after=10
            )
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send("You can only suggest an idea every one minute")

    @commands.command(aliases=["sync"])
    @commands.is_owner()
    async def sync_slash_commands(self, ctx):
        self.client.tree.copy_global_to(guild=self.guild)
        await self.client.tree.sync(guild=self.guild)
        await ctx.send("slash commands synced")


async def setup(client):
    await client.add_cog(InformationCommands(client))
