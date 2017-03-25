from urllib.parse import urlencode

import requests
from django.conf import settings
from django.contrib import messages
from django.http import *

from .models import *


def add_storage_account(request, next_url, cloud):
    if 'error' in request.GET:
        error_message = 'An error occurred (%s)' % request.GET['error']
        if 'error_description' in request.GET:
            error_message += ': %s' % (request.GET['error_description'])
        messages.error(request, error_message + "\r\n")
        return HttpResponseRedirect(next_url)
    elif 'code' in request.GET:
        r = requests.post('https://api.dropboxapi.com/oauth2/token',
                          data={'code': request.GET['code'], 'grant_type': 'authorization_code',
                                'client_id': settings.DROPBOX_APP_KEY, 'client_secret': settings.DROPBOX_APP_SECRET,
                                'redirect_uri': settings.DROPBOX_REDIRECT_URL})
        j = r.json()
        account_id = j['account_id']
        access_token = j['access_token']
        r = requests.post('https://api.dropboxapi.com/2/users/get_account', json={'account_id': account_id},
                          headers={'Authorization': 'Bearer ' + access_token})
        j = r.json()
        full_name = j['name']['display_name']
        short_name = j['name']['abbreviated_name']
        email = j['email']
        if StorageAccount.objects.all().filter(identifier=account_id).exists():
            messages.warning(request, 'This Dropbox space is already linked')
        else:
            sa = StorageAccount(user=request.user, cloud=cloud, identifier=account_id, status=1,
                                credentials=access_token, user_full_name=full_name,
                                user_short_name=short_name, email=email)
            sa.save()
            messages.success(request, 'A new Dropbox space is now linked to your account')
        return HttpResponseRedirect(next_url)
    else:
        url = 'https://www.dropbox.com/oauth2/authorize'
        params = urlencode({'response_type': 'code', 'client_id': settings.DROPBOX_APP_KEY,
                            'redirect_uri': settings.DROPBOX_REDIRECT_URL, 'require_role': 'personal'})
        return HttpResponseRedirect(url + '?' + params)


def get_client(acc: StorageAccount) -> str:
    return acc.credentials


def get_space(db: str) -> dict:
    r = requests.post('https://api.dropboxapi.com/2/users/get_space_usage',
                      headers={'Authorization': 'Bearer ' + db})
    j = r.json()
    used = j['used']
    total = j['allocation']['allocated']
    return {'used': used, 'total': total}


def get_file_list(db: str, path: str) -> list:
    ret = []
    path = path.rstrip('/')
    r = requests.post('https://api.dropboxapi.com/2/files/list_folder',
                      json={'path': path},
                      headers={'Authorization': 'Bearer ' + db})
    j = r.json()
    try:
        for f in j['entries']:
            try:
                if f['.tag'] == 'file':
                    ret.append({'name': f['name'], 'id': f['path_lower'], 'size': f['size'],
                                'time': f['client_modified'], 'is_folder': False})
                elif f['.tag'] == 'folder':
                    ret.append({'name': f['name'], 'id': f['path_lower'], 'is_folder': True})
            except:
                pass
    except:
        pass
    return ret


def get_down_link(db: str, fid: str) -> str:
    r = requests.post('https://api.dropboxapi.com/2/files/get_temporary_link',
                      json={'path': fid},
                      headers={'Authorization': 'Bearer ' + db})
    j = r.json()
    return j['link']


def get_upload_creds(db: str, data: str) -> dict:
    return {'token': db}


def create_folder(db: str, path: str, name: str) -> dict:
    r = requests.post('https://api.dropboxapi.com/2/files/create_folder',
                      json={'path': path + name},
                      headers={'Authorization': 'Bearer ' + db})
    j = r.json()
    if 'error' in j and 'path' in j['error'] and 'conflict' in j['error']['path']:
        return {'id': ''}
    return {'id': j['id']}
