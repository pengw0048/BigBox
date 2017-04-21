import importlib
import json
import uuid
from concurrent.futures.thread import ThreadPoolExecutor

import requests
from concurrent.futures import as_completed
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import default_token_generator
from django.core.handlers.wsgi import WSGIRequest
from django.core.mail import send_mail
from django.core.urlresolvers import reverse
from django.db import transaction
from django.http import *
from django.shortcuts import render, get_object_or_404
from typing import *

from .forms import *
from .models import *


# user account related operations

def validate_captcha(request: WSGIRequest) -> bool:
    """
    A helper function that validates if the given request passes recaptcha validation.
    
    :param request: the wsgi request object
    :return: whether valid or not
    """
    if 'g-recaptcha-response' not in request.POST:
        return False
    recaptcha_response = request.POST.get('g-recaptcha-response')
    url = 'https://www.google.com/recaptcha/api/siteverify'
    values = {
        'secret': settings.GOOGLE_RECAPTCHA_SECRET_KEY,
        'response': recaptcha_response
    }
    try:
        result = requests.post(url, data=values).json()
        if not result['success']:
            raise Exception()
        return True
    except:
        return False


def login(request: WSGIRequest) -> HttpResponse:
    """
    Renders the login view or log the user in.
    
    :param request: the wsgi request object
    :return: rendered page from login.html, or redirection to root view if validated
    """
    if request.user.is_authenticated:
        return HttpResponseRedirect(reverse('list', args=['/']))
    elif request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            if validate_captcha(request):
                user = authenticate(username=form.cleaned_data['username'], password=form.cleaned_data['password'])
                if user is None:
                    messages.error(request, 'Please check your username and password.')
                else:
                    auth_login(request, user)
                    if request.GET.get('next', None):
                        return HttpResponseRedirect(request.GET['next'])
                    else:
                        messages.success(request, 'Successfully logged in. Welcome to Big Box!')
                        return HttpResponseRedirect(reverse('list', args=['/']))
            else:
                messages.error(request, 'Invalid reCAPTCHA. Please try again.')
    else:
        form = LoginForm()
    return render(request, 'login.html', {'form': form})


@transaction.atomic
def register(request: WSGIRequest) -> HttpResponse:
    """
    Renders the registration view, or validate input and send confirmation email on form submit.
    
    :param request: the wsgi request object
    :return: rendered page from register.html, or redirection to login when email is sent
    """
    if request.user.is_authenticated:
        return HttpResponseRedirect(reverse('list', args=['/']))
    elif request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            if User.objects.filter(username=form.cleaned_data['username']).exists():
                messages.error(request, "There's already a user with this username. Try another one?")
            else:
                if validate_captcha(request):
                    user = User.objects.create_user(form.cleaned_data['username'], form.cleaned_data['email'],
                                                    form.cleaned_data['password'],
                                                    first_name=form.cleaned_data['first_name'],
                                                    last_name=form.cleaned_data['last_name'], is_active=False)
                    user.save()
                    token = default_token_generator.make_token(user)
                    email_body = """
    Welcome to Big Box. Please click the link below to verify
    your email address and complete the registration of your account:
      http://%s%s
    """ % (request.get_host(), reverse('confirm', args=[user.username, token]))
                    send_mail(subject="Verify your email address", message=email_body,
                              from_email=settings.EMAIL_ADDRESS, recipient_list=[user.email])
                    messages.info(request, 'Please check your inbox and activate your account')
                    return HttpResponseRedirect(reverse('login'))
                else:
                    messages.error(request, 'Invalid reCAPTCHA. Please try again.')
    else:
        form = RegisterForm()
    return render(request, 'register.html', {'form': form})


@transaction.atomic
def confirm(request: WSGIRequest, username: str, token: str) -> HttpResponse:
    """
    The view which user visits when receiving the link in the confirmation email.
    
    :param request: the wsgi request object
    :param username: the username to confirm
    :param token: the confirmation token
    :return: if valid, redirection to home view
    """
    user = get_object_or_404(User, username=username)
    if not default_token_generator.check_token(user, token):
        return HttpResponseNotFound('Link is invalid')
    user.is_active = True
    user.save()
    auth_login(request, user)
    messages.success(request, 'Your account has been created. Welcome to Big Box!')
    return HttpResponseRedirect(reverse('list', args=['/']))


