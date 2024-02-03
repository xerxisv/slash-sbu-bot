import aiosqlite
import alluka
import hikari
import miru
import tanjun

from utils import get, profile_choices, trigger_typing
from utils.checks.db_checks import registered_check
from utils.checks.role_checks import weight_banned_check
from utils.config import Config, ConfigHandler
from utils.database import convert_to_user


###############
#   Buttons   #
###############

class RoleButton(miru.Button):
    def __init__(self, role: str, user_id: int):
        self.role = role
        self.user_id = user_id
        self.config = ConfigHandler().get_config()
        super().__init__(style=hikari.ButtonStyle.PRIMARY, label=self.config['stats']['weight_roles'][role]["name"])

    async def callback(self, ctx: miru.ViewContext) -> None:
        if ctx.member.id != self.user_id:
            return

        view = miru.View()

        view.add_item(AcceptButton(self.role, self.user_id))
        view.add_item(CancelButton(self.user_id))

        name = self.config['stats']['weight_roles'][self.role]['role_id']

        embed = hikari.Embed(
            title="Weight roles",
            description=f"By clicking *'Accept'* you will be given the <@&{name}> role.",
            color=self.config['colors']['primary']
        )
        message = await ctx.edit_response(embed=embed, components=view)
        await view.start(message)
        await view.wait()


class AcceptButton(miru.Button):
    def __init__(self, role: str, user_id: int):
        super().__init__(label='Accept', style=hikari.ButtonStyle.SUCCESS)
        self.role = role
        self.user_id = user_id
        self.config = ConfigHandler().get_config()

    async def callback(self, ctx: miru.ViewContext) -> None:
        if ctx.member.id != self.user_id:
            return

        roles = [hikari.Snowflake(role) for role in self.config['stats']['weight_roles'][self.role]['previous']]
        roles.append(hikari.Snowflake(self.config['stats']['weight_roles'][self.role]['role_id']))

        roles += list(ctx.member.role_ids)
        if self.config['stats']['default_weight_role_id'] in roles:
            roles.remove(hikari.Snowflake(self.config['stats']['default_weight_role_id']))

        roles = set(roles)

        await ctx.member.edit(roles=roles, reason='Weight Roles')

        embed = hikari.Embed(
            title='Success',
            description='Successfully updated your roles!',
            color=self.config['colors']['success']
        )

        await ctx.edit_response(components=None, embed=embed)


class CancelButton(miru.Button):
    def __init__(self, user_id: int):
        super().__init__(label='Cancel', style=hikari.ButtonStyle.DANGER)
        self.user_id = user_id
        self.config = ConfigHandler().get_config()

    async def callback(self, ctx: miru.ViewContext) -> None:
        if ctx.member.id != self.user_id:
            return

        embed = hikari.Embed(
            title='Weight Roles',
            description='Command Canceled.',
            color=self.config['colors']['secondary']
        )
        await ctx.edit_response(components=None, embed=embed)


################
#   Commands   #
################

component = tanjun.Component()


@component.with_command()
@tanjun.with_argument('ign')
@tanjun.as_message_command('hypixel')
async def hypixel(ctx: tanjun.abc.MessageContext, ign: str, config: Config = alluka.inject(type=Config)):
    await trigger_typing(ctx)

    res = await get(f'https://api.slothpixel.me/api/players/{ign}')
    if res.status != 200:
        embed = hikari.Embed(
            title=f'Error',
            description='Error fetching information from the API. Try again later',
            color=config['colors']['error']
        )
        embed.set_footer(f"Status (profile): `{res.status}`")
        await ctx.respond(embed=embed)
        return

    player = await res.json()

    # Fetch player's guild info
    res = await get(f'https://api.slothpixel.me/api/guilds/{ign}')

    if res.status == 404:
        guild = None
    elif res.status != 200:
        embed = hikari.Embed(
            title=f'Error',
            description='Error fetching information from the API. Try again later',
            color=config['colors']['error']
        )
        embed.set_footer(f"Status (guild): `{res.status}`")
        await ctx.respond(embed=embed)
        return
    else:
        guild = await res.json()

    embed = hikari.Embed(
        title=f'{ign} Hypixel stats',
        color=config['colors']['primary']
    )

    embed.add_field(name='Rank',
                    value=f'{player["rank"].replace("PLUS", "+").replace("_", "") if player["rank"] else "None"}',
                    inline=False)
    embed.add_field(name='Level:', value=f'{player["level"]}', inline=False)
    embed.add_field(name='Discord:', value=f'{player["links"]["DISCORD"]}', inline=False)
    embed.add_field(name='Online:', value=f'{player["online"]}', inline=False)

    if guild is None:
        embed.add_field(name='Guild:', value=f'{ign} isn\'t in a guild')
    else:
        embed.add_field(name='Guild:', value=guild["name"])
    await ctx.respond(embed=embed)


