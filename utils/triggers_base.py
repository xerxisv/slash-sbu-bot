import json
from abc import abstractmethod

import hikari


class BaseTriggersFileHandler:
    triggers_file_path: str = ""

    def __init__(self):
        self._triggers = {}

    @property
    @abstractmethod
    def triggers(self):
        return self._triggers

    @abstractmethod
    async def add_trigger(self, *args, **kwargs) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def handle_trigger(self, event: hikari.GuildMessageCreateEvent) -> None:
        raise NotImplementedError

    @abstractmethod
    def is_trigger(self, msg: str) -> bool:
        raise NotImplementedError

    def load_triggers(self) -> None:
        """
        Loads the contents of triggers.json to memory
        :return: None
        """

        with open(self.triggers_file_path, mode='r') as f:
            self._triggers = json.loads(f.read())

    def save_triggers(self) -> None:
        """
        Writes the in-memory triggers to the triggers.json file
        :return: None
        """

        with open(self.triggers_file_path, mode='w') as f:
            json.dump(self._triggers, f, indent=4)

    def reload_triggers(self) -> None:
        """
        save_triggers() and load_triggers() shortcut
        :return: None
        """

        self.save_triggers()
        self.load_triggers()

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
