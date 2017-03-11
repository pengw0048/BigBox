from django.http import *
from django.conf import settings
from django.contrib import messages
from .models import *
from dateutil import parser
import json
from datetime import datetime, timedelta
import requests
from urllib.parse import urlencode


def add_storage_account(request, next_url, cloud):
    if 'error' in request.GET:
        error_message = 'An error occurred: ' + request.GET['error']
        messages.error(request, error_message)
        return HttpResponseRedirect(next_url)
    elif 'code' in request.GET:
        try:
            r = requests.post("https://www.googleapis.com/oauth2/v4/token",
                              {'code': request.GET['code'], 'client_id': settings.GDRIVE_APP_KEY,
                               'client_secret': settings.GDRIVE_APP_SECRET,
                               'redirect_uri': settings.GDRIVE_REDIRECT_URL, 'grant_type': 'authorization_code'})
            credentials = r.json()
            expire_at = (datetime.utcnow() + timedelta(0, credentials['expires_in'])).isoformat()
            access_token = credentials['access_token']
            refresh_token = credentials['refresh_token']
            r = requests.get("https://www.googleapis.com/oauth2/v3/userinfo",
                             headers={'Authorization': 'Bearer ' + access_token})
            about = r.json()
            uid = about['sub']
            full_name = about['name']
            email = about['email']
        except Exception as e:
            messages.error(request, 'An error occurred: ' + str(e))
        else:
            if StorageAccount.objects.all().filter(identifier=uid).exists():
                messages.warning(request, 'This Google Drive space is already linked')
            else:
                sa = StorageAccount(user=request.user, cloud=cloud, identifier=uid, status=1,
                                    user_full_name=full_name, email=email,
                                    credentials=json.dumps({'a': access_token, 'r': refresh_token, 'e': expire_at}))
                sa.save()
                messages.success(request, 'A new Google Drive space is now linked to your account')
        return HttpResponseRedirect(next_url)
    else:
        url = 'https://accounts.google.com/o/oauth2/v2/auth'
        param = urlencode({'client_id': settings.GDRIVE_APP_KEY, 'redirect_uri': settings.GDRIVE_REDIRECT_URL,
                           'response_type': 'code', 'scope': settings.GDRIVE_SCOPE, 'access_type': 'offline',
                           'prompt': 'consent select_account'})
        return HttpResponseRedirect(url + '?' + param)


def get_client(acc: StorageAccount) -> str:
    cred = json.loads(acc.credentials)
    expire_at = parser.parse(cred['e'])
    delta = (expire_at - datetime.utcnow()).total_seconds()
    if delta < 60:
        r = requests.post("https://www.googleapis.com/oauth2/v4/token",
                          {'client_id': settings.GDRIVE_APP_KEY, 'client_secret': settings.GDRIVE_APP_SECRET,
                           'refresh_token': cred['r'], 'grant_type': 'refresh_token'})
        if r.status_code == 200:
            j = r.json()
            cred['a'] = j['access_token']
            cred['e'] = (datetime.utcnow() + timedelta(0, j['expires_in'])).isoformat()
            acc.credentials = json.dumps(cred)
            acc.save()
    return cred['a']


def get_space(g: str) -> dict:
    r = requests.get("https://www.googleapis.com/drive/v3/about", params={'fields': 'storageQuota'},
                     headers={'Authorization': 'Bearer ' + g})
    res = r.json()
    used = res['storageQuota']['usage']
    total = res['storageQuota']['limit']
    return {'used': used, 'total': total}


def find_path_id(g: str, path: str) -> str:
    fid = 'root'
    if path == '/':
        return fid
    levels = path.strip('/').split('/')
    try:
        for level in levels:
            r = requests.get("https://www.googleapis.com/drive/v3/files",
                             params={'q': "'%s' in parents and name='%s' and trashed = false"
                                          % (fid.replace("'", "\\'"), level.replace("'", "\\'")),
                                     'fields': "files(id,mimeType)"},
                             headers={'Authorization': 'Bearer ' + g})
            fs = r.json()['files']
            if len(fs) < 1:
                return ''
            fid = fs[0]['id']
    except:
        return ''
    return fid


def get_file_list(g: str, path: str) -> list:
    fid = find_path_id(g, path)
    if fid == '':
        return []
    r = requests.get("https://www.googleapis.com/drive/v3/files",
                     params={'q': "'%s' in parents and trashed = false" % fid.replace("'", "\\'"),
                             'fields': "files(id,mimeType,modifiedTime,name,size)"},
                     headers={'Authorization': 'Bearer ' + g})
    fs = r.json()
    ret = []
    try:
        for f in fs['files']:
            try:
                if f['mimeType'] == 'application/vnd.google-apps.folder':
                    ret.append({'name': f['name'], 'id': f['id'], 'is_folder': True})
                else:
                    ret.append({'name': f['name'], 'id': f['id'], 'size': f['size'],
                                'time': parser.parse(f['modifiedTime']), 'is_folder': False})
            except:
                raise
    except:
        raise
    return ret
