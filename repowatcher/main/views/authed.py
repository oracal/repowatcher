from GithubProvider import GithubProvider
from collections import defaultdict
from datetime import timedelta, datetime
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from oauth_hook import OAuthHook
from operator import itemgetter
from repowatcher.main.models import Repository, RepositoryCategory, \
    RepositoryUser, RepositoryUserRepositoryLink
from repowatcher.main.tasks import get_events
from repowatcher.main.views.BitbucketProvider import BitbucketProvider
import dateutil.parser
import json
import logging
import requests
import urllib
logger = logging.getLogger(__name__)


OAuthHook.consumer_key = settings.BITBUCKET_CONSUMER_KEY
OAuthHook.consumer_secret = settings.BITBUCKET_CONSUMER_SECRET

@login_required
def authed(request):
    user = request.user
    bitbucket_authed = True
    github_authed = True
    bitbucket_user_events = []
    github_user_events = []
    github_repository_user = None
    bitbucket_repository_user = None
    try:
        github_username = user.social_auth.get(provider='github').extra_data['username']
        github_provider = GithubProvider(user)
        update = False

        # Get user information
        try:
            github_repository_user = github_provider.retrieve_user_details(github_username)
        except ObjectDoesNotExist:
            update = True
            github_repository_user = RepositoryUser()
        if update or (datetime.now() - github_repository_user.last_modified) > timedelta(days = 1):
            github_user_dict = github_provider.get_user_details(github_username)
            github_repository_user = github_provider.create_or_update_user_details(github_user_dict, github_repository_user)
            github_repository_user.save()
        github_user_events = github_provider.get_user_events(github_username)
        for github_user_event in github_user_events:
            github_user_event['host'] = 'github'
            github_user_event['created_on'] = dateutil.parser.parse(github_user_event['created_at'])

        # Get repository information
        repositories, _ = github_provider.retrieve_watched_repositories_list(github_username)

        if len(repositories) == 0:
            if not github_repository_user:
                github_repository_user,_ = RepositoryUser.objects.get_or_create(login=github_username,host='github')
            watched = github_provider.get_watched_repositories(github_username)
            for repo in watched:
                update = False
                try:
                    repository = Repository.objects.get(host_slug= 'github/'+repo['owner'].lower() + '/' + repo['name'].lower())
                except ObjectDoesNotExist:
                    update = True
                    repository = Repository()
                if update or (datetime.now() - repository.last_modified) > timedelta(days = 1):
                    repository = github_provider.create_or_update_repository_details(repo, repository)
                    if not repository.private:
                        repository.save()
                    RepositoryCategory.objects.get_or_create(name = repository.language)
                if not repository.private:
                    RepositoryUserRepositoryLink.objects.get_or_create(user = github_repository_user, repository = repository, owned = False, starred = True)

                repositories.append(repository)
            github_repository_user.starred = len(repositories)
            github_repository_user.save()

        # Get repository information
        repositories, _ = github_provider.retrieve_watched_repositories_list(github_username, starred = False)

        if len(repositories) == 0:
            if not github_repository_user:
                github_repository_user,_ = RepositoryUser.objects.get_or_create(login=github_username,host='github')
            watched = github_provider.get_watched_repositories(github_username)
            for repo in watched:
                update = False
                try:
                    repository = Repository.objects.get(host_slug= 'github/'+repo['owner'].lower() + '/' + repo['name'].lower())
                except ObjectDoesNotExist:
                    update = True
                    repository = Repository()
                if update or (datetime.now() - repository.last_modified) > timedelta(days = 1):
                    repository = github_provider.create_or_update_repository_details(repo, repository)
                    if not repository.private:
                        repository.save()
                    RepositoryCategory.objects.get_or_create(name = repository.language)
                if not repository.private:
                    RepositoryUserRepositoryLink.objects.get_or_create(user = github_repository_user, repository = repository, owned = False, starred = False)

                repositories.append(repository)
            github_repository_user.watched = len(repositories)
            github_repository_user.save()
    except ObjectDoesNotExist:
        github_authed = False

    try:
        bitbucket_username = user.social_auth.get(provider='bitbucket').extra_data['username']
        bitbucket_provider = BitbucketProvider(user)
        # Get user information
        update = False
        try:
            bitbucket_repository_user = bitbucket_provider.retrieve_user_details(bitbucket_username)
        except ObjectDoesNotExist:
            update = True
            bitbucket_repository_user = RepositoryUser()
        if update or (datetime.now() - bitbucket_repository_user.last_modified) > timedelta(days = 1):
            user_dict = bitbucket_provider.get_user_details(bitbucket_username)
            bitbucket_repository_user = bitbucket_provider.create_or_update_user_details(user_dict, bitbucket_repository_user)
            bitbucket_repository_user.save()
        bitbucket_user_events = bitbucket_provider.get_user_events(bitbucket_username)
        for bitbucket_user_event in bitbucket_user_events:
            bitbucket_user_event['host'] = 'bitbucket'
            bitbucket_user_event['created_on'] = dateutil.parser.parse(bitbucket_user_event['utc_created_on'])
        # Get repository information
        owned_repositories, _ = bitbucket_provider.retrieve_owned_repositories_list(bitbucket_username)
        watched_repositories, _ = bitbucket_provider.retrieve_watched_repositories_list(bitbucket_username)

        if len(owned_repositories) == 0:
            owned = bitbucket_provider.get_owned_repositories(bitbucket_username)
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
                    RepositoryUserRepositoryLink.objects.get_or_create(user=bitbucket_repository_user, repository = repository, owned = True)
                owned_repositories.append(repository)
            bitbucket_repository_user.public_repos = len(owned_repositories)
            bitbucket_repository_user.save()

        if len(watched_repositories) == 0:
            watched = bitbucket_provider.get_watched_repositories(bitbucket_username)
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
            bitbucket_repository_user.starred = len(watched_repositories)
    except ObjectDoesNotExist:
        bitbucket_authed = False

    user_events = sorted(github_user_events + bitbucket_user_events,key=itemgetter('created_on'), reverse = True)[:30]

    return render_to_response('authed.html', {'user_events':user_events,'github_repository_user':github_repository_user,'bitbucket_repository_user':bitbucket_repository_user,'github_authed':github_authed,'bitbucket_authed':bitbucket_authed}, context_instance=RequestContext(request))

