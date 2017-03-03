"""webapps URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.10/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url
from django.contrib import admin
from bigbox import views
from django.contrib.auth.views import logout_then_login
from django.core.urlresolvers import reverse_lazy

urlpatterns = [
    url(r'^$', views.login, name='root'),
    url(r'^admin/', admin.site.urls, name='admin'),
    url(r'^login/?$', views.login, name='login'),
    url(r'^logout/?$', logout_then_login, {'login_url':reverse_lazy('login')}, name='logout'),
    url(r'^register/?$', views.register, name='register'),
    url(r'^home/?$', views.home, name='home'),
    url(r'^confirm/(?P<username>\w+)/(?P<token>[\w-]+)/?$', views.confirm, name='confirm'),
]
