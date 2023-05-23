import json
from random import choice
from typing import List, TypedDict

import hikari

from utils import Singleton


class TriggerInfo(TypedDict):
    owner: List[int]
    reply: str | List[str]
    enabled: bool


class TriggersFileHandler(metaclass=Singleton):
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

    def save_triggers(self) -> None:
        """
        Writes the in-memory triggers to the triggers.json file
        :return: None
        """

        with open(TriggersFileHandler.triggers_file_path, mode='w') as f:
            json.dump(self._triggers, f, indent=4)

    def reload_triggers(self) -> None:
        """
        save_triggers() and load_triggers() shortcut
        :return: None
        """

        self.save_triggers()
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
        self.reload_triggers()

    async def remove_trigger(self, key: str) -> bool:
        """
        Removed a trigger from the triggers file

        :param key: The trigger to remove
        :return: True if trigger found, False otherwise
        """

        removed = self._triggers.pop(key.upper(), None)
        self.reload_triggers()
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
        self.reload_triggers()

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