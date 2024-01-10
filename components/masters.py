from typing import Annotated, Literal

import aiohttp
import hikari
import tanjun

from utils import profile_choices, trigger_typing
from utils.config import Config, ConfigHandler

################
#   Commands   #
################

commands_component = tanjun.Component()


# noinspection PyTypedDict
async def check_req_routine(ctx: tanjun.abc.Context, ign: str, cute_name, is_jr: bool, min_passed_reqs=3):
    config = ConfigHandler().get_config()
    await trigger_typing(ctx)

    session = aiohttp.ClientSession()

    (await session.get(f"https://sky.shiiyu.moe/stats/{ign}")).close()

    async with session.get(f"https://sky.shiiyu.moe/api/v2/profile/{ign}") as res:
        if res.status != 200:
            embed = hikari.Embed(
                title='Error',
                description=f'User with IGN `{ign}` not found.\n'
                            f'If `{ign}` is a valid IGN then it\'s an API error.\n'
                            f'Please check manually.',
                color=config['colors']['error']
            )
            embed.set_footer(f"Status code: {res.status}")
            await ctx.respond(embed=embed)
            await session.close()
            return

        profiles = await res.json()

    await session.close()

    weight = 0  # used to store the weight but also find the biggest weight in the profiles

    is_valid_profile = cute_name is None
    selected_profile = None

    try:
        for profile in profiles["profiles"].values():
            if cute_name is not None:
                if profile["cute_name"].lower() != cute_name.lower():
                    continue
                is_valid_profile = True
                selected_profile = profile
            elif profile["data"]["weight"]["senither"]["overall"] > weight:
                weight = int(profile["data"]["weight"]["senither"]["overall"])
                selected_profile = profile
    except KeyError:
        embed = hikari.Embed(
            title='Error',
            description='Something went wrong. Make sure your APIs in on.\n'
                        'If this problem continues, open a technical difficulties ticket.',
            color=config['colors']['error']
        )
        await ctx.respond(embed=embed)
        return

    if not is_valid_profile:
        embed = hikari.Embed(
            title='Error',
            description=f'You have no {cute_name.title()} profile.',
            color=config['colors']['error']
        )
        await ctx.respond(embed=embed)
        return

    try:
        dungeon_lvl = int(selected_profile["data"]["dungeons"]["catacombs"]["level"]["level"])
        slayer_xp = int(selected_profile["data"]["slayer"]["total_slayer_xp"])
    except KeyError:
        embed = hikari.Embed(
            title='Error',
            description='Something went wrong. Make sure your APIs in on.\n'
                        'If this problem continues, open a technical difficulties ticket.',
            color=config['colors']['error']
        )
        await ctx.respond(embed=embed)
        return

    guild = 'jr' if is_jr else 'main'

    dungeon_req = config['masters'][guild]['dungeon_lvl']
    slayer_req = config['masters'][guild]['slayer_xp']
    weight_req = config['masters'][guild]['weight']

    passed_flag = 0b000
    passed_reqs = 0

    if slayer_xp >= slayer_req:
        passed_flag += 0b1 << 0
        passed_reqs += 1
    if dungeon_lvl >= dungeon_req:
        passed_flag += 0b1 << 1
        passed_reqs += 1
    if weight >= weight_req:
        passed_flag += 0b1 << 2
        passed_reqs += 1

    title = 'Masters Junior Requirements' if is_jr else 'Masters Requirements'

    if not passed_reqs:
        embed = hikari.Embed(
            title=title,
            description='',
            color=config['colors']['error']
        )
        embed.add_field(name="No requirements met", value="You dont meet any of the requirements", inline=False)
    elif passed_reqs < min_passed_reqs:
        embed = hikari.Embed(
            title=title,
            description='',
            color=config['colors']['secondary']
        )
        embed.add_field(name="Hold Up", value=f"You meet {passed_reqs}/3 of the requirements.", inline=False)
    else:
        embed = hikari.Embed(
            title=title,
            description='',
            color=config['colors']['primary']
        )
        embed.add_field(name="Congratulations!",
                        value=f"You meet {'all the' if min_passed_reqs == 3 else 'enough'} requirements",
                        inline=False)

    p = "**Passed**"
    np = "**Not Passed**"

    embed.add_field(name="Your Stats",
                    value=f"Slayer Req: `{slayer_req}` xp | "
                          f"Your Slayers: `{slayer_xp}` | {p if passed_flag & (0b1 << 0) else np} \n"
                          f"Cata req: level `{dungeon_req}` | "
                          f"Your Cata: `{dungeon_lvl}` | {p if passed_flag & (0b1 << 1) else np} \n"
                          f"Weight req: `{weight_req}` senither weight | "
                          f"Your Weight: `{weight}` | {p if passed_flag & (0b1 << 2) else np}",
                    inline=False)
    embed.set_footer(text=f'{ign} | {selected_profile["cute_name"]}')

    await ctx.respond(embed=embed)


