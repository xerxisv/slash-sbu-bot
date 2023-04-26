import hikari
import tanjun

from utils.config.config import ConfigHandler

config = ConfigHandler().get_config()


async def weight_banned_check(ctx: tanjun.abc.Context):
    if config['stats']['weight_banned_role_id'] in ctx.member.role_ids:
        embed = hikari.Embed(
            title='Error',
            description=f"You have been banned from applying for weight roles.",
            color=config['colors']['error']
        )
        await ctx.respond(embed=embed)
        return False

    return True


async def active_check(ctx: tanjun.abc.Context):
    return await _has_role(ctx, config['misc']['allowed_role_id'])


async def jr_mod_check(ctx: tanjun.abc.Context):
    return await _has_role(ctx, config['jr_mod_role_id'])


async def mod_check(ctx: tanjun.abc.Context):
    return await _has_role(ctx, config['mod_role_id'])


async def jr_admin_check(ctx: tanjun.abc.Context):
    return await _has_role(ctx, config['jr_admin_role_id'])


async def admin_check(ctx: tanjun.abc.Context):
    return await _has_role(ctx, config['admin_role_id'])


async def _has_role(ctx: tanjun.abc.Context, role: int) -> bool | None:
    if not role in ctx.member.role_ids:
        embed = hikari.Embed(
            title='Error',
            description=f"Insufficient permissions, only members with **{ctx.get_guild().get_role(role)}** role can run this command",
            color=config['colors']['error']
        )
        await ctx.respond(embed=embed)
        return False

    return True
