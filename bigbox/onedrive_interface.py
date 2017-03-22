from django.http import *
from django.conf import settings
from django.contrib import messages
from .models import *
import requests
import json
from dateutil import parser
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode


def add_storage_account(request, next_url, cloud):
    if 'error' in request.GET:
        error_message = 'An error occurred'
        if 'error_description' in request.GET:
            error_message += ' (%s): %s' % (request.GET['error'], request.GET['error_description'])
        messages.error(request, error_message)
        return HttpResponseRedirect(next_url)
    elif 'code' in request.GET:
        try:
            r = requests.post('https://login.microsoftonline.com/common/oauth2/v2.0/token',
                              {'code': request.GET['code'], 'client_id': settings.ONEDRIVE_APP_KEY,
                               'client_secret': settings.ONEDRIVE_APP_SECRET,
                               'redirect_uri': settings.ONEDRIVE_REDIRECT_URL, 'grant_type': 'authorization_code'})
            credentials = r.json()
            expire_at = (datetime.now(timezone.utc) + timedelta(0, credentials['expires_in'])).isoformat()
            access_token = credentials['access_token']
            refresh_token = credentials['refresh_token']
            info = get_user_info(access_token)
            uid = info['id']
            full_name = info['displayName']
            short_name = info['givenName']
            email = info['userPrincipalName']
        except Exception as e:
            messages.error(request, 'An error occurred: ' + str(e))
        else:
            if StorageAccount.objects.all().filter(identifier=uid).exists():
                messages.warning(request, 'This OneDrive space is already linked')
            else:
                sa = StorageAccount(user=request.user, cloud=cloud, identifier=uid, status=1,
                                    credentials=json.dumps({'a': access_token, 'r': refresh_token, 'e': expire_at}),
                                    user_full_name=full_name, user_short_name=short_name, email=email)
                sa.save()
                messages.success(request, 'A new OneDrive space is now linked to your account')
        return HttpResponseRedirect(next_url)
    else:
        url = 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize'
        param = urlencode({'client_id': settings.ONEDRIVE_APP_KEY, 'redirect_uri': settings.ONEDRIVE_REDIRECT_URL,
                           'response_type': 'code', 'scope': settings.ONEDRIVE_SCOPE})
        return HttpResponseRedirect(url + '?' + param)


def get_user_info(access_token):
    r = requests.get(settings.ONEDRIVE_BASE_URL + 'users/me', headers={'Authorization': 'Bearer ' + access_token})
    return r.json()


def get_client(acc: StorageAccount) -> str:
    cred = json.loads(acc.credentials)
    expire_at = parser.parse(cred['e'])
    delta = (expire_at - datetime.now(timezone.utc)).total_seconds()
    if delta < 60:
        r = requests.post('https://login.microsoftonline.com/common/oauth2/v2.0/token',
                          {'client_id': settings.ONEDRIVE_APP_KEY, 'client_secret': settings.ONEDRIVE_APP_SECRET,
                           'refresh_token': cred['r'], 'grant_type': 'refresh_token',
                           'redirect_uri': settings.ONEDRIVE_REDIRECT_URL})
        if r.status_code == 200:
            j = r.json()
            cred['a'] = j['access_token']
            if 'refresh_token' in j:
                cred['r'] = j['refresh_token']
            cred['e'] = (datetime.now(timezone.utc) + timedelta(0, j['expires_in'])).isoformat()
            acc.credentials = json.dumps(cred)
            acc.save()
    return cred['a']


def get_space(od: str) -> dict:
    r = requests.get(settings.ONEDRIVE_BASE_URL + 'me/drive',
                     headers={'Authorization': 'bearer ' + od}).json()
    used = r['quota']['used']
    total = r['quota']['total']
    return {'used': used, 'total': total}


def get_file_list(od: str, path: str) -> tuple:
    ret = []
    opath = path
    if path == '/':
        path = 'drive/root/children'
    else:
        path = 'drive/root:' + path + ':/children'
    try:
        fs = requests.get(settings.ONEDRIVE_BASE_URL + path,
                          headers={'Authorization': 'bearer ' + od}).json()
        for f in fs['value']:
            try:
                if 'file' in f:
                    ret.append({'name': f['name'], 'id': f['id'], 'size': f['size'],
                                'time': parser.parse(f['lastModifiedDateTime']), 'is_folder': False})
                else:
                    ret.append({'name': f['name'], 'id': f['id'], 'is_folder': True})
            except:
                pass
    except:
        pass
    return ret, opath


def get_down_link(od: str, fid: str) -> str:
    r = requests.get(settings.ONEDRIVE_BASE_URL + 'drive/items/' + fid + '/content',
                     headers={'Authorization': 'bearer ' + od})
    if r.status_code < 300 or r.status_code >= 400:
        r.raise_for_status()
    if r.url:
        return r.url
    else:
        raise Exception('File not found')


def get_upload_creds(od: str, data: str) -> dict:
    try:
        j = json.loads(data)
        path = j['path']
        name = j['name']
    except:
        return {}
    full_path = path.strip('/') + '/' + name
    r = requests.post(settings.ONEDRIVE_BASE_URL + 'drive/root:/' + full_path + ':/createUploadSession',
                      headers={'Authorization': 'bearer ' + od})
    return {'url': r.json()['uploadUrl']}


def create_folder(od: str, path: str, name: str) -> dict:
    if path == '':
        path = 'drive/root/children'
    else:
        path = 'drive/root:' + path + ':/children'
    r = requests.post(settings.ONEDRIVE_BASE_URL + path,
                      json={'name': name, 'folder': {}},
                      headers={'Authorization': 'bearer ' + od})
    return {'id': r.json()['id']}
