from datetime import timedelta

from discord.ext import commands
from discord import Embed, utils, Member, NotFound, Forbidden, HTTPException, AllowedMentions
from humanfriendly import parse_timespan, InvalidTimespan
from dotenv import load_dotenv
load_dotenv()


class AdminCommands(commands.Cog):
    def __init__(self, client):
        self.client = client

    async def mod_action_logs(self, actor: Member, action, reason=None, member: Member=None):
        staff_logs_channel = utils.get(actor.guild.text_channels, name="❗staff-logs")
        mod_action_embed = Embed(color=0xCC2222)
        mod_action_embed.set_footer(text=f"by {actor.display_name}")
        mod_action_embed.set_author(name=action, icon_url=actor.guild.icon.url)
        if reason:
            mod_action_embed.description = reason
        if member:
            mod_action_embed.set_footer(
                text=f'To {member.display_name} by {actor.display_name}',
                icon_url=member.avatar.url
                )

        await staff_logs_channel.send(embed=mod_action_embed)
        return mod_action_embed

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx, msg_count: int, *, reason: str):
        await ctx.channel.purge(limit=msg_count + 1)
        mod_action_embed = await self.mod_action_logs(
            actor=ctx.author,
            action=f"Cleared {msg_count} messages in {ctx.channel}",
            reason=reason,
        )
        await ctx.channel.send(embed=mod_action_embed, delete_after=10, mention_author=False)

    @clear.error
    async def clear_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.reply(
                "You need to be at least a helper to use this command",
                delete_after=10,
                mention_author=False
            )
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.reply(
                f"It is !clear (num of message) (reason), missing `{error.param}`",
                delete_after=10,
                mention_author=False
            )
        else:
            await ctx.reply(
                "Something went wrong, it is !clear (num of message) (reason)",
                delete_after=10,
                mention_author=False
            )

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, member: Member, *, reason: str):
        def check(message):
            return message.author == member
        await ctx.channel.purge(limit=200, check=check)
        mod_action_embed = await self.mod_action_logs(
            actor=ctx.author,
            action=f"Purged {member.display_name} messages in {ctx.channel}",
            reason=reason,
            member=member
        )
        await ctx.reply(embed=mod_action_embed, delete_after=10, mention_author=False)

    @purge.error
    async def purge_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.reply(
                "You need to be at least a helper to use this command",
                delete_after=10,
                mention_author=False
            )
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.reply(
                f"It is !purge (member) (reason), missing `{error.param}`",
                delete_after=10,
                mention_author=False
            )
        elif isinstance(error, commands.MemberNotFound):
            await ctx.reply(
                f"Member `{error.argument}` not found",
                delete_after=10,
                allowed_mentions=AllowedMentions.none(),
            )
        else:
            await ctx.reply(
                "Something went wrong, it is !purge (member) (reason)",
                delete_after=10,
                mention_author=False
            )

    @commands.command(name="ban")
    @commands.has_guild_permissions(ban_members=True)
    async def ban(self, ctx, member: Member, *, reason: str):
        mod_action_embed = await self.mod_action_logs(
            actor=ctx.author,
            action=f"{member.display_name} have been banned",
            reason=reason,
            member=member
        )
        try:
            await member.send(embed=mod_action_embed)
        except Forbidden:
            pass

        await member.ban(reason=reason)
        await ctx.message.reply(f"{member} has been banned for {reason}", mention_author=False)

    @ban.error
    async def ban_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.reply(
                "You need to be at least a mod to use this command",
                delete_after=10,
                mention_author=False
            )

        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.reply(
                f"It is !ban (member) (reason), missing `{error.param}`",
                delete_after=10,
                mention_author=False
            )

        else:
            await ctx.reply(
                "Something went wrong, please try again, it is !ban (member) (reason)",
                delete_after=10,
                mention_author=False
            )

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, member_id: int, *, reason: str):
        try:
            user = await self.client.fetch_user(member_id)
            try:
                await ctx.guild.unban(user)
                mod_action_embed = await self.mod_action_logs(
                    actor=ctx.author,
                    action=f"{user.display_name} is unbanned",
                    reason=reason,
                    member=user
                )
                await ctx.message.reply(embed=mod_action_embed, mention_author=False)
            except NotFound:
                await ctx.reply("User is not banned", delete_after=10, mention_author=False)

            except HTTPException:
                await ctx.reply("Something went wrong", delete_after=10, mention_author=False)

        except NotFound:
            await ctx.reply(f"User with id {member_id} not found", delete_after=10, mention_author=False)

        except HTTPException:
            await ctx.reply("Something went wrong", delete_after=10, mention_author=False)

    @unban.error
    async def unban_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.reply(
                "You need to be at least a mod to use this command",
                delete_after=10,
                mention_author=False
            )
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.reply(
                f"It is !unban (user_id) (reason), missing `{error.param}`",
                delete_after=10,
                mention_author=False
            )

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def mute(self, ctx, member: Member, time: str, *, reason: str):
        try:
            time_span = parse_timespan(time)
            await member.edit(timed_out_until=utils.utcnow() + timedelta(seconds=time_span))
            mod_action_embed = await self.mod_action_logs(
                actor=ctx.author,
                action=f"{member.display_name} have been muted",
                reason=reason,
                member=member
            )
            try:
                await member.send(embed=mod_action_embed)
            except Forbidden:
                pass
            await ctx.reply(embed=mod_action_embed, mention_author=False)
        except InvalidTimespan:
            await ctx.reply("You must provide a valid timespan,  for example `1y, 1w, 1d, 1h, 1m, 1s`")

    @mute.error
    async def mute_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.reply(
                "You need to be at least a helper to use this command",
                delete_after=10,
                mention_author=False
            )
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.reply(
                "It is !mute (member) (time: 1y, 1w, 1d, 1h, 1m, 1s) (reason)\n"
                f"Missing {error.param}",
                delete_after=10,
                mention_author=False
            )
        else:
            await ctx.reply(
                "Something went wrong, it is !mute (member) (time: e.g 1y, 1w, 1d, 1h, 1m, 1s) (reason)\n"
                "Please try again",
                delete_after=10,
                mention_author=False
            )

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def unmute(self, ctx, member: Member, *, reason):
        muted_role = utils.get(ctx.guild.roles, name="Muted")
        member_role = utils.get(ctx.guild.roles, name="Member")
        if member.timed_out_until:
            await member.edit(timed_out_until=None)
        elif muted_role in member.roles:
            await member.remove_roles(muted_role)
            await member.add_roles(member_role)
        else:
            await ctx.reply(f"{member.mention} is not muted", delete_after=10, allow_mentions=AllowedMentions.none())
            return
        mod_action_embed = await self.mod_action_logs(
            actor=ctx.author,
            action=f"{member.display_name} have been unmuted",
            reason=reason,
            member=member
        )
        try:
            await member.send(embed=mod_action_embed)
        except Forbidden:
            pass
        await ctx.reply(
            embed=mod_action_embed,
            delete_after=10,
            mention_author=False
            )

    @unmute.error
    async def unmute_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.reply(
                "You need to be at least a helper to use this command",
                delete_after=10,
                mention_author=False
            )
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.reply(
                f"It is !unmute (@user or id) (reason), missing `{error.param}`",
                delete_after=10,
                mention_author=False
            )
        else:
            await ctx.reply(
                "Something went wrong, it is !unmute (@user or id) (reason), please try again",
                delete_after=10,
                mention_author=False
            )

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def echo(self, ctx, *, message):
        await ctx.send(message)
        await ctx.message.delete()
        mod_action_embed = await self.mod_action_logs(
            actor=ctx.author,
            action=f"An echo message have been sent in {ctx.channel}",
        )

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def weekly_giftaway_remove(self, ctx):
        weekly_giftaway_role = utils.get(ctx.guild.roles, name="📅Weekly giveaway📅")
        weekly_giftaway_channel = utils.get(ctx.guild.channels, name="🎉weekly-giveaways")
        loading_emoji = utils.get(self.client.emojis, name="loading")
        status_message = await ctx.send(f"Removing the weekly giftaway role from everyone {loading_emoji}")
        await weekly_giftaway_channel.send(
            embed=Embed(
                description=f"{weekly_giftaway_role.mention} has been removed from everyone!\n"
                            "**Time to buy a ticket!**",
                colour=0xADD8E6,
                timestamp=ctx.message.created_at
            ).set_author(
                name="Weekly giftaway restart!",
                icon_url=self.client.user.avatar.url,
            )
        )
        count = 0
        for member in ctx.guild.members:
            if weekly_giftaway_role in member.roles:
                await member.remove_roles(weekly_giftaway_role)
                count += 1
        await status_message.edit(content=f"Removed {count} members from the weekly giftaway role")

    @echo.error
    async def echo_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.reply(
                "You need to be at least an admain to use this command",
                delete_after=10,
                mention_author=False
            )
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.reply(
                "It is !echo (message)",
                delete_after=10,
                mention_author=False
            )
        else:
            await ctx.reply(
                "Something went wrong, it is !echo (message), please try again",
                delete_after=10,
                mention_author=False
            )

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def slowmode(self, ctx, seconds: int):
        await ctx.channel.edit(slowmode_delay=seconds)
        mod_action_embed = await self.mod_action_logs(
            actor=ctx.author,
            action=f"A slowmode of {seconds} have been set in {ctx.channel}",
        )
        await ctx.reply(embed=mod_action_embed, delete_after=10, mention_author=False)

    @slowmode.error
    async def slowmode_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.reply(
                "You need to be at least an admain to use this command",
                delete_after=10,
                mention_author=False
            )
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.reply(
                "It is !showmode (seconds)",
                delete_after=10,
                mention_author=False
            )
        else:
            await ctx.reply(
                "Something went wrong, it is !showmode (seconds), please try again",
                delete_after=10,
                mention_author=False
            )

    @commands.is_owner()
    @commands.command(aliases=["skybies_admin", "s_c", "s_a"])
    async def skybies_control(self, ctx, member: Member, skybies_count: int):
        skybies_cog = self.client.get_cog("Skybies")
        mod_action_embed = None
        if not skybies_count:
            await ctx.reply(
                f"You are making no changes to {member.display_name}'s Skybies count",
                delete_after=10,
                mention_author=False
            )

        elif skybies_count > 0:
            await skybies_cog.give_skybies(member, skybies_count)
            mod_action_embed = await self.mod_action_logs(
                actor=ctx.author,
                action=f"{skybies_count} Skybies have been given to {member.display_name}",
            )

        elif skybies_count < 0:
            await skybies_cog.take_skybies(member, skybies_count)
            await ctx.reply(f"you have removed {abs(skybies_count)} Skybies to {member.display_name}'s Skybies count", delete_after=10)
            mod_action_embed = await self.mod_action_logs(
                actor=ctx.author,
                action=f"{abs(skybies_count)} Skybies have been removed from {member.display_name}",
                member=member
            )
        if mod_action_embed:
            try:
                await member.send(embed=mod_action_embed)
            except Forbidden:
                pass
            await ctx.reply(embed=mod_action_embed, delete_after=10, mention_author=False)






async def setup(client):
    await client.add_cog(AdminCommands(client))
