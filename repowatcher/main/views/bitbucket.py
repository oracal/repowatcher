from collections import defaultdict
from datetime import timedelta, datetime
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.db.models.aggregates import Max
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from django.views.decorators.cache import never_cache, cache_control
from oauth_hook import OAuthHook
from repowatcher.main.decorators import ajax_required
from repowatcher.main.models import Repository, UserRepositoryLink, \
    RepositoryCategory, RepositoryUser, RepositoryUserRepositoryLink
from repowatcher.main.views.BitbucketProvider import BitbucketProvider
import json
import logging
import requests
import urllib
logger = logging.getLogger(__name__)


OAuthHook.consumer_key = settings.BITBUCKET_CONSUMER_KEY
OAuthHook.consumer_secret = settings.BITBUCKET_CONSUMER_SECRET

@login_required
@never_cache
def bitbucket(request):
    user = request.user
    try:
        username = user.social_auth.get(provider='bitbucket').extra_data['username']
        return HttpResponseRedirect(reverse(bitbucket_username, kwargs={'username': username}))
    except ObjectDoesNotExist:
        return HttpResponseRedirect(reverse('repowatcher.main.views.authed'))

def bitbucket_repo(request, owner, repo):
    owner = urllib.unquote(owner)
    repo = urllib.unquote(repo)
    user = request.user
    slug = '/'.join((owner,repo))
    host_slug = '/'.join(('bitbucket',owner,repo))
    bitbucket_provider = BitbucketProvider(user)
    update = False
    try:
        repository = bitbucket_provider.retrieve_repository_details(owner, repo)
    except ObjectDoesNotExist:
        update = True
        repository = Repository()
    if update or (datetime.now() - repository.last_modified) > timedelta(days = 1):
        repository_dict = bitbucket_provider.get_repository_details(owner, repo)
        repository = bitbucket_provider.create_or_update_repository_details(repository_dict, repository)
        if not repository.private:
            repository.save()
    repo_events = bitbucket_provider.get_repository_events(owner, repo)
    return render_to_response('bitbucket_repo.html', {'repository': repository, 'repo_events': repo_events}, RequestContext(request))

@login_required
def bitbucket_username_watched(request,username):
    user = request.user
    # need to fixed the problem with owned repos
    try:
        bitbucket_username = user.social_auth.get(provider='bitbucket').extra_data['username']
        if username == bitbucket_username:
            bitbucket_provider = BitbucketProvider(user)
            repositories_by_language, repository_user = bitbucket_provider.retrieve_watched_repositories_dict(username)
            repository_user.save()
            if len(repositories_by_language) == 0:

                repositories = bitbucket_provider.get_watched_repositories(username)
                for repo in repositories:
                    update = False
                    try:
                        repository = bitbucket_provider.retrieve_repository_details(repo['owner'], repo['name'])
                    except ObjectDoesNotExist:
                        update = True
                        repository = Repository()
                    if update or (datetime.now() - repository.last_modified) > timedelta(days = 1):
                        repository = bitbucket_provider.create_or_update_repository_details(repo, repository)
                        if not repository.private:
                            repository.save()
                    repositories_by_language[repository.language].append(repository)
                for category in repositories_by_language.keys():
                    RepositoryCategory.objects.get_or_create(name = category)
                    repositories_by_language[category].sort(key=lambda x: x.watchers, reverse = True)
            return render_to_response('bitbucket_username_watched.html', {'username':username,'repositories_by_language':sorted(dict(repositories_by_language).iteritems(),key=lambda (k, v): len(v),reverse = True),'owned':False},context_instance=RequestContext(request))
    except ObjectDoesNotExist:
        pass
    res = HttpResponse("Unauthorized")
    res.status_code = 401
    return res

def bitbucket_username_owned(request,username):
    user = request.user
    bitbucket_provider = BitbucketProvider(user)
    repositories_by_language, repository_user = bitbucket_provider.retrieve_owned_repositories_dict(username)
    repository_user.save()

    if len(repositories_by_language)==0:
        watched = bitbucket_provider.get_owned_repositories(username)
        for repo in watched:
            update = False
            try:
                repository = bitbucket_provider.retrieve_repository_details(repo['owner'], repo['name'])
            except ObjectDoesNotExist:
                update = True
                repository = Repository()
            if update or (datetime.now() - repository.last_modified) > timedelta(days = 1):
                repository = bitbucket_provider.create_or_update_repository_details(repo, repository)
                if not repository.private:
                    repository.save()
            if not repository.private:
                RepositoryUserRepositoryLink.objects.get_or_create(user = repository_user, repository = repository, owned = True)
            repositories_by_language[repository.language].append(repository)
        repository_user.public_repos = len(watched)
        repository_user.save()
        for category in repositories_by_language.keys():
            RepositoryCategory.objects.get_or_create(name = category)
            repositories_by_language[category].sort(key=lambda x: x.watchers, reverse = True)
    return render_to_response('bitbucket_username_watched.html', {'username':username,'repositories_by_language':sorted(dict(repositories_by_language).iteritems(),key=lambda (k, v): len(v),reverse = True),'owned':True},context_instance=RequestContext(request))

