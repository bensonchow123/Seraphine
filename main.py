from nextcord.ext import commands, tasks
from dotenv import load_dotenv
from itertools import cycle
import nextcord
import os
load_dotenv()
client = commands.Bot(command_prefix="!", intents=nextcord.Intents.all(), case_insensitive=True)
client.remove_command('help')
activity = cycle(
    [nextcord.Activity(type=nextcord.ActivityType.watching, name="Anti Dante documentation,watching [!]"),
     nextcord.Activity(type=nextcord.ActivityType.listening, name="Hypixel ost,watching [!]"),
     nextcord.Activity(type=nextcord.ActivityType.playing, name="community projects,watching [!]"),
     nextcord.Activity(type=nextcord.ActivityType.streaming, name="mayor elections,watching [!]")
     ]
)


@tasks.loop(seconds=15)
async def change_status():
    await client.change_presence(activity=next(activity))


@client.event
async def on_ready():
    change_status.start()
    print("I am ready hypicksell")

for filename in os.listdir('Cogs'):
    if filename.endswith('.py'):
        client.load_extension(f'Cogs.{filename[:-3]}')
client.run(os.getenv("DiscordToken"))

