import datetime
import time
from math import ceil

import aiosqlite
import alluka
import hikari
import tanjun

from miru.ext import nav
from utils.config import Config, ConfigHandler
from utils.database.converters import convert_to_suggestion
from utils.error_utils import log_error


#############################
#    Commands' Functions    #
#############################

async def answer(ctx: tanjun.abc.SlashContext, suggestion_id: int, reason: str, is_approved: bool, config: Config,
                 db: aiosqlite.Connection):
    cursor: aiosqlite.Cursor
    async with db.cursor() as cursor:
        await cursor.execute('''
            SELECT *
            FROM SUGGESTIONS
            WHERE suggestion_number=:suggestion_id
        ''', {
            "suggestion_id": suggestion_id
        })
        res = await cursor.fetchone()

    if res is None:
        embed = hikari.Embed(
            title="Error",
            description="Suggestion not found.",
            color=config['colors']['error']
        )
        await ctx.respond(embed=embed)
        return

    suggestion = convert_to_suggestion(res)

    title = 'Approved' if is_approved else 'Denied'
    color = config['colors']['success'] if is_approved else config['colors']['error']

    suggestion_embed = hikari.Embed(
        title=title,
        description=f"{suggestion['suggestion']}",
        timestamp=datetime.datetime.now(tz=datetime.timezone.utc),
        color=color
    )
    suggestion_author: hikari.User | int
    suggestion_author = ctx.cache.get_user(suggestion['author_id'])
    if suggestion_author is None:
        suggestion_author = await ctx.rest.fetch_user(suggestion['author_id'])
    if suggestion_author is None:
        suggestion_author = suggestion["author_id"]

    suggestion_embed.set_author(name=f'Suggested by {suggestion_author}')
    suggestion_embed.add_field(name="Reason", value=f"{reason}", inline=False)
    suggestion_embed.set_footer(text=f'Suggestion number {suggestion_id} | {title} by {ctx.author}')
    suggestion_embed.set_thumbnail(config['logo_url'])

    channel = ctx.get_guild().get_channel(config['suggestions']['suggestions_channel_id'])
    message: hikari.Message = await channel.fetch_message(suggestion['message_id'])

    if message.author.id != ctx.client.cache.get_me().id:
        await message.delete()
        await channel.send(embed=suggestion_embed)
    else:
        await message.edit(embed=suggestion_embed)

    approved_embed = hikari.Embed(
        title=title,
        description=f'Suggestion number {suggestion_id} {title.lower()} successfully.',
        timestamp=datetime.datetime.now(tz=datetime.timezone.utc),
        color=config['colors']['success']
    )
    try:
        # Try DMing the user
        await suggestion_author.send(embed=suggestion_embed)
    except (hikari.InternalServerError, hikari.ForbiddenError, AttributeError):
        # DMing can throw because: API error, user having DMs closed/ bad intents or suggestion_author is an int
        approved_embed.add_field(name="Direct Message", value=f"User could not be dmed", inline=False)

    except Exception as exception:
        # Any other error will be sent to the logs
        approved_embed.add_field(name="Direct Message", value=f"User could not be dmed", inline=False)
        await log_error(ctx, exception)

    else:
        # If no errors occurred send successful message
        approved_embed \
            .add_field(name="Direct Message", value=f"{suggestion_author} dmed successfully", inline=False)

    finally:
        # Send the embed regardless of errors
        await ctx.respond(embed=approved_embed)

        await db.execute('''
            UPDATE "SUGGESTIONS"
            SET "answered"=:answered, "approved"=:approved, "reason"=:reason, "approved_by"=:approved_by
            WHERE "suggestion_number"=:suggestion_id;
        ''', {
            "answered": True,
            "approved": is_approved,
            "reason": reason,
            "approved_by": ctx.author.id,
            "suggestion_id": suggestion_id,
        })
        await db.commit()


################
#   Commands   #
################

component = tanjun.Component()

suggestion_group = tanjun.slash_command_group('suggestion', 'Suggestion related commands', default_to_ephemeral=True,
                                              default_member_permissions=hikari.Permissions.MANAGE_CHANNELS)

