from django.shortcuts import render
from django.http import HttpResponse

import requests
import os

def index(request):
    if request.method == "POST":
        if not request.FILES.has_key('file'):
            content = json.dumps({'error':'Missing "file" parameter with uploaded replay file data'})
        else:
            replayFile = request.FILES.get('file')
            srp = StormReplayParser(replayFile)      # this returns an UploadedFile, which has a 'read' member function as required by mpyq
            content = json.dumps({
                #'game_id': srp.getGameId(),
                #'map': srp.getMapName(),
                #'players': srp.getReplayPlayers(),
                #'chat': srp.getChat(),
                'game': srp.getReplayGameEventsDebug(),
            })
        return HttpResponse(content, content_type="application/json")

    return render(request, 'file-upload.html', {})

