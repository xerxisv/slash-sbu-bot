# TODO use miru's navigator to implement the rep list pagination
import time
from math import ceil

import aiosqlite
import alluka
import hikari
import tanjun

from utils.config import Config
from utils.database import convert_to_rep
from utils.error_utils import log_error

################
#   Commands   #
################

component = tanjun.Component()

rep_slash_group = tanjun.slash_command_group('rep', 'Reputation commands', default_to_ephemeral=True)
rep_slash_group_perms = tanjun.slash_command_group('rep', 'Reputation commands', default_to_ephemeral=True,
                                                   default_member_permissions=hikari.Permissions.MANAGE_ROLES)

component.add_slash_command(rep_slash_group)
component.add_slash_command(rep_slash_group_perms)


@tanjun.with_bool_slash_option('collateral', 'Was collateral given?')
@tanjun.with_str_slash_option('value', 'Approximate value of items')
@tanjun.with_str_slash_option('comments', 'Brief description of the exchange')
@tanjun.with_member_slash_option('receiver', 'The user to give rep to')
@rep_slash_group.as_sub_command('give', 'Give reputation to a user', always_defer=True)
async def rep_give(ctx: tanjun.abc.SlashContext, receiver: hikari.Member, comments: str, value: str, collateral: str,
                   config: Config = alluka.inject(type=Config),
                   db: aiosqlite.Connection = alluka.inject(type=aiosqlite.Connection)):
    if receiver.id == ctx.author.id:
        embed = hikari.Embed(
            title='Error',
            description='You can\'t rep yourself.',
            color=config['colors']['error']
        )
        await ctx.respond(embed=embed)
        return

    if len(comments) > 500:
        embed = hikari.Embed(
            title='Error',
            description='Rep can\'t be longer than 500 characters.',
            color=config['colors']['error']
        )
        await ctx.respond(embed=embed)
        return

    cursor: aiosqlite.Cursor
    async with db.cursor() as cursor:
        await cursor.execute('''
            SELECT max("rep-id")
            FROM "REPUTATION"
        ''')

        rep_id = (await cursor.fetchone())[0] + 1

    rep_embed = hikari.Embed(
        title=f'Craft Reputation Given',
        color=config['colors']['secondary']
    )

    rep_embed.set_author(name=f'Reputation by {ctx.author}')
    rep_embed.add_field(name='Receiver', value=receiver.mention, inline=True)
    rep_embed.add_field(name='Comments', value=comments, inline=False)
    rep_embed.set_footer(text=f'Rep ID: {rep_id}')
    rep_embed.set_thumbnail(config['logo_url'])

    rep_log_channel = ctx.get_guild().get_channel(config['rep']['rep_log_channel_id'])
    if isinstance(rep_log_channel, hikari.TextableGuildChannel):
        message = await rep_log_channel.send(embed=rep_embed)
    else:
        await ctx.respond('Something went wrong')
        return

    await db.execute('''
        INSERT INTO "REPUTATION"("rep-id", receiver, provider, comments, created_at, type, msg_id)
        VALUES (:rep_id, :receiver, :provider, :comments, :created_at, :type, :msg_id)
    ''', {
        "rep_id": rep_id,
        "receiver": receiver.id,
        "provider": ctx.author.id,
        "comments": comments.strip() + ' | ' + value.strip() + ' | ' + 'With collateral' if collateral else 'No collateral',
        "created_at": int(time.time()),
        "type": 'craft',
        "msg_id": message.id
    })
    await db.commit()

    embed = hikari.Embed(
        title='Success',
        description=f'Successfully gave rep to {receiver.mention}',
        color=config['colors']['success']
    )

    await ctx.respond(embed=embed)


