import talents

hero_talent_options = {
}

def decode_game_events_talent_choices(game_events, player_selected_heroes):
    for choice in talents._decode_game_events_talent_choices(game_events, player_selected_heroes, hero_talent_options):
        yield choice

attribute_options = {
     500: ('m_playerType', {'Comp': 'Computer', 'Humn': 'Human'}),
    2001: ('m_teamSize', {'1v1': '1v1', '2v2': '2v2', '3v3': '3v3', '4v4':'4v4', '5v5': '5v5'}),
    3000: ('m_gameSpeed', {'Slor': 'Slower', 'Slow': 'Slow', 'Norm': 'Normal', 'Fast': 'Fast', 'Fasr': 'Faster'}),
    3001: ('m_playerRace', {}),
    3002: ('m_playerColor', {}),
    3003: ('m_handicap', {}),
    3004: ('m_difficultyLevel', {'VyEy': 'Very Easy', 'Easy': 'Easy', 'Medi': 'Medium', 'Hard': 'Hard', 'VyHd': 'Very Hard', 'Insa': 'Insane'}),
    3009: ('m_gameType', {'Priv': 'Custom', 'Amm': 'Quick Match'}),
    4002: ('m_hero', {
        'Abat': 'Abathur',
        'Anub': 'Anubarak',
        'Arth': 'Arthas',
        'Azmo': 'Azmodan',
        'Barb': 'Sonya',
        'Chen': 'Chen',
        'Demo': 'Valla',
        'Diab': 'Diablo',
        'Fals': 'Falstad',
        'Illi': 'Illidan',
        'Jain': 'Jaina',
        'Kerr': 'Kerrigan',
        'L90E': 'E.T.C',
        'LiLi': 'Li Li',
        'Lost': 'The Lost Vikings',
        'Faer': 'Brightwing',
        'Malf': 'Malfurion',
        'Mura': 'Muradin',
        'Murk': 'Murky',
        'Nova': 'Nova',
        'Rand': 'Autoselect',
        'Rayn': 'Raynor',
        'Rehg': 'Rehgar',
        'Sgth': 'Sgt. Hammer',
        'Stit': 'Stitches',
        'Tass': 'Tassadar',
        'Thra': 'Thrall',
        'Tink': 'Gazlowe',
        'Tych': 'Tychus',
        'Tyrd': 'Tyrande',
        'Tyrl': 'Tyrael',
        'Uthe': 'Uther',
        'Witc': 'Nazeebo',
        'Zaga': 'Zagara',
        'Zera': 'Zeratul',
        }),
    4003: ('m_heroSkin', {}),
    4004: ('m_mount', {}),
    4006: ('m_heroAttack', {'rang': 'Ranged', 'mele': 'Melee'}),
    4007: ('m_heroRole', {'spec': 'Specialist', 'supp': 'Support', 'assa': 'Assassin', 'warr': 'Warrior'}),
    4008: ('m_characterLevel', {}),
    4010: ('m_heroSelectionMode', {'stan': 'Free Pick', 'drft': 'Draft'}),
}

def translate_replay_attributes_events(replay_attributes_events):
    return talents._translate_replay_attributes_events(replay_attributes_events, attribute_options)

