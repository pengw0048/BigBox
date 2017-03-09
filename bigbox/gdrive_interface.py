from django.http import *
from django.conf import settings
from django.contrib import messages
from oauth2client import client
from apiclient.discovery import build, Resource
from .models import *
import httplib2


def add_storage_account(request, next_url, cloud):
    flow = client.OAuth2WebServerFlow(settings.GDRIVE_APP_KEY, client_secret=settings.GDRIVE_APP_SECRET,
                                      scope=settings.GDRIVE_SCOPE, redirect_uri=settings.GDRIVE_REDIRECT_URL)
    flow.params['access_type'] = 'offline'
    if 'error' in request.GET:
        error_message = 'An error occurred: ' + request.GET['error']
        messages.error(request, error_message)
        return HttpResponseRedirect(next_url)
    elif 'code' in request.GET:
        try:
            credentials = flow.step2_exchange(request.GET['code'])
            id = credentials.id_token['sub']
            http = credentials.authorize(httplib2.Http())
            drive = build('drive', 'v3', http=http)
            about = drive.about().get(fields='user').execute()
            full_name = about['user']['displayName']
            email = about['user']['emailAddress']
        except Exception as e:
            messages.error(request, 'An error occurred: ' + str(e))
        else:
            if StorageAccount.objects.all().filter(identifier=id).exists():
                messages.warning(request, 'This Google Drive space is already linked')
            else:
                sa = StorageAccount(user=request.user, cloud=cloud, identifier=id, status=1,
                                    credentials=credentials.to_json(), user_full_name=full_name, email=email)
                sa.save()
                messages.success(request, 'A new Google Drive space is now linked to your account')
        return HttpResponseRedirect(next_url)
    else:
        auth_uri = flow.step1_get_authorize_url()
        return HttpResponseRedirect(auth_uri)


def get_client(acc: StorageAccount) -> Resource:
    cred = client.OAuth2Credentials.from_json(acc.credentials)
    http = cred.authorize(httplib2.Http())
    acc.credentials = cred.to_json()
    acc.save()
    drive = build('drive', 'v3', http=http)
    return drive


def get_space(g: Resource) -> dict:
    res = g.about().get(fields='storageQuota').execute()
    used = res['storageQuota']['usage']
    total = res['storageQuota']['limit']
    return {'used': used, 'total': total}


def get_file_list(g: Resource, path: str) -> list:
    return []