@tanjun.with_int_slash_option('rep_id', 'The ID of the rep to remove')
@rep_slash_group_perms.as_sub_command('remove', 'Removes a rep from the database', always_defer=True)
async def rep_remove(ctx: tanjun.abc.SlashContext, rep_id: int,
                     config: Config = alluka.inject(type=Config),
                     db: aiosqlite.Connection = alluka.inject(type=aiosqlite.Connection)):
    cursor: aiosqlite.Cursor
    # Ensure that rep with given ID exists
    async with await db.cursor() as cursor:
        await cursor.execute('''
            SELECT *
            FROM "REPUTATION"
            WHERE "rep-id"=:rep_id
        ''', {"rep_id": rep_id})
        rep_tuple = await cursor.fetchone()

    # If not, return
    if rep_tuple is None:
        embed = hikari.Embed(
            title='Error',
            description=f'Reputation with id {rep_id} not found.',
            color=config['colors']['error']
        )
        await ctx.respond(embed=embed)
        return

    rep = convert_to_rep(rep_tuple)
    await db.execute('''
        DELETE
        FROM "REPUTATION"
        WHERE "rep-id"=:rep_id
    ''', {"rep_id": rep_id})
    await db.commit()

    embed = None
    channel_id = config['rep']['rep_log_channel_id']
    channel = ctx.get_guild().get_channel(channel_id)

    try:
        await channel.delete_messages(rep['msg_id'])
    except (hikari.BulkDeleteError, AttributeError) as exception:
        await log_error(ctx, exception)
        embed = hikari.Embed(
            title=f'Partial Deletion',
            description=f'Reputation with id {rep_id} removed from'
                        f' database but not from <#{channel_id}>.',
            color=config['colors']['secondary']
        )
    else:
        embed = hikari.Embed(
            title=f'Successful Deletion',
            description=f'Reputation with id {rep_id} removed'
                        f' from <#{channel_id}>.',
            color=config['colors']['success']
        )
    finally:
        await ctx.respond(embed=embed)


@tanjun.with_int_slash_option('page', 'The page of the list. Each page contains 10 reps', default=1)
@tanjun.with_user_slash_option('user', 'The user to list reps for')
@rep_slash_group.as_sub_command('list', 'Lists the reps the user has received', always_defer=True)
async def rep_list(ctx: tanjun.abc.SlashContext, user: hikari.User, page: int,
                   config: Config = alluka.inject(type=Config),
                   db: aiosqlite.Connection = alluka.inject(type=aiosqlite.Connection)):
    cursor: aiosqlite.Cursor = await db.cursor()

    await cursor.execute('''
        SELECT COUNT(1)
        FROM "REPUTATION"
        WHERE receiver=:receiver_id
    ''', {"receiver_id": user.id})
    rows = (await cursor.fetchone())[0]

    if rows == 0:
        embed = hikari.Embed(
            description='User has not received any reps.',
            color=config['colors']['primary']
        )
        await ctx.respond(embed=embed)
        return

    max_page = ceil(rows / 10)

    if page > max_page or page < 1:
        embed = hikari.Embed(
            title='Error',
            description=f'There is no page {page}. Valid pages are between 1 and {max_page}',
            color=config['colors']['error']
        )
        await ctx.respond(embed=embed)
        return

    await cursor.execute(f'''
        SELECT *
        FROM "REPUTATION"
        WHERE receiver=:receiver_id
        ORDER BY "rep-id"
        LIMIT 10
        OFFSET {(page - 1) * 10}
    ''', {"receiver_id": user.id})
    res = await cursor.fetchall()
    await cursor.close()

    embed = hikari.Embed(
        title=f'Reps given to {user}',
        color=config['colors']['primary']
    )

    for rep_tuple in res:
        rep = convert_to_rep(rep_tuple)
        provider = await ctx.rest.fetch_user(rep['provider'])

        embed.add_field(name=f"__Rep #{rep['rep_id']}__",
                        value=f"`{rep['comments']}`\n"
                              f"*By: {provider.mention if provider else '<@' + str(rep['provider']) + '>'}*",
                        inline=False)

    embed.set_footer(text=f'Page: {page}/{max_page}')

    await ctx.respond(embed=embed)


@tanjun.as_loader()
def load(client: tanjun.Client):
    client.add_component(component)


@tanjun.as_unloader()
def unload(client: tanjun.Client):
    client.remove_component(component)
