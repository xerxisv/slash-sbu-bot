# TODO create trigger list command
# TODO add autocomplete to trigger remove

import json
import re
from random import choice
from typing import List, TypedDict

import aiofiles
import alluka
import hikari.api.cache
import tanjun

from utils import trigger_typing
from utils.config import Config, ConfigHandler

################
#   Commands   #
################

component = tanjun.Component()
ct_slash_group = tanjun.slash_command_group("trigger", "Commands related to chat triggers",
                                            default_member_permissions=hikari.Permissions.MANAGE_ROLES)


@tanjun.with_str_slash_option("response5", "Other possible trigger responses", default=None, key='response5')
@tanjun.with_str_slash_option("response4", "Other possible trigger responses", default=None, key='response4')
@tanjun.with_str_slash_option("response3", "Other possible trigger responses", default=None, key='response3')
@tanjun.with_str_slash_option("response2", "Other possible trigger responses", default=None, key='response2')
@tanjun.with_member_slash_option("user4", "Additional user", default=None, key='user5')
@tanjun.with_member_slash_option("user3", "Additional user", default=None, key='user4')
@tanjun.with_member_slash_option("user2", "Additional user", default=None, key='user3')
@tanjun.with_member_slash_option("user1", "Additional user", default=None, key='user2')
@tanjun.with_bool_slash_option("overwrite", "Whether to skip checking if trigger already exists or not.", default=False)
@tanjun.with_str_slash_option("response", "Trigger response", key='response1')
@tanjun.with_member_slash_option("owner", "Owner of the trigger", key='user1')
@tanjun.with_str_slash_option("trigger", "Phrase that will trigger a response")
@ct_slash_group.as_sub_command("add", "Add a new chat trigger")
async def add(ctx: tanjun.abc.SlashContext, trigger: str, user1: hikari.Member, response1: str, overwrite: bool,
              user2: hikari.Member, user3: hikari.Member, user4: hikari.Member, user5: hikari.Member,
              response2: str, response3: str, response4: str, response5: str,
              config: Config = alluka.inject(type=Config)):
    await trigger_typing(ctx)

    args = locals()
    for key in list(args.keys()):
        if re.match("user\d|response\d", key) is not None:
            continue

        del args[key]

    trigger_info: TriggerInfo = {
        "owner": [user.id for user in args.values() if isinstance(user, hikari.Member)],
        "reply": [response for response in args.values() if isinstance(response, str)],
        "enabled": True
    }

    trigger_handler = TriggersFileHandler()
    try:
        await trigger_handler.add_trigger(trigger, trigger_info, overwrite)

    except KeyError:
        embed = hikari.Embed(
            title='Error',
            description=f'Trigger `{trigger}` already exists. Set overwrite to True if you want to replace.',
            color=config['colors']['error']
        )
        await ctx.respond(embed=embed)

    else:
        embed = hikari.Embed(
            title='Success',
            description='Chat trigger added successfully',
            color=config['colors']['success']
        )
        await ctx.respond(embed=embed)


@tanjun.with_str_slash_option("trigger", "The trigger to remove")
@ct_slash_group.as_sub_command("remove", "Remove a chat trigger")
async def remove(ctx: tanjun.abc.Context,
                 trigger: str,
                 config: Config = alluka.inject(type=Config)
                 ):
    trigger_handler = TriggersFileHandler()
    removed = await trigger_handler.remove_trigger(trigger)
    if removed:
        embed = hikari.Embed(
            title='Success',
            description=f'Removed trigger `{trigger}`.',
            color=config['colors']['success']
        )
    else:
        embed = hikari.Embed(
            title='Error',
            description=f'Trigger `{trigger}` not found.',
            color=config['colors']['success']
        )

    await ctx.respond(embed=embed)


class TriggerInfo(TypedDict):
    owner: List[int]
    reply: str | List[str]
    enabled: bool


class TriggersFileHandler:
    triggers_file_path = './data/triggers.json'

    def __init__(self):
        self._triggers = {}

    def get_triggers(self) -> dict:
        return self._triggers

    def load_triggers(self) -> None:
        """
        Loads the contents of triggers.json to memory
        :return: None
        """

        with open(TriggersFileHandler.triggers_file_path, mode='r') as f:
            self._triggers = json.loads(f.read())

    async def save_triggers(self) -> None:
        """
        Writes the in-memory triggers to the triggers.json file
        :return: None
        """

        async with aiofiles.open(TriggersFileHandler.triggers_file_path, mode='w') as f:
            await f.write(json.dumps(self._triggers, indent=4))

    async def reload_triggers(self) -> None:
        """
        save_triggers() and load_triggers() shortcut
        :return: None
        """

        await self.save_triggers()
        self.load_triggers()

    async def add_trigger(self, trigger_name: str, trigger_info: TriggerInfo, overwrite=False) -> None:
        """
        Creates a new trigger

        :param trigger_name: The trigger's name
        :param trigger_info: The trigger's info
        :param overwrite: Whether to skip checking if trigger exists or not
        :return: None
        :raise KeyError: If trigger already exists
        """

        trigger_name = trigger_name.upper()
        if not overwrite and trigger_name in self._triggers:
            raise KeyError('Key already exists')
        self._triggers[trigger_name] = trigger_info
        await self.reload_triggers()

    async def remove_trigger(self, key: str) -> bool:
        """
        Removed a trigger from the triggers file

        :param key: The trigger to remove
        :return: True if trigger found, False otherwise
        """

        removed = self._triggers.pop(key.upper(), None)
        await self.reload_triggers()
        return True if removed else False

    async def toggle_trigger(self, trigger_name: str) -> bool:
        """
        Toggles a trigger

        :param trigger_name: The trigger's name
        :return: The new state of the trigger
        :raise KeyError: If the trigger does not exist
        """

        trigger_name = trigger_name.upper()

        if trigger_name not in self._triggers:
            raise KeyError(f'Trigger {trigger_name} not found')

        self._triggers[trigger_name]['enabled'] = not self._triggers[trigger_name]['enabled']
        await self.reload_triggers()

        return self._triggers[trigger_name]['enabled']

    async def handle_trigger(self, event: hikari.GuildMessageCreateEvent) -> None:
        content = event.message.content.upper()

        trigger: TriggerInfo = self._triggers[content]
        if event.message.author.id not in trigger['owner'] or not trigger['enabled']:
            return

        reply = trigger['reply'] if type(trigger['reply']) is str else choice(trigger['reply'])
        await event.message.respond(reply)

    def is_trigger(self, msg: str) -> bool:
        return msg.upper() in self._triggers.keys()


component.load_from_scope()


@tanjun.as_loader()
def load(client: tanjun.Client) -> None:
    if not ConfigHandler().get_config()['modules']['triggers']:
        return

    client.add_component(component)


@tanjun.as_unloader()
def unload(client) -> None:
    client.remove_component(component)
