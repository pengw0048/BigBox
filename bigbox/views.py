from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import *
from django.core.urlresolvers import reverse
from .forms import *
from django.contrib.auth import authenticate, login as auth_login
from django.contrib import messages
from django.contrib.auth.models import User
from django.db import transaction
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.conf import settings
from .models import *
import importlib
from urllib.parse import quote


def login(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect(reverse('home'))
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
                    return HttpResponseRedirect(reverse('home'))
    else:
        form = LoginForm()
    return render(request, 'login.html', {'form': form})


def register(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect(reverse('home'))
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


@login_required
def home(request):
    return listview(request, '/')


@login_required
def listview(request, path):
    dir_list = []
    dir_base = ''
    if len(path.strip('/')) > 0:
        for dir in path.strip('/').split('/'):
            dir_base += '/' + dir
            dir_list.append({'name': dir, 'url': dir_base})
    user = request.user
    accs = StorageAccount.objects.filter(user=user)
    files = []
    folders = {}
    for c in accs:
        module = importlib.import_module('bigbox.'+c.cloud.class_name)
        client = getattr(module, "get_client")(c)
        fs, did = getattr(module, "get_file_list")(client, path)
        c.did = did
        for f in fs:
            f['clouds'] = [c]
            if f['is_folder']:
                if f['name'] in folders:
                    folders[f['name']]['clouds'].append(c)
                else:
                    folders[f['name']] = f
            else:
                f['acc'] = c
                f['id'] = quote(f['id'])
                files.append(f)
    files.extend(list(folders.values()))
    fl = sorted(files, key=lambda f: ('d' if f['is_folder'] else 'f') + f['name'].lower())
    return render(request, 'home.html', {'user': user, 'acc': accs, 'files': fl, 'dir_list': dir_list,
                                         'path': path if path[-1] == '/' else path + '/'})


@transaction.atomic
def confirm(request, username, token):
    user = get_object_or_404(User, username=username)
    if not default_token_generator.check_token(user, token):
        return HttpResponseNotFound('Link is invalid')
    user.is_active = True
    user.save()
    auth_login(request, user)
    messages.success(request, 'Your account has been created. Welcome to Big Box!')
    return HttpResponseRedirect(reverse('home'))


@login_required
def storage_accounts(request):
    user = request.user
    clouds = CloudInterface.objects.all()
    account_info = []
    for acc in StorageAccount.objects.filter(user=user):
        module = importlib.import_module('bigbox.'+acc.cloud.class_name)
        client = getattr(module, "get_client")(acc)
        acc.space = getattr(module, "get_space")(client)
        acc.space['percent'] = (float(acc.space['used']) * 100.0 / float(acc.space['total']) if acc.space['total']
                                else 0)
        account_info.append(acc)
    return render(request, 'clouds.html', {'accounts': account_info, 'clouds': clouds})


@login_required
def add_storage_account(request, cloud):
    cloud = get_object_or_404(CloudInterface, name=cloud)
    fun = getattr(importlib.import_module('bigbox.'+cloud.class_name), "add_storage_account")
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


@login_required
def get_download_link(request):
    if 'pk' not in request.GET or 'id' not in request.GET:
        return HttpResponseBadRequest('missing fields')
    acc = get_object_or_404(StorageAccount, pk=request.GET['pk'])
    if acc.user != request.user:
        return HttpResponseForbidden('not your account')
    module = importlib.import_module('bigbox.'+acc.cloud.class_name)
    client = getattr(module, "get_client")(acc)
    try:
        link = getattr(module, "get_down_link")(client, request.GET['id'])
        return HttpResponseRedirect(link)
    except Exception as e:
        return HttpResponseBadRequest(str(e))


@login_required
def get_upload_creds(request):
    if 'pk' not in request.GET:
        return JsonResponse({'status': 'error', 'msg': 'missing fields'})
    acc = get_object_or_404(StorageAccount, pk=request.GET['pk'])
    if acc.user != request.user:
        return JsonResponse({'status': 'error', 'msg': 'not your account'})
    data = request.GET.get('data', None)
    module = importlib.import_module('bigbox.'+acc.cloud.class_name)
    client = getattr(module, "get_client")(acc)
    creds = getattr(module, "get_upload_creds")(client, data)
    return JsonResponse(creds)


@login_required
def create_folder(request):
    if 'pk' not in request.POST or 'path' not in request.POST or 'name' not in request.POST:
        return JsonResponse({'status': 'error', 'msg': 'missing fields'})
    accs = []
    for pk in request.POST.getlist('pk'):
        acc = get_object_or_404(StorageAccount, pk=pk)
        if acc.user != request.user:
            return JsonResponse({'status': 'error', 'msg': 'not your account'})
        accs.append(acc)
    rets = {}
    for acc in accs:
        module = importlib.import_module('bigbox.'+acc.cloud.class_name)
        client = getattr(module, "get_client")(acc)
        ret = getattr(module, "create_folder")(client, request.POST['path'].rstrip('/'), request.POST['name'])
        rets[acc.pk] = ret
    return JsonResponse(rets)
