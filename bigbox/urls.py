from django.conf.urls import url
from django.contrib.auth.views import logout_then_login
from django.core.urlresolvers import reverse_lazy
from django.views.generic.base import RedirectView

from . import views

favicon_view = RedirectView.as_view(url='/static/favicon.ico', permanent=True)

urlpatterns = [
    url(r'^$', views.login, name='root'),
    url(r'^login/?$', views.login, name='login'),
    url(r'^logout/?$', logout_then_login, {'login_url': reverse_lazy('login')}, name='logout'),
    url(r'^register/?$', views.register, name='register'),
    url(r'^confirm/(?P<username>\w+)/(?P<token>[\w-]+)/?$', views.confirm, name='confirm'),
    url(r'^home(?P<path>.*)$', views.file_list_view, name='list'),
    url(r'^get-files(?P<path>.*)$', views.get_files, name='get-files'),
    url(r'^get-down/?$', views.get_download_link, name='get-download'),
    url(r'^get-up-creds/?$', views.get_upload_creds, name='get-upload-creds'),
    url(r'^create-folder/?$', views.create_folder, name='create-folder'),
    url(r'^delete/?$', views.delete, name='delete'),
    url(r'^clouds/?$', views.storage_accounts, name='clouds'),
    url(r'^clouds/add/(?P<cloud>\w+)/?$', views.add_storage_account, name='cloud-add'),
    url(r'^clouds/rename/?$', views.rename_storage_account, name='cloud-rename'),
    url(r'^clouds/color/?$', views.color_storage_account, name='cloud-color'),
    url(r'^favicon\.ico$', favicon_view),
]
