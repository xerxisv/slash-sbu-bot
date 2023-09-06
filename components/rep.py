import time
from math import ceil

import aiosqlite
import alluka
import hikari
import tanjun
from aiosqlite import Connection
from miru.ext import nav

from utils.checks.role_checks import jr_admin_check
from utils.config import Config
from utils.database import convert_to_rep
from utils.error_utils import log_error

################
#   Commands   #
################

component = tanjun.Component()

rep_slash_group = tanjun.slash_command_group("rep", "Reputation commands")

component.add_slash_command(rep_slash_group)


@tanjun.with_str_slash_option("comments", "Brief description of the rep")
@tanjun.with_user_slash_option("receiver", "The user to give rep to")
@rep_slash_group.as_sub_command("give", "Give reputation to a user", always_defer=True, default_to_ephemeral=True)
async def rep_give(ctx: tanjun.abc.SlashContext, receiver: hikari.User, comments: str,
                   config: Config = tanjun.inject(), db: Connection = tanjun.inject()):
    craft_ch = config['rep']['craft_rep_channel_id']
    carry_ch = config['rep']['carry_rep_channel_id']

    description = ""
    error = False

    if ctx.channel_id != carry_ch and ctx.channel_id != craft_ch:
        description = f"You can only use this in <#{craft_ch}> or <#{carry_ch}>"
        error = True
    elif receiver.id == ctx.author.id:
        description = "You can't rep yourself."
        error = True
    elif len(comments) > 500:
        description = "Rep can't be longer than 500 characters."
        error = True

    if error:
        embed = hikari.Embed(
            title="Error",
            description=description,
            color=config['colors']['error']
        )
        await ctx.respond(embed=embed)
        return

    cursor: aiosqlite.Cursor
    async with db.cursor() as cursor:
        await cursor.execute('''
            SELECT max(rep_id)
            FROM "REPUTATION"
        ''')

        rep_id = (await cursor.fetchone())[0] + 1

    rep_type = 0 if ctx.channel_id == craft_ch else 1
    rep_embed = hikari.Embed(
        title=f"{'Carry' if rep_type else 'Craft'} Reputation Given",
        color=config['colors']['secondary']
    )

    rep_embed.set_author(name=ctx.author.username, icon=ctx.author.avatar_url)
    rep_embed.add_field(name="Receiver", value=receiver.mention, inline=True)
    rep_embed.add_field(name="Comments", value=comments, inline=False)
    rep_embed.set_footer(text=f"Rep ID: {rep_id}")
    rep_embed.set_thumbnail(config['logo_url_dark'])

    msg = await ctx.get_channel().send(embed=rep_embed)

    await db.execute('''
        INSERT INTO "REPUTATION"
        VALUES (:rep_id, :receiver, :provider, :comments, :created_at, :msg_id, :type)
    ''', {
        "rep_id": rep_id,
        "receiver": receiver.id,
        "provider": ctx.author.id,
        "comments": comments,
        "created_at": int(time.time()),
        "type": rep_type,
        "msg_id": msg.id
    })
    await db.commit()

    embed = hikari.Embed(
        title="Success",
        description=f"Successfully gave rep to {receiver.mention}",
        color=config['colors']['success']
    )

    await ctx.respond(embed=embed)


@tanjun.with_check(jr_admin_check)
@tanjun.with_int_slash_option("rep_id", "The ID of the rep to remove")
@rep_slash_group.as_sub_command("remove", "Removes a rep from the database", always_defer=True,
                                default_to_ephemeral=True)
async def rep_remove(ctx: tanjun.abc.SlashContext, rep_id: int,
                     config: Config = tanjun.inject(), db: Connection = tanjun.inject()):
    cursor: aiosqlite.Cursor
    # Ensure that rep with given ID exists
    async with await db.cursor() as cursor:
        await cursor.execute('''
            SELECT COUNT(1), msg_id, type
            FROM "REPUTATION"
            WHERE rep_id=:rep_id
        ''', {"rep_id": rep_id})
        data = await cursor.fetchone()

    # If not, return
    if not data[0]:
        embed = hikari.Embed(
            title="Error",
            description=f"Reputation with id {rep_id} not found.",
            color=config['colors']['error']
        )
        await ctx.respond(embed=embed)
        return

    await db.execute('''
        DELETE
        FROM "REPUTATION"
        WHERE rep_id=:rep_id
    ''', {"rep_id": rep_id})
    await db.commit()

    channel_id = config['rep']['craft_rep_channel_id'] if data[2] == 0 else config['rep']['carry_rep_channel_id']
    channel = ctx.get_guild().get_channel(channel_id)

    try:
        if not isinstance(channel, hikari.TextableGuildChannel):
            raise AttributeError

        await channel.delete_messages(data[1])
    except (hikari.BulkDeleteError, AttributeError) as exception:
        await log_error(ctx, exception)
        embed = hikari.Embed(
            title="Partial Deletion",
            description=f"Reputation with id {rep_id} removed from database but not from <#{channel_id}>.",
            color=config['colors']['secondary']
        )
    else:
        embed = hikari.Embed(
            title="Success",
            description=f"Reputation with id {rep_id} removed"
                        f" from <#{channel_id}>.",
            color=config['colors']['success']
        )

    await ctx.respond(embed=embed)


@tanjun.with_user_slash_option("carrier", "The user whose carrier reps to list", default=None)
@tanjun.with_user_slash_option("crafter", "The user whose carry reps to list", default=None)
@rep_slash_group.as_sub_command("list", "Lists the reps a user has received", always_defer=True)
async def rep_list(ctx: tanjun.abc.SlashContext, carrier: hikari.User, crafter: hikari.User,
                   config: Config = alluka.inject(type=Config),
                   db: aiosqlite.Connection = alluka.inject(type=aiosqlite.Connection)):
    user = carrier if carrier is not None else crafter
    rep_type = 0 if crafter is not None else 1

    cursor: aiosqlite.Cursor = await db.cursor()
    await cursor.execute('''
        SELECT *
        FROM "REPUTATION"
        WHERE receiver=:receiver_id AND type=:type
    ''', {
        "receiver_id": user.id,
        "type": rep_type
    })
    data = await cursor.fetchall()

    if (rep_num := len(list(data))) == 0:
        embed = hikari.Embed(
            description=f"User has not received any {'carry' if rep_type else 'craft'} reps.",
            color=config['colors']['primary']
        )
        await ctx.respond(embed=embed)
        return

    pages = []
    max_page = ceil(rep_num / 10)
    for page in range(1, max_page + 1):
        embed = hikari.Embed(
            title=f"{'Carry' if rep_type else 'Craft'} Reps",
            color=config['colors']['primary']
        )
        for rep in data[(page-1) * 10:page * 10]:
            rep = convert_to_rep(rep)

            embed.add_field(name=f"Rep #{rep['rep_id']}",
                            value=f"<t:{rep['created_at']}:D>\n"
                                  f"From: <@{rep['provider']}>\n"
                                  f"```{rep['comments']}```\n"
                            )
        embed.set_footer(text=f"User has a total of {rep_num} {'carry' if rep_type else 'craft'} reps")
        embed.set_author(name=user.username, icon=user.avatar_url)
        pages.append(embed)

    navigator = nav.NavigatorView(pages=pages, timeout=30)
    await navigator.send(ctx.interaction, responded=True)


@tanjun.as_loader()
def load(client: tanjun.Client):
    client.add_component(component)


@tanjun.as_unloader()
def unload(client: tanjun.Client):
    client.remove_component(component)