@login_required
def authed_watched(request):
    repositories_by_language = defaultdict(list)
    github_repositories_by_language = defaultdict(list)
    bitbucket_repositories_by_language = defaultdict(list)
    bitbucket_authed = True
    github_authed = True
    owned = False
    user = request.user
    github_username = None
    bitbucket_username = None
    try:
        github_username = user.social_auth.get(provider='github').extra_data['username']
        github_provider = GithubProvider(user)
        github_repositories_by_language, github_repository_user = github_provider.retrieve_repositories_dict(github_username, owned)
        if len(github_repositories_by_language) == 0:
            watched = github_provider.get_repositories(github_username, owned)
            count = 0
            for repo in watched:
                update = False
                try:
                    repository = Repository.objects.get(host_slug= 'github/'+repo['owner'].lower() + '/' + repo['name'].lower())
                except ObjectDoesNotExist:
                    update = True
                    repository = Repository()
                if update or (datetime.now() - repository.last_modified) > timedelta(days = 1):
                    repository = github_provider.create_or_update_repository_details(repo, repository)
                    if not repository.private:
                        repository.save()
                if not repository.private:
                    count += 1
                    RepositoryUserRepositoryLink.objects.get_or_create(user = github_repository_user, repository = repository, owned = owned)

                github_repositories_by_language[repository.language].append(repository)
            for category in github_repositories_by_language.keys():
                RepositoryCategory.objects.get_or_create(name=category)
                repositories_by_language[category].extend(github_repositories_by_language[category])
            for category in repositories_by_language.keys():
                repositories_by_language[category].sort(key=lambda x: x.watchers, reverse = True)
            github_repository_user.starred = count
            github_repository_user.save()
        else:
            for category in github_repositories_by_language.keys():
                repositories_by_language[category].extend(github_repositories_by_language[category])
    except ObjectDoesNotExist:
        github_authed = False
    try:
        bitbucket_username = user.social_auth.get(provider='bitbucket').extra_data['username']
        bitbucket_provider = BitbucketProvider(user)
        bitbucket_repositories_by_language, bitbucket_repository_user = bitbucket_provider.retrieve_watched_repositories_dict(bitbucket_username)
        if len(bitbucket_repositories_by_language) == 0:
            watched = bitbucket_provider.get_watched_repositories(bitbucket_username)
            count = 0
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
                        count += 1
                        repository.save()
                bitbucket_repositories_by_language[repository.language].append(repository)
            for category in bitbucket_repositories_by_language.keys():
                RepositoryCategory.objects.get_or_create(name=category)
                repositories_by_language[category].extend(bitbucket_repositories_by_language[category])
            for category in repositories_by_language.keys():
                repositories_by_language[category].sort(key=lambda x: x.watchers, reverse = True)
            bitbucket_repository_user.starred = count
        else:
            for category in bitbucket_repositories_by_language.keys():
                repositories_by_language[category].extend(bitbucket_repositories_by_language[category])
    except ObjectDoesNotExist:
        bitbucket_authed = False
    if bitbucket_authed or github_authed:
        return render_to_response('username_watched.html', {'github_username': github_username,'github_authed': github_authed,'bitbucket_username':bitbucket_username, 'bitbucket_authed':bitbucket_authed, 'repositories_by_language':sorted(dict(repositories_by_language).iteritems(),key=lambda (k, v): len(v),reverse = True),'owned':owned},context_instance=RequestContext(request))
    else:
        return HttpResponseRedirect(reverse('repowatcher.main.views.authed'))

