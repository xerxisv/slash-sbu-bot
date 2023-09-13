# TODO implement verification co-routine into Modal
import aiohttp
import hikari
import miru

from main import bot
from utils.config import ConfigHandler, Config

config: Config = ConfigHandler().get_config()


async def invite_member(endpoint, username):
    async with aiohttp.ClientSession() as session:
        r = await session.post(
            url=endpoint,
            headers={'Content-Type': 'application/json'},
            json={'username': username}
        )
        response = await r.json()
        r.close()
        return bool(response['success'])


class JoinModal(miru.Modal):
    def __init__(self, invite_endpoint, title: str) -> None:
        super().__init__(title)
        self.invite_endpoint = invite_endpoint

    name = miru.TextInput(label="IGN", placeholder="Enter your username", required=True, style = hikari.TextInputStyle.SHORT)

    async def callback(self, ctx: miru.ModalContext) -> None:
        success = await invite_member(self.invite_endpoint, self.name.value)
        if success:
            embed = hikari.Embed(
                title="Join Request",
                description=f"Successfully invited {self.name.value} to the guild. If you haven't been invited, please create a support ticket",
                colour=config['colors']['success']
            )
            await ctx.respond(
                embeds=embed,
                flags=hikari.MessageFlag.EPHEMERAL
            )
        else:
            embed = hikari.Embed(
                title="Join Request",
                description=f"An internal error has occurred, please create a support ticket",
                colour=config['colors']['error']
            )
            await ctx.respond(
                embeds=embed,
                flags=hikari.MessageFlag.EPHEMERAL
            )

class JoinButtons(miru.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)  # Setting timeout to None

    @miru.button(label="SB Alpha PSI", custom_id="alpha_psi")
    async def alpha_psi(self, button: miru.Button, ctx: miru.ViewContext) -> None:
        endpoint = config['guilds']["SB ALPHA PSI"]['endpoint'] + "invite"
        await ctx.respond_with_modal(JoinModal(endpoint, "Join Alpha PSI"))

    @miru.button(label="SB Lambda Pi", custom_id="lambda_pi")
    async def lambda_pi(self, button: miru.Button, ctx: miru.ViewContext) -> None:
        endpoint = config['guilds']["SB LAMBDA PI"]['endpoint'] + "invite"
        await ctx.respond_with_modal(JoinModal(endpoint, "Join Lambda Pi"))

    @miru.button(label="SB Sigma Chi", custom_id="sigma_chi")
    async def sigma_chi(self, button: miru.Button, ctx: miru.ViewContext) -> None:
        endpoint = config['guilds']["SB SIGMA CHI"]['endpoint'] + "invite"
        await ctx.respond_with_modal(JoinModal(endpoint, "Join Sigma Chi"))

    @miru.button(label="SB University", custom_id="sbu_uni")
    async def sbu_uni(self, button: miru.Button, ctx: miru.ViewContext) -> None:
        endpoint = config['guilds']["SB UNIVERSITY"]['endpoint'] + "invite"
        await ctx.respond_with_modal(JoinModal(endpoint, "Join SB University"))


@bot.listen()
async def startup_views(event: hikari.StartedEvent) -> None:
    view = JoinButtons()
    await view.start()


@bot.listen()
async def buttons(event: hikari.GuildMessageCreateEvent) -> None:
    if not event.is_human:
        return

    me = bot.get_me()

    # If the bot is mentioned
    if me.id in event.message.user_mentions_ids and 780889323162566697 == event.member.id and event.message.content == "!joinmessage":
        view = JoinButtons()
        await event.message.respond(
            embeds=hikari.Embed(title="Kyo is a lazy bum", description="bro didnt give me the embed"),
            components=view
        )


