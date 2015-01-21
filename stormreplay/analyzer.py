from s2protocol.mpyq import mpyq
from s2protocol import protocol15405
from s2protocol.decoders import *
import os

import reader

# todo: get this logger from elsewhere
from celery.utils.log import get_task_logger
log = get_task_logger(__name__)

class StormReplayAnalyzer:

    def __init__(self, reader):
        self.reader = reader

    def analyze(self, fieldMappings=None):
        if fieldMappings is None:
            fieldMappings = self.getDefaultFieldMappings()
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
        return retval

    def getDefaultFieldMappings(self):
        return [('match_uid', 'getUniqueMatchId'), (('map','name'), 'getMapName')]

    # Returns a unique string that is shared among all of the 10+ replays involved in this match
    def getUniqueMatchId(self):
        try:
            return self.matchId
        except AttributeError:
            self.matchId = "todo"
            return self.matchId

    def getMapName(self):
        try:
            return self.mapName
        except AttributeError:
            self.mapName = self.reader.getReplayDetails()['m_title']
        return self.mapName