# file list related operations

def normalize_path(path: str) -> str:
    """
    A helper function that transforms path into the unified format our system adopts:
    The path to a folder has slashes on both sides;
    The path to a file has a slash on the right but no slash on the left;
    The root folder is '/'.
    
    :param path: the path to be transformed
    :return: a normalized path
    """
    if not path:
        return '/'
    if not path.startswith('/'):
        path = '/' + path
    if not path.endswith('/'):
        path += '/'
    return path


@login_required
def file_list_view(request: WSGIRequest, path: str) -> HttpResponse:
    """
    Renders the file list HTML with navbar, upload buttons, list of storage accounts (with color legends), and empty
    breadcrumb folder list and file list, which will be filled in by AJAX at client side.
    
    :param request: the wsgi request object
    :param path: the path of folder to display at beginning; later AJAX will load other folders
    :return: a rendered HTML from home.html
    """
    path = normalize_path(path)
    user = request.user
    acc = StorageAccount.objects.filter(user=user)
    num = '['
    cloudclass = '['
    for sub_acc in acc:
        num = num + str(sub_acc.pk) + ','
        cloudclass = cloudclass + '"' + str(sub_acc.cloud.class_name)  + '"' + ','
    num = num[:-1] + ']'
    cloudclass = cloudclass[:-1] + ']'
    return render(request, 'home.html', {'user': user, 'acc': acc, 'path': path, 'num': num, 'cloudclass': cloudclass})


def get_file_list(c: StorageAccount, path: str) -> List[dict]:
    """
    A helper function that gets the contents under given path (if it is a folder) on cloud account c.
    
    :param c: the storage account to use
    :param path: path to the folder to look at
    :return: a list of files, each represented by a dict with 'name': str, 'id': str, 'is_folder': bool;
    when 'is_folder' == False, there will be 'size': int, 'time': datetime; returns [] on exceptions
    """
    path = normalize_path(path)
    try:
        mod = importlib.import_module('bigbox.' + c.cloud.class_name)
        client = getattr(mod, "get_client")(c)
        fs = getattr(mod, "get_file_list")(client, path)
    except Exception as e:
        print(str(e))
        return []
    else:
        return fs


@login_required
def get_files(request: WSGIRequest, path: str) -> JsonResponse:
    """
    Returns a json with all files and folders under a given path on all cloud accounts of this user
    
    :param request: the wsgi request object
    :param path: path to the folder to look at
    :return: a response with the json of an array of files; in addition to all properties returned by get_file_list,
    an entry also has 'colors': List[str] (representing which cloud it is in), 'acc': int (the pk of associated account)
    """
    path = normalize_path(path)
    user = request.user
    if 'pks' in request.GET:
        acc = []
        for pk in request.GET.getlist('pks'):
            acc.extend(StorageAccount.objects.filter(pk=pk, user=user))
    else:
        acc = StorageAccount.objects.filter(user=user)
    files = []
    folders = {}
    try:
        with ThreadPoolExecutor() as executor:
            future_to_files = {executor.submit(get_file_list, c, path): c for c in acc}
            for future in as_completed(future_to_files):
                c = future_to_files[future]
                fs = future.result()
                for f in fs:
                    f['colors'] = [c.color]
                    if f['is_folder']:
                        if f['name'] in folders:
                            folders[f['name']]['id'].append({c.pk: f['id']})
                            folders[f['name']]['colors'].append(c.color)
                        else:
                            f['id'] = [{c.pk: f['id']}]
                            folders[f['name']] = f
                    else:
                        f['acc'] = c.pk
                        files.append(f)
    except Exception as e:
        print(str(e))
        return JsonResponse({'error': str(e)})
    else:
        files.extend(list(folders.values()))
        return JsonResponse(files, safe=False)


@login_required
def get_download_link(request: WSGIRequest) -> HttpResponse:
    """
    For a given pk of storage account and a file id, return (redirection to) its temporary download link.
    Expects 'pk' and 'id' in request.GET.
    
    :param request: the wsgi request object
    :return: an HTTP redirection to the download link
    """
    if not 'id' in request.GET and not 'path' in request.GET:
        return HttpResponseBadRequest('missing fields')
    acc = get_object_or_404(StorageAccount, pk=request.GET.get('pk', ''), user=request.user)
    try:
        mod = importlib.import_module('bigbox.' + acc.cloud.class_name)
        client = getattr(mod, "get_client")(acc)
        link = getattr(mod, "get_down_link")(client, request.GET.get('id', None), request.GET.get('path', None))
    except Exception as e:
        print("exception")
        print(str(e))
        return HttpResponseBadRequest(str(e))
    else:
        if not link:
            return HttpResponseNotFound()
        elif 'astext' in request.GET:
            return HttpResponse(link)
        else:
            return HttpResponseRedirect(link)

