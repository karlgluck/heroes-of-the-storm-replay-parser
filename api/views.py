from django.shortcuts import render
from django.http import HttpResponse

import requests
import os
import json

from StormReplayParser import StormReplayParser
from tasks import LocallyStoredReplayParsingTask
from tempfile import NamedTemporaryFile

def index(request):
    if request.method == "POST":
        if not request.FILES.has_key('file'):
            content = json.dumps({'error':'Missing "file" parameter with uploaded replay file data'})
        else:
            replayFile = request.FILES.get('file')
            # replayFile might have an issue if it is >= 2.5 MB, but this should never be the case
            # with .StormReplay files
            srp = StormReplayParser(replayFile)
            content = json.dumps({
                'unique_match_id': srp.getUniqueMatchId(),
                'map': srp.getMapName(),
                'players': srp.getReplayPlayers(),
                'chat': srp.getChat(),
                'game': srp.getReplayGameEvents(),
            })
        return HttpResponse(content, content_type="application/json")

    return render(request, 'api/file-upload.html', {})

def debug(request):
    if request.method == "POST":
        if not request.FILES.has_key('file'):
            content = json.dumps({'error':'Missing "file" parameter with uploaded replay file data'})
        else:
            replayFile = request.FILES.get('file')
            savedReplayFile = NamedTemporaryFile(delete=False)
            for chunk in replayFile.chunks():
                savedReplayFile.write(chunk)
            savedReplayFileName = savedReplayFile.name
            savedReplayFile.close()
            asyncResult = LocallyStoredReplayParsingTask.delay(savedReplayFileName)
            content = json.dumps({
                'result_url': request.META.get('HTTP_REFERER') + '/result?id=' + asyncResult.id
            })
        return HttpResponse(content, content_type="application/json")

    return render(request, 'api/file-upload.html', {})

def truncate(string, length):
    return string if len(string)<=length else string[0:length-1]

#def computeChecksumOfCeleryTaskId(celeryTaskId):
#    return sum(bytearray('HotS'+celeryTaskId))

#def result(request):
#    celeryTaskId = truncate(request.GET.get('id', ''), 36)
#    checksum = request.GET.get('cs', '')
#    if (computeChecksumOfCeleryTaskId (celeryTaskId) != checksum):
#        return HttpResponseBadRequest(json.dumps({'error':'invalid id'}), content_type="application/json")
#    result = ReplayParsingTask.AsyncResult(celeryTaskId)
#    if (result.status == 'FAILURE'):
#        return HttpResponse(json.dumps({'status':'FAILURE','exception':str(result.result)}), content_type="application/json")
#    if (result.status == 'SUCCESS'):
#        return HttpResponse(json.dumps({'status':'SUCCESS','data':result.get()}), content_type="application/json")
#    return HttpResponse(json.dumps({'status':'PENDING'})

def debugResult(request):
    celeryTaskId = truncate(request.GET.get('id', ''), 36)
    result = LocallyStoredReplayParsingTask.AsyncResult(celeryTaskId)
    if (result.status == 'FAILURE'):
        return HttpResponse(json.dumps({'status':'FAILURE','exception':str(result.result)}), content_type="application/json")
    if (result.status == 'SUCCESS'):
        return HttpResponse(json.dumps({'status':'SUCCESS','data':result.get()}), content_type="application/json")
    return HttpResponse(json.dumps({'status':'PENDING'}), content_type="application/json")

