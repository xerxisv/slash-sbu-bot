import random

import alluka
import hikari
import tanjun

from utils.config import Config, ConfigHandler

################
#    Config    #
################

################
#   Commands   #
################

component = tanjun.Component()


@tanjun.as_slash_command("lookup_section", "Posts look-up examples for Helper Academy",
                         default_member_permissions=hikari.Permissions.BAN_MEMBERS)
async def lookup_section(ctx: tanjun.abc.SlashContext,
                         config: Config = alluka.inject(type=Config)):
    # Lookup Questions
    questions = hikari.Embed(
        title='Lookup Section',
        description='',
        color=config['colors']['primary']
    )
    questions.set_footer(text='SBU Rank Academy Questions')
    questions.add_field(name="What to do.",
                        value="Look up this list of people and mention if they are cleared to enter our guild or not:",
                        inline=False)
    # Lookup Answers
    answers = hikari.Embed(
        title='Lookup Section Answers',
        description=f'<#{ctx.get_channel().id}>',
        color=config['colors']['secondary']
    )
    answers.set_footer(text='SBU Rank Academy Answers')

    # Add random scammers to the embeds
    lookup_scammers = config['helper_academy']['lookup_scammers']
    length = len(lookup_scammers)
    random_list = random.sample(range(0, length), 9)
    channel = ctx.get_guild().get_channel(config['helper_academy']['ticket_commands_channel_id'])

    question_list = ""
    answer_list = ""
    for ran_index in random_list:
        scammer_ign = list(lookup_scammers.keys())[ran_index]

        answer_list += f"`{scammer_ign}`: **" + ("Not allowed ❌" if lookup_scammers[scammer_ign][
            'is_scammer'] else "Allowed ✅") + "**\n"
        question_list += f"\n`{scammer_ign}`"

    questions.add_field(name="Lookup: ", value=question_list, inline=False)
    answers.add_field(name="Answers: ", value=answer_list, inline=False)

    await ctx.respond(embed=questions)
    await channel.send(embed=answers)


component.load_from_scope()


@tanjun.as_loader()
def load(client: tanjun.Client):
    if not ConfigHandler().get_config()['modules']['helper_academy']:
        return

    client.add_component(component)


@tanjun.as_unloader()
def unload(client: tanjun.Client):
    client.remove_component_by_name(component.name)
