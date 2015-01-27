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
            return self.replayPlayers
        except AttributeError:
            self.players = [None] * 10
            for i, player in enumerate(self.getReplayDetails()['m_playerList']):
                #TODO: confirm that m_workingSetSlotId == i always
                toon = player['m_toon']
                player['toon_id'] = "%i-%s-%i-%i" % (toon['m_region'], toon['m_programId'], toon['m_realm'], toon['m_id'])
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