@login_required
def authed_owned(request):
    repositories_by_language = defaultdict(list)
    github_repositories_by_language = defaultdict(list)
    bitbucket_repositories_by_language = defaultdict(list)
    bitbucket_authed = True
    github_authed = True
    owned = True
    api_only = True
    user = request.user
    github_username = None
    bitbucket_username = None
    try:
        github_username = user.social_auth.get(provider='github').extra_data['username']
        github_provider = GithubProvider(user)
        github_repositories_by_language, github_repository_user = github_provider.retrieve_repositories_dict(github_username, owned)
        if len(github_repositories_by_language) == 0:
            owned_repos = github_provider.get_repositories(github_username, owned)

            count = 0
            for repo in owned_repos:
                update = False
                try:
                    repository = github_provider.retrieve_repository_details(repo['owner'], repo['name'])
                except ObjectDoesNotExist:
                    update = True
                    repository = Repository()
                if update or (datetime.now() - repository.last_modified) > timedelta(days = 1):
                    repository = github_provider.create_or_update_repository_details(repo, repository)
                    if not repository.private:
                        repository.save()
                if not repository.private:
                    count += 1
                    RepositoryUserRepositoryLink.objects.get_or_create(user = github_repository_user, repository = repository, owned = owned)

                github_repositories_by_language[repository.language.lower()].append(repository)
            for category in github_repositories_by_language.keys():
                RepositoryCategory.objects.get_or_create(name=category)
                repositories_by_language[category].extend(github_repositories_by_language[category])
            for category in repositories_by_language.keys():
                repositories_by_language[category].sort(key=lambda x: x.watchers, reverse = True)
        else:
            for category in github_repositories_by_language.keys():
                repositories_by_language[category].extend(github_repositories_by_language[category])
    except ObjectDoesNotExist:
        github_authed = False
    try:
        bitbucket_username = user.social_auth.get(provider='bitbucket').extra_data['username']
        bitbucket_provider = BitbucketProvider(user)
        bitbucket_repositories_by_language, bitbucket_repository_user = bitbucket_provider.retrieve_owned_repositories_dict(bitbucket_username)
        if len(bitbucket_repositories_by_language)==0:
            owned_repos = bitbucket_provider.get_owned_repositories(bitbucket_username)
            for repo in owned_repos:
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
                bitbucket_repositories_by_language[repository.language].append(repository)
            for category in bitbucket_repositories_by_language.keys():
                RepositoryCategory.objects.get_or_create(name=category)
                repositories_by_language[category].extend(bitbucket_repositories_by_language[category])
            for category in repositories_by_language.keys():
                repositories_by_language[category].sort(key=lambda x: x.watchers, reverse = True)
        else:
            for category in bitbucket_repositories_by_language.keys():
                repositories_by_language[category].extend(bitbucket_repositories_by_language[category])
    except ObjectDoesNotExist:
        bitbucket_authed = False
    if bitbucket_authed or github_authed:
        return render_to_response('username_watched.html', {'github_username': github_username,'github_authed': github_authed,'bitbucket_username':bitbucket_username, 'bitbucket_authed':bitbucket_authed,'repositories_by_language':sorted(dict(repositories_by_language).iteritems(),key=lambda (k, v): len(v),reverse = True),'owned':owned},context_instance=RequestContext(request))
    else:
        return HttpResponseRedirect(reverse('repowatcher.main.views.authed'))

