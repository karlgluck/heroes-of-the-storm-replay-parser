import os
import reader

import json

# todo: get this logger from elsewhere
from celery.utils.log import get_task_logger
log = get_task_logger(__name__)

defaultFieldMappings = [
    #(('map','name'), 'getMapName'),
    #('players', 'getPlayers'),
    #('chat', 'getChat'),
    #(('raw','details'), 'getReplayDetails'),
    #(('raw','details'), 'getReplayInitData'),
    #(('raw','game_events'), 'getReplayGameEvents'),
    #(('raw','tracker_events'), 'getReplayTrackerEvents'),

    (('raw','players_hero_array'), 'getPlayersHeroChoiceArray'),
    (('raw','talents'), 'getTalents'),
    (('raw','levels'), 'getTeamLevels'),
    #(('raw','selections'), 'getTalentSelectionGameEvents'),

    #(('raw','message_events'), 'getReplayMessageEvents'),
]

class StormReplayAnalyzer:

    def __init__(self, reader):
        self.reader = reader

    def analyze(self, fieldMappings=None):
        if fieldMappings is None:
            fieldMappings = defaultFieldMappings
        retval = {}
        log.info("fieldMappings = " + str(fieldMappings));
        for field in fieldMappings:
            obj = retval
            keyPath = field[0]
            if (isinstance(keyPath, basestring)):
                key = keyPath
            else:
                for key in keyPath[:-1]:
                    obj = obj.setdefault(key, {})
                key = keyPath[-1]
            obj[key] = getattr(self, field[1])()
        log.info("Finished: " + str(retval));
        return retval

    def getTalentSelectionGameEvents(self):
        events = []
        for event in self.reader.getReplayGameEvents():
            if (event['_event'] != 'NNet.Game.SHeroTalentTreeSelectedEvent'):
                continue
            events.append(event)
        return events

    def getReplayInitData(self):
        return self.reader.getReplayInitData();

    def getReplayDetails(self):
        return self.reader.getReplayDetails();

    def getReplayTrackerEvents(self):
        return self.reader.getReplayTrackerEvents();

    def getReplayGameEvents(self):
        return self.reader.getReplayGameEvents();

    def getReplayMessageEvents(self):
        return self.reader.getReplayMessageEvents();

    def getGameSpeed(self):
        try:
            return self.gameSpeed
        except AttributeError:
            self.gameSpeed = 0
        return self.gameSpeed

    def getTalents(self):
        try:
            return self.talents
        except AttributeError:
            self.talents = [[] for _ in xrange(10)]
            replayVersion = self.reader.getReplayProtocolVersion()
            try:
                talentsReader = __import__('stormreplay.talents%s' % replayVersion, fromlist=['talents'])
            except ImportError:
                raise Exception('Unsupported StormReplay build number for talents: %i' % replayVersion);
            generator = talentsReader.decode_game_events_talent_choices(self.reader.getReplayGameEvents(), self.getPlayersHeroChoiceArray());
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
                # The m_controlPlayerId is the field value to reference this player in the tracker events
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
                elif event['_event'] == 'NNet.Replay.Tracker.SUnitBornEvent':
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

    def getMatchUTCTimestamp(self):
        try:
            return self.utcTimestamp
        except AttributeError:
            self.utcTimestamp = (self.getReplayDetails()['m_timeUTC'] / 10000000) - 11644473600
            return self.utcTimestamp

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




