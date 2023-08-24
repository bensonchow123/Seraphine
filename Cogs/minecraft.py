from base64 import b64decode
from io import BytesIO
from json import loads
from os import getenv
from random import choice
from urllib.parse import quote_plus
from re import sub, IGNORECASE

from aiohttp import ClientSession
from discord import Embed, ui, utils, File
from minepi import Player, uuid_to_name
from dotenv import load_dotenv
from googleapiclient.discovery import build as google
from mcstatus import JavaServer, BedrockServer
from discord.ext import commands

load_dotenv()


class MoreResultsButton(ui.View):
    def __init__(self, link):
        super().__init__()
        self.add_item(ui.Button(label='More Results', url=link))


class Minecraft(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.colors = [0xEA4335, 0x4285F4, 0xFBBC05, 0x34A853]

    @property
    def guild(self):
        return self.client.get_guild(int(getenv("GUILD_ID")))

    @property
    def seraphine_commands(self):
        return utils.get(self.guild.text_channels, name="👩seraphine-commands")

    @property
    def success_emoji(self):
        return utils.get(self.client.emojis, name="success")

    async def render_skin(self, uuid):
        p = Player(uuid="1cb4b37f623d439d9528d17e3a452f0a")  # create a Player object by UUID
        await p.initialize()
        im = await p.skin.render_skin(hr=180, vr=0)
        bytes = BytesIO()
        im.save(bytes, 'PNG')
        bytes.seek(0)
        return bytes

    async def get_hypixel_online_status(self, ign):
        uuid = await uuid_to_name(ign)
        async with ClientSession() as session:
            async with session.get(
                    f"https://api.hypixel.net/status?uuid={uuid}",
                    headers={"API-Key": getenv("HYPIXEL_API_KEY")},
            ) as response:
                if response.status == 200:
                    hypixel_status = await response.json()
                    return hypixel_status

    async def get_appearance(self, uuid):
        async with ClientSession() as session:
            async with session.get(f"https://sessionserver.mojang.com/session/minecraft/profile/{uuid}") as r:
                appearance_dict = await r.json()
        if not appearance_dict.get("errorMessage"):
            appearance_dict = loads((b64decode(appearance_dict["properties"][0]["value"])))
            skin_url = appearance_dict["textures"]["SKIN"]["url"]
            cape_url = appearance_dict["textures"]["CAPE"]["url"] if "CAPE" in appearance_dict["textures"] else None
            return skin_url, cape_url
        return None, None

    @commands.command()
    async def mcinfo(self, ctx, *, ign):
        if ctx.channel.id != self.seraphine_commands.id and not ctx.author.guild_permissions.administrator:
            await ctx.send(f"Use this command in the {self.seraphine_commands.mention} channel", delete_after=10)
            return
        ign = ign.strip()
        async with ctx.typing():
            success_emoji = utils.get(self.client.emojis, name="success")
            try:
                uuid = await uuid_to_name(ign)

            except ValueError:
                await ctx.reply(
                    embed=Embed(title="Account not found", timestamp=ctx.message.created_at).set_image(
                        url="https://i.imgur.com/hlnwEMu.png"
                    ).set_footer(
                        text=f"This command only supports Java.\nRequested by {ctx.author.display_name}"
                    ),
                    mention_author=False
                )
                return

            skin_url, cape_url = await self.get_appearance(uuid)
            rendered_skin_png = File(await self.render_skin(uuid), 'skin.png')
            mcinfo_embed = Embed(
                title=f"{success_emoji}Minecraft Java account info of {ign}:",
                description=f"Uuid: {uuid}",
                colour=0xf4c2c2,
            ).set_footer(
                text=f"This command only supports Java. Requested by {ctx.author.display_name}"
            )
            if skin_url:
                url_message = f"Skin texture: [Click here to download]({skin_url})\n"
                mcinfo_embed.set_thumbnail(url=skin_url)
                cape_url_message = f"Cape Texture: {ign.capitalize()} have no capes"
                if cape_url:
                    cape_url_message = f"Cape texture: [Click here to download]({cape_url})"
                    mcinfo_embed.set_thumbnail(url=cape_url)
                url_message += cape_url_message
                mcinfo_embed.add_field(
                    name=f"Links for skin and cape (if any):",
                    value=url_message,
                    inline=False
                )
            if rendered_skin_png:
                mcinfo_embed.set_image(url='attachment://skin.png')
            await ctx.send(embed=mcinfo_embed, file=rendered_skin_png)

    @mcinfo.error
    async def mcinfo_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("you need to do !mcinfo (MC Java account username)", delete_after=10)

    async def handle_java_embed(self, domain, server, status):
        motd = status.description
        latency = status.latency
        version = status.version.name
        players_online = status.players.online
        max_players = status.players.max
        players_names = None
        try:
            server_query = await server.async_query()

        except:
            server_query = None
        if server_query:
            players_names = server_query.players.names
            if players_names and len(players_names) > 50:
                players_names = players_names[:50]

        java_embed = Embed(
            title=f"{self.success_emoji} {domain}'s status: (Java)",
            description="Server is online",
            colour=0x4bb543,
        ).set_thumbnail(
            url=f"https://api.mcsrvstat.us/icon/{domain}"
        )

        if latency:
            java_embed.description += f" with a latency of **{round(latency, 2)}ms**\n"

        if version:
            java_embed.add_field(name="Server minecraft version", value=version, inline=False)

        if players_online and max_players:
            java_embed.add_field(
                name="Online players",
                value=f"There are {players_online} players online out of {max_players}",
                inline=False
            )

        if motd:
            motd = motd if type(motd) is not dict else motd['text']
            motd_clean = sub(r"[\xA7|&][0-9A-FK-OR]", "", motd, flags=IGNORECASE)
            java_embed.add_field(
                name="Server motd",
                value=motd_clean,
                inline=False
            )

        if players_names:
            java_embed.add_field(name="Online players", value=f"```{', '.join(players_names)}```", inline=False)

        return java_embed

    async def handle_bedrock_embed(self, domain, status):
        latency = round(status.latency * 100)
        version = status.map
        players_online = status.players_online
        max_players = status.players_max
        motd = status.motd
        bedrock_embed = Embed(
            title=f"{self.success_emoji} {domain}'s  status: (bedrock)",
            description="Server is online",
            colour=0x4bb543,
        )
        if latency:
            bedrock_embed.description += f" with a latency of {latency}ms\n"

        if version:
            bedrock_embed.add_field(name="Server minecraft version", value=version, inline=False)

        if players_online and max_players:
            bedrock_embed.add_field(
                name="Online players",
                value=f"There are {players_online} players online out of {max_players}",
                inline=False
            )

        if motd:
            motd_clean = sub(r"[\xA7|&][0-9A-FK-OR]", "", motd, flags=IGNORECASE)
            bedrock_embed.add_field(name="Server motd", value=motd_clean, inline=False)

        return bedrock_embed

    @commands.command()
    async def online(self, ctx, *, domain):
        if ctx.channel.id != self.seraphine_commands.id and not ctx.author.guild_permissions.administrator:
            await ctx.send(f"Use this command in the {self.seraphine_commands.mention} channel", delete_after=10)
            return

        loading_emoji = utils.get(self.client.emojis, name="loading")
        embed_to_edit = await ctx.reply(
            embed=Embed(
                title=f"Pining {domain}",
                description=f" This can take up to 1 minute, please wait {loading_emoji}",
                color=0xffffff
            ),
            mention_author=False
        )

        try:
            server = await JavaServer.async_lookup(domain)
            status = await server.async_status()
            online_embed = await self.handle_java_embed(domain, server, status)
        except:
            try:
                server = BedrockServer.lookup(domain)
                status = await server.async_status()
                online_embed = await self.handle_bedrock_embed(domain, status)
            except Exception as e:
                print(e)
                online_embed = Embed(
                    title=f"Cannot find status of {domain}",
                    description="Server is offline, does not exist, not a Minecraft server "
                                "or does not use regular Minecraft protocols",
                    colour=0xff0033
                )
        await embed_to_edit.edit(embed=online_embed)


    @commands.command()
    async def wiki(self, ctx, *, query):
        if ctx.channel.id != self.seraphine_commands.id and not ctx.author.guild_permissions.administrator:
            await ctx.send(f"Use this command in the {self.seraphine_commands.mention} channel", delete_after=10)
            return

        async with ctx.typing():
            color = choice(self.colors)
            url_search = (
                f"https://www.google.com/search?hl=en&q={quote_plus(query)}"
                "&btnG=Google+Search&tbs=0&safe=on"
            )
            message = await ctx.send(
                embed=self.create_google_message(
                    ctx,
                    f"Searching...\n\n[Filtered for you]({url_search})",
                    color,
                ),
            )
            query_obj = google(
                "customsearch",
                "v1",
                developerKey=getenv("GoogleDeveloperKey"),
            )
            query_result = (
                query_obj.cse()
                    .list(
                    q=query,
                    cx=getenv("GoogleCustomSearchEngine"),
                    num=5,
                )
                    .execute()
            )

        results = []
        for result in query_result.get("items", []):
            title = result["title"]
            if len(title) > 77:
                title = f"{title[:77]}..."
            results.append(f"{len(results) + 1}. [{title}]({result['link']})\n")
        await message.edit(
            embed=self.create_google_message(
                ctx,
                f"Results for \"{query}\"\n\n{''.join(results)}",
                color,
            ),
            view=MoreResultsButton(url_search),
        )

    def create_google_message(self, ctx, message, color):
        google_message_embed = Embed(
            description=message,
            color=color
        ).set_author(
            name=f"Hypixel wiki result",
            icon_url=ctx.guild.icon.url
        )
        if ctx:
            google_message_embed.set_thumbnail(url=ctx.guild.icon.url)

        return google_message_embed

    @wiki.error
    async def mcwiki_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("you need to do !wiki (your search term))", delete_after=10)


async def setup(client):
    await client.add_cog(Minecraft(client))