def bitbucket_username(request, username):
    username = urllib.unquote(username)
    user = request.user
    repository_user = None
    update = False
    response = None

    bitbucket_provider = BitbucketProvider(user)
    # Get user information
    try:
        repository_user = bitbucket_provider.retrieve_user_details(username)
    except ObjectDoesNotExist:
        update = True
        repository_user = RepositoryUser()
    if update or (datetime.now() - repository_user.last_modified) > timedelta(days = 1):
        user_dict = bitbucket_provider.get_user_details(username)
        repository_user = bitbucket_provider.create_or_update_user_details(user_dict, repository_user)
        repository_user.save()

    user_events = bitbucket_provider.get_user_events(username)
    # Get repository information
    owned_repositories, repository_user = bitbucket_provider.retrieve_owned_repositories_list(username)
    watched_repositories, repository_user = bitbucket_provider.retrieve_watched_repositories_list(username)

    if len(owned_repositories) == 0:
        owned = bitbucket_provider.get_owned_repositories(username)
        for repo in owned:
            update = False
            try:
                repository = bitbucket_provider.retrieve_repository_details(repo['owner'], repo['name'])
            except ObjectDoesNotExist:
                update = True
                repository = Repository()
            if update or (datetime.now() - repository.last_modified) > timedelta(days = 1):
                repository = bitbucket_provider.create_or_update_repository_details(repo, repository)
                if not repository.private:
                    repository.save()
                RepositoryCategory.objects.get_or_create(name=repository.language)
            if not repository.private:
                RepositoryUserRepositoryLink.objects.get_or_create(user=repository_user, repository = repository, owned = True)
            owned_repositories.append(repository)
        repository_user.public_repos = len(owned_repositories)
        repository_user.save()

    if len(watched_repositories) == 0:
        watched = bitbucket_provider.get_watched_repositories(username)
        for repo in watched:
            update = False
            try:
                repository = bitbucket_provider.retrieve_repository_details(repo['owner'], repo['name'])
            except ObjectDoesNotExist:
                update = True
                repository = Repository()
            if update or (datetime.now() - repository.last_modified) > timedelta(days = 1):
                repository = bitbucket_provider.create_or_update_repository_details(repo, repository)
                if not repository.private:
                    repository.save()
            watched_repositories.append(repository)
        repository_user.starred = len(watched_repositories)
    return render_to_response('bitbucket_username.html', {'user_events':user_events,'repository_user':repository_user},context_instance=RequestContext(request))

@ajax_required
@never_cache
def bitbucket_username_watched_save(request, username, owned=False):
    user = request.user
    username = urllib.unquote(username)
    try:
        if user.is_authenticated() and username == user.social_auth.get(provider='bitbucket').extra_data['username']:
            profile = user.get_profile()
            profile.save()
            try:
                updated_dictionary = json.loads(request.POST["order"])
            except ValueError:
                updated_dictionary = {}
            bitbucket_provider = BitbucketProvider(user)
            bitbucket_provider.save_repositories(updated_dictionary, owned)
            data= {'outcome':'success'}
            return HttpResponse(json.dumps(data),mimetype="application/json")
    except ObjectDoesNotExist:
        pass
    res = HttpResponse("Unauthorized")
    res.status_code = 401
    return res


@login_required
@never_cache
def bitbucket_username_watched_refresh(request,username,owned):
    user = request.user
    username = urllib.unquote(username)
    try:
        bitbucket_username = user.social_auth.get(provider='bitbucket').extra_data['username']
        if username == bitbucket_username:
            profile = user.get_profile()
            links = profile.userrepositorylink_set.filter(owned=owned).filter(repository__host='bitbucket')
            links.delete()
            profile.save()
            if owned:
                return HttpResponseRedirect(reverse('bitbucket_username_owned', kwargs={'username': username}))
            else:
                return HttpResponseRedirect(reverse('bitbucket_username_watched', kwargs={'username': username}))
    except ObjectDoesNotExist:
        pass
    res = HttpResponse("Unauthorized")
    res.status_code = 401
    return res

