from django.http import *
from django.conf import settings
from django.contrib import messages
from oauth2client import client
from apiclient.discovery import build, Resource
from .models import *
import httplib2


def add_storage_account(request, next_url, cloud):
    flow = client.OAuth2WebServerFlow(settings.GDRIVE_APP_KEY, settings.GDRIVE_APP_SECRET, settings.GDRIVE_SCOPE,
                                      settings.GDRIVE_REDIRECT_URL)
    flow.params['access_type'] = 'offline'
    if 'error' in request.GET:
        error_message = 'An error occurred: ' + request.GET['error']
        messages.error(request, error_message)
        return HttpResponseRedirect(next_url)
    elif 'code' in request.GET:
        try:
            credentials = flow.step2_exchange(request.GET['code'])
            id = credentials.id_token['email']
        except:
            messages.error(request, 'An error occurred')
        else:
            if StorageAccount.objects.all().filter(identifier=id).exists():
                messages.warning(request, 'This Google Drive space is already linked')
            else:
                sa = StorageAccount(user=request.user, cloud=cloud, identifier=id, status=1,
                                    refresh_token=credentials.refresh_token, access_token=credentials.access_token,
                                    access_token_expire=credentials.token_expiry, additional_data=credentials.to_json())
                sa.save()
                messages.success(request, 'A new Google Drive space is now linked to your account')
        return HttpResponseRedirect(next_url)
    else:
        auth_uri = flow.step1_get_authorize_url()
        return HttpResponseRedirect(auth_uri)


def get_client(acc: StorageAccount) -> Resource:
    cred = client.OAuth2Credentials.from_json(acc.additional_data)
    http = cred.authorize(httplib2.Http())
    drive = build('drive', 'v3', http=http)
    return drive


def get_full_name(g: Resource) -> str:
    res = g.about().get(fields='user/displayName').execute()
    return res['user']['displayName']


def get_email(g: Resource) -> str:
    res = g.about().get(fields='user/emailAddress').execute()
    return res['user']['emailAddress']


def get_space(g: Resource) -> dict:
    res = g.about().get(fields='storageQuota').execute()
    used = res['storageQuota']['usage']
    total = res['storageQuota']['limit']
    return {'used': used, 'total': total}
