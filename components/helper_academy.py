import random

import alluka
import hikari
import tanjun

from utils.config import Config, ConfigHandler

################
#    Config    #
################

# True stands for scammer - False stands for not scammer
lookup = {
    "shachi": True, "Rvon": True, "Fijit": False, "someonestolemypc": True, "jpgaming55": True, "LordZarach": False,
    'Skeldow': True, 'StopWipingMe': True, 'LavenderHeights': True, 'MartinNemi03': False, '69mn': True,
    'zStrelizia': True, 'Adviceful': True, 'Zykm': True, 'muffinio': True, 'spedwick': True, 'FantasmicGalaxy': False,
    'urra': True, 'Iwolf05': True, 'noscope_': True, 'luvanion': True, 'KSavvv18': True, '43110s': True,
    'dukioooo': False, 'CoruptKun': True, 'Teunman': True, '302q': True, 'Tera_Matt': True, 'jexh': False,
    'Royalist': True, 'McMuffinLover': True, 'o600': False, 'jjww2': False, 'UnityUWU': True, 'LeaPhant': False,
    'Zanjoe': True, 'Yarnzy_': True, 'ih8grinding': True, 'Verychillvibes': True, 'LesbianCatgirl': False,
    'Legendofhub': True, 'Spectrov': True, '_YungGravy': False, 'wigner': True, 'U4BJ': True
}

################
#   Commands   #
################

component = tanjun.Component()


@tanjun.as_slash_command("lookup_section", "Posts look-up examples for Helper Academy",
                         default_member_permissions=hikari.Permissions.BAN_MEMBERS)
async def lookup_section(ctx: tanjun.abc.SlashContext,
                         config: Config = alluka.inject(type=Config)):
    length = len(lookup)
    random_list = random.sample(range(0, length), 9)
    channel = ctx.get_guild().get_channel(config['helper_academy']['ticket_commands_channel_id'])

    questions = hikari.Embed(
        title='Lookup Section',
        description='',
        color=config['colors']['primary']
    )
    answers = hikari.Embed(
        title=f'Lookup Section Answers',
        description='',
        color=config['colors']['secondary']
    )
    questions.set_footer(text='SBU Rank Academy Questions')
    questions.add_field(name="What to do.",
                        value="Look up this list of people and mention if they are cleared to enter our guild or not:",
                        inline=False)
    answers.set_footer(text='SBU Rank Academy Answers')
    temp_list = ""
    for banned in random_list:
        answers.add_field(name=list(lookup.keys())[banned],
                          value="Scammer" if list(lookup.values())[banned] else "Not scammer", inline=False)
        temp_list = temp_list + "\n" + list(lookup.keys())[banned]
    questions.add_field(name="Lookup: ", value=temp_list, inline=False)
    await channel.send(f"Lookup Section Answers for <#{ctx.get_channel().id}>")
    await ctx.respond(embed=questions)
    await channel.send(embed=answers)


component.add_command(lookup_section)


@tanjun.as_loader()
def load(client: tanjun.Client):
    if not ConfigHandler().get_config()['modules']['helper_academy']:
        return

    client.add_component(component)


@tanjun.as_unloader()
def unload(client: tanjun.Client):
    client.remove_component_by_name(component.name)
