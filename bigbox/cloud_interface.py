# This file specifies what each cloud interface should implement
# This file is never really loaded

from django.core.handlers.wsgi import WSGIRequest
from django.http import *

from .models import *


class Client:
    """
    The type of client object that a cloud interface requires to perform actions. If cloud SDK is used, for example,
    this might be a "complete" client object. Otherwise, we might only need a valid access token, and this class can
    even be str.
    """
    pass


# General note: functions here need not handle *unexpected* exceptions explicitly, because the caller will always wrap
# them in a try block. However, if the cloud interface has nontrivial handlers to some exceptions, they should still
# attempt to do so.

def add_storage_account(request: WSGIRequest, next_url: str, cloud: CloudInterface) -> HttpResponse:
    """
    When user wants to authorize (link) a new cloud account, this function will be called on the corresponding cloud
    interface. OAuth involves multiple steps: init and redirect, callback, redeem token; so the implement should decide
    what to do from the request object.
    
    :param request: the WSGI request object
    :param next_url: if CI has nothing more to do, where to redirect the user
    :param cloud: the CloudInterface object required when adding a storage account
    :return: whatever the CI wants to send to the user
    """
    pass


def get_client(acc: StorageAccount) -> Client:
    """
    Returns a valid Client object for the controller to call other functions with. Since a Client will only be used for
    one request (i.e. the controller won't persist Client), we don't need to always refresh tokens unless it's expired
    or only a few seconds away.
    
    :param acc: the storage account that stores relevant information
    :return: a Client object with which this CI can perform actions
    """
    pass


def get_space(c: Client) -> dict:
    """
    Returns the used and total space of this cloud account. If the limit is undefined, use None.
    
    :param c: the Client object just acquired from get_client
    :return: {'used': used_space_in_bytes, 'total': total_space_in_bytes}
    """
    pass


def get_file_list(c: Client, path: str) -> list:
    """
    Return the list of all files and folders under a given path.
    
    :param c: the Client object just acquired from get_client
    :param path: the desired path in normalized format
    :return: a list of files, each represented by a dict with 'name': str, 'id': str, 'is_folder': bool;
    when 'is_folder' == False, there will be 'size': int, 'time': datetime
    """
    pass


def get_down_link(c: Client, fid: str) -> str:
    """
    Given a file id (obtained from get_file_list), return a download link to it.
    
    :param c: the Client object just acquired from get_client
    :param fid: the desired file id
    :return: a download link
    """
    pass


def get_upload_creds(c: Client, data: str) -> dict:
    """
    For a given storage account, return the necessary credentials as a cloud interface thinks necessary given
    provided data.
    
    :param c: the Client object just acquired from get_client
    :param data: any data the cloud interface's JS want to send to the CI python file
    :return: an object of whatever the cloud interface wants to hand over to its javascript
    """
    pass


def create_folder(c: Client, path: str, name: str) -> dict:
    """
    For a given storage account, create a folder 'name' under 'path'.
    
    :param c: the Client object just acquired from get_client
    :param path: the path to the new folder, can either include the new folder's name (and name='') or not
    :param name: the name of the new folder, or '' if already in path
    :return: {'id': id_of_new_folder}
    """
    pass
