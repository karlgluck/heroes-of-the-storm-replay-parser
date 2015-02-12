import os
import reader

import json

# todo: get this logger from elsewhere
from celery.utils.log import get_task_logger
log = get_task_logger(__name__)

defaultFieldMappings = [
### SET
    (['info','protocol'], 'getReplayProtocolVersion'),
    (['info','bytes'], 'getReplayFileByteSize'),
    (['info','gameloops'], 'getMatchLengthGameloops'),
    (['info','seconds'], 'getMatchLengthSeconds'),
    (['info','start_timestamp'], 'getMatchUTCTimestamp'),
    (['info','speed'], 'getMatchSpeed'),
    (['info','match_type'], 'getMatchType'),
    (['info','hero_selelection_mode'], 'getHeroSelectionMode'),

    (['map','name'], 'getMapName'),
    (['map',{'m_mapSizeX':'width', 'm_mapSizeY':'height'}], 'getGameDescription'),
    (['team', [], 'levels'], 'getTeamLevels'),


    #(['players', [], 'talents'], 'getTalents'),
    #(['players', [], 'talents', [], {'name':'name'}], 'getTalents'),
    #(['players', [], {'m_teamId': 'team', 'm_name': 'name', 'm_toonId': 'toon_id'}], 'getPlayers'),

    (['raw','players'], 'getPlayers'),
    (['raw','details'], 'getReplayDetails'),
    (['raw','init_data'], 'getReplayInitData'),
    #(['raw','translated_attributes_events'], 'getTranslatedReplayAttributesEvents'),

    #(['players', [], 'hero'], 'getPlayersHeroChoiceArray'),

]

named_field_mappings = {
    'RawReplayDetails':             [(['raw','details'], 'getReplayDetails')],
    'RawReplayInitData':            [(['raw','init_data'], 'getReplayInitData')],
    'RawReplayTrackerEvents':       [(['raw','tracker_events'], 'getReplayTrackerEvents')],
    'RawReplayAttributesEvents':    [(['raw','attributes_events'], 'getReplayAttributesEvents')],
    'RawReplayGameEvents':          [(['raw','game_events'], 'getReplayGameEvents')],
    'RawReplayMessageEvents':       [(['raw','message_events'], 'getReplayMessageEvents')],
    'RawTalentSelectionGameEvents': [(['raw','selections'], 'getTalentSelectionGameEvents')],
}

