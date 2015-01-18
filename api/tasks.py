from __future__ import absolute_import

import os

from celery import shared_task
from celery.utils.log import get_task_logger

from api.StormReplayParser import StormReplayParser

import boto
import StringIO

from boto.s3.key import Key

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

@shared_task
def S3StoredReplayParsingTask(key):
    #todo: duplicate limiting
    log.info('Key='+key)
    s3 = boto.connect_s3()
    bucket = s3.get_bucket(os.environ.get('AWS_BUCKET_NAME'), validate=False)

    k = Key(bucket)
    k.key = key
    #todo: there is a better way than just pretending the string is a file
    replayFile = StringIO.StringIO(k.get_contents_as_string())
    srp = StormReplayParser(replayFile)
    log.info("Created StormReplayParser, getting data") 
    #todo: write this data back to S3 and return the address
    retval = {
        'unique_match_id': srp.getUniqueMatchId(),
        'map': srp.getMapName(),
        'players': srp.getReplayPlayers(),
        'chat': srp.getChat(),
        #'game': srp.getReplayGameEvents(),
    }
    log.info("Finished reading from StormReplay. Cleaning up.")
    return retval


# todo: task specific logging?
# http://blog.mapado.com/task-specific-logging-in-celery/
