from os import getenv
from asyncio import gather
from aiohttp import ClientSession
from discord import utils, Embed, Message, DMChannel, Webhook
from discord.ext import commands
from dotenv import load_dotenv
load_dotenv()


class ChannelInstructions(commands.Cog):
    def __init__(self, client):
        self.client = client

    async def trading_section_instructions(self, message, channel, title, description, webhook_url):
        channel = utils.get(message.guild.text_channels, name=channel)
        if message.channel.id != channel.id:
            return

        async for message in channel.history(limit=20):
            if message.webhook_id:
                if message.embeds and message.embeds[0]:
                    await message.delete()

        instruction_embed = Embed(
            title=title,
            description=description,

            colour=0x97BC62
        ).set_thumbnail(
            url="https://i.imgur.com/Jo7Lc9h.png"
        )
        async with ClientSession() as session:
            webhook = Webhook.from_url(webhook_url, session=session)
            await webhook.send(embed=instruction_embed)

    async def self_promotion_channel_instructions(self, message: Message):
        self_promotion_channel = utils.get(message.guild.text_channels, name="📺self-promotion")
        sky_promoter = utils.get(message.guild.roles, name="📢Sky Promoter📢")
        if message.reference:
            return

        if message.channel.id != self_promotion_channel.id:
            return

        async for message in message.channel.history(limit=20):
            if message.author.id == self.client.user.id:
                if message.embeds and message.embeds[0].thumbnail:
                    await message.delete()

        explanation_embed = Embed(
            title="Thanks for joining Skyhub",
            description=f"In order to send ads in this channel, "
                        f"you will need some darkweb connections from Seraphine.\n"
                        f"Do `!skybies shop` to purchase the {sky_promoter.mention} role,\n"
                        f"to signify yourself as a friend of Seraphine, escaping from "
                        f"all ad blocker ban lists.\n\n"
                        f"You will also need to pay for ad space with skybies, which increases as you send more ads, "
                        f"though it resets every week 😎",

            colour=0x97BC62
        ).set_thumbnail(
            url="https://i.imgur.com/1bKgTgo.png"
        )
        await self_promotion_channel.send(embed=explanation_embed)

    async def command_channel_instructions(self, message: Message):
        commands_channels = [
            utils.get(message.guild.text_channels, name="👩seraphine-commands"),
            utils.get(message.guild.text_channels, name="🚨scammer-commands"),
            utils.get(message.guild.text_channels, name="🏅trading-honor-commands"),
            utils.get(message.guild.text_channels, name="🏅carrying-honor-commands"),
        ]
        if message.channel.id not in [channel.id for channel in commands_channels]:
            return

        if message.content.lower().startswith("!"):
            return

        await gather(
            message.reply(
                "Only commands are allowed in this channel",
                delete_after=3,
                mention_author=False
            ),
            message.delete(),
        )

    async def verification_chat_channel(self, message: Message, webhook_url):
        verification_chat_channel = utils.get(message.guild.text_channels, name="💬verification-chat")
        if message.channel.id != verification_chat_channel.id:
            return

        async for message in verification_chat_channel.history(limit=20):
            if message.webhook_id:
                if message.embeds and message.embeds[0] and message.embeds[0].title == "Verification Q&A":
                    await message.delete()

        instruction_embed = Embed(
            title="Verification Q&A",
            description=
            "Many people are concerned that our verification system may be a 'rat', so I, Seraphine the popo will explain our verification system\n\n"
            "**We use __1__ method to verify accounts: __Hypixel social menu__ **\n"
            "> __It can't be used to steal your account__.\n"
            "If you are doubtful, our bot's source code is completely open sourced for you to verify.\n"
            "> You can personally check our source code here: https://github.com/bensonchow123/Seraphine\n"
            "> And know more about 'rats' here: https://hypixel.net/threads/all-about-skyblock-account-stealing-part-ii.5231557/\n\n"
            "**Why do we have a verification system**\n"
            "> We categorize users as __verified__ and __unverified__ to stop dms from bots, make banning more effective, and system usage without specifying account names."
            "**!Verify doesn't exist**\n"
            "> Go to the <#1004284081011437629> channel and verify by clicking the button!",

            colour=0xdc0d1f
        ).set_footer(
            text="!verify does not exist, go to the verification channel to verify"
        )
        async with ClientSession() as session:
            webhook = Webhook.from_url(webhook_url, session=session)
            await webhook.send(embed=instruction_embed)

    @commands.Cog.listener("on_message")
    async def instructions_trigger(self, message: Message):
        if message.author.bot:
            return

        if isinstance(message.channel, DMChannel):
            return
        trading_section_info = utils.get(message.guild.text_channels, name="📝trading-section-info")
        trading_honor_commands = utils.get(message.guild.text_channels, name="🏅trading-honor-commands")
        make_a_ticket_channel = utils.get(message.guild.text_channels, name="🎫make-a-ticket")
        await gather(
            self.self_promotion_channel_instructions(message),
            self.command_channel_instructions(message),
            self.verification_chat_channel(message, getenv("VERIFICATION_CHAT_WEBHOOK")),
            self.trading_section_instructions(
                message,
                "🤝trading-channel",
                "Trading channel instructions:",
                (
                    f"Please include `buy` or `sell` and the `item` you want to trade in your message. \n"
                    f"Do not use this channel to trade items that already have dedicated channels for it.\n"
                    f"You can use the **discord search feature** to find your item with:\n"
                    f" `in: 🤝trading-channel (item)`"
                ),
                getenv("TRADING_CHANNEL_WEBHOOK")
            ),
            self.trading_section_instructions(
                message,
                "🌾farming-tools-trading",
                "Farming tools trading instructions:",
                (
                    f"Please include `buy` or `sell` and the `item` you want to trade in your message,"
                    f"and trade only farming tools in this channel\n"
                    f"You can use the **discord search feature** to find your item with:\n"
                    f" `in: 🌾farming-tools-trading (item)`"

                ),
                getenv("FARMING_TOOLS_TRADING_WEBHOOK")
            ),
            self.trading_section_instructions(
                message,
                "❓unobtainable-items-trading",
                "Unobtainable items trading instructions:",
                (
                    "Please include `buy` or `sell` and the `item` you want to trade in your message.\n"
                    "If your item is an exotic, please include the hex code (obtainable by using `F3+H` for advanced tooltips).\n"
                    "You can use the **discord search feature** to find your item with:\n"
                    " `in: ❓unobtainable-items-trading (item)`"
                ),
                getenv("UNOBTAINABLE_ITEMS_TRADING_WEBHOOK")
            ),
            self.trading_section_instructions(
                message,
                "💲lowballing-channel",
                "Lowballing channel instructions:",
                (
                    "Pleae include your `IGN` and `percentage` that you takes and the `items` you accept.\n"
                    "This channel is only for lowballers to advertise and is not intended for you to buying specific cheap items.\n"
                    "You can use the **discord search feature** to find your item with:\n"
                    " `in: 💲lowballing-channel (item/ percentage)`"
                ),
                getenv("LOWBALLING_CHANNEL_WEBHOOK")
            ),
            self.trading_section_instructions(
                message,
                "🪵craft-and-transfers",
                "Craft and transfers instructions:",
                (
                    "Please include your `items` and `price` of the items you want someone to craft or transfer for you.\n"
                    f"Please report any scammers you encounter in {make_a_ticket_channel.mention}.\n"
                    f"Give the person who helped you a trading honor in {trading_honor_commands.mention}.\n\n"
                    f"Crafters, please stay within the allowed price range for items based on your trading honor,\n"
                    f"which you can see in {trading_section_info.mention}."
                ),
                getenv("CRAFT_AND_TRANSFERS_WEBHOOK")
            ),

        )

async def setup(client):
    await client.add_cog(ChannelInstructions(client))
