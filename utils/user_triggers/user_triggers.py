from random import choice
from typing import List, TypedDict

import hikari

from utils import Singleton
from utils.triggers_base import BaseTriggersFileHandler


class TriggerInfo(TypedDict):
    owner: List[int]
    reply: str | List[str]
    enabled: bool


class UserTriggersFileHandler(BaseTriggersFileHandler, metaclass=Singleton):
    triggers_file_path = './data/triggers.json'

    @property
    def triggers(self):
        return self._triggers

    async def add_trigger(self, trigger_name: str, trigger_info: TriggerInfo, overwrite=False) -> bool:
        """
        Creates a new trigger

        :param trigger_name: The trigger's name
        :param trigger_info: The trigger's info
        :param overwrite: Whether to skip checking if trigger exists or not
        :return: True if trigger creation was successful
        """

        trigger_name = trigger_name.upper()
        if not overwrite and trigger_name in self._triggers:
            return False

        self._triggers[trigger_name] = trigger_info
        self.reload_triggers()

        return True

    async def handle_trigger(self, event: hikari.GuildMessageCreateEvent) -> None:
        content = event.message.content.upper()

        trigger: TriggerInfo = self._triggers[content]
        if event.message.author.id not in trigger['owner'] or not trigger['enabled']:
            return

        reply = trigger['reply'] if type(trigger['reply']) is str else choice(trigger['reply'])
        await event.message.respond(reply)

    def is_trigger(self, msg: str) -> bool:
        return msg.upper() in self.triggers
