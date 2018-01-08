from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin
from django.contrib.auth import views as auth_views

from welcome.views import index, health
from swift_browser.views import container, containers, create_container, delete_container

urlpatterns = [
    url(r'^$', containers, name='containers'),
    url(r'^accounts/login/$', auth_views.login, name='login'),
    url(r'^logout/$', auth_views.logout, {'next_page': '/accounts/login'}, name='logout'),
    url(r'^health$', health),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^container/create/$', create_container, name='create_container'),
    url(r'^container/delete/$', delete_container, name='delete_container'),
    url(r'^container/view/$', container, name='container'),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