@login_required
def get_big_file(request: WSGIRequest) -> JsonResponse:
    """
    for a given file name, download each chunk from all the clouds, call the "cat" request in linux,
    store them in static folder
    after finishing the download, send notification to front end.
    :return:
    """
    user = request.user
    acc = StorageAccount.objects.filter(user=user)
    path = request.GET.get('path')
    file_name = str(uuid.uuid4())
    file_folder = "/Users/Judy/Desktop/web project/BigBox/bigbox/static/bigfile/"
    file_path = "/Users/Judy/Desktop/web project/BigBox/bigbox/static/bigfile/" + file_name
    print(file_path)
    record = 1;
    for account in acc:
        try:
            mod = importlib.import_module('bigbox.' + account.cloud.class_name)
            client = getattr(mod, "get_client")(account)
            link = getattr(mod, "get_down_link")(client, None, path)
            # send request to different accounts
            r = requests.get(link)
            print(r)

            with open(file_path + str(record), "wb") as target:
                target.write(r.text)
                record += 1

            with open(file_path, "wb") as target:
                target.write(r.text)
            # call linux function "cat" to connect to different file
        except Exception as e:
            print(str(e))
            return HttpResponseBadRequest(str(e))
    return JsonResponse({'link': file_name})


@login_required
def get_upload_creds(request: WSGIRequest) -> JsonResponse:
    """
    For a given pk of storage account, return the necessary credentials as a cloud interface thinks necessary given
    provided data. Expects 'pk' and 'data' (optional) in request.GET.
    
    :param request: the wsgi request object
    :return: a response with the json of whatever the cloud interface wants to hand over to its javascript
    """
    acc = get_object_or_404(StorageAccount, pk=request.GET.get('pk', ''), user=request.user)
    data = request.GET.get('data', None)
    try:
        mod = importlib.import_module('bigbox.' + acc.cloud.class_name)
        client = getattr(mod, "get_client")(acc)
        creds = getattr(mod, "get_upload_creds")(client, data)
    except Exception as e:
        print(str(e))
        return JsonResponse({'error': str(e)})
    else:
        print(creds)
        return JsonResponse(creds)


@login_required
def create_folder(request: WSGIRequest) -> JsonResponse:
    """
    For a given pk of storage account, create a folder 'name' under 'path'. Expects 'pk' (can be multiple), 'path',
    'name' (optional) in request.POST.
    
    :param request: the wsgi request object
    :return: a response with the json of a dict of the ids of the newly created folder with pks as keys
    """
    if 'path' not in request.POST or 'name' not in request.POST:
        return JsonResponse({'error': 'missing fields'})
    path = normalize_path(request.POST['path'])
    accs = []
    list = request.POST.getlist('pk')
    for pk in request.POST.getlist('pk'):
        acc = get_object_or_404(StorageAccount, pk=pk, user=request.user)
        accs.append(acc)
    rets = {}
    for acc in accs:
        try:
            mod = importlib.import_module('bigbox.' + acc.cloud.class_name)
            client = getattr(mod, "get_client")(acc)
            ret = getattr(mod, "create_folder")(client, path, request.POST['name'])
        except Exception as e:
            print(str(e))
            rets[acc.pk] = {'error': str(e)}
        else:
            rets[acc.pk] = ret
    return JsonResponse(rets)


@login_required
def delete(request: WSGIRequest) -> JsonResponse:
    if 'data' not in request.POST:
        return JsonResponse({'error': 'missing fields'})
    try:
        j = json.loads(request.POST['data'])
        ids = {}
        for item in j:
            for key, value in item.items():
                if key in ids:
                    ids[key].append(value)
                else:
                    ids[key] = [value]
        rets = {}
        for key, value in ids.items():
            acc = get_object_or_404(StorageAccount, pk=key, user=request.user)
            mod = importlib.import_module('bigbox.' + acc.cloud.class_name)
            client = getattr(mod, "get_client")(acc)
            ret = getattr(mod, "delete")(client, value)
            rets[key] = ret
    except Exception as e:
        print(str(e))
        return JsonResponse({'error': str(e)})
    return JsonResponse(rets)