@login_required
def authed_category_watched(request,category):
    """has all github repos and the latest 30 events for a username with a specific category"""
    owned = False
    category = urllib.unquote(category).lower()
    github_watched_filtered = []
    bitbucket_watched_filtered = []
    github_repo_events = []
    bitbucket_repo_events = []
    user = request.user
    repository_user = None
    github_username = None
    bitbucket_username = None
    bitbucket_authed = True
    github_authed = True
    watched_filtered = []
    try:
        github_username = user.social_auth.get(provider='github').extra_data['username']
        github_provider = GithubProvider(user)
        github_watched_filtered, github_repository_user = github_provider.retrieve_category_repositories(github_username, category, owned)
        watched_filtered.extend(github_watched_filtered)
        github_repository_user.save()
        if len(github_watched_filtered) == 0:
            watched = github_provider.get_repositories(github_username, owned)

            count = 0
            for repo in watched:
                update = False
                try:
                    repository = Repository.objects.get(host_slug= 'github/'+repo['owner'].lower() + '/' + repo['name'].lower())
                except ObjectDoesNotExist:
                    update = True
                    repository = Repository()
                if update or (datetime.now() - repository.last_modified) > timedelta(days = 1):
                    repository = github_provider.create_or_update_repository_details(repo, repository)
                    if not repository.private:
                        repository.save()
                if repository.language == category:
                    github_watched_filtered.append(repository)
                    if not repository.private:
                        count += 1
                if not repository.private:
                    RepositoryUserRepositoryLink.objects.get_or_create(user = repository_user, repository = repository, owned = owned)
            watched_filtered.extend(github_watched_filtered)
            watched_filtered.sort(key=lambda x: x.watchers, reverse = True)
            RepositoryCategory.objects.get_or_create(name = category.lower())
            github_repository_user.starred = count
            github_repository_user.save()


        # Get repository events
        github_repo_events = github_provider.get_repositories_events(github_watched_filtered)
        for github_repo_event in github_repo_events:
            github_repo_event['host'] = 'github'
            github_repo_event['created_on'] = dateutil.parser.parse(github_repo_event['created_at'])
    except ObjectDoesNotExist:
        github_authed = False

    user = request.user
    try:
        bitbucket_username = user.social_auth.get(provider='bitbucket').extra_data['username']
        bitbucket_provider = BitbucketProvider(user)
        bitbucket_watched_filtered, bitbucket_repository_user = bitbucket_provider.retrieve_watched_category_repositories(bitbucket_username, category)
        watched_filtered.extend(bitbucket_watched_filtered)
        bitbucket_repository_user.save()
        if len(bitbucket_watched_filtered) == 0:
            watched = bitbucket_provider.get_repositories(bitbucket_username, owned)
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
                    bitbucket_watched_filtered.append(repository)
            RepositoryCategory.objects.get_or_create(name = category)
            watched_filtered.extend(bitbucket_watched_filtered)
            watched_filtered.sort(key=lambda x: x.watchers, reverse = True)
        bitbucket_repo_events = bitbucket_provider.get_repositories_events(bitbucket_watched_filtered)
        for bitbucket_repo_event in bitbucket_repo_events:
            bitbucket_repo_event['host'] = 'bitbucket'
            bitbucket_repo_event['created_on'] = dateutil.parser.parse(bitbucket_repo_event['utc_created_on'])
    except ObjectDoesNotExist:
        bitbucket_authed = False
    repo_events = sorted(github_repo_events + bitbucket_repo_events,key=itemgetter('created_on'), reverse = True)[:30]
    if bitbucket_authed or github_authed:
        return render_to_response('username_category_watched.html', {'github_username': github_username,'github_authed': github_authed,'bitbucket_username':bitbucket_username, 'bitbucket_authed':bitbucket_authed, 'watched':watched_filtered, 'category':category, 'repo_events':repo_events,'owned':owned},context_instance=RequestContext(request))
    else:
        return HttpResponseRedirect(reverse('repowatcher.main.views.authed'))

