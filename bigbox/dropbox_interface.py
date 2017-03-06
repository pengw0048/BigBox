from django.http import *
from django.conf import settings
from django.contrib import messages
from dropbox.oauth import *
from dropbox.dropbox import *
from .models import *


def get_dropbox_auth_flow(web_app_session):
    return DropboxOAuth2Flow(settings.DROPBOX_APP_KEY, settings.DROPBOX_APP_SECRET, settings.DROPBOX_REDIRECT_URL,
                             web_app_session, "dropbox-auth-csrf-token")


def add_storage_account(request, next_url, cloud):
    if 'state' in request.GET:
        try:
            oauth_result = get_dropbox_auth_flow(request.session).finish(request.GET)
        except:
            error_message = 'An error occurred'
            if 'error' in request.GET and 'error_description' in request.GET:
                error_message += ' (%s): %s' % (request.GET['error'], request.GET['error_description'])
            messages.error(request, error_message)
        else:
            if StorageAccount.objects.all().filter(user=request.user).filter(identifier=oauth_result.account_id).exists():
                messages.warning(request, 'This Dropbox space is already linked to your account')
            else:
                sa = StorageAccount(user=request.user, cloud=cloud, identifier=oauth_result.account_id, status=1,
                                    access_token=oauth_result.access_token)
                sa.save()
                messages.success(request, 'A new Dropbox space is now linked to your account')
        return HttpResponseRedirect(next_url)
    else:
        url = get_dropbox_auth_flow(request.session).start()
        return HttpResponseRedirect(url)


def show_storage_account(acc):
    return {}


def get_client(acc: StorageAccount) -> Dropbox:
    return Dropbox(acc.access_token)