class StormReplayAnalyzer:

    @staticmethod
    def getAllFieldMappingNames():
        return named_field_mappings.keys()

    @staticmethod
    def getFieldMappingForNames(names):
        fieldMapping = []
        for name in names:
            fieldMapping = fieldMapping + named_field_mappings.get(name, [])
        return fieldMapping

    def __init__(self, reader):
        self.reader = reader

    def analyze(self, fieldMappings=None):
        if fieldMappings is None:
            fieldMappings = defaultFieldMappings
        retval = {}
        for field in fieldMappings:
            value = getattr(self, field[1])()
            worklist = [(retval, field[0], value)]
            while len(worklist) > 0:
                workItem = worklist.pop()
                obj = workItem[0]
                keyPath = workItem[1]
                value = workItem[2]

                key = keyPath[0]

                isArray = isinstance(key, (int, long)) 
                if isArray and key >= len(obj):
                    obj.extend([None]*(key + 1 - len(obj)))

                if len(keyPath) == 1:
                    obj[key] = value
                elif isinstance(keyPath[1], basestring):
                    if isArray:
                        if obj[key] is None:
                            obj[key] = {}
                        obj = obj[key]
                    else:
                        obj = obj.setdefault(key, {})
                    worklist.append( (obj, keyPath[1:], value) )
                elif isinstance(keyPath[1], list):
                    if isArray:
                        if obj[key] is None:
                            obj[key] = []
                        obj = obj[key]
                    else:
                        obj = obj.setdefault(key, [])
                    for index, element in enumerate(value):
                        worklist.append( (obj, [index] + keyPath[2:], element) )
                elif isinstance(keyPath[1], dict):
                    if isArray:
                        if obj[key] is None:
                            obj[key] = {}
                        obj = obj[key]
                    else:
                        obj = obj.setdefault(key, {})
                    for dictKey in value:
                        if 0 == len(keyPath[1]):
                            keyToWrite = dictKey
                        elif keyPath[1].has_key(dictKey):
                            keyToWrite = keyPath[1][dictKey]
                        else:
                            continue
                        worklist.append( (obj, [keyToWrite] + keyPath[2:], value[dictKey]) )
                else:
                    raise Exception('Key of invalid type: %s' % str(key))

        return retval

    def getReplayFileByteSize(self):
        return self.reader.getReplayFileByteSize()

    def getTalentSelectionGameEvents(self):
        events = []
        for event in self.reader.getReplayGameEvents():
            if (event['_event'] != 'NNet.Game.SHeroTalentTreeSelectedEvent'):
                continue
            events.append(event)
        return events

    def getReplayProtocolVersion(self):
        return self.reader.getReplayProtocolVersion()

    def getReplayInitData(self):
        return self.reader.getReplayInitData()

    def getReplayAttributesEvents(self):
        return self.reader.getReplayAttributesEvents()

    def getReplayDetails(self):
        return self.reader.getReplayDetails()

    def getReplayTrackerEvents(self):
        return self.reader.getReplayTrackerEvents()

    def getReplayGameEvents(self):
        return self.reader.getReplayGameEvents()

    def getReplayMessageEvents(self):
        return self.reader.getReplayMessageEvents()

    def getTranslatedReplayAttributesEvents(self):
        talentsReader = self.getTalentsReader()
        return talentsReader.translate_replay_attributes_events(self.getReplayAttributesEvents())

    def getGameDescription(self):
        initData = self.getReplayInitData()
        return initData['m_syncLobbyState']['m_gameDescription']

    def getGameSpeed(self):
        try:
            return self.gameSpeed
        except AttributeError:
            self.gameSpeed = 0
        return self.gameSpeed

    def getTalentsReader(self):
        try:
            return self.talentsReader
        except AttributeError:
            replayVersion = self.reader.getReplayProtocolVersion()
            try:
                self.talentsReader = __import__('stormreplay.talents%s' % replayVersion, fromlist=['talents'])
            except ImportError:
                raise Exception('Unsupported StormReplay build number for talents: %i' % replayVersion)
        return self.talentsReader

    def getTalents(self):
        try:
            return self.talents
        except AttributeError:
            self.talents = [[] for _ in xrange(10)]
            talentsReader = self.getTalentsReader()
            generator = talentsReader.decode_game_events_talent_choices(self.reader.getReplayGameEvents(), self.getPlayersHeroChoiceArray())
            for choice in generator:
                self.talents[choice['_userid']].append({
                    'seconds': self.gameloopToSeconds(choice['_gameloop']),
                    'level': choice['m_level'],
                    'name': choice['m_talentName'],
                    'description': choice['m_talentDescription'],
                    'index': choice['m_talentIndex'],
                })
        return self.talents

    def getTeamTalentTierTimes(self):
        try:
            return self.teamTalentTierTimes
        except AttributeError:
            teamTalentTierLevel = [[], []]
            teamTalentTiersFirstPick = [[], []]
            teamTalentTiersLastPick = [[], []]
            players = self.getPlayers()
            for playerIndex, playerTalentPicks in enumerate(self.getTalents()):
                player = players[playerIndex]
                for talentTierIndex, talentPick in enumerate(playerTalentPicks):
                    talentPickTime = talentPick['seconds']
                    teamIndex = player['m_teamId']

                    tiersFirstPick = teamTalentTiersFirstPick[teamIndex]
                    if (talentTierIndex >= len(tiersFirstPick)):
                        tiersFirstPick.append(talentPickTime)
                    elif (talentPickTime < tiersFirstPick[talentTierIndex]):
                        tiersFirstPick[talentTierIndex] = talentPickTime

                    tiersLastPick = teamTalentTiersLastPick[teamIndex]
                    if (talentTierIndex >= len(tiersLastPick)):
                        tiersLastPick.append(talentPickTime)
                    elif (talentPickTime > tiersLastPick[talentTierIndex]):
                        tiersLastPick[talentTierIndex] = talentPickTime

                    if (talentTierIndex >= len(teamTalentTierLevel[teamIndex])):
                        teamTalentTierLevel[teamIndex].append(talentPick['level'])
                    else:
                        teamTalentTierLevel[teamIndex][talentTierIndex] = talentPick['level']

            self.teamTalentTierTimes = [[], []]
            for teamIndex in xrange(2):
                for talentTierIndex, level in enumerate(teamTalentTierLevel[teamIndex]):
                    self.teamTalentTierTimes[teamIndex].append({
                        'earliest': teamTalentTiersFirstPick[teamIndex][talentTierIndex],
                        'latest': teamTalentTiersLastPick[teamIndex][talentTierIndex],
                        'level': level,
                    })

        return self.teamTalentTierTimes

    def getTeamLevels(self):
        try:
            return self.teamLevels
        except AttributeError:
            teamTalentTierTimes = self.getTeamTalentTierTimes()
            self.teamLevels = [[], []]
            for teamIndex in xrange(2):
                talentTierTimes = teamTalentTierTimes[teamIndex]
                levelTimes = [0] * talentTierTimes[-1]['level']
                for firstTier, nextTier in zip(talentTierTimes, talentTierTimes[1:]):
                    levelRange = nextTier['level'] - firstTier['level']
                    for level in xrange(firstTier['level'], nextTier['level']+1):
                        levelIndex = level-1
                        lerp = float(level - firstTier['level']) / levelRange
                        time = lerp * (nextTier['earliest'] - firstTier['earliest']) + firstTier['earliest']
                        levelTimes[levelIndex] = time
                levelToTalentTierInfo = {}
                for tierInfo in talentTierTimes:
                    levelToTalentTierInfo[str(tierInfo['level'])] = tierInfo
                for levelIndex, time in enumerate(levelTimes):
                    level = levelIndex + 1
                    levelInfo = {
                        'level': levelIndex + 1,
                        'seconds': time,
                        'is_talent_tier': False,
                    }
                    if levelToTalentTierInfo.has_key(str(level)):
                        tierInfo = levelToTalentTierInfo[str(level)]
                        levelInfo['is_talent_tier'] = True
                        levelInfo['earliest_talent_picked_time'] = tierInfo['earliest']
                        levelInfo['latest_talent_picked_time'] = tierInfo['latest']
                    self.teamLevels[teamIndex].append(levelInfo)
        return self.teamLevels

    def getMapName(self):
        try:
            return self.mapName
        except AttributeError:
            self.mapName = self.reader.getReplayDetails()['m_title']['utf8']
        return self.mapName

    def getPlayersHeroChoiceArray(self):
        try:
            return self.playersHeroArray
        except AttributeError:
            self.playersHeroArray = [None] * 10
            for i, player in enumerate(self.getPlayerSpawnInfo()):
                self.playersHeroArray[i] = player['hero']
        return self.playersHeroArray

    # returns array indexed by user ID
    def getPlayers(self):
        try:
            return self.players
        except AttributeError:
            self.players = [None] * 10
            for i, player in enumerate(self.getReplayDetails()['m_playerList']):
                #TODO: confirm that m_workingSetSlotId == i always
                toon = player['m_toon']
                player['m_toonId'] = "%i-%s-%i-%i" % (toon['m_region'], toon['m_programId'], toon['m_realm'], toon['m_id'])
                player['m_name'] = player['m_name']['utf8']
                player['m_controlPlayerId'] = i+1
                self.players[i] = player
            return self.players

    # returns array indexed by user ID
    def getPlayerSpawnInfo(self):
        try:
            return self.playerSpawnInfo
        except AttributeError:
            self.playerSpawnInfo = [None] * 10
            playerIdToUserId = {}
            for event in self.getReplayTrackerEvents():
                if event['_event'] == 'NNet.Replay.Tracker.SPlayerSetupEvent':
                    playerIdToUserId[event['m_playerId']] = event['m_userId']
                elif event['_event'] == 'NNet.Replay.Tracker.SUnitBornEvent' and (int(event['_gameloop']) > 0):
                    playerId = event['m_controlPlayerId']
                    if (playerIdToUserId.has_key(playerId)):
                        playerIndex = playerIdToUserId[playerId] # always playerId-1 so far, but this is safer
                        self.playerSpawnInfo[playerIndex] = {
                            'hero': event['m_unitTypeName']['utf8'],
                            'unit_tag': event['m_unitTag']
                        }
                        del playerIdToUserId[playerId]
                if len(playerIdToUserId) == 0:
                    break
            return self.playerSpawnInfo

    def getMatchSpeed(self):
        attributes = self.getTranslatedReplayAttributesEvents()
        return attributes[16]['m_gameSpeed']

    def getMatchType(self):
        attributes = self.getTranslatedReplayAttributesEvents()
        return attributes[16]['m_gameType']

    def getHeroSelectionMode(self):
        attributes = self.getTranslatedReplayAttributesEvents()
        return attributes[16]['m_heroSelectionMode']

    def getMatchUTCTimestamp(self):
        try:
            return self.utcTimestamp
        except AttributeError:
            self.utcTimestamp = (self.getReplayDetails()['m_timeUTC'] / 10000000) - 11644473600
            return self.utcTimestamp

    def getMatchLengthGameloops(self):
        lastEvent = self.getReplayTrackerEvents()[-1]
        return lastEvent['_gameloop']

    def getMatchLengthSeconds(self):
        return self.gameloopToSeconds(self.getMatchLengthGameloops())

    def gameloopToSeconds(self, gameloop):
        return gameloop / 16.0

    def gameloopToTimestamp(self, gameloop):
        return self.getMatchUTCTimestamp() + _gameloop / 16.0

    def getChat(self):
        try:
            return self.chat
        except AttributeError:
            self.chat = []
            for messageEvent in self.getReplayMessageEvents():
                if (messageEvent['_event'] != 'NNet.Game.SChatMessage'):
                    continue
                userId = messageEvent['_userid']['m_userId']
                chatData = {
                    't': self.gameloopToTimestamp(messageEvent['_gameloop']),
                    'user': userId,
                    'msg': messageEvent['m_string']['utf8'],
                }
                self.chat.append(chatData)
            return self.chat




