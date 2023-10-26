# TODO implement verification co-routine into Modal
import aiohttp
import hikari
import miru
import tanjun

from utils.config import Config, ConfigHandler
from utils.error_utils import log_error


#######################
#  Functions & Views  #
#######################

async def invite_member(ctx, endpoint, username):
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(connect=5)) as session:
        try:
            r = await session.post(
                url=endpoint,
                headers={'Content-Type': 'application/json'},
                json={'username': username}
            )
            response = await r.json()
            r.close()
            return bool(response['success'])
        except Exception as exception:
            await log_error(ctx, exception)
            return False


class JoinModal(miru.Modal):
    def __init__(self, invite_endpoint, title: str, config: Config) -> None:
        super().__init__(title)
        self.invite_endpoint = invite_endpoint
        self.config = config

    name = miru.TextInput(label="IGN", placeholder="Enter your username", required=True,
                          style=hikari.TextInputStyle.SHORT)

    async def callback(self, ctx: miru.ModalContext) -> None:
        await ctx.defer(hikari.ResponseType.DEFERRED_MESSAGE_CREATE, flags=hikari.MessageFlag.EPHEMERAL)
        success = await invite_member(ctx, self.invite_endpoint, self.name.value)

        embed = hikari.Embed(title="Join Request")

        if success:
            embed.description=(f"Successfully invited {self.name.value} to the guild. If you haven't been invited, "
                               f"please create a support ticket")
            embed.colour=self.config['colors']['success']
        else:
            embed.description=f"An internal error has occurred, please create a support ticket"
            embed.colour=self.config['colors']['error']

        await ctx.respond(embed=embed, flags=hikari.MessageFlag.EPHEMERAL)


class JoinButtons(miru.View):
    def __init__(self, config: Config) -> None:
        self.config = config
        super().__init__(timeout=None)  # Setting timeout to None

    @miru.button(label="SB University", custom_id="sbu_uni")
    async def sbu_uni(self, _: miru.Button, ctx: miru.ViewContext) -> None:
        endpoint = self.config['guilds']["SB UNIVERSITY"]['endpoint'] + "invite"
        await ctx.respond_with_modal(JoinModal(endpoint, "Join SB University", self.config))

    @miru.button(label="SB Alpha Psi", custom_id="alpha_psi")
    async def alpha_psi(self, _: miru.Button, ctx: miru.ViewContext) -> None:
        endpoint = self.config['guilds']["SB ALPHA PSI"]['endpoint'] + "invite"
        await ctx.respond_with_modal(JoinModal(endpoint, "Join Alpha PSI", self.config))

    @miru.button(label="SB Sigma Chi", custom_id="sigma_chi")
    async def sigma_chi(self, _: miru.Button, ctx: miru.ViewContext) -> None:
        endpoint = self.config['guilds']["SB SIGMA CHI"]['endpoint'] + "invite"
        await ctx.respond_with_modal(JoinModal(endpoint, "Join Sigma Chi", self.config))

    @miru.button(label="SB Lambda Pi", custom_id="lambda_pi")
    async def lambda_pi(self, _: miru.Button, ctx: miru.ViewContext) -> None:
        endpoint = self.config['guilds']["SB LAMBDA PI"]['endpoint'] + "invite"
        await ctx.respond_with_modal(JoinModal(endpoint, "Join Lambda Pi", self.config))

    @miru.button(label="Random", custom_id="random", row=1, style=hikari.ButtonStyle.SUCCESS)
    async def random(self, _: miru.Button, ctx: miru.ViewContext) -> None:
        endpoint = self.config['guilds']["SB SIGMA CHI"]['endpoint'] + "invite"
        await ctx.respond_with_modal(JoinModal(endpoint, "Join a random guild", self.config))


################
#   Commands   #
################


component = tanjun.Component()


@tanjun.as_slash_command('join_embed', 'Sends the join embed in the current channel.',
                         default_member_permissions=hikari.Permissions.ADMINISTRATOR, default_to_ephemeral=True)
async def join_embed(ctx: tanjun.abc.SlashContext):
    embed = hikari.Embed()
    embed.title = 'Join Us!'
    embed.description = 'Press any of the buttons below to get invited!'
    embed.color = ConfigHandler().get_config()['colors']['primary']

    view = JoinButtons(ConfigHandler().get_config())

    await ctx.get_channel().send(embed=embed, components=view)
    await ctx.respond('Success')


component.load_from_scope()


###############
#   Loaders   #
###############

@tanjun.as_loader()
def load(client: tanjun.Client) -> None:
    if not ConfigHandler().get_config()['modules']['join_buttons']:
        return

    client.add_component(component)


@tanjun.as_unloader()
def unload(client: tanjun.Client) -> None:
    client.remove_component_by_name(component.name)