component.add_slash_command(suggestion_group)


@component.with_command()
@tanjun.with_concurrency_limit("database_commands")
@tanjun.with_greedy_argument('suggestion')
@tanjun.as_message_command('suggest')
async def suggest(ctx: tanjun.abc.MessageContext, suggestion: str,
                  config: Config = alluka.inject(type=Config),
                  db: aiosqlite.Connection = alluka.inject(type=aiosqlite.Connection)):
    if len(suggestion) > 500:
        embed = hikari.Embed(
            title='Error',
            description='Suggestion can\'t be longer than 500 characters',
            color=config['colors']['error']
        )
        await ctx.respond(embed=embed)
        return

    cursor: aiosqlite.Cursor
    async with db.cursor() as cursor:
        await cursor.execute('''
            SELECT max(suggestion_number)
            FROM "SUGGESTIONS"
        ''')
        suggestion_num = (await cursor.fetchone())[0] + 1

    # Create embed
    suggestion_embed = hikari.Embed(
        title=f'Suggestion',
        description=f'{suggestion}',
        timestamp=datetime.datetime.now(tz=datetime.timezone.utc),
        color=config['colors']['primary']
    )

    # Set author icon if there is one
    if ctx.message.author.display_avatar_url is not None:
        suggestion_embed.set_author(name=f'Suggested by {ctx.message.author}',
                                    icon=ctx.message.author.display_avatar_url)
    else:
        suggestion_embed.set_author(name=f'Suggested by {ctx.message.author}')

    suggestion_embed.set_footer(text=f'Suggestion number {suggestion_num}')
    suggestion_embed.set_thumbnail(config['logo_url'])

    channel = ctx.get_guild().get_channel(config['suggestions']['suggestions_channel_id'])
    message = await channel.send(embed=suggestion_embed)

    await ctx.respond(f"Suggestion sent to <#{config['suggestions']['suggestions_channel_id']}>")
    await message.add_reaction('✅')
    await message.add_reaction('❌')

    await db.execute('''
        INSERT INTO "SUGGESTIONS" (suggestion_number, message_id, author_id, suggestion, created_at) 
        VALUES (:suggestion_number, :message_id, :author_id, :suggestion, :created_at)
    ''', {
        "suggestion_number": suggestion_num,
        "message_id": message.id,
        "suggestion": suggestion,
        "author_id": ctx.author.id,
        "created_at": int(time.time())
    })
    await db.commit()


@tanjun.with_concurrency_limit("database_commands")
@tanjun.with_str_slash_option('reason', 'The reason for approving', default=None)
@tanjun.with_int_slash_option('suggestion', 'The suggestion\'s ID to approve', key='suggestion_id')
@suggestion_group.as_sub_command('approve', 'Approves the given suggestion', always_defer=True)
async def suggestion_approve(ctx: tanjun.abc.SlashContext, suggestion_id: int, reason: str,
                             config: Config = alluka.inject(type=Config),
                             db: aiosqlite.Connection = alluka.inject(type=aiosqlite.Connection)):
    await answer(ctx, suggestion_id, reason, True, config, db)


@tanjun.with_concurrency_limit("database_commands")
@tanjun.with_str_slash_option('reason', 'The reason for denying', default=None)
@tanjun.with_int_slash_option('suggestion', 'The suggestion\'s ID to deny', key='suggestion_id')
@suggestion_group.as_sub_command('deny', 'Denies the given suggestion', always_defer=True)
async def suggestion_deny(ctx: tanjun.abc.SlashContext, suggestion_id: int, reason: str,
                          config: Config = alluka.inject(type=Config),
                          db: aiosqlite.Connection = alluka.inject(type=aiosqlite.Connection)):
    await answer(ctx, suggestion_id, reason, False, config, db)


