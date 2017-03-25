import importlib
from concurrent.futures.thread import ThreadPoolExecutor
from concurrent.futures import as_completed
from urllib.parse import quote
from typing import *

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.core.urlresolvers import reverse
from django.db import transaction
from django.http import *
from django.core.handlers.wsgi import WSGIRequest
from django.shortcuts import render, get_object_or_404

from .forms import *
from .models import *


# user account related operations

def login(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect(reverse('list', args=['/']))
    elif request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
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
        form = LoginForm()
    return render(request, 'login.html', {'form': form})


def register(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect(reverse('list', args=['/']))
    elif request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            if User.objects.filter(username=form.cleaned_data['username']).exists():
                messages.error(request, "There's already a user with this username. Try another one?")
            else:
                with transaction.atomic():
                    user = User.objects.create_user(form.cleaned_data['username'],
                                                    password=form.cleaned_data['password'])
                    user.first_name = form.cleaned_data['first_name']
                    user.last_name = form.cleaned_data['last_name']
                    user.email = form.cleaned_data['email']
                    user.is_active = False
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
        form = RegisterForm()
    return render(request, 'register.html', {'form': form})


@transaction.atomic
def confirm(request, username, token):
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
    return render(request, 'home.html', {'user': user, 'acc': acc,
                                         'path': path if path[-1] == '/' else path + '/'})


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
                            folders[f['name']]['colors'].append(c.color)
                        else:
                            folders[f['name']] = f
                    else:
                        f['acc'] = c.pk
                        files.append(f)
    except Exception as e:
        print(str(e))
        return JsonResponse({'error': str(e)})
    else:
        files.extend(list(folders.values()))
        fl = sorted(files, key=lambda file: ('d' if file['is_folder'] else 'f') + file['name'].lower())
        return JsonResponse(fl, safe=False)


@login_required
def get_download_link(request: WSGIRequest) -> HttpResponse:
    """
    For a given pk of storage account and a file id, return (redirection to) its temporary download link.
    Expects 'pk' and 'id' in request.GET.
    
    :param request: the wsgi request object
    :return: an HTTP redirection to the download link
    """
    acc = get_object_or_404(StorageAccount, pk=request.GET.get('pk', ''), user=request.user)
    try:
        mod = importlib.import_module('bigbox.' + acc.cloud.class_name)
        client = getattr(mod, "get_client")(acc)
        link = getattr(mod, "get_down_link")(client, request.GET.get('id', ''))
    except Exception as e:
        print(str(e))
        return HttpResponseBadRequest(str(e))
    else:
        if not link:
            return HttpResponseNotFound()
        else:
            return HttpResponseRedirect(link)


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


# storage account related operations

@login_required
def storage_accounts(request):
    user = request.user
    clouds = CloudInterface.objects.all()
    account_info = []
    for acc in StorageAccount.objects.filter(user=user):
        mod = importlib.import_module('bigbox.' + acc.cloud.class_name)
        client = getattr(mod, "get_client")(acc)
        acc.space = getattr(mod, "get_space")(client)
        acc.space['percent'] = (float(acc.space['used']) * 100.0 / float(acc.space['total']) if acc.space['total']
                                else 0)
        account_info.append(acc)
    return render(request, 'clouds.html', {'accounts': account_info, 'clouds': clouds})


@login_required
def add_storage_account(request, cloud):
    cloud = get_object_or_404(CloudInterface, name=cloud)
    fun = getattr(importlib.import_module('bigbox.' + cloud.class_name), "add_storage_account")
    return fun(request, reverse('clouds'), cloud)


@transaction.atomic
@login_required
def rename_storage_account(request):
    if 'pk' not in request.POST or 'value' not in request.POST:
        return JsonResponse({'status': 'error', 'msg': 'missing fields'})
    acc = get_object_or_404(StorageAccount, pk=request.POST['pk'])
    if acc.user != request.user:
        return JsonResponse({'status': 'error', 'msg': 'not your account'})
    acc.display_name = request.POST['value']
    acc.save()
    return JsonResponse({'status': 'ok'})


@transaction.atomic
@login_required
def color_storage_account(request):
    if 'pk' not in request.POST or 'value' not in request.POST:
        return JsonResponse({'status': 'error', 'msg': 'missing fields'})
    acc = get_object_or_404(StorageAccount, pk=request.POST['pk'])
    if acc.user != request.user:
        return JsonResponse({'status': 'error', 'msg': 'not your account'})
    acc.color = request.POST['value']
    acc.save()
    return JsonResponse({'status': 'ok'})
