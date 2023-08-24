import asyncio
from json import load
from random import choice, randint
from os import getenv
from asyncio import sleep

from datetime import timedelta, datetime
from discord import Embed, Message, utils, Status
from discord.ext import commands, tasks
from dotenv import load_dotenv

load_dotenv()


class SeraphineAsk(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.on_cooldown = True
        self.current_allowed_questions = None
        self.current_question_message = None
        self.current_question_response = None
        self.current_adjusted_cap = None
        self.answer = None
        self.answered_correctly = False
        self.gave_incorrect_answer = {}


    @property
    def guild(self):
        return self.client.get_guild(int(getenv("GUILD_ID")))

    @property
    def seraphine_ask_channel(self):
        return utils.get(self.client.get_all_channels(), name="❓seraphine-ask")


    async def get_questions(self):
        with open(r"./Utilities/seraphine_ask.json", "r") as f:
            questions = load(f)
        return questions

    async def get_questions_embeds_and_answers(self):
        questions = await self.get_questions()
        questioon_embeds = []
        for question in questions["seraphine_questions"]:
            embed = Embed(
                description=question["description"],
                color=0x97BC62
            ).set_author(
                name="A question is posted! (look out for Seraphine imposters)",
                icon_url="https://cdn.discordapp.com/avatars/850059003593621514/44afa025d40b2761edb694df4493d852.webp?size=160"
            )
            if question["fields"]:
                fields_list = question["fields"]
                for num_field, field in enumerate(fields_list):
                    embed.add_field(
                        name=field,
                        value="\u200b",
                        inline=True
                    )
                    if num_field == 0 or num_field == 2:
                        embed.add_field(
                            name="\u200b",
                            value="\u200b",
                            inline=True
                        )
            if question["footer"]:
                embed.set_footer(text=question["footer"])

            if question["thumbnail_url"]:
                embed.set_thumbnail(url=question["thumbnail_url"])

            if question["image_url"]:
                embed.set_image(url=question["image_url"])

            questioon_embeds.append({"embed": embed, "answer": question["answer"]})

        return questioon_embeds

    async def send_question(self):
        if not self.current_allowed_questions:
            self.current_allowed_questions = await self.get_questions_embeds_and_answers()

        chosen_question = choice(self.current_allowed_questions)
        self.current_allowed_questions.remove(chosen_question)
        seraphine_ask_notification_role = utils.get(self.guild.roles, name="Seraphine Follower")
        self.current_question_message = await self.seraphine_ask_channel.send(
            seraphine_ask_notification_role.mention,
            embed=chosen_question["embed"]
        )
        self.answer = chosen_question["answer"]

    async def get_adjusted_cap(self):
        roles_to_be_considered_members = [
            utils.get(self.guild.roles, name="Member"),
            utils.get(self.guild.roles, name="Staff-Team")
        ]
        online_members = []
        for member in self.guild.members:
            if not member.bot:
                if member.status != Status.offline:
                    if any(role in member.roles for role in roles_to_be_considered_members):
                        online_members.append(member)
        online_members = len(online_members)
        hard_cap = 420
        soft_cap = 120
        max_members = 140
        minimum_members = 80
        decrease_per_member = (hard_cap - soft_cap) / (max_members - minimum_members)
        adjusted_cap = hard_cap - (decrease_per_member * (min(online_members, max_members) - minimum_members))
        adjusted_cap = max(soft_cap + 30, int(adjusted_cap))
        print(online_members, adjusted_cap)
        return adjusted_cap

    async def get_current_question_response_embed(self, member_correct_answer_message=None):
        two_minutes_formatted = f"<t:{round((datetime.utcnow() + timedelta(minutes=2)).timestamp())}:T>"
        seven_minutes_formatted = f"<t:{round((datetime.utcnow() + timedelta(seconds=self.current_adjusted_cap)).timestamp())}:T>"
        question_response_embed = Embed(
                title="",
                description=f"\nNext question will be posted between {two_minutes_formatted} "
                            f"and {seven_minutes_formatted}\n"
                            f"(The time is decreased based on how many members are online)!",
                color=0x4bb543 if member_correct_answer_message else 0xff0033)
        if not member_correct_answer_message:
            question_response_embed.title = "Times up!"
            question_response_embed.description = \
                f"No one answered correctly!\nThe correct answer is: `{','.join(self.answer)}`{question_response_embed.description}"
        else:
            question_response_embed.title = "Correct!"
            question_response_embed.description = \
                f"{member_correct_answer_message.author.mention} answered correctly and got 1 skybie!{question_response_embed.description}"
        return question_response_embed

    async def prepare_for_next_question(self):
        self.answered_correctly = False
        self.gave_incorrect_answer = {}
        self.answer = None
        self.current_question_message = None
        self.current_question_response = None

    async def delete_all_seraphine_messages(self):
        async for message in self.seraphine_ask_channel.history(limit=200):
            if message.author.id == self.client.user.id:
                await message.delete()

    async def ask_question(self):
        self.current_adjusted_cap = await self.get_adjusted_cap()
        await sleep(randint(120, self.current_adjusted_cap))
        await self.delete_all_seraphine_messages()
        await self.send_question()
        self.on_cooldown = False
        await sleep(60)
        if not self.answered_correctly:
            self.on_cooldown = True
            self.current_question_response = await self.current_question_message.reply(
                embed=await self.get_current_question_response_embed()
            )
            await self.prepare_for_next_question()
            await self.ask_question()

    async def handle_answered_correctly(self, message: Message):
        skybies_cog = self.client.get_cog("Skybies")
        await skybies_cog.give_skybies(message.author, 1, "Answered a question correctly in seraphine ask!")
        self.current_question_response = await message.reply(
            embed=await self.get_current_question_response_embed(message),
        )
        await self.prepare_for_next_question()
        await self.ask_question()

    @commands.Cog.listener("on_message")
    async def check_for_answers(self, message: Message):
        if message.author.bot or not message.content:
            return

        if message.channel != self.seraphine_ask_channel:
            return

        if self.on_cooldown:
            await message.reply(
                embed=Embed(description="🛑 There is no active questions currently", color=0xff0033),
            )
            return

        if message.content.lower().strip() in [x.lower() for x in self.answer]:
            self.on_cooldown = True
            self.answered_correctly = True
            await self.handle_answered_correctly(message)

        elif message.author.id in self.gave_incorrect_answer.keys():
            if self.gave_incorrect_answer[message.author.id] ==1:
                self.gave_incorrect_answer[message.author.id] += 1
                await message.reply(
                    embed=Embed(description="🛑Incorrect answer, you can't answer anymore", color=0xff0033),
                )

            elif self.gave_incorrect_answer[message.author.id] >= 2:
                await message.reply(
                    embed=Embed(description="🛑You ran out of attempts, you can't answer anymore", color=0xff0033),
                    delete_after=3
                )
                await message.delete()
        else:
            self.gave_incorrect_answer[message.author.id] = self.gave_incorrect_answer.get(message.author.id, 0) + 1
            await message.reply(
                embed=Embed(description="🛑Incorrect answer! You have 1 more attempt!", color=0xff0033),
            )

    async def ask_first_question(self):
        await self.client.wait_until_ready()
        await self.ask_question()

    async def cog_load(self):
        asyncio.create_task(self.ask_first_question())


async def setup(client):
    await client.add_cog(SeraphineAsk(client))