import aiosqlite
import alluka
import hikari
import tanjun

from utils.checks.role_checks import jr_admin_check
from utils.config import Config, ConfigHandler
from utils.converters.converters import to_player_info
from utils.database.converters import convert_to_user

component = tanjun.Component()
command_group = tanjun.slash_command_group("gtatsu", "Guild Tatsu commands")
component.add_slash_command(command_group)


@tanjun.with_check(jr_admin_check)
@tanjun.with_int_slash_option("amount", "The amount of gtatsu to give")
@tanjun.with_str_slash_option("ign", "The user's IGN to give gtatsu to")
@command_group.as_sub_command("give", "Give gtatsu to a user", always_defer=True)
async def give_tatsu(ctx: tanjun.abc.SlashContext, ign: str, amount: int,
                     db: aiosqlite.Connection = alluka.inject(type=aiosqlite.Connection),
                     config: Config = alluka.inject()):
    await db.execute('''
            UPDATE "USERS"
            SET tatsu_score = tatsu_score + :amount
            WHERE UPPER(ign)=:ign;
        ''', {
        "count": amount,
        "ign": ign.upper()
    })
    await db.commit()
    embed = hikari.Embed(
        title=f"Success",
        description=f"`{ign}` has been given `{amount}` gtatsu score",
        color=config['colors']['success']
    )
    await ctx.respond(embed=embed)


@tanjun.with_int_slash_option("amount", "The amount of gtatsu to remove")
@tanjun.with_member_slash_option("ign", "The user's IGN to remove gtatsu from")
@command_group.as_sub_command("remove", "Remove gtatsu from a user", always_defer=True)
async def remove_gtatsu(ctx: tanjun.abc.SlashContext, ign: str, amount: int,
                        db: aiosqlite.Connection = alluka.inject(type=aiosqlite.Connection),
                        config: Config = alluka.inject()):
    await db.execute('''
            UPDATE "USERS"
            SET tatsu_score=tatsu_score - :amount
            WHERE UPPER(ign)=:ign;
        ''', {
        "amount": amount,
        "ign": ign.upper()
    })
    await db.commit()

    embed = hikari.Embed(
        title=f"Success",
        description=f"`{amount}` gtatsu score has been remove from `{ign}`",
        color=config['colors']['success']
    )
    await ctx.respond(embed=embed)


@tanjun.with_int_slash_option("amount", "The user's new tatsu score")
@tanjun.with_member_slash_option("ign", "The user's IGN")
@command_group.as_sub_command("set", "Set gtatsu a user's gtatsu", always_defer=True)
async def set_gtatsu(ctx: tanjun.abc.SlashContext, ign: str, amount: int,
                     db: aiosqlite.Connection = alluka.inject(type=aiosqlite.Connection),
                     config: Config = alluka.inject()):
    await db.execute('''
            UPDATE "USERS"
            SET tatsu_score = :amount
            WHERE UPPER(ign)=:ign;
        ''', {
        "amount": amount,
        "ign": ign
    })
    await db.commit()
    embed = hikari.Embed(
        title=f'Success',
        description=f"`{ign}` gtatsu has been set to `{amount}`",
        color=config['colors']['success']
    )
    await ctx.respond(embed=embed)


@tanjun.with_member_slash_option('user', 'The user', default=None)
@tanjun.with_str_slash_option('ign', 'The username of the member', default=None)
@command_group.as_sub_command('info', 'The info of a users gtatsu', always_defer=True)
async def gtatsu_info(ctx: tanjun.abc.SlashContext, user: hikari.User, ign: str,
                      db: aiosqlite.Connection = tanjun.inject(),
                      config: Config = tanjun.inject()):
    if user:
        script = (
            '''
                SELECT * 
                FROM "USERS"
                WHERE discord_id = :discord_id
            ''', {
                "discord_id": user.id
            })
    elif ign:
        script = (
            '''
                SELECT *
                FROM "USERS"
                WHERE uuid = :uuid
            ''', {
                "uuid": (await to_player_info(ign))['uuid']
            }
        )
    else:
        script = (
            '''
                SELECT * 
                FROM "USERS"
                WHERE discord_id = :discord_id
            ''', {
                "discord_id": ctx.member.id
            })

    cursor: aiosqlite.Cursor
    async with db.cursor() as cursor:
        await cursor.execute(*script)
        res = await cursor.fetchone()

    user_info = convert_to_user(res)

    embed = hikari.Embed(
        title="Gtatsu",
        description=f'''
        **User**: <@{user_info['discord_id']}>
        **IGN**: `{user_info['ign']}`
    ''',
        color=config['colors']['primary']
    )

    embed.add_field("This week's Tatsu", str(user_info['this_week_tatsu_score']))
    embed.add_field("Total Tatsu", str(user_info['tatsu_score']))
    embed.set_thumbnail('https://mc-heads.net/avatar/' + user_info['uuid'])

    await ctx.respond(embed=embed)


@tanjun.as_loader()
def load(client: tanjun.Client) -> None:
    if not ConfigHandler().get_config()['modules']['gtatsu']:
        return

    client.add_component(component)


@tanjun.as_unloader()
def unload(client: tanjun.Client) -> None:
    client.remove_component_by_name(component.name)
