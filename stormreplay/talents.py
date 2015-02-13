
def _decode_game_events_talent_choices(game_events, player_selected_heroes, hero_talent_options):
    hero_talent_tier = [0] * 10
    for event in game_events:
        if (event['_event'] != 'NNet.Game.SHeroTalentTreeSelectedEvent'):
            continue

        player = event['_userid']['m_userId']
        hero_name = player_selected_heroes[player]
        hero_talents = hero_talent_options[hero_name]
        currentTalentTier = hero_talent_tier[player]
        hero_talent_tier_info = hero_talents[currentTalentTier]

        talent_index = event['m_uint32']
        for tier in range(0,currentTalentTier):
            talent_index -= len(hero_talents[tier][1])

        talent_data = hero_talent_tier_info[1][talent_index]

        yield {
            "_userid": player,
            "_gameloop": event['_gameloop'],
            "m_level": hero_talent_tier_info[0],
            "m_talentName": talent_data[0],
            "m_talentDescription": talent_data[1],
            "m_talentIndex": talent_index,
        }

        hero_talent_tier[player] += 1


def _translate_replay_attributes_events(replay_attributes_events, attribute_options):
    scopes = replay_attributes_events['scopes']
    retval = {}
    for player_number in scopes:
        player_attributes = scopes[player_number]
        player = retval.setdefault(player_number, {})
        for attribute in player_attributes:
            value = str(player_attributes[attribute][0]['value']).strip()
            mapping = attribute_options.get(int(attribute), ('m_attrId_' + str(attribute), {}))
            player[mapping[0]] = mapping[1].get(value, value)
    return retval