@component.with_command()
@tanjun.with_argument('profile', default=None)
@tanjun.with_argument('ign')
@tanjun.as_message_command('skycrypt', 's')
async def skycrypt(ctx: tanjun.abc.MessageContext, ign: str, profile: str = None):
    await ctx.respond(fr'https://sky.shiiyu.moe/stats/{ign}/{profile if profile else ""}')


@component.with_command()
@tanjun.with_concurrency_limit("database_commands")
@tanjun.with_all_checks(weight_banned_check, registered_check)
@tanjun.with_str_slash_option('profile', 'Profile name. NOT YOUR IGN', key='cute_name', choices=profile_choices, default=None)
@tanjun.as_slash_command('weight_check', 'Gives weight roles')
async def weight_check(ctx: tanjun.abc.SlashContext, cute_name: str,
                       config: Config = alluka.inject(type=Config),
                       db: aiosqlite.Connection = alluka.inject(type=aiosqlite.Connection)):
    await trigger_typing(ctx)

    cursor: aiosqlite.Cursor
    async with db.cursor() as cursor:
        await cursor.execute('''
            SELECT *
            FROM "USERS"
            WHERE discord_id=:discord_id
        ''', {
            "discord_id": ctx.author.id
        })
        res = await cursor.fetchone()

    user = convert_to_user(res)
    weight_view = miru.View()

    # get user's profiles

    res = await get(f'https://sky.shiiyu.moe/api/v2/profile/{user["uuid"]}')
    if res.status != 200:
        embed = hikari.Embed(
            title="Error",
            description="Something went wrong. Make sure your APIs in on.\n"
                        "If this problem continues, please open a technical difficulties ticket.",
            color=config['colors']['error']
        )
        embed.set_footer(f"Status: `{res.status}`")
        await ctx.respond(embed=embed)
        return

    # get user's best weight or specified profile's weight

    profiles = await res.json()
    profile = None

    is_valid_profile = cute_name is None

    for prof in profiles["profiles"].values():
        if cute_name is not None:
            if prof["cute_name"].lower() != cute_name.lower():
                continue
            is_valid_profile = True
            profile = prof
            break

        if prof["current"]:
            profile = prof
            break

    if not is_valid_profile:
        embed = hikari.Embed(
            title='Error',
            description=f'You have no {cute_name.title()} profile.',
            color=config['colors']['error']
        )
        await ctx.respond(embed=embed)
        return

    # catch any wierd api responses

    try:
        weight = int(profile["data"]["weight"]["senither"]["overall"])

    except (KeyError, TypeError):
        embed = hikari.Embed(
            title='Error',
            description='Something went wrong. Make sure your APIs in on.'
                        'If this problem continues, please open a technical difficulties ticket.',
            color=config['colors']['error']
        )
        embed.set_footer("Status: `Key Error`")
        await ctx.respond(embed=embed)
        return

    has_previous_role = False
    max_role = None
    role = None

    for role in config['stats']['weight_roles']:
        if weight < config['stats']['weight_roles'][role]["weight_req"]:
            break
        if config['stats']['weight_roles'][role]["role_id"] in ctx.member.role_ids:
            has_previous_role = True
            continue
        max_role = role

    if max_role is not None:
        if not has_previous_role:
            description = "You have enough weight to teach others! These ranks will grant you access to our " \
                          "tutoring and carry systems. Are you interested in providing these things for newer " \
                          "players? Any sort of toxicity in tickets or channels won’t be tolerated and will " \
                          "result in punishment."
        else:
            description = "You have enough weight for the next role"

        weight_view.add_item(RoleButton(max_role, ctx.author.id))
        weight_view.add_item(CancelButton(ctx.author.id))
        embed = hikari.Embed(
            title="Weight roles",
            description=description,
            color=config['colors']['primary']
        )
    else:
        embed = hikari.Embed(
            title="Weight roles",
            description="You dont have enough weight for any of the next weight roles.\n"
                        f"The next requirement is `{config['stats']['weight_roles'][role]['weight_req']}` weight for"
                        f"<@&{config['stats']['weight_roles'][role]['role_id']}> role.\n"
                        f"Your weight: `{weight}`",
            color=config['colors']['secondary']
        )

    embed.set_footer(text=f'{user["ign"]} - {profile["cute_name"]}')

    message = await ctx.respond(embed=embed, components=weight_view, ensure_result=True)

    if len(weight_view.children):
        await weight_view.start(message)


@tanjun.as_loader()
def load(client: tanjun.Client) -> None:
    if not ConfigHandler().get_config()['modules']['masters']:
        return

    client.add_component(component)


@tanjun.as_unloader()
def unload(client: tanjun.Client) -> None:
    client.remove_component_by_name(component.name)
