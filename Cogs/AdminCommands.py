from nextcord.ext import commands
from nextcord import Embed, utils, Member, NotFound
from datetime import timedelta
from humanfriendly import parse_timespan, InvalidTimespan



class AdminCommands(commands.Cog):
    def __init__(self, client):
        self.client = client

    async def mod_action_logs(self, actor: Member, action, reason=None, member: Member=None):
        mod_action_embed = Embed(color=0xCC2222)
        mod_action_embed.set_footer(text=f"by {actor.display_name}")
        mod_action_embed.set_author(name=action, icon_url=self.guild.icon.url)
        if reason:
            mod_action_embed.description = reason
        if member:
            mod_action_embed.set_footer(
                text=f'To {member.display_name} by {actor.display_name}',
                icon_url=member.avatar.url
                )
        await self.staff_logs_channel.send(embed=mod_action_embed)
        return mod_action_embed

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx, msg_count, member=None, *, reason=None):
        if not member:
            await ctx.channel.purge(limit=int(msg_count))
            mod_action_embed = await self.mod_action_logs(
                actor=ctx.author,
                action=f"Cleared {msg_count} messages in {ctx.channel}",
                reason=reason if reason else None,
            )
        else:
            mod_action_embed = await self.mod_action_logs(
                actor=ctx.author,
                action=f"Cleared {msg_count} messages from {member.display_name} in {ctx.channel}",
                member=member,
                reason=reason if reason else None,
            )
        await ctx.channel.send(embed=mod_action_embed, delete_after=10)


    @clear.error
    async def clear_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("you need to be at least a helper to use this command", delete_after=10)
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("It is !clear (amount of messages) (member=optional) (reason=optional)", delete_after=10)

    @commands.command(name="ban")
    @commands.has_guild_permissions(ban_members=True)
    async def ban(self, ctx, member: Member, *, reason):
        mod_action_embed = await self.mod_action_logs(
            actor=ctx.author,
            action=f"{member.display_name} have been banned",
            reason=reason,
            member=member
        )
        try:
            await member.send(embed=mod_action_embed)
        except:
            pass

        await member.ban(reason=reason)
        await ctx.message.reply(f"{member} has been banned for {reason}")

    @ban.error
    async def ban_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("you need to be at least a mod to use this command", delete_after=10)
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("it is !ban (@user or id) (reason), all arguments are not optional", delete_after=10)

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, member_id, *, reason):
        user = await self.client.fetch_user(member_id)
        try:
            entry = await ctx.guild.get_ban(user)
        except NotFound:
            await ctx.message.reply("Can't find that member in the ban list")
            return
        await ctx.guild.unban(user)
        mod_action_embed = await self.mod_action_logs(
            actor=ctx.author,
            action=f"{user.display_name} is unbanned",
            reason=reason,
            member=user
        )
        await ctx.message.reply(f"{user} has been unbanned")

    @unban.error
    async def unban_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("you need to be at least a mod to use this command", delete_after=10)
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("It is !unban (user_id) (reason), both arguments are not optional", delete_after=10)

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: Member, *, reason):
        mod_action_embed = await self.mod_action_logs(
            actor=ctx.author,
            action=f"{member.display_name} have been kicked",
            reason=reason,
            member=member
        )
        try:
            await member.send(embed=mod_action_embed)
        except:
            pass
        await member.kick(reason=reason)
        await ctx.send(f"{member} has been kicked for {reason}")

    @kick.error
    async def kick_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("you need to be at least a mod to use this command", delete_after=10)
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("It is !kick (@member or id) (reason), all arguments are not optional", delete_after=10)

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def mute(self, ctx, member: Member, time, *, reason):
        try:
            time_span = parse_timespan(time)
            await member.edit(timeout=utils.utcnow() + timedelta(seconds=time_span))
            mod_action_embed = await self.mod_action_logs(
                actor=ctx.author,
                action=f"{member.display_name} have been muted",
                reason=reason,
                member=member
            )
            try:
                await member.send(embed=mod_action_embed)
            except:
                pass
            await ctx.send(f"{member.mention} have been muted for {reason}")
        except InvalidTimespan:
            await ctx.send("You must provide a valid timespan,  for example `1y, 1w, 1d, 1h, 1m, 1s`")

    @mute.error
    async def mute_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("you need to be at least a helper to use this command", delete_after=10)
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("It is !mute (@user or id) (time: 1y, 1w, 1d, 1h, 1m, 1s) (reason)\n"
                           "all arguments are not optional", delete_after=10)

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def unmute(self, ctx, member: Member, *, reason):
        if member.communication_disabled_until:
            await member.edit(timeout=None)
        elif self.muted_role in member.roles:
            await member.remove_roles(self.muted_role)
        else:
            await ctx.send(f"{member.mention} is not muted")
            return
        mod_action_embed = await self.mod_action_logs(
            actor=ctx.author,
            action=f"{member.display_name} have been unmuted",
            reason=reason,
            member=member
        )
        try:
            await member.send(embed=mod_action_embed)
        except:
            pass
        await ctx.send(f"{member.mention} have been unmuted for {reason}")

    @unmute.error
    async def unmute_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("you need to be at least a helper to use this command", delete_after=10)
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("It is !unmute (@user or id) (reason), all arguments are not optional", delete_after=10)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def echo(self, ctx, *, message):
        await ctx.send(message)
        await ctx.message.delete()
        mod_action_embed = await self.mod_action_logs(
            actor=ctx.author,
            action=f"An echo message have been sent in {ctx.channel}",
        )

    @echo.error
    async def echo_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("you need to be at least an admain to use this command", delete_after=10)
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("It is !echo (message)", delete_after=10)

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def slowmode(self, ctx, seconds: int):
        await ctx.channel.edit(slowmode_delay=seconds)
        mod_action_embed = await self.mod_action_logs(
            actor=ctx.author,
            action=f"A slowmode of {seconds} have been set in {ctx.channel}",
        )
        await ctx.send(f"Setted the slowmode delay in this channel to {seconds} seconds!")

    @slowmode.error
    async def set_delay_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("you need to be at least an Admain to use this command", delete_after=10)
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("It is !showmode (seconds)", delete_after=10)

    @commands.command(aliases=["skybiesadmin"])
    @commands.has_permissions(administrator=True)
    async def skybiescontrol(self, ctx, member: Member, count: int):
        try:
            if int(count) == 0:
                await ctx.send(f"You are making no changes to {member.display_name}'s Skybies count", delete_after=10)
            if int(count) > 0:
                await self.skybies._give_skybies(member, count)
                await ctx.send(f"you have added {count} Skybies to {member.display_name}'s Skybies count", delete_after=10)
            if int(count) < 0:
                await self.skybies._take_skybies(member.id, count)
                await ctx.send(f"you have removed {abs(int(count))} Skybies to {member.display_name}'s Skybies count", delete_after=10)
                mod_action_embed = await self.mod_action_logs(
                    actor=ctx.author,
                    action=f"{member.display_name} skybies have been added {count}",
                    member=member
                )
        except Exception as x:
            raise commands.BadArgument

    @skybiescontrol.error
    async def skybiesControl_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("you need to be an Admain to use this command", delete_after=10)
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("It is !skybiecontrol (@member) (1 or -1)", delete_after=10)
        elif isinstance(error, commands.BadArgument):
            await ctx.send("It is !skybiecontrol (@member) (1 or -1)", delete_after=10)

    @commands.Cog.listener()
    async def on_ready(self):
        self.guild = self.client.get_guild(844231449014960160)
        self.muted_role = utils.get(self.guild.roles, name="Muted")
        self.staff_logs_channel = utils.get(self.guild.text_channels, name="❗staff-logs")
        self.skybies = self.client.get_cog("Skybies")


def setup(client):
    client.add_cog(AdminCommands(client))
