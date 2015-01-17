from __future__ import absolute_import

import os

from celery import shared_task
from celery.utils.log import get_task_logger

from api.StormReplayParser import StormReplayParser

log = get_task_logger(__name__)

@shared_task
def LocallyStoredReplayParsingTask(fileName):
    log.info('File name='+fileName)
    replayFile = open(fileName)
    srp = StormReplayParser(replayFile)
    log.info("Created StormReplayParser, getting data") 
    retval = {
        'unique_match_id': srp.getUniqueMatchId(),
        'map': srp.getMapName(),
        'players': srp.getReplayPlayers(),
        'chat': srp.getChat(),
        #'game': srp.getReplayGameEvents(),
    }
    log.info("Finished reading from StormReplay. Cleaning up.")
    replayFile.close()
    os.remove(replayFile.name)
    return retval

# todo: task specific logging?
# http://blog.mapado.com/task-specific-logging-in-celery/