@commands_component.with_command(follow_wrapped=True)
@tanjun.annotations.with_annotated_args(follow_wrapped=True)
@tanjun.as_message_command('checkreq')
@tanjun.as_slash_command('checkreq', 'Checks if you pass the requirements for masters')
async def checkreq(ctx: tanjun.abc.Context,
                   ign: Annotated[tanjun.annotations.Str, "Your IGN"],
                   cute_name: Annotated[
                       tanjun.annotations.Str, "Profile name", tanjun.annotations.Choices(profile_choices)] = None):
    await check_req_routine(ctx, ign, cute_name, is_jr=False)


@commands_component.with_command(follow_wrapped=True)
@tanjun.annotations.with_annotated_args(follow_wrapped=True)
@tanjun.as_message_command('checkreqjr')
@tanjun.as_slash_command('checkreqjr', 'Checks if you pass the requirements for masters jr')
async def checkreqjr(ctx: tanjun.abc.Context,
                     ign: Annotated[tanjun.annotations.Str, "Your IGN"],
                     cute_name: Annotated[
                         tanjun.annotations.Str, "Profile name", tanjun.annotations.Choices(profile_choices)] = None):
    await check_req_routine(ctx, ign, cute_name, is_jr=True, min_passed_reqs=2)


@commands_component.with_command()
@tanjun.with_int_slash_option('weight_req', 'The new weight requirement', key='weight', default=None)
@tanjun.with_int_slash_option('slayer_req', 'The new slayer requirement', key='slayer', default=None)
@tanjun.with_int_slash_option('dungeon_req', 'The new dungeon requirement', key='dungeon', default=None)
@tanjun.with_str_slash_option('guild', 'Which guild\'s requirements to change', choices=('main', 'jr'))
@tanjun.as_slash_command('change_reqs', 'Changes the requirements for the given guild',
                         default_member_permissions=hikari.Permissions.MANAGE_CHANNELS)
async def change_reqs(ctx: tanjun.abc.SlashContext, guild: Literal['main', 'jr'],
                      dungeon: int | None, slayer: int | None, weight: int | None,
                      config: Config = tanjun.inject()):
    if list(locals().values()).count(None) > 2:
        embed = hikari.Embed(
            title='Abort',
            description='No requirement option was selected',
            color=config['colors']['error']
        )
        await ctx.respond(embed=embed)
        return

    try:
        if slayer is not None:
            await ConfigHandler().set_val(['masters', guild, 'slayer_xp'], slayer)
        if dungeon is not None:
            await ConfigHandler().set_val(['masters', guild, 'dungeon_lvl'], dungeon)
        if weight is not None:
            await ConfigHandler().set_val(['masters', guild, 'weight'], weight)

        await ConfigHandler().save_config()
        await ConfigHandler().load_config()

    except Exception as exception:
        embed = hikari.Embed(
            title='Error',
            description='Something went wrong.',
            color=config['colors']['error']
        )
        embed.set_footer(str(exception.__class__))
        await ctx.respond(embed=embed)
        return

    embed = hikari.Embed(
        title='Success',
        description='Given requirements were successfully changed',
        color=config['colors']['success']
    )

    await ctx.respond(embed=embed)


@tanjun.as_loader()
def load(client: tanjun.Client) -> None:
    if not ConfigHandler().get_config()['modules']['masters']:
        return

    client.add_component(commands_component)


@tanjun.as_unloader()
def unload(client) -> None:
    client.remove_component(commands_component)
