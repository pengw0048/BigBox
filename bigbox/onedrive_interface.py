from django.http import *
from django.conf import settings
from django.contrib import messages
from .models import *
import onedrivesdk
import asyncio
import requests
from onedrivesdk.session import Session
import json
from time import time
from dateutil import parser


def add_storage_account(request, next_url, cloud):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    client = onedrivesdk.get_default_client(settings.ONEDRIVE_APP_KEY, settings.ONEDRIVE_SCOPE.split(","))
    if 'error' in request.GET:
        error_message = 'An error occurred'
        if 'error_description' in request.GET:
            error_message += ' (%s): %s' % (request.GET['error'], request.GET['error_description'])
        messages.error(request, error_message)
        return HttpResponseRedirect(next_url)
    elif 'code' in request.GET:
        try:
            client.auth_provider.authenticate(request.GET['code'], settings.ONEDRIVE_REDIRECT_URL,
                                              settings.ONEDRIVE_APP_SECRET)
            access_token = client.auth_provider._session.access_token
            info = get_user_info(access_token)
            id = info['id']
            full_name = info['displayName']
            short_name = info['givenName']
            email = info['userPrincipalName']
        except Exception as e:
            messages.error(request, 'An error occurred: ' + str(e))
        else:
            if StorageAccount.objects.all().filter(identifier=id).exists():
                messages.warning(request, 'This OneDrive space is already linked')
            else:
                sa = StorageAccount(user=request.user, cloud=cloud, identifier=id, status=1,
                                    credentials=MySession.save_session(client.auth_provider._session),
                                    user_full_name=full_name, user_short_name=short_name, email=email)
                sa.save()
                messages.success(request, 'A new OneDrive space is now linked to your account')
        return HttpResponseRedirect(next_url)
    else:
        auth_url = client.auth_provider.get_auth_url(settings.ONEDRIVE_REDIRECT_URL)
        return HttpResponseRedirect(auth_url)


def get_user_info(access_token):
    r = requests.get(settings.ONEDRIVE_BASE_URL + "users/me", headers={'Authorization': 'Bearer ' + access_token})
    return r.json()


def get_client(acc: StorageAccount):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    http_provider = onedrivesdk.HttpProvider()
    auth_provider = onedrivesdk.AuthProvider(http_provider, settings.ONEDRIVE_APP_KEY,
                                             settings.ONEDRIVE_SCOPE.split(","), session_type=MySession)
    auth_provider.load_session(cred=acc.credentials)
    auth_provider.refresh_token()
    client = onedrivesdk.OneDriveClient(settings.ONEDRIVE_BASE_URL, auth_provider, http_provider)
    acc.credentials = MySession.save_session(client.auth_provider._session)
    acc.save()
    return client


def get_space(od: onedrivesdk.OneDriveClient) -> dict:
    r = requests.get(settings.ONEDRIVE_BASE_URL + "me/drive",
                     headers={'Authorization': 'bearer ' + od.auth_provider._session.access_token}).json()
    used = r['quota']['used']
    total = r['quota']['total']
    return {'used': used, 'total': total}


def get_file_list(od: onedrivesdk.OneDriveClient, path: str) -> list:
    ret = []
    if path == '/':
        path = "drive/root/children"
    else:
        path = "drive/root:" + path + ":/children"
    try:
        fs = requests.get(settings.ONEDRIVE_BASE_URL + path,
                          headers={'Authorization': 'bearer ' + od.auth_provider._session.access_token}).json()
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
    return ret


def get_down_link(od: onedrivesdk.OneDriveClient, fid: str) -> str:
    r = requests.get(settings.ONEDRIVE_BASE_URL + "drive/items/" + fid + '/content',
                     headers={'Authorization': 'bearer ' + od.auth_provider._session.access_token})
    if r.status_code < 300 or r.status_code >= 400:
        r.raise_for_status()
    if r.url:
        return r.url
    else:
        raise Exception('File not found')


class MySession(Session):
    def save_session(self, **save_session_kwargs):
        data = {'token_type': self.token_type, 'scope': ' '.join(self.scope), 'access_token': self.access_token,
                'client_id': self.client_id, 'auth_server_url': self.auth_server_url,
                'redirect_uri': self.redirect_uri, 'refresh_token': self.refresh_token,
                'client_secret': self.client_secret, 'expires_at': self._expires_at}
        return json.dumps(data)

    def load_session(**load_session_kwargs):
        data = json.loads(load_session_kwargs['cred'])
        session = Session(data['token_type'], data['expires_at'] - time(), data['scope'], data['access_token'],
                          data['client_id'], data['auth_server_url'], data['redirect_uri'], data['refresh_token'],
                          data['client_secret'])
        return session