@login_required
def authed_category_owned(request,category):
    """has all github repos and the latest 30 events for a username with a specific category"""
    owned = True
    category = urllib.unquote(category).lower()
    github_repo_events = []
    bitbucket_repo_events = []
    github_watched_filtered = []
    bitbucket_watched_filtered = []
    user = request.user
    repository_user = None
    github_username = None
    bitbucket_username = None
    bitbucket_authed = True
    github_authed = True
    watched_filtered = []
    try:
        github_username = user.social_auth.get(provider='github').extra_data['username']
        github_provider = GithubProvider(user)
        github_watched_filtered, github_repository_user = github_provider.retrieve_category_repositories(github_username, category, owned)
        watched_filtered.extend(github_watched_filtered)
        github_repository_user.save()
        if len(github_repository_user) == 0:
            watched = github_provider.get_repositories(github_username, owned)
            category_lower = category.lower()
            for repo in watched:
                update = False
                try:
                    repository = Repository.objects.get(host_slug= 'github/'+repo['owner'].lower() + '/' + repo['name'].lower())
                except ObjectDoesNotExist:
                    update = True
                    repository = Repository()
                if update or (datetime.now() - repository.last_modified) > timedelta(days = 1):
                    repository = github_provider.create_or_update_repository_details(repo, repository)
                    if not repository.private:
                        repository.save()
                if repository.language == category_lower:
                    github_watched_filtered.append(repository)
                if not repository.private:
                    RepositoryUserRepositoryLink.objects.get_or_create(user = github_repository_user, repository = repository, owned = owned)
            watched_filtered.extend(github_watched_filtered)
            watched_filtered.sort(key=lambda x: x.watchers, reverse = True)
            RepositoryCategory.objects.get_or_create(name = category.lower())
            github_repository_user.save()


        # Get repository events

        github_repo_events = github_provider.get_repositories_events(github_watched_filtered)
        for github_repo_event in github_repo_events:
            github_repo_event['host'] = 'github'
            github_repo_event['created_on'] = dateutil.parser.parse(github_repo_event['created_at'])
    except ObjectDoesNotExist:
        github_authed = False
    user = request.user
    try:
        bitbucket_username = user.social_auth.get(provider='bitbucket').extra_data['username']
        profile = user.get_profile()
        bitbucket_provider = BitbucketProvider(user)
        bitbucket_watched_filtered, bitbucket_repository_user = bitbucket_provider.retrieve_owned_category_repositories(bitbucket_username, category)
        watched_filtered.extend(bitbucket_watched_filtered)
        if len(bitbucket_watched_filtered) == 0:
            owned = bitbucket_provider.get_owned_repositories(bitbucket_username)
            for repo in owned:
                update = False
                try:
                    repository = Repository.objects.get(host_slug= 'bitbucket/'+repo['owner'].lower() + '/' + repo['name'].lower())
                except ObjectDoesNotExist:
                    update = True
                    repository = Repository()
                if update or (datetime.now() - repository.last_modified) > timedelta(days = 1):
                    repository = bitbucket_provider.create_or_update_repository_details(repo, repository)
                    if not repository.private:
                        repository.save()


                if repository.language == category_lower:
                    bitbucket_watched_filtered.append(repository)
            watched_filtered.extend(bitbucket_watched_filtered)
            watched_filtered.sort(key=lambda x: x.watchers, reverse = True)
            RepositoryCategory.objects.get_or_create(name = category.lower())
        bitbucket_repo_events = bitbucket_provider.get_repositories_events(bitbucket_watched_filtered)
        for bitbucket_repo_event in bitbucket_repo_events:
                bitbucket_repo_event['host'] = 'bitbucket'
                bitbucket_repo_event['created_on'] = dateutil.parser.parse(bitbucket_repo_event['utc_created_on'])
    except ObjectDoesNotExist:
        bitbucket_authed = False
    repo_events = sorted(github_repo_events + bitbucket_repo_events,key=itemgetter('created_on'), reverse = True)[:30]
    if bitbucket_authed or github_authed:
        return render_to_response('username_category_watched.html', {'github_username': github_username,'github_authed': github_authed,'bitbucket_username':bitbucket_username, 'bitbucket_authed':bitbucket_authed, 'watched':watched_filtered, 'category':category, 'repo_events':repo_events,'owned':owned},context_instance=RequestContext(request))
    else:
        return HttpResponseRedirect(reverse('repowatcher.main.views.authed'))
