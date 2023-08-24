from datetime import datetime
from os import getenv
from math import log2
from bson.objectid import ObjectId

from discord import Embed, utils, ui, ButtonStyle, Interaction
from discord.ext import commands
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
load_dotenv()
cluster = AsyncIOMotorClient(getenv("MongoDbSecretKey"))
bump_db = cluster["Skyhub"]["BumpRecord"]
restart_date_db = cluster["Skyhub"]["ResetDates"]


class AdvertisementConfirmButton(ui.View):
    def __init__(self, author, skybies_cost, remaining_skybies):
        super().__init__(timeout=15)
        self.remaining_skybies = remaining_skybies
        self.reply = None
        self.author = author
        self.skybies_cost = skybies_cost

    async def on_timeout(self):
        if self.reply.reference:
            replied_to = self.reply.reference.resolved
            await replied_to.delete()
        await self.reply.delete()

    async def interaction_check(self, interaction):
        if self.author.id != interaction.user.id:
            await interaction.response.send_message(
                "This confirmation is not for you, you cannot confirm other's advertisement",
                ephemeral=True
            )
            return False
        return True

    async def _status_embed(self, author, confirmed):
        if confirmed:
            description = (
                f"✅ You've paid {self.skybies_cost} skybies to share this advert! \n"
                f"You have {self.remaining_skybies} skybies remaining."
            )
        else:
            description = (
                f"🛑 Message is deleted, as you canceled your advertisement"
            )
        colour = 0x4bb543 if confirmed else 0xff0033
        status_embed = Embed(
            description=description,
            colour=colour
        ).set_author(
            name=author.display_name,
            icon_url=author.avatar.url
        ).set_thumbnail(
            url="https://i.imgur.com/1bKgTgo.png"
        )
        return status_embed

    @ui.button(label="Confirm", style=ButtonStyle.success)
    async def confirm(self, interaction: Interaction, button: ui.Button,):
        skybies = interaction.client.get_cog("Skybies")
        await skybies.take_skybies(interaction.user, self.skybies_cost)
        status_embed = await self._status_embed(interaction.user, True)
        await interaction.response.send_message(
            embed=status_embed,
            ephemeral=True
            )
        await interaction.message.delete()
        self.stop()

    @ui.button(label="Cancel", style=ButtonStyle.danger,)
    async def decline(self, interaction: Interaction, button: ui.Button, ):
        status_embed = await self._status_embed(interaction.user, False)
        await interaction.response.send_message(
            embed=status_embed,
            ephemeral=True
        )
        if self.reply.reference:
            replied_to = self.reply.reference.resolved
            await replied_to.delete()
        await interaction.message.delete()
        self.stop()


class SelfPromotion(commands.Cog):
    def __init__(self, client):
        self.client = client

    @property
    def guild(self):
        return self.client.get_guild(int(getenv("GUILD_ID")))

    @property
    def self_promotion_channel(self):
        return utils.get(self.guild.text_channels, name="📺self-promotion")

    @commands.Cog.listener("on_member_remove")
    async def delete_ads_on_member_leave(self, member):
        def member_check(message):
            return message.author == member

        deleted = await self.self_promotion_channel.purge(limit=100, check=member_check)
        if len(deleted) == 0:
            return

        plural = lambda num: "s" * (num != 1)
        await self.self_promotion_channel.send(
            embed=Embed(
                description=f"deleted {len(deleted)} ad{plural(len(deleted))} from {member.mention}, "
                            f"as they left the server:(",
                colour=0xf9423a
            )
        )
    @commands.Cog.listener("on_message")
    async def explanation_embed(self, message):
        if message.embeds and message.embeds[0].thumbnail:
            return

    async def find_weekly_restart_date(self):
        last_restart = await restart_date_db.find_one({"_id": ObjectId("62b4546da162f9c1a2fbdfe8")})
        last_restart = last_restart["last_weekly_restart"]
        last_restart_date = datetime.strptime(last_restart, "%S:%M:%H:%d:%m:%Y:%z")
        return last_restart_date

    async def determine_message_amount_in_last_7_days(self, message):
        last_restart_date = await self.find_weekly_restart_date()
        messages_in_last_7_days = message.channel.history(after=last_restart_date)
        messages_send_last_7_days_by_author = []
        async for last_7_day_message in messages_in_last_7_days:
            if message.author.id == last_7_day_message.author.id:
                messages_send_last_7_days_by_author.append(last_7_day_message)
        return len(messages_send_last_7_days_by_author)

    async def evaluate_cost(self, message):
        new_message_count = await self.determine_message_amount_in_last_7_days(message)
        cost = round(log2((new_message_count + 1) * 0.8 + 0.3))
        return cost, new_message_count

    async def format_day(self, day):
        if day in {11, 12, 13}:
            suffix = "th"

        else:
            suffix = {
                1: "st",
                2: "nd",
                3: "rd",
            }.get(day % 10, "th")

        return f"{day}{suffix}"

    @commands.Cog.listener("on_message")
    async def message_cost_system(self, message):
        if message.author.bot:
            return

        if message.channel != self.self_promotion_channel:
            return
        skybies_cog = self.client.get_cog("Skybies")
        cost, new_message_count = await self.evaluate_cost(message)
        skybies_aquired, _ = await skybies_cog.get_skybies(message.author)
        remaining_skybies = skybies_aquired - cost
        if remaining_skybies >= 0:
            confirm_embed = Embed(
                description=f"As this is your {await self.format_day(new_message_count)} advert in this week, "
                            f"It will cost **{cost} skybies** for this advert to be sent\n"
                            f"You got 15 seconds to confirm before the advert deletes itself\n",
                colour=0x4169E1
            ).set_author(
                name="Click the buttons below to confirm or cancel your advertisement",
            )
            confirm_button = AdvertisementConfirmButton(message.author, cost, remaining_skybies)
            confirm_button.reply = await message.reply(
                embed=confirm_embed,
                view=confirm_button
                )
            return
        await message.reply(
            f"You need {cost} skybies to send this ad,\n"
            f"but you only have {skybies_aquired}"
        )


async def setup(client):
    await client.add_cog(SelfPromotion(client))
