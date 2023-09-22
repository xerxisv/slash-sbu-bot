import hikari

from utils import Singleton
from utils.triggers_base import BaseTriggersFileHandler
from .cmd_descriptor import CommandDescriptor
from .actions import convert_actions, convert_parameters, format_res, send_res

cmd_prefix = "+"

class CommandTriggersFileHandler(BaseTriggersFileHandler, metaclass=Singleton):
    triggers_file_path = "./data/commands.json"
    _triggers: dict[str, CommandDescriptor]

    @property
    def triggers(self):
        return self._triggers

    async def add_trigger(self, cmd_name: str, descriptor: CommandDescriptor, overwrite: bool = False) -> bool:
        cmd_name = cmd_name.upper()

        if not overwrite and cmd_name in self.triggers:
            return False

        self._triggers[cmd_name] = descriptor
        self.reload_triggers()

        return True

    async def handle_trigger(self, event: hikari.GuildMessageCreateEvent) -> None:
        msg_array = event.message.content.split()

        cmd_name = msg_array.pop(0).upper().removeprefix(cmd_prefix)
        cmd = self.triggers[cmd_name]

        if not cmd['is_enabled']: # Command has to be enabled
            return
        if cmd['min_role_req'] and cmd['min_role_req'] not in event.member.role_ids: # Invoker has to have the min role
            return
        if len(cmd['param_types']) != len(msg_array): # Number of words in the message need to be param# + 1
            await event.message.respond("Invalid parameters")
            return

        given_parameters = convert_parameters(dict(zip(msg_array[:len(cmd['param_types'])], cmd['param_types'])))
        static_parameters = cmd['static_params']

        for index, action_fn in enumerate(convert_actions(cmd['actions'])):
            await action_fn(event, *static_parameters[index], *given_parameters)

        await send_res(
            event,
            format_res(given_parameters, cmd['res']) if cmd.get('do_format') else cmd['res'],
            cmd.get('delete_after')
        )

    def is_trigger(self, msg: str) -> bool:
        return msg.startswith(cmd_prefix) and msg.upper().split()[0].removeprefix(cmd_prefix) in self._triggers.keys()
