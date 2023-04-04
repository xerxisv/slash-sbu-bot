from typing import Annotated

import aiohttp
import alluka
import hikari
import tanjun

from utils import profile_choices, trigger_typing
from utils.config import Config, ConfigHandler

################
#   Commands   #
################

commands_component = tanjun.Component()


@commands_component.with_command(follow_wrapped=True)
@tanjun.annotations.with_annotated_args(follow_wrapped=True)
@tanjun.as_message_command('checkreq')
@tanjun.as_slash_command('checkreq', 'Checks if you pass the requirements for masters')
async def checkreq(ctx: tanjun.abc.Context,
                   ign: Annotated[tanjun.annotations.Str, "Your IGN"],
                   cute_name: Annotated[
                       tanjun.annotations.Str, "Profile name", tanjun.annotations.Choices(profile_choices)] = None,
                   config: Config = alluka.inject(type=Config)):
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
            return

        profiles = await res.json()

    await session.close()

    dungeon_lvl = 0
    slayer_xp = 0
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
                weight = profile["data"]["weight"]["senither"]["overall"]
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
        slayer_xp = int(selected_profile["data"]["slayer_xp"])
        weight = int(selected_profile["data"]["weight"]["senither"]["overall"])
    except KeyError:
        embed = hikari.Embed(
            title='Error',
            description='Something went wrong. Make sure your APIs in on.\n'
                        'If this problem continues, open a technical difficulties ticket.',
            color=config['colors']['error']
        )
        await ctx.respond(embed=embed)

    passed_reqs = 3
    slayer_req = True
    dungeon_req = True
    weight_req = True

    if dungeon_lvl < 30:
        dungeon_req = False
        passed_reqs -= 1
    if slayer_xp < 1000000:
        slayer_req = False
        passed_reqs -= 1
    if weight < 4200:
        weight_req = False
        passed_reqs -= 1

    if passed_reqs != 0 and passed_reqs != 3:
        embed = hikari.Embed(
            title='Masters Requirements',
            description='',
            color=config['colors']['secondary']
        )
        embed.add_field(name="Hold Up", value=f"You meet {passed_reqs}/3 of the requirements.", inline=False)
    elif passed_reqs == 0:
        embed = hikari.Embed(
            title='Masters Requirements',
            description='',
            color=config['colors']['error']
        )
        embed.add_field(name="No requirements met", value="You dont meet any of the requirements", inline=False)
    else:
        embed = hikari.Embed(
            title='Masters Requirements',
            description='',
            color=config['colors']['primary']
        )
        embed.add_field(name="Congratulations!", value="You meet all the requirements", inline=False)

    p = "**Passed**"
    np = "**Not Passed**"

    embed.add_field(name="Your Stats", value=f"Slayer Req: 1000000 xp | "
                                             f"Your Slayers: **{slayer_xp}** | {p if slayer_req else np} \n"
                                             f"Cata req: level 30 | "
                                             f"Your Cata: **{dungeon_lvl}** | {p if dungeon_req else np} \n"
                                             f"Weight req: 4200 senither weight | "
                                             f"Your Weight: {weight} | {p if weight_req else np}", inline=False)
    embed.set_footer(text=f'{ign} | {selected_profile["cute_name"]}')

    await ctx.respond(embed=embed)


@tanjun.as_loader()
def load(client: tanjun.Client) -> None:
    if not ConfigHandler().get_config()['modules']['masters']:
        return

    client.add_component(commands_component)


@tanjun.as_unloader()
def unload(client) -> None:
    client.remove_component(commands_component)
