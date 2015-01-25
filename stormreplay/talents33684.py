


hero_talent_options = {
	"Uther": [
		( 1, ["Conjurer's Pursuit", "Reach", "Dense Weightstone", "Blessed Champion"]),
		( 4, ["Hammer of the Lightbringer", "Fist of Justice", "Protect the Weak", "Protective Shield"]),
		( 7, ["Wave of Light", "Rebuke", "Holy Devotion (Trait)", "Clairvoyance", "Cleanse"]),
		(10, ["Divine Shield", "Divine Storm"]),
		(13, ["Burning Rage", "Spell Shield", "Sprint", "Shrink Ray"]),
		(16, ["Hardened Focus", "Gathering Radiance", "Holy Shock", "Imposing Presence"]),
		(20, ["Bulwark of Light", "Divine Hurricane", "Storm Shield"])
	],
}


def decode_game_events_talent_choices(game_events, player_selected_heroes):
	hero_talent_tier = [0] * 10
    for event in game_events:
    	if (event['event'] != 'NNet.Game.SHeroTalentTreeSelectedEvent'):
    		continue

    	player = event['_userid']
    	hero_name = player_selected_heroes[player]
    	hero_talents = hero_talent_options[hero_name]
    	hero_talent_tier_info = hero_talents[hero_talent_tier[player]]

    	talent_index = event['m_uint32']
    	talent_name = hero_talent_tier_info[1][talent_index]

        yield {
        	"_userid": player,
        	"_gameloop": event['_gameloop'],
        	"m_level", hero_talent_tier_info[0],
        	"m_talentName": talent_name,
        	"m_talentIndex": talent_index,
        }

        hero_talent_tier[player] += 1
