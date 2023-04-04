import datetime
from typing import Annotated

import alluka
import hikari
import tanjun

from utils import trigger_typing
from utils.checks.role_checks import jr_mod_check, mod_check
from utils.config import Config
from utils.converters import to_timestamp
from utils.error_utils import log_error

################
#   Commands   #
################

component = tanjun.Component()


@tanjun.with_check(mod_check, follow_wrapped=True)
# message options
@tanjun.with_greedy_argument('reason')
@tanjun.with_option('dm', '--dm', converters=tanjun.conversion.to_bool, default=True, empty_value=True)
@tanjun.with_argument('user', converters=tanjun.conversion.to_user)
@tanjun.as_message_command('ban')
# slash options
@tanjun.with_bool_slash_option('dm', 'Should the user be DM-ed?', default=True)
@tanjun.with_str_slash_option('reason', 'Reason for banning the user')
@tanjun.with_user_slash_option('user', 'The user to ban')
@tanjun.as_slash_command('ban', 'Bans the given user', default_member_permissions=hikari.Permissions.BAN_MEMBERS)
async def ban(ctx: tanjun.abc.Context, user: hikari.User, reason: str, dm: bool = True,
              config: Config = alluka.inject(type=Config)):
    await trigger_typing(ctx)
    if user.id == ctx.author.id:
        await ctx.respond('You can\'t ban yourself you potato')

    successful_dm = False
    if dm:
        try:
            ban_dm = f"You have been banned from SBU for `{reason}`\n" \
                     fr"You may appeal in {config['moderation']['appeals_invite']}"
            await (await user.fetch_dm_channel()).send(ban_dm)
        except hikari.ForbiddenError:
            pass
        except Exception as exception:
            await log_error(ctx, exception)
        else:
            successful_dm = True

    try:
        await ctx.get_guild().ban(user.id, reason=reason)
    except hikari.NotFoundError:
        await ctx.respond(f'User {user} not found.')
        return
    except Exception as exception:
        await log_error(ctx, exception)
        return

    channel = ctx.get_guild().get_channel(config['moderation']['action_log_channel_id'])
    author_id = ctx.author.id

    log = f'Moderator: <@{author_id}>\nUser: <@{user.id}> | {user}\nAction: Ban\nReason: {reason}'

    successful_log = False
    if isinstance(channel, hikari.TextableChannel):
        try:
            await channel.send(log)
        except Exception as exception:
            await log_error(ctx, exception)
        else:
            successful_log = True

    embed = hikari.Embed(
        description=f"{user} was banned.\n"
                    f"*Reason*: `{reason}`\n\n"
                    f"*DM?*: {'✅' if successful_dm else '❌'}\n"
                    f"*Log?*: {'✅' if successful_log else '❌'}\n",
        color=config['colors']['secondary']
    )
    await ctx.respond(embed=embed)


@tanjun.with_check(mod_check, follow_wrapped=True)
@tanjun.with_greedy_argument('reason', default=None)
@tanjun.annotations.with_annotated_args(follow_wrapped=True)
@tanjun.as_message_command('unban')
@tanjun.with_str_slash_option('reason', 'Reason for unbanning the user', default=None)
@tanjun.as_slash_command('unban', 'Unbans the given user', default_member_permissions=hikari.Permissions.BAN_MEMBERS)
async def unban(ctx: tanjun.abc.Context,
                user: Annotated[tanjun.annotations.User, 'The user to unban'],
                reason: str,
                config: Config = alluka.inject(type=Config)):
    try:
        await ctx.get_guild().unban(user, reason=reason)
    except hikari.NotFoundError:
        await ctx.respond(f'User {user} not found.')
        return
    except Exception as exception:
        await log_error(ctx, exception)
        return

    log = f"Moderator: <@{ctx.author.id}> \n User: <@{user.id}> | {user} \n Action: unban \n Reason: {reason}"
    channel = ctx.get_guild().get_channel(config['moderation']['action_log_channel_id'])

    successful_log = False
    if isinstance(channel, hikari.TextableChannel):
        try:
            await channel.send(log)
        except Exception as exception:
            await log_error(ctx, exception)
        else:
            successful_log = True

    embed = hikari.Embed(
        description=f"{user} was unbanned.\n"
                    f"*Reason*: `{reason}`\n\n"
                    f"*Log?*: {'✅' if successful_log else '❌'}\n",
        color=config['colors']['secondary']
    )
    await ctx.respond(embed=embed)


