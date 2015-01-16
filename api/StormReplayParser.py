from s2protocol.mpyq import mpyq
from s2protocol import protocol15405
import os

class StormReplayParser:

    def __init__(self, replayFile):

        # The replayFile can be either the name of a file or any object that has a 'read()' method.
        self.mpq = mpyq.MPQArchive(replayFile)

        self.buildStormReplay = protocol15405.decode_replay_header(self.mpq.header['user_data_header']['content'])['m_version']['m_baseBuild']

        try:
            self.protocol = __import__('s2protocol' + '.protocol%s' % self.buildS2Protocol, fromlist=['protocol2'])
        except ImportError:
            raise Exception('Unsupported build number: %i' % self.buildStormReplay)

    # Returns a unique string that is shared among all of the 10+ replays involved in this match
    def getUniqueMatchId(self):
        try:
            return self.matchId
        except AttributeError:
            self.gameId = "todo"
            return self.matchId

    def getReplayInitData(self):
        try:
            return self.replayInitData
        except AttributeError:
            self.replayInitData = self.protocol.decode_replay_initdata(self.mpq.read_file('replay.initData'))
            return self.replayInitData

    def getReplayDetails(self):
        try:
            return self.replayDetails
        except AttributeError:
            self.replayDetails = self.protocol.decode_replay_details(self.mpq.read_file('replay.details'))
            return self.replayDetails

    # returns array indexed by user ID
    def getReplayPlayers(self):
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
            players = self.getReplayPlayers()
            playerIdToUserId = {}
            for event in self.getReplayTrackerEvents():
                if event['_event'] == 'NNet.Replay.Tracker.SPlayerSetupEvent':
                    playerIdToUserId[event['m_playerId']] = event['m_userId']
                elif event['_event'] == 'NNet.Replay.Tracker.SUnitBornEvent':
                    playerId = event['m_controlPlayerId']
                    if (playerIdToUserId.has_key(playerId)):
                        playerIndex = playerIdToUserId[playerId] # always playerId-1 so far, but this is safer
                        self.playerSpawnInfo[playerIndex] = {
                            'hero': event['m_unitTypeName'],
                            'unit_tag': event['m_unitTag']
                        }
                        del playerIdToUserId[playerId]
                if len(playerIdToUserId) == 0:
                    break
            return self.playerSpawnInfo

    def getReplayMessageEvents(self):
        try:
            return self.replayMessageEvents
        except AttributeError:
            messageGenerator = self.protocol.decode_replay_message_events(self.mpq.read_file('replay.message.events'))
            self.replayMessageEvents = []
            for event in messageGenerator:
                self.replayMessageEvents.append(event)
            return self.replayMessageEvents

    def getMapName(self):
        try:
            return self.mapName
        except AttributeError:
            self.mapName = self.getReplayDetails()['m_title']
        return self.mapName

    def getMatchUTCTimestamp(self):
        try:
            return self.utcTimestamp
        except AttributeError:
            self.utcTimestamp = (self.getReplayDetails()['m_timeUTC'] / 10000000) - 11644473600
            return self.utcTimestamp

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
                    'timestamp': self.getMatchUTCTimestamp() + messageEvent['_gameloop'] / 16,
                    'user': userId,
                    'string': messageEvent['m_string'],
                }
                self.chat.append(chatData)
            return self.chat

    def getReplayGameEvents(self):
        try:
            return self.replayGameEvents
        except AttributeError:
            generator = self.protocol.decode_replay_game_events(self.mpq.read_file('replay.game.events'))
            self.replayGameEvents = []
            for event in generator:
                self.replayGameEvents.append(event)
            return self.replayGameEvents

    def getReplayGameEventsDebug(self):
        try:
            return self.replayGameEventsDebug
        except AttributeError:
            generator = self.protocol.decode_replay_game_events_debug(self.mpq.read_file('replay.game.events'))
            self.replayGameEvents = []
            for event in generator:
                self.replayGameEvents.append(event)
            return self.replayGameEvents

    def getReplayTrackerEvents(self):
        try:
            return self.replayTrackerEvents
        except AttributeError:
            generator = self.protocol.decode_replay_tracker_events(self.mpq.read_file('replay.tracker.events'))
            self.replayTrackerEvents = []
            for event in generator:
                if event.has_key('m_unitTagIndex') and event.has_key('m_unitTagRecycle'):
                    event['m_unitTag'] = self.protocol.unit_tag(event['m_unitTagIndex'], event['m_unitTagRecycle'])
                self.replayTrackerEvents.append(event)
            return self.replayTrackerEvents
