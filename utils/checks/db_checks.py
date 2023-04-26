import aiosqlite
import alluka
import hikari
import tanjun

from utils.config.config import ConfigHandler

config = ConfigHandler().get_config()


async def registered_check(ctx: tanjun.abc.Context, db: alluka.Injected[aiosqlite.Connection]):
    cursor: aiosqlite.Cursor
    async with db.cursor() as cursor:
        await cursor.execute('''
            SELECT COUNT(1), discord_id
            FROM "USERS"
            WHERE "discord_id"=:discord_id
        ''', {"discord_id": ctx.author.id})

        res = (await cursor.fetchone())

    if res[0] == 0 or res[1] == 1:
        embed = hikari.Embed(
            title=f'Error',
            description='You need to be verified to run this command.\nRun `+verify <IGN>`',
            color=config['colors']['error']
        )
        await ctx.respond(embed=embed)
        return False

    return True