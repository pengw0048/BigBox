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
            db = Dropbox(oauth_result.access_token)
            ai = db.users_get_current_account()
        except Exception as e:
            error_message = 'An error occurred'
            if 'error' in request.GET and 'error_description' in request.GET:
                error_message += ' (%s): %s' % (request.GET['error'], request.GET['error_description'])
            messages.error(request, error_message + "\r\n" + str(e))
        else:
            if StorageAccount.objects.all().filter(identifier=oauth_result.account_id).exists():
                messages.warning(request, 'This Dropbox space is already linked')
            else:
                sa = StorageAccount(user=request.user, cloud=cloud, identifier=oauth_result.account_id, status=1,
                                    credentials=oauth_result.access_token, user_full_name=ai.name.display_name,
                                    user_short_name=ai.name.abbreviated_name, email=ai.email)
                sa.save()
                messages.success(request, 'A new Dropbox space is now linked to your account')
        return HttpResponseRedirect(next_url)
    else:
        url = get_dropbox_auth_flow(request.session).start()
        return HttpResponseRedirect(url)


def get_client(acc: StorageAccount) -> Dropbox:
    return Dropbox(acc.credentials)


def get_space(db: Dropbox) -> dict:
    info = db.users_get_space_usage()
    used = info.used
    total = info.allocation.get_individual().allocated
    return {'used': used, 'total': total}


def get_file_list(db: Dropbox, path: str) -> list:
    ret = []
    try:
        for f in db.files_list_folder(path.rstrip('/')).entries:
            try:
                if hasattr(f, 'size'):
                    ret.append({'name': f.name, 'id': f.path_lower, 'size': f.size,
                                'time': f.client_modified, 'is_folder': False})
                else:
                    ret.append({'name': f.name, 'id': f.path_lower, 'is_folder': True})
            except:
                pass
    except:
        pass
    return ret


def get_down_link(db: Dropbox, fid: str) -> str:
    res = db.files_get_temporary_link(fid)
    return res.link
