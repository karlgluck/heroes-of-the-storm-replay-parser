from django.shortcuts import render
from django.http import HttpResponse

import requests
import os
import json

from StormReplayParser import StormReplayParser

def index(request):
    if request.method == "POST":
        if not request.FILES.has_key('file'):
            content = json.dumps({'error':'Missing "file" parameter with uploaded replay file data'})
        else:
            replayFile = request.FILES.get('file')
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
            srp = StormReplayParser(replayFile)
            content = json.dumps({
                'gameDebug': srp.getReplayGameEventsDebug(),
            })
        return HttpResponse(content, content_type="application/json")

    return render(request, 'api/file-upload.html', {})

