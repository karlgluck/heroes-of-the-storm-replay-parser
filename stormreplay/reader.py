from s2protocol.mpyq import mpyq
from s2protocol import protocol15405
from s2protocol.decoders import *
import os

# todo: get this logger from elsewhere
from celery.utils.log import get_task_logger
log = get_task_logger(__name__)




# Reads data from the .StormReplay file into easily-read dictionaries. Analysis of
# the contents is split into another class.
class StormReplayReader:

    def __init__(self, replayFile):

        relativeToEndOfFile = 2
        replayFile.seek(0, relativeToEndOfFile)
        self.replayFileByteSize = replayFile.tell()
        replayFile.seek(0)

        # The replayFile can be either the name of a file or any object that has a 'read()' method.
        self.mpq = mpyq.MPQArchive(replayFile)

        self.buildStormReplay = protocol15405.decode_replay_header(self.mpq.header['user_data_header']['content'])['m_version']['m_baseBuild']

        try:
            self.protocol = __import__('s2protocol' + '.protocol%s' % self.buildStormReplay, fromlist=['protocol2'])
        except ImportError:
            raise Exception('Unsupported StormReplay protocol build number: %i' % self.buildStormReplay)

    def getReplayFileByteSize(self):
        return self.replayFileByteSize

    def getReplayProtocolVersion(self):
        return self.buildStormReplay

    def getReplayInitData(self):
        try:
            return self.replayInitData
        except AttributeError:
            self.replayInitData = self.protocol.decode_replay_initdata(self.mpq.read_file('replay.initData'))
            return self.replayInitData

    def getReplayAttributesEvents(self):
        try:
            return self.replayAttributesEvents
        except AttributeError:
            self.replayAttributesEvents = self.protocol.decode_replay_attributes_events(self.mpq.read_file('replay.attributes.events'))
        return self.replayAttributesEvents
        

    def getReplayDetails(self):
        try:
            return self.replayDetails
        except AttributeError:
            self.replayDetails = self.protocol.decode_replay_details(self.mpq.read_file('replay.details'))
            return self.replayDetails

    def getReplayMessageEvents(self):
        try:
            return self.replayMessageEvents
        except AttributeError:
            messageGenerator = self.protocol.decode_replay_message_events(self.mpq.read_file('replay.message.events'))
            self.replayMessageEvents = []
            for event in messageGenerator:
                self.replayMessageEvents.append(event)
            return self.replayMessageEvents

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
            try:
                i = 0
                for event in generator:
                    event['index'] = i
                    if (i >= 25000):
                        return self.replayGameEvents
                    i = i + 1
            except CorruptedError as e:
                self.replayGameEvents.append({'error': str(e)});
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