@tanjun.with_concurrency_limit("database_commands")
@tanjun.with_int_slash_option('suggestion', 'The suggestion\'s ID to remove', key='suggestion_id')
@suggestion_group.as_sub_command('delete', 'Deletes the given suggestion', always_defer=True)
async def suggestion_delete(ctx: tanjun.abc.SlashContext, suggestion_id: int,
                            config: Config = alluka.inject(type=Config),
                            db: aiosqlite.Connection = alluka.inject(type=aiosqlite.Connection)):
    cursor: aiosqlite.Cursor
    async with db.cursor() as cursor:
        await cursor.execute('''
            SELECT *
            FROM "SUGGESTIONS"
            WHERE suggestion_number=:suggestion_id
        ''', {
            "suggestion_id": suggestion_id
        })
        res = await cursor.fetchone()
    # Check if suggestion with given ID exists
    if res is None:
        embed = hikari.Embed(
            title='Error',
            description=f'Suggestion with ID {suggestion_id} not found',
            color=config['colors']['error']
        )
        await ctx.respond(embed=embed)
        return

    suggestion = convert_to_suggestion(res)

    # Delete suggestion
    await db.execute('''
        DELETE
        FROM "SUGGESTIONS"
        WHERE suggestion_number=:suggestion_id
    ''', {
        "suggestion_id": suggestion_id
    })
    await db.commit()

    msg = 'Suggestion deleted'
    try:
        await (await ctx.get_guild()
               .get_channel(config['suggestions']['suggestions_channel_id'])
               .fetch_message(suggestion['message_id'])).delete()
    except hikari.NotFoundError:
        msg = f"Suggestion deleted from database but" \
              f"was not found in <#{config['suggestions']['suggestions_channel_id']}>. Please delete manually"

    embed = hikari.Embed(
        title='Success',
        description=msg,
        color=config['colors']['success']
    )
    await ctx.respond(embed=embed)


@tanjun.with_concurrency_limit("database_commands")
@tanjun.with_bool_slash_option('approved', 'Lists approved/denied suggestion', default=None)
@tanjun.with_bool_slash_option('answered', 'Lists answered/unanswered suggestions', default=None)
@tanjun.with_user_slash_option('author', 'The author of the suggestion', default=None)
@suggestion_group.as_sub_command('list', 'Lists suggestions')
async def suggestion_list(ctx: tanjun.abc.SlashContext, author: hikari.User, answered: bool, approved: bool,
                            config: Config = alluka.inject(type=Config),
                            db: aiosqlite.Connection = alluka.inject(type=aiosqlite.Connection)):
    script = '''
        SELECT *
        FROM "SUGGESTIONS"
    '''

    if author is not None:
        script += '\nWHERE author_id=:author_id'
    elif answered is not None:
        script += '\nWHERE answered=:answered'
    elif approved is not None:
        script += '\nWHERE approved=:approved'

    cursor: aiosqlite.Cursor
    async with db.cursor() as cursor:
        await cursor.execute(script, {
            "author_id": author.id if author else None,
            "answered": 1 if answered else 0,
            "approved": 1 if approved else 0
        })
        res = await cursor.fetchall()

    if (rows := len(list(res))) == 0:
        embed = hikari.Embed(
            title='Nothing to show',
            description='No suggestions passed the filter',
            color=config['colors']['secondary']
        )
        await ctx.respond(embed=embed)
        return

    pages = []
    pages_num = ceil(rows / 10)
    for page in range(1, pages_num + 1):
        embed = hikari.Embed(
            title='Reps',
            color=config['colors']['primary']
        )

        for suggestion in res[(page - 1) * 10:page * 10]:
            suggestion = convert_to_suggestion(suggestion)
            embed.add_field(name=f"Suggestion **#{suggestion['suggestion_number']}**",
                            value=f"`{suggestion['suggestion']}`\n"
                                  f"*By <@{suggestion['author_id']}>*",
                            inline=False
                            )

        pages.append(embed)

    navigator = nav.NavigatorView(pages=pages, timeout=30)
    await navigator.send(ctx.interaction)

@tanjun.as_loader()
def load(client: tanjun.Client):
    if not ConfigHandler().get_config()['modules']['suggestions']:
        return

    client.add_component(component)


@tanjun.as_unloader()
def unload(client: tanjun.Client):
    client.remove_component_by_name(component.name)