@ajax_required
@never_cache
def bitbucket_username_category_watched_save(request, username, category, owned=False):
    username = urllib.unquote(username)
    user = request.user
    category = urllib.unquote(category)
    try:
        if user.is_authenticated() and username == user.social_auth.get(provider='bitbucket').extra_data['username']:
            profile = user.get_profile()
            try:
                updated_list = json.loads(request.POST["order"])
            except ValueError:
                updated_list = []
            updated_dictionary = {category: updated_list}
            bitbucket_provider = BitbucketProvider(user)
            bitbucket_provider.save_repositories(updated_dictionary, owned)
            data = {'outcome': 'success'}
            profile.save()
            return HttpResponse(json.dumps(data),mimetype="application/json")
    except ObjectDoesNotExist:
        pass
    res = HttpResponse("Unauthorized")
    res.status_code = 401
    return res

@login_required
@never_cache
def bitbucket_username_category_watched_refresh(request, username, category, owned):
    user = request.user
    username = urllib.unquote(username)
    category = urllib.unquote(category)
    try:
        bitbucket_username = user.social_auth.get(provider='bitbucket').extra_data['username']
        if username == bitbucket_username:
            profile = user.get_profile()
            links = profile.userrepositorylink_set.filter(owned=owned).filter(repository_category__name__iexact=category).filter(repository__host='bitbucket')
            links.delete()
            profile.save()
            if owned:
                return HttpResponseRedirect(reverse('bitbucket_username_category_owned', kwargs={'username': username,'category':category}))
            else:
                return HttpResponseRedirect(reverse('bitbucket_username_category_watched', kwargs={'username': username,'category':category}))
    except ObjectDoesNotExist:
        pass
    res = HttpResponse("Unauthorized")
    res.status_code = 401
    return res

def bitbucket_username_category_owned(request,username,category):
    """has all bitbucket repos and the latest 30 events for a username with a specific category"""
    owned = True
    username = urllib.unquote(username)
    category = urllib.unquote(category)
    user = request.user
    bitbucket_provider = BitbucketProvider(user)
    watched_filtered, repository_user = bitbucket_provider.retrieve_owned_category_repositories(username, category)
    repository_user.save()

    if len(watched_filtered) == 0:
        owned = bitbucket_provider.get_owned_repositories(username)
        category_lower = category.lower()
        for repo in owned:
            update = False
            try:
                repository = bitbucket_provider.retrieve_repository_details(repo['owner'], repo['name'])
            except ObjectDoesNotExist:
                update = True
                repository = Repository()
            if update or (datetime.now() - repository.last_modified) > timedelta(days = 1):
                repository = bitbucket_provider.create_or_update_repository_details(repo, repository)
                if not repository.private:
                    repository.save()
            if repository.language == category_lower:
                watched_filtered.append(repository)
            if not repository.private:
                RepositoryUserRepositoryLink.objects.get_or_create(user = repository_user, repository = repository, owned = owned)
        RepositoryCategory.objects.get_or_create(name = category)
        repository_user.public_repos = len(owned)
        repository_user.save()
        watched_filtered.sort(key=lambda x: x.watchers, reverse = True)
    # Get repository events
    repo_events = bitbucket_provider.get_repositories_events(watched_filtered)
    return render_to_response('bitbucket_username_category_watched.html', {'username': username, 'watched':watched_filtered, 'category':category, 'repo_events':repo_events,'owned':owned},context_instance=RequestContext(request))

@login_required
def bitbucket_username_category_watched(request,username,category):
    """has all bitbucket repos and the latest 30 events for a username with a specific category"""
    owned = False
    username = urllib.unquote(username)
    category = urllib.unquote(category)
    category = category.lower()
    user = request.user
    try:
        bitbucket_username = user.social_auth.get(provider='bitbucket').extra_data['username']
        if username == bitbucket_username:
            bitbucket_provider = BitbucketProvider(user)
            watched_filtered, repository_user = bitbucket_provider.retrieve_watched_category_repositories(username, category)
            repository_user.save()
            if len(watched_filtered) == 0:
                watched = bitbucket_provider.get_repositories(username, owned)
                for repo in watched:
                    update = False
                    try:
                        repository = Repository.objects.get(host_slug= 'bitbucket/'+repo['owner'].lower() + '/' + repo['name'].lower())
                    except ObjectDoesNotExist:
                        update = True
                        repository = Repository()
                    if update or (datetime.now() - repository.last_modified) > timedelta(days = 1):
                        bitbucket_provider.create_or_update_repository_details(repo, repository)
                        if not repository.private:
                            repository.save()
                    if repository.language == category:
                        watched_filtered.append(repository)
                RepositoryCategory.objects.get_or_create(name = category)
                watched_filtered.sort(key=lambda x: x.watchers, reverse = True)
            repo_events = bitbucket_provider.get_repositories_events(watched_filtered)
            return render_to_response('bitbucket_username_category_watched.html', {'username': username, 'watched':watched_filtered, 'category':category, 'repo_events':repo_events,'owned':owned},context_instance=RequestContext(request))
    except ObjectDoesNotExist:
        pass
    res = HttpResponse("Unauthorized")
    res.status_code = 401
    return res

