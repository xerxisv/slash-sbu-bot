from tanjun.abc import Context
import traceback

from utils.config.config import ConfigHandler

ERROR_MESSAGE = '**Exception raised during the execution of {}**.\n```{}```*Channel: {}*'


def exception_to_string(command: str, exception: Exception, jump_url: str = None):
    stack = traceback.extract_stack(limit=1)[:-3] + traceback.extract_tb(exception.__traceback__, limit=1)
    pretty = traceback.format_list(stack)
    return ERROR_MESSAGE.format(command, ''.join(pretty) + '\n  {} {}'.format(exception.__class__, exception), jump_url)


async def log_error(ctx: Context, exception: Exception):
    await ctx.get_guild()\
        .get_channel(ConfigHandler().get_config()['bot_log_channel_id'])\
        .send(exception_to_string(ctx.triggering_name, exception, ctx.get_channel().mention))