@login_required
def rename(request: WSGIRequest) -> JsonResponse:
    if 'data' not in request.POST or 'to' not in request.POST:
        return JsonResponse({'error': 'missing fields'})
    try:
        to = request.POST['to']
        j = json.loads(request.POST['data'])
        ids = {}
        for item in j:
            for key, value in item.items():
                if key in ids:
                    ids[key].append(value)
                else:
                    ids[key] = [value]
        rets = {}
        for key, value in ids.items():
            acc = get_object_or_404(StorageAccount, pk=key, user=request.user)
            mod = importlib.import_module('bigbox.' + acc.cloud.class_name)
            client = getattr(mod, "get_client")(acc)
            ret = getattr(mod, "rename")(client, value, to)
            rets[key] = ret
    except Exception as e:
        print(str(e))
        return JsonResponse({'error': str(e)})
    return JsonResponse(rets)

# storage account related operations

@login_required
def storage_accounts(request: WSGIRequest) -> HttpResponse:
    """
    Renders the HTML page showing user's linked accounts and give user the option to add one.
    
    :param request: the wsgi request object
    :return: a rendered HTML from clouds.html
    """
    user = request.user
    clouds = CloudInterface.objects.all()
    account_info = []
    for acc in StorageAccount.objects.filter(user=user):
        try:
            mod = importlib.import_module('bigbox.' + acc.cloud.class_name)
            client = getattr(mod, "get_client")(acc)
            acc.space = getattr(mod, "get_space")(client)
        except Exception as e:
            print(str(e))
        else:
            acc.space['percent'] = (float(acc.space['used']) * 100.0 / float(acc.space['total']) if acc.space['total']
                                    else 0)
            account_info.append(acc)
    return render(request, 'clouds.html', {'accounts': account_info, 'clouds': clouds})


@login_required
def add_storage_account(request: WSGIRequest, cloud: str) -> HttpResponse:
    """
    Link a cloud account to the user. The OAuth flow involves multiple steps, and this view will forward the whole
    request to the handler function in the corresponding cloud interface. For example, on the first call, there will
    be no query parameters, so the cloud interface will know to initialize the flow. CI can set OAuth callback to this
    view, and will get code or error etc from the query parameters.
    
    :param request: the wsgi request object
    :param cloud: `name` field of the chosen CloudInterface
    :return: whatever the cloud interface wants to return to user
    """
    cloud = get_object_or_404(CloudInterface, name=cloud)
    try:
        mod = importlib.import_module('bigbox.' + cloud.class_name)
        ret = getattr(mod, "add_storage_account")(request, reverse('clouds'), cloud)
        return ret
    except Exception as e:
        print(str(e))
        messages.error(request, "Error: " + str(e))
        return HttpResponseRedirect(reverse('clouds'))


@transaction.atomic
@login_required
def rename_storage_account(request: WSGIRequest) -> JsonResponse:
    """
    Change the nickname of a storage account. Expects 'pk' and 'value' in request.POST.
    
    :param request: the wsgi request object
    :return: a json with error or status ok to satisfy the requirements of the javascript plugin
    """
    if 'value' not in request.POST:
        return JsonResponse({'status': 'error', 'msg': 'missing fields'})
    acc = get_object_or_404(StorageAccount, pk=request.POST.get('pk', ''), user=request.user)
    acc.display_name = request.POST['value']
    acc.save()
    return JsonResponse({'status': 'ok'})


@transaction.atomic
@login_required
def color_storage_account(request: WSGIRequest) -> JsonResponse:
    """
    Change the color of a storage account. Expects 'pk' and 'value' in request.POST.
    
    :param request: the wsgi request object
    :return: a json with error or status ok to satisfy the requirements of the javascript plugin
    """
    if 'value' not in request.POST:
        return JsonResponse({'status': 'error', 'msg': 'missing fields'})
    acc = get_object_or_404(StorageAccount, pk=request.POST.get('pk', ''), user=request.user)
    acc.color = request.POST['value']
    acc.save()
    return JsonResponse({'status': 'ok'})
