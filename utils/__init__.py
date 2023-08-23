from random import random

import aiohttp
import tanjun


profile_choices = ['apple', 'banana', 'blueberry', 'coconut', 'cucumber', 'grapes',
            'kiwi', 'lemon', 'lime', 'mango', 'orange', 'papaya', 'pear',
            'peach', 'pineapple', 'pomegranate', 'raspberry', 'strawberry',
            'tomato', 'watermelon', 'zucchini']

class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


async def get(url) -> aiohttp.ClientResponse:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as res:
            await res.read()
        return res


async def extract_uuid(ign: str) -> str | None:
    uuid = None

    res = await get(f'https://api.mojang.com/users/profiles/minecraft/{ign}')

    if res.status == 200:
        uuid = (await res.json())['id']
    return uuid


async def trigger_typing(ctx: tanjun.abc.Context, defer: bool = False):
    if isinstance(ctx, tanjun.abc.MessageContext):
        await ctx.rest.trigger_typing(ctx.get_channel())
    elif isinstance(ctx, tanjun.abc.SlashContext):
        await ctx.defer(ephemeral=defer)

def weighted_randint(end, loops=1) -> int:
    result = 0
    for _ in range(loops):
        result += round(random() * (end / loops))

    return int(result)
