from django.http import *
from django.conf import settings
from django.contrib import messages
from .models import *
from dateutil import parser
import json
from datetime import datetime, timedelta, timezone
import requests
from urllib.parse import urlencode


def add_storage_account(request, next_url, cloud):
    if 'error' in request.GET:
        error_message = 'An error occurred: ' + request.GET['error']
        messages.error(request, error_message)
        return HttpResponseRedirect(next_url)
    elif 'code' in request.GET:
        try:
            r = requests.post('https://www.googleapis.com/oauth2/v4/token',
                              {'code': request.GET['code'], 'client_id': settings.GDRIVE_APP_KEY,
                               'client_secret': settings.GDRIVE_APP_SECRET,
                               'redirect_uri': settings.GDRIVE_REDIRECT_URL, 'grant_type': 'authorization_code'})
            credentials = r.json()
            expire_at = (datetime.now(timezone.utc) + timedelta(0, credentials['expires_in'])).isoformat()
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
    delta = (expire_at - datetime.now(timezone.utc)).total_seconds()
    if delta < 60:
        r = requests.post('https://www.googleapis.com/oauth2/v4/token',
                          {'client_id': settings.GDRIVE_APP_KEY, 'client_secret': settings.GDRIVE_APP_SECRET,
                           'refresh_token': cred['r'], 'grant_type': 'refresh_token'})
        if r.status_code == 200:
            j = r.json()
            cred['a'] = j['access_token']
            cred['e'] = (datetime.now(timezone.utc) + timedelta(0, j['expires_in'])).isoformat()
            acc.credentials = json.dumps(cred)
            acc.save()
    return cred['a']


def get_space(g: str) -> dict:
    r = requests.get("https://www.googleapis.com/drive/v3/about", params={'fields': 'storageQuota'},
                     headers={'Authorization': 'Bearer ' + g})
    res = r.json()
    used = res['storageQuota']['usage']
    total = res['storageQuota'].get('limit', None)
    return {'used': used, 'total': total}


def find_path_id(g: str, path: str, create: bool = False) -> str:
    fid = 'root'
    if path == '/':
        return fid
    levels = path.strip('/').split('/')
    try:
        for level in levels:
            r = requests.get("https://www.googleapis.com/drive/v3/files",
                             params={'q': "'%s' in parents and name='%s' and trashed=false and "
                                          "mimeType='application/vnd.google-apps.folder'"
                                          % (fid.replace("'", "\\'"), level.replace("'", "\\'")),
                                     'fields': "files(id,mimeType)"},
                             headers={'Authorization': 'Bearer ' + g})
            fs = r.json()['files']
            if len(fs) < 1:
                if create:
                    fid = create_folder_with_parent_id(g, fid, level)
                else:
                    return ''
            else:
                fid = fs[0]['id']
    except:
        return ''
    return fid


def create_folder(g: str, path: str, name: str) -> dict:
    if path == 'root' or path == '' or path == '/':
        return {'id': 'root'}
    fullpath = path if name == '' else path + '/' + name
    return {'id': find_path_id(g, fullpath, True)}


def create_folder_with_parent_id(g: str, parent: str, name: str) -> str:
    r = requests.post('https://www.googleapis.com/drive/v3/files',
                      json={'mimeType': 'application/vnd.google-apps.folder',
                            'parents': [parent],
                            'name': name},
                      headers={'Authorization': 'Bearer ' + g})
    return r.json()['id']


def get_file_list(g: str, path: str) -> list:
    fid = find_path_id(g, path)
    if fid == '':
        return []
    r = requests.get('https://www.googleapis.com/drive/v3/files',
                     params={'q': "'%s' in parents and trashed = false" % fid.replace("'", "\\'"),
                             'fields': 'files(id,mimeType,modifiedTime,name,size)'},
                     headers={'Authorization': 'Bearer ' + g})
    fs = r.json()
    ret = []
    try:
        for f in fs['files']:
            try:
                if f['mimeType'] == 'application/vnd.google-apps.folder':
                    ret.append({'name': f['name'], 'id': f['id'], 'is_folder': True})
                else:
                    ret.append({'name': f['name'], 'id': f['id'], 'size': f.get('size', 0),
                                'time': parser.parse(f['modifiedTime']), 'is_folder': False})
            except:
                raise
    except:
        raise
    return ret


def get_down_link(g: str, fid: str) -> str:
    r = requests.get('https://www.googleapis.com/drive/v3/files/' + fid,
                     params={'fields': 'webContentLink,webViewLink'},
                     headers={'Authorization': 'Bearer ' + g})
    if r.status_code != 200:
        r.raise_for_status()
    j = r.json()
    if 'webContentLink' in j:
        return j['webContentLink']
    elif 'webViewLink' in j:
        return j['webViewLink']
    else:
        raise Exception('File not found')


def get_upload_creds(g: str, data: str) -> dict:
    try:
        j = json.loads(data)
        parent = j['parent']
        name = j['name']
    except:
        return {}
    r = requests.get('https://www.googleapis.com/drive/v3/files',
                     params={'q': "'%s' in parents and name='%s' and trashed=false and "
                                  "mimeType!='application/vnd.google-apps.folder'"
                                  % (parent.replace("'", "\\'"), name.replace("'", "\\'")),
                             'fields': 'files(id)'},
                     headers={'Authorization': 'Bearer ' + g})
    fs = r.json()['files']
    if len(fs) < 1:
        r = requests.post('https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable',
                          json={'parents': [parent], 'name': name},
                          headers={'Authorization': 'Bearer ' + g})
    else:
        r = requests.patch('https://www.googleapis.com/upload/drive/v3/files/%s?uploadType=resumable' % fs[0]['id'],
                           headers={'Authorization': 'Bearer ' + g})
    return {'url': r.headers['Location']}
