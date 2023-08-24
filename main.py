from itertools import cycle
from os import getenv, listdir

from discord.ext import tasks, commands
from discord import Intents, Activity, ActivityType
from dotenv import load_dotenv

load_dotenv()


class Seraphine(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.help_command = None
        self.seraphine_status = cycle(
            [Activity(type=ActivityType.watching, name="Anti Dante documentation,watching [!]"),
             Activity(type=ActivityType.listening, name="Hypixel ost,watching [!]"),
             Activity(type=ActivityType.playing, name="community projects,watching [!]"),
             Activity(type=ActivityType.streaming, name="mayor elections,watching [!]")
             ]
        )

    async def load_cogs(self):
        for filename in listdir('Cogs'):
            if filename.endswith('.py'):
                await self.load_extension(f'Cogs.{filename[:-3]}')

    @tasks.loop(seconds=15)
    async def change_status(self):
        await self.change_presence(activity=next(self.seraphine_status))

    @change_status.before_loop
    async def before_change_status(self):
        await self.wait_until_ready()

    async def setup_hook(self):
        await self.load_cogs()
        self.change_status.start()

    async def on_ready(self):
        print("I am ready hypicksell")


client = Seraphine(command_prefix="!", intents=Intents.all(), case_insensitive=True)
client.run(getenv("DiscordToken"))