@login_required
@never_cache
def bitbucket_username_watched_update(request, username):
    owned = False
    username = urllib.unquote(username)
    user = request.user
    try:
        bitbucket_username = user.social_auth.get(provider='bitbucket').extra_data['username']
        if username == bitbucket_username:
            profile = user.get_profile()
            profile.save()
            bitbucket_provider = BitbucketProvider(user)
            repository_user = bitbucket_provider.update_watched_repositories(username)
            repository_user.watched = None
            repository_user.save()
            return HttpResponseRedirect(reverse('bitbucket_username_watched', kwargs={'username': username}))
    except ObjectDoesNotExist:
        pass
    res = HttpResponse("Unauthorized")
    res.status_code = 401
    return res

@login_required
@never_cache
def bitbucket_username_owned_update(request, username):
    owned = True
    username = urllib.unquote(username)
    user = request.user
    try:
        bitbucket_username = user.social_auth.get(provider='bitbucket').extra_data['username']
        if username == bitbucket_username:
            profile = user.get_profile()
            profile.save()
            bitbucket_provider = BitbucketProvider(user)
            repository_user = bitbucket_provider.update_owned_repositories(username)
            repository_user.save()
            return HttpResponseRedirect(reverse('bitbucket_username_owned', kwargs={'username': username}))
    except ObjectDoesNotExist:
        pass
    res = HttpResponse("Unauthorized")
    res.status_code = 401
    return res

@login_required
@never_cache
def bitbucket_username_category_watched_update(request,username, category):
    owned = False
    category = urllib.unquote(category).lower()
    username = urllib.unquote(username)
    user = request.user
    logger.error(username)
    try:
        bitbucket_username = user.social_auth.get(provider='bitbucket').extra_data['username']
        logger.error(bitbucket_username)
        if username == bitbucket_username:
            profile = user.get_profile()
            profile.save()
            bitbucket_provider = BitbucketProvider(user)
            repository_user = bitbucket_provider.update_watched_category_repositories(username, category)
            repository_user.watched = None
            repository_user.save()
            if owned:
                return HttpResponseRedirect(reverse('bitbucket_username_category_owned', kwargs={'username': username, 'category':category}))
            else:
                return HttpResponseRedirect(reverse('bitbucket_username_category_watched', kwargs={'username': username,'category':category}))
    except ObjectDoesNotExist:
        pass
    res = HttpResponse("Unauthorized")
    res.status_code = 401
    return res

@login_required
@never_cache
def bitbucket_username_category_owned_update(request, username, category):
    owned = True
    category = urllib.unquote(category).lower()
    username = urllib.unquote(username)
    user = request.user
    try:
        bitbucket_username = user.social_auth.get(provider='bitbucket').extra_data['username']
        if username == bitbucket_username:
            profile = user.get_profile()
            profile.save()
            bitbucket_provider = BitbucketProvider(user)
            repository_user = bitbucket_provider.update_owned_category_repositories(username, category)
            repository_user.save()
            if owned:
                return HttpResponseRedirect(reverse('bitbucket_username_category_owned', kwargs={'username': username, 'category':category}))
            else:
                return HttpResponseRedirect(reverse('bitbucket_username_category_watched', kwargs={'username': username,'category':category}))
    except ObjectDoesNotExist:
        pass
    res = HttpResponse("Unauthorized")
    res.status_code = 401
    return res

@cache_control(max_age=60 * 60 * 24)
def bitbucket_watched_popular(request):
    repositories_by_language = defaultdict(list)
    repositories = Repository.objects.filter(watchers__isnull=False).filter(private=False).filter(host='bitbucket')[:50]
    for repository in repositories:
        repositories_by_language[repository.language].append(repository)
    return render_to_response('bitbucket_watched_popular.html', {'hosts': ['bitbucket'], 'repositories_by_language':sorted(dict(repositories_by_language).iteritems(),key=lambda (k, v): len(v),reverse = True)},context_instance=RequestContext(request))

@cache_control(max_age=60 * 60 * 24)
def bitbucket_watched_language_popular(request, language):
    language = urllib.unquote(language.lower())
    repositories = Repository.objects.filter(language=language).filter(watchers__isnull=False).filter(private=False).filter(host='bitbucket')[:20]
    return render_to_response('bitbucket_watched_language_popular.html', {'language':language, 'repositories':repositories},context_instance=RequestContext(request))
