from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin
from django.contrib.auth import views as auth_views

from swift_browser.views import container, containers, create_container, delete_container, upload, delete_object, create_folder

urlpatterns = [
    url(r'^$', containers, name='containers'),
    url(r'^accounts/login/$', auth_views.login, name='login'),
    url(r'^logout/$', auth_views.logout, {'next_page': '/accounts/login'}, name='logout'),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^create_container/$', create_container, name='create_container'),
    url(r'^delete_container/$', delete_container, name='delete_container'),
    url(r'^view_container/$', container, name='container'),
    url(r'^upload/$', upload, name='upload'),
    url(r'^delete_object/$', delete_object, name='delete_object'),
    url(r'^create_folder/$', create_folder, name='create_folder'),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
