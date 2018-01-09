from django.shortcuts import render
from django.conf import settings
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.contrib import messages
from urllib.parse import urlparse
from swiftclient import client
import logging

from .forms import CreateContainerForm, UploadFileForm, ViewContainerForm

logger = logging.getLogger(__name__)

def replace_hyphens(olddict):
    """ Replaces all hyphens in dict keys with an underscore.

    Needed in Django templates to get a value from a dict by key name. """
    newdict = {}
    for key, value in olddict.items():
        key = key.replace('-', '_')
        newdict[key] = value
    return newdict

def prefix_list(prefix):
    prefixes = []

    if prefix:
        elements = prefix.split('/')
        elements = filter(None, elements)
        prefix = ""
        for element in elements:
            prefix += element + '/'
            prefixes.append({'display_name': element, 'full_name': prefix})

    return prefixes

def pseudofolder_object_list(objects, prefix):
    pseudofolders = []
    objs = []

    duplist = []

    for obj in objects:
        # Rackspace Cloudfiles uses application/directory
        # Cyberduck uses application/x-directory
        if obj.get('content_type', None) in ('application/directory',
                                             'application/x-directory'):
            obj['subdir'] = obj['name']

        if 'subdir' in obj:
            # make sure that there is a single slash at the end
            # Cyberduck appends a slash to the name of a pseudofolder
            entry = obj['subdir'].strip('/') + '/'
            if entry != prefix and entry not in duplist:
                duplist.append(entry)
                pseudofolders.append((entry, obj['subdir']))
        else:
            objs.append(obj)

    return (pseudofolders, objs)

@login_required
def containers(request):
    if 'auth_token' not in request.session.keys():
        logger.info('No auth_token, attempting to authenticate')
        try:
            auth_version = settings.SWIFT_AUTH_VERSION or 1
            conn = client.Connection(authurl=settings.SWIFT_AUTH_URL,
                    user=settings.SWIFT_AUTH_USER,
                    key=settings.SWIFT_AUTH_KEY,
                    auth_version=auth_version,
                    insecure=settings.SWIFT_SSL_INSECURE)
            (storage_url, auth_token) = conn.get_auth()
            logger.info('auth_token: %s' % auth_token)
            logger.info('storage_url: %s' % storage_url)
            request.session['storage_url'] = storage_url
            request.session['auth_token'] = auth_token
        except client.ClientException:
            messages.add_message(request, messages.ERROR, "Login failed.")

    auth_token = request.session['auth_token']
    storage_url = request.session['storage_url']

    try:
        http_conn = (urlparse(storage_url),
                     client.HTTPConnection(storage_url, insecure=settings.SWIFT_SSL_INSECURE))
        account_stat, containers = client.get_account(storage_url, auth_token, http_conn=http_conn)
    except client.ClientException as exc:
        if exc.http_status == 403:
            account_stat = {}
            containers = []
            msg = 'Container listing failed.'
            messages.add_message(request, messages.ERROR, msg)
        else:
            request.session.flush()
            return redirect(settings.LOGIN_URL)

    account_stat = replace_hyphens(account_stat)

    return render(request,'containers.html', {
        'account_stat': account_stat,
        'containers': containers,
        'session': request.session,
    })

@login_required
def container(request, container=None):
    auth_token = request.session['auth_token']
    storage_url = request.session['storage_url']

    if 'container' not in request.GET.keys():
        return redirect(containers)
    container = request.GET['container']
    subdir = ''
    if 'subdir' in request.GET.keys():
        subdir = request.GET['subdir']

    try:
        http_conn = (urlparse(storage_url),
                     client.HTTPConnection(storage_url, insecure=settings.SWIFT_SSL_INSECURE))
        meta, objects = client.get_container(storage_url, auth_token,
                                             container, delimiter='/',
                                             prefix=subdir,
                                             http_conn=http_conn)
        subdirs = list()
        folder_objects = list()
        for folder_object in objects:
            if 'subdir' in folder_object.keys():
                if folder_object['subdir'].startswith(subdir):
                    subdirs.append({
                            'display_name': folder_object['subdir'][len(subdir):],
                            'subdir': folder_object['subdir'],
                        })
                else:
                    subdirs.append({
                            'display_name': folder_object['subdir'],
                            'subdir': folder_object['subdir'],
                        })
            else:
                if folder_object['name'].startswith(subdir):
                    folder_object['display_name'] = folder_object['name'][len(subdir):]
                else:
                    folder_object['display_name'] = folder_object['name']
                folder_objects.append(folder_object)
    
        account = storage_url.split('/')[-1]
        path = list()
        if subdir:
            current_path = ''
            for path_element in subdir.split('/'):
                if path_element:
                    current_path += "%s/" % (path_element)
                    path.append({ 'subdir': current_path, 'path_element': path_element })
    
        read_acl = meta.get('x-container-read', '').split(',')
        public = False
        required_acl = ['.r:*', '.rlistings']
        if [x for x in read_acl if x in required_acl]:
            public = True

        return render(request, "container.html", {
            'container': container,
            'subdirs': subdirs,
            'folder_objects': folder_objects,
            'account': account,
            'public': public,
            'session': request.session,
            'path': path,
            })

    except client.ClientException:
        messages.add_message(request, messages.ERROR, "Access denied.")
        return redirect(containers)

@login_required
def create_container(request):
    auth_token = request.session['auth_token']
    storage_url = request.session['storage_url']

    if request.method == 'POST':
        form = CreateContainerForm(request.POST)
        if form.is_valid():
            container = form.cleaned_data['container_name']
            try:
                http_conn = (urlparse(storage_url),
                             client.HTTPConnection(storage_url, insecure=settings.SWIFT_SSL_INSECURE))
                client.put_container(storage_url, auth_token, container, http_conn=http_conn)
                messages.add_message(request, messages.INFO, "Container created.")
            except client.ClientException:
                messages.add_message(request, messages.ERROR, "Access denied.")

            return redirect(containers)
    else:
        form = CreateContainerForm()

    return render(request, 'create_container.html', {'form': form})


@login_required
def delete_container(request, container, prefix=None):
    auth_token = request.session['auth_token']
    storage_url = request.session['storage_url']

    try:
        http_conn = (urlparse(storage_url),
                     client.HTTPConnection(storage_url, insecure=settings.SWIFT_SSL_INSECURE))
        _m, objects = client.get_container(storage_url, auth_token, container, http_conn=http_conn)
        for obj in objects:
            client.delete_object(storage_url, auth_token,
                                 container, obj['name'], http_conn=http_conn)
        client.delete_container(storage_url, auth_token, container)
        messages.add_message(request, messages.INFO, "Container deleted.")
    except client.ClientException:
        messages.add_message(request, messages.ERROR, "Access denied.")

    return redirect(containers)

@login_required
def upload(request):
    auth_token = request.session['auth_token']
    storage_url = request.session['storage_url']

    if request.method == 'POST':
        form = UploadFileForm(request.POST)
        if form.is_valid():
            container = form.cleaned_data['container_name']
            try:
                http_conn = (urlparse(storage_url),
                             client.HTTPConnection(storage_url, insecure=settings.SWIFT_SSL_INSECURE))
                client.put_container(storage_url, auth_token, container, http_conn=http_conn)
                messages.add_message(request, messages.INFO, "Container created.")
            except client.ClientException:
                messages.add_message(request, messages.ERROR, "Access denied.")

            return redirect(containers)
    else:
        form = CreateContainerForm()

    return render(request, 'create_container.html', {'form': form})

