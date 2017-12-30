from django.shortcuts import render
from django.conf import settings
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from urllib.parse import urlparse
from swiftclient import client


def replace_hyphens(olddict):
    """ Replaces all hyphens in dict keys with an underscore.

    Needed in Django templates to get a value from a dict by key name. """
    newdict = {}
    for key, value in olddict.items():
        key = key.replace('-', '_')
        newdict[key] = value
    return newdict

@login_required
def containers(request):
    if 'auth_token' not in request.session.keys():
        try:
            auth_version = settings.SWIFT_AUTH_VERSION or 1
            conn = client.Connection(authurl=settings.SWIFT_AUTH_URL,
                    user=settings.SWIFT_AUTH_USER,
                    key=settings.SWIFT_AUTH_KEY,
                    auth_version=auth_version,
                    insecure=settings.SWIFT_SSL_INSECURE)
            (storage_url, auth_token) = conn.get_auth()
            request.session['storage_url'] = storage_url
            request.session['auth_token'] = auth_token
        except client.ClientException:
            messages.add_message(request, messages.ERROR, _("Login failed."))

    auth_token = request.session['auth_token']
    storage_url = request.session['storage_url']

    try:
        http_conn = (urlparse(storage_url),client.HTTPConnection(storage_url, insecure=settings.SWIFT_SSL_INSECURE))
        account_stat, containers = client.get_account(storage_url, auth_token, http_conn=http_conn)
    except client.ClientException as exc:
        if exc.http_status == 403:
            account_stat = {}
            containers = []
            msg = 'Container listing failed.'
            messages.add_message(request, messages.ERROR, msg)
        else:
            return redirect(login)

    account_stat = replace_hyphens(account_stat)

    return render(request,'containers.html', {
        'account_stat': account_stat,
        'containers': containers,
        'session': request.session,
    })



