import nextcord
from nextcord.ext import commands


class Direct_to_bot_channel(nextcord.ui.View):
    def __init__(self):
        super().__init__()
        url = "https://discord.gg/9Pfjx3qVG5"
        self.add_item(nextcord.ui.Button(label='Click here to test out my commands', url=url))


class Onboarding(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.unwelcomedids = []

    @commands.Cog.listener("on_member_join")
    async def welcome_rewards(self, member):
        if member.bot:
            await member.add_roles(self.bot_role)
        else:
            await member.add_roles(self.memberRole)
            self.memberid = member.id
            self.unwelcomedids.append(member.id)

    @commands.Cog.listener("on_message")
    async def give_skybies_for_welcomeing(self, message):
        if message.author.bot:
            return

        if message.channel.id != self.welcome_channel.id:
            return

        if not self.unwelcomedids:
            return

        if message.author.id == self.memberid:
            return

        usernames = []
        for x in self.unwelcomedids:
            member = self.guild.get_member(x)
            usernames.append(member.mention if member else "Unknown")
        await self.skybies._give_skybies(message.author, 1, f"{message.author.display_name} had welcomed {','.join(usernames)} to Skyhub!!!")
        await message.reply(
            f"{message.author.display_name} have been given 1 skybie for welcoming {len(usernames)} member",
            delete_after=7,
            mention_author=False
        )
        self.unwelcomedids.clear()

    @commands.Cog.listener("on_member_join")
    async def welcome_dm(self, member):
        file = nextcord.File(r"./Utilities/seraphine_onboarding.mp3")
        welcome_embed = nextcord.Embed(
            description=
            '''\n**Hi, I am Seraphine (a chatbot), you can chat with me right here in this dm channel**
            \nYou can listen to me introducing myself with this mp3 file above''',
            colour=0xf4e98c
        ).set_thumbnail(
            url=self.guild.icon.url
        ).set_footer(
            text="I can't response to commands in dm channels",
            icon_url=self.client.user.avatar.url
        )
        try:
            await member.send(embed=welcome_embed, file=file, view=Direct_to_bot_channel())
        except:
            return

    @commands.Cog.listener()
    async def on_ready(self):
        self.guild = self.client.get_guild(844231449014960160)
        self.memberRole = nextcord.utils.get(self.guild.roles, name="Member")
        self.bot_role = nextcord.utils.get(self.guild.roles, name="Bot")
        self.welcome_channel = nextcord.utils.get(self.guild.text_channels, name="👋🏻welcome")
        self.skybies = self.client.get_cog("Skybies")


def setup(client):
    client.add_cog(Onboarding(client))
