from django.http import *
from django.conf import settings
from django.contrib import messages
from .models import *
import onedrivesdk
import asyncio
import requests


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
            refresh_token = client.auth_provider._session.refresh_token
            expires_at = client.auth_provider._session._expires_at
            id = get_user_info(access_token)['id']
        except:
            messages.error(request, 'An error occurred')
        else:
            if StorageAccount.objects.all().filter(user=request.user).filter(identifier=id).exists():
                messages.warning(request, 'This space is already linked to your account')
            else:
                sa = StorageAccount(user=request.user, cloud=cloud, identifier=id, status=1,
                                    refresh_token=refresh_token, access_token=access_token,
                                    access_token_expire=datetime.fromtimestamp(int(expires_at)))
                sa.save()
                messages.success(request, 'A new OneDrive space is now linked to your account')
        return HttpResponseRedirect(next_url)
    else:
        auth_url = client.auth_provider.get_auth_url(settings.ONEDRIVE_REDIRECT_URL)
        return HttpResponseRedirect(auth_url)


def get_user_info(access_token):
    r = requests.get("https://apis.live.net/v5.0/me", params={'access_token': access_token})
    return r.json()

