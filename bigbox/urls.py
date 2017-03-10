from django.conf.urls import url
from . import views
from django.contrib.auth.views import logout_then_login
from django.core.urlresolvers import reverse_lazy

urlpatterns = [
    url(r'^$', views.login, name='root'),
    url(r'^login/?$', views.login, name='login'),
    url(r'^logout/?$', logout_then_login, {'login_url': reverse_lazy('login')}, name='logout'),
    url(r'^register/?$', views.register, name='register'),
    url(r'^home/?$', views.home, name='home'),
    url(r'^home(?P<path>/.*)$', views.listview, name='list'),
    url(r'^confirm/(?P<username>\w+)/(?P<token>[\w-]+)/?$', views.confirm, name='confirm'),
    url(r'^clouds/?$', views.storage_accounts, name='clouds'),
    url(r'^clouds/add/(?P<cloud>\w+)/?$', views.add_storage_account, name='cloud-add'),
    url(r'^clouds/rename/?$', views.rename_storage_account, name='cloud-rename'),
    url(r'^clouds/color/?$', views.color_storage_account, name='cloud-color'),
]
