from __future__ import absolute_import

import os

from celery import shared_task

from stormreplay import *

import boto
import StringIO
import cStringIO

import json
import gzip

from celery.utils.log import get_task_logger
log = get_task_logger(__name__)

from boto.s3.key import Key

def AnalyzeReplayFile (replayFile):
    stormReader = StormReplayReader(replayFile)
    log.info("Created StormReplayReader") 
    stormAnalyzer = StormReplayAnalyzer(stormReader)
    log.info("Created StormReplayAnalyzer") 
    retval = stormAnalyzer.analyze();
    return retval

@shared_task
def LocallyStoredReplayParsingTask(fileName):
    log.info('File name='+fileName)
    replayFile = open(fileName)
    retval = AnalyzeReplayFile(replayFile)
    replayFile.close()
    os.remove(replayFile.name)
    return retval

@shared_task
def S3StoredReplayParsingTask(keyName):

    splitKey = keyName.split('/')
    if len(splitKey) != 2:
        raise ValueError("keyName must be of the form: <folder>/<file>")
    keyBase = splitKey[0]
    resultKeyName = keyBase + '/replay.json.gz'

    # todo: duplicate request limiting
    log.info('Key='+keyName)
    s3 = boto.connect_s3()
    bucket = s3.get_bucket(os.environ.get('AWS_BUCKET_NAME'), validate=False)

    k = Key(bucket)
    k.key = keyName

    # todo: do we need to read this to an on-disk temp file to save memory?
    replayFile = cStringIO.StringIO(k.get_contents_as_string())
    retval = AnalyzeReplayFile(replayFile)
    # todo: close the original key?

    resultKey = Key(bucket)
    resultKey.key = resultKeyName
    resultKey.set_metadata('Content-Encoding', 'gzip')

    out = cStringIO.StringIO()
    with gzip.GzipFile(fileobj=out, mode="w") as f:
        f.write(json.dumps(retval))
    resultKey.set_contents_from_file(out, rewind=True)
    out.close()

    secondsToExpire = 1*60*60
    responseHeaders = {
        'response-content-encoding': 'gzip',
        'response-content-type': 'application/json',
    }
    s3UrlToResultKey = resultKey.generate_url(secondsToExpire, 'GET', response_headers=responseHeaders)

    log.info("Result: " + s3UrlToResultKey);
    log.info("Finished reading from StormReplay. Cleaning up.")
    return {
        'url': s3UrlToResultKey
    }