@tanjun.with_check(jr_mod_check, follow_wrapped=True)
@tanjun.with_greedy_argument('reason', default=None)
@tanjun.with_argument('time', converters=to_timestamp, default='24h')
@tanjun.with_argument('member', converters=tanjun.conversion.to_member)
@tanjun.as_message_command('mute')
@tanjun.with_str_slash_option('reason', 'Reason for muting the user', default=None)
@tanjun.with_str_slash_option('time', 'The amount of time to mute for (default: 24h)', converters=to_timestamp,
                              default='24h')
@tanjun.with_member_slash_option('user', 'The user to mute', key='member')
@tanjun.as_slash_command('mute', 'Mutes the given user', default_member_permissions=hikari.Permissions.MUTE_MEMBERS)
async def mute(ctx: tanjun.abc.Context, member: hikari.Member, time: int, reason: str,
               config: Config = alluka.inject(type=Config)):
    if time > (28 * 86400):
        embed = hikari.Embed(
            title='Error',
            description='Max mute duration is 28 days',
            color=config['colors']['error']
        )
        await ctx.respond(embed=embed)
        return

    if config['jr_mod_role_id'] in member.role_ids and member.id != ctx.author.id:
        embed = hikari.Embed(
            title='Error',
            description='You cannot mute other staff members',
            color=config['colors']['error']
        )
        await ctx.respond(embed=embed)
        return

    duration = datetime.timedelta(seconds=time)

    await member.edit(communication_disabled_until=datetime.datetime.now() + duration, reason=reason)
    await ctx.respond(f"{member.mention} has been muted for {duration} | Reason {reason}")

    await ctx.get_guild().get_channel(config['moderation']['action_log_channel_id']).send(
        f"Moderator: <@{ctx.author.id}> \n"
        f"User: <@{member.id}> \n"
        f"Action: Mute \n"
        f"Duration: {duration} \n"
        f"Reason: {reason}")

    try:
        await (await member.fetch_dm_channel()).send("You have been muted in Skyblock University.\n\n"
                                                     "If you would like to appeal your mute, please DM <@575252669443211264>")
    except (hikari.ForbiddenError, hikari.BadRequestError):
        pass


@tanjun.with_check(jr_mod_check, follow_wrapped=True)
@tanjun.with_greedy_argument('reason', default=None)
@tanjun.with_argument('member', converters=tanjun.conversion.to_member)
@tanjun.as_message_command('unmute')
@tanjun.with_str_slash_option('reason', 'Reason for muting the user', default=None)
@tanjun.with_member_slash_option('user', 'The user to unmute', key='member')
@tanjun.as_slash_command('unmute', 'Unmutes the given user', default_member_permissions=hikari.Permissions.MUTE_MEMBERS)
async def unmute(ctx: tanjun.abc.Context, member: hikari.Member, reason: str,
                 config: Config = alluka.inject(type=Config)):
    await member.edit(communication_disabled_until=None, reason=reason)
    await ctx.respond(f"{member.mention} has been unmuted | Reason {reason}")

    await ctx.get_guild().get_channel(config['moderation']['action_log_channel_id']).send(
        f"Moderator: <@{ctx.author.id}> \n"
        f"User: <@{member.id}> \n"
        f"Action: Unmute \n"
        f"Reason: {reason}")


component.load_from_scope()


@tanjun.as_loader()
def load(client: tanjun.Client):
    client.add_component(component)


@tanjun.as_unloader()
def unload(client: tanjun.Client):
    client.remove_component(component)
