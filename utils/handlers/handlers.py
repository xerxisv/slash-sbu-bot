import hikari

from utils.config import ConfigHandler

config = ConfigHandler().get_config()

async def handle_warn(message: hikari.GuildMessageCreateEvent):
    if config['jr_mod_role_id'] not in message.member.role_ids:
        return

    # Split the message on every space character
    split_msg = message.content.split(' ')
    # If the message is less than 2 words long then it's an invalid warn command, return
    if len(split_msg) < 3:
        return

    # Else remove the discord formatting characters from the mention
    user_id = split_msg[1].replace('<', '').replace('@', '').replace('>', '')

    # And check if it was indeed a mention
    if not user_id.isnumeric():
        return

    # Fetch the member with the specified ID
    member: hikari.Member = message.get_guild().get_member(int(user_id))

    if member is None:
        member = await message.app.rest.fetch_member(message.get_guild(), int(user_id))

    # Make sure member exists and is not staff
    if member is None or config['jr_mod_role_id'] in member.role_ids:
        return

    await message.get_guild().get_channel(config['moderation']['action_log_channel_id']).send(
        f"Moderator: {message.author.mention} \n"
        f"User: {member.mention} \n"
        f"Action: Warn \n"
        f"Reason: {' '.join(split_msg[2:])}")

    await message.get_channel().send("Log created")


def is_warn(message: str):
    return message and message.startswith("!warn")
