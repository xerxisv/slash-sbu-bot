from io import BytesIO

import aiohttp
import hikari
import tanjun
from petpetgif import petpet

from utils.checks.role_checks import active_check


################
#   Commands   #
################

@tanjun.with_cooldown("spam")
@tanjun.with_check(active_check)
@tanjun.with_argument('user', converters=tanjun.conversion.to_user, default=None)
@tanjun.as_message_command('pat')
async def pat(ctx: tanjun.abc.MessageContext, user: hikari.User = None):
    if user is None:
        user = ctx.author

    async with aiohttp.ClientSession() as session:
        async with session.get(user.display_avatar_url.url) as res:
            content = await res.content.read()

    source = BytesIO(content)
    dest = BytesIO()

    petpet.make(source, dest)
    dest.seek(0)

    await ctx.respond(attachment=hikari.Bytes(dest, f'{ctx.author.username}-petpet.gif'))


component = tanjun.Component().load_from_scope()
loader = component.make_loader()
