from GithubProvider import GithubProvider
from collections import defaultdict
from datetime import timedelta, datetime
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from django.views.decorators.cache import never_cache, cache_control
from repowatcher.main.decorators import ajax_required
from repowatcher.main.models import Repository, UserRepositoryLink, \
    RepositoryCategory, RepositoryUser, RepositoryUserRepositoryLink, LinkType
from repowatcher.main.utils import expire_view_cache
import hashlib
import json
import logging
import urllib
logger = logging.getLogger(__name__)

@never_cache
def anonymous_github_user(request):
    username = request.GET.get('username', '')
    return HttpResponseRedirect(reverse(github_username, kwargs={'username': username}))


@login_required
@never_cache
def github(request):
    """has all github repos for a username"""
    user = request.user
    try:
        username = user.social_auth.get(provider='github').extra_data['username']
    except ObjectDoesNotExist:
        return HttpResponseRedirect(reverse('repowatcher.main.views.authed'))
    return HttpResponseRedirect(reverse(github_username, kwargs={'username': username}))

def github_username(request, username):
    username = urllib.unquote(username)
    user = request.user
    repository_user = None
    update = False
    github_provider = GithubProvider(user)
    # Get user information
    try:
        repository_user = github_provider.retrieve_user_details(username)
    except ObjectDoesNotExist:
        update = True
        repository_user = RepositoryUser()
    if update or (datetime.now() - repository_user.last_modified) > timedelta(days = 1):

        github_user_dict = github_provider.get_user_details(username)
        repository_user = github_provider.create_or_update_user_details(github_user_dict, repository_user)
        repository_user.save()

    user_events = github_provider.get_user_events(username)

    # Get repository information
    repositories, _ = github_provider.retrieve_starred_repositories_list(username)
    if len(repositories) == 0:
        repo_link_type, _ = LinkType.objects.get_or_create(name = "starred")
        for repo in github_provider.get_starred_repositories(username):
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
                repository = repository
                RepositoryCategory.objects.get_or_create(name = repository.language)
            if not repository.private:
                RepositoryUserRepositoryLink.objects.get_or_create(user = repository_user, repository = repository, link_type = repo_link_type)

            repositories.append(repository)
    repository_user.starred = len(repositories)

    # Get repository information
    repositories, _ = github_provider.retrieve_watched_repositories_list(username)
    if len(repositories) == 0:
        repo_link_type, _ = LinkType.objects.get_or_create(name = "watched")
        for repo in github_provider.get_watched_repositories(username):
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
                repository = repository
                RepositoryCategory.objects.get_or_create(name = repository.language)
            if not repository.private:
                RepositoryUserRepositoryLink.objects.get_or_create(user = repository_user, repository = repository, link_type = repo_link_type)

            repositories.append(repository)
    repository_user.watched = len(repositories)
    repository_user.save()

    return render_to_response('github_username.html', {'user_events':user_events,'repository_user':repository_user},context_instance=RequestContext(request))

def github_username_watched(request,username, link_type):
    """has all github repos for a username"""
    owned = False
    starred = False
    if link_type == "owned":
        owned = True
    elif link_type == "starred":
        starred = True
    repo_link_type, _ = LinkType.objects.get_or_create(name = link_type)
    username = urllib.unquote(username)
    user = request.user
    github_provider = GithubProvider(user)

    repositories_by_language, repository_user = github_provider.retrieve_repositories_dict(username, link_type = link_type)
    repository_user.save()
    if len(repositories_by_language) == 0:
        watched = github_provider.get_repositories(username, link_type = link_type)
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
                RepositoryUserRepositoryLink.objects.get_or_create(user = repository_user, repository = repository, link_type = repo_link_type)

            repositories_by_language[repository.language].append(repository)
        if repo_link_type.name == "owned":
            owned = True
            pass
        elif repo_link_type.name == "starred":
            repository_user.starred = count
            starred = True
        elif repo_link_type.name == "watched":
            repository_user.watched = count
        repository_user.save()
        for category in repositories_by_language.keys():
            RepositoryCategory.objects.get_or_create(name = category)
            repositories_by_language[category].sort(key=lambda x: x.watchers, reverse = True)
    return render_to_response('github_username_watched.html', {'username':username,'repositories_by_language':sorted(dict(repositories_by_language).iteritems(),key=lambda (k, v): len(v),reverse = True),'owned':owned,"starred":starred},context_instance=RequestContext(request))

@ajax_required
@never_cache
def github_username_watched_save(request,username, link_type):
    user = request.user
    username = urllib.unquote(username)
    try:
        if user.is_authenticated() and username == user.social_auth.get(provider='github').extra_data['username']:
            profile = user.get_profile()
            try:
                updated_dictionary = json.loads(request.POST["order"])
            except ValueError:
                updated_dictionary ={}
            profile.save()
            github_provider = GithubProvider(user)
            github_provider.save_repositories(updated_dictionary, link_type)
            data= {'outcome':'success'}
            return HttpResponse(json.dumps(data),mimetype="application/json")
    except ObjectDoesNotExist:
        pass
    res = HttpResponse("Unauthorized")
    res.status_code = 401
    return res

@login_required
@never_cache
def github_username_watched_update(request,username, link_type):
    username = urllib.unquote(username)
    user = request.user
    try:
        github_username = user.social_auth.get(provider='github').extra_data['username']
        if username == github_username:
            github_provider = GithubProvider(user)
            repository_user = github_provider.update_repositories(username, link_type)
            repository_user.save()
            if link_type == "owned":
                return HttpResponseRedirect(reverse('github_username_owned', kwargs={'username': username}))
            elif link_type == "starred":
                return HttpResponseRedirect(reverse('github_username_starred', kwargs={'username': username}))
            elif link_type == "watched":
                return HttpResponseRedirect(reverse('github_username_watched', kwargs={'username': username}))
    except ObjectDoesNotExist:
        pass
    res = HttpResponse("Unauthorized")
    res.status_code = 401
    return res

@login_required
@never_cache
def github_username_watched_refresh(request,username, link_type):
    repo_link_type, _ = LinkType.objects.get_or_create(name = link_type)
    user = request.user
    username = urllib.unquote(username)
    try:
        github_username = user.social_auth.get(provider='github').extra_data['username']
        if username == github_username:
            profile = user.get_profile()
            profile.save()
            try:
                links = profile.userrepositorylink_set.filter(link_type = repo_link_type).filter(repository__host='github')
            except ObjectDoesNotExist:
                pass
            links.delete()
            if repo_link_type.name == "owned":
                return HttpResponseRedirect(reverse('github_username_owned', kwargs={'username': username}))
            elif repo_link_type.name == "starred":
                return HttpResponseRedirect(reverse('github_username_starred', kwargs={'username': username}))
            elif repo_link_type.name == "watched":
                return HttpResponseRedirect(reverse('github_username_watched', kwargs={'username': username}))
    except ObjectDoesNotExist:
        pass
    res = HttpResponse("Unauthorized")
    res.status_code = 401
    return res

def github_username_category_watched(request,username,category, link_type):
    """has all github repos and the latest 30 events for a username with a specific category"""
    owned = False
    starred = False
    repo_link_type, _ = LinkType.objects.get_or_create(name = link_type)
    if request.GET.get('sorted_by_watchers', 'false') == 'true':
        sorted_by_watchers = True
    username = urllib.unquote(username)
    category = urllib.unquote(category).lower()
    user = request.user
    github_provider = GithubProvider(user)
    watched_filtered, repository_user = github_provider.retrieve_category_repositories(username, category, link_type)
    repository_user.save()
    if len(watched_filtered) == 0:
        watched = github_provider.get_repositories(username, link_type)
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
            if repository.language.lower() == category:
                watched_filtered.append(repository)
                if not repository.private:
                    count += 1
            if not repository.private:
                RepositoryUserRepositoryLink.objects.get_or_create(user = repository_user, repository = repository, link_type = repo_link_type)
        RepositoryCategory.objects.get_or_create(name = category.lower())
        if repo_link_type.name == "owned":
            pass
        elif repo_link_type.name == "starred":
            repository_user.starred = count
        elif repo_link_type.name == "watched":
            repository_user.watched = count
        repository_user.save()
        watched_filtered.sort(key=lambda x: x.watchers, reverse = True)
    if repo_link_type.name == "owned":
        owned = True
    elif repo_link_type.name == "starred":
        starred = True
    elif repo_link_type.name == "watched":
        pass
    # Get repository events
    repo_events = []
#    page = 0
#    watched_filtered_length = len(watched_filtered)
#    user_path = False
#    if owned:
#        if repository_user is not None and repository_user.public_repos is not None and float(repository_user.public_repos) < 0.5*(watched_filtered_length**2):
#            user_path = True
#    else:
#        if repository_user is not None and repository_user.watched is not None and float(repository_user.watched) < 0.5*(watched_filtered_length**2):
#            user_path = True
#    if user_path:
#        while len(repo_events) < 30 and page <= watched_filtered_length:
#            page += 1
#            r = requests.get('https://api.github.com/users/'+ username + '/received_events', params = {'page':page})
#            try:
#                user_events = json.loads(r.text)
#            except ValueError:
#                user_events = []
#            for user_event in user_events:
#                for watched_filter in watched_filtered:
#                    if user_event['repo']['name'] == watched_filter.slug:
#                        repo_events.append(user_event)
#        repo_events = repo_events[:30]
#    else:
    repo_events = github_provider.get_repositories_events(watched_filtered)
    return render_to_response('github_username_category_watched.html', {'username': username, 'watched':watched_filtered, 'category':category, 'repo_events':repo_events,'owned':owned,"starred":starred},context_instance=RequestContext(request))

@ajax_required
@never_cache
def github_username_category_watched_save(request, username, category, link_type):
    username = urllib.unquote(username)
    user = request.user
    category = urllib.unquote(category).lower()
    try:
        if user.is_authenticated() and username == user.social_auth.get(provider='github').extra_data['username']:
            profile = user.get_profile()
            profile.save()
            try:
                updated_list = json.loads(request.POST["order"])
            except ValueError:
                updated_list =[]
            updated_dictionary = {category:updated_list}
            github_provider = GithubProvider(user)
            github_provider.save_repositories(updated_dictionary, link_type)
            data= {'outcome': 'success'}
            return HttpResponse(json.dumps(data),mimetype="application/json")
    except ObjectDoesNotExist:
        pass
    res = HttpResponse("Unauthorized")
    res.status_code = 401
    return res

@login_required
@never_cache
def github_username_category_watched_update(request,username,category, link_type):
    category = urllib.unquote(category).lower()
    username = urllib.unquote(username)
    user = request.user
    try:
        github_username = user.social_auth.get(provider='github').extra_data['username']
        repository_user = None
        if username == github_username:
            profile = user.get_profile()
            profile.save()
            github_provider = GithubProvider(user)
            repository_user = github_provider.update_category_repositories(username, category, link_type)
            repository_user.save()
            if link_type == "owned":
                return HttpResponseRedirect(reverse('github_username_category_owned', kwargs={'username': username,'category':category}))
            elif link_type == "starred":
                return HttpResponseRedirect(reverse('github_username_category_starred', kwargs={'username': username,'category':category}))
            elif link_type == "watched":
                return HttpResponseRedirect(reverse('github_username_category_watched', kwargs={'username': username,'category':category}))
    except ObjectDoesNotExist:
        pass
    res = HttpResponse("Unauthorized")
    res.status_code = 401
    return res

@login_required
@never_cache
def github_username_category_watched_refresh(request,username,category, link_type):
    category = urllib.unquote(category).lower()
    username = urllib.unquote(username)
    user = request.user
    try:
        github_username = user.social_auth.get(provider='github').extra_data['username']
        if username == github_username:
            repo_link_type, _ = LinkType.objects.get_or_create(name = link_type)
            profile = user.get_profile()
            profile.save()
            links = profile.userrepositorylink_set.filter(repository_category__name__iexact=category).filter(link_type = repo_link_type).filter(repository__host='github')
            links.delete()
            username = user.social_auth.get(provider='github').extra_data['username']
            if repo_link_type.name == "owned":
                return HttpResponseRedirect(reverse('github_username_category_owned', kwargs={'username': username,'category':category}))
            elif repo_link_type.name == "starred":
                return HttpResponseRedirect(reverse('github_username_category_starred', kwargs={'username': username,'category':category}))
            elif repo_link_type.name == "watched":
                return HttpResponseRedirect(reverse('github_username_category_watched', kwargs={'username': username,'category':category}))
    except ObjectDoesNotExist:
        pass
    res = HttpResponse("Unauthorized")
    res.status_code = 401
    return res

def github_repo(request, owner, repo):
    owner = urllib.unquote(owner)
    repo = urllib.unquote(repo)
    user = request.user
    github_provider = GithubProvider(user)
    # check to see if the repo is being watched by the authed user or not
    watched = github_provider.get_watched_status(owner, repo)
    starred = github_provider.get_starred_status(owner, repo)
    update = False
    try:
        repository = github_provider.retrieve_repository_details(owner, repo)
    except ObjectDoesNotExist:
        update = True
        repository = Repository()
    if update or (datetime.now() - repository.last_modified) > timedelta(days = 1):
        repository_dict = github_provider.get_repository_details(owner, repo)
        repository = github_provider.create_or_update_repository_details(repository_dict, repository)
        if not repository.private:
            repository.save()
    repo_events = github_provider.get_repository_events(owner, repo)
    return render_to_response('github_repo.html', {'repository': repository, 'repo_events': repo_events, 'watched':watched, 'starred':starred}, RequestContext(request))

@ajax_required
@never_cache
def github_repo_watch(request, owner, repo):
    user = request.user
    if user.is_authenticated():
        try:
            github_provider = GithubProvider(user)
            github_provider.watch(owner, repo)
            data= {'outcome':'success'}
            github_username = None
            bitbucket_username = None
            try:
                github_username = user.social_auth.get(provider='github').extra_data['username']
                github_prefix = github_username
            except:
                github_prefix = ''
            try:
                bitbucket_username = user.social_auth.get(provider='bitbucket').extra_data['username']
                bitbucket_prefix=bitbucket_username
            except:
                bitbucket_prefix = ''
            custom_prefix = '.'.join((hashlib.md5(github_prefix).hexdigest(),hashlib.md5(bitbucket_prefix).hexdigest()))
            expire_view_cache('repowatcher.main.views.github_repo', kwargs = {'owner':owner,'repo':repo}, key_prefix=custom_prefix)
            return HttpResponse(json.dumps(data),mimetype="application/json")
        except ObjectDoesNotExist:
            pass
    res = HttpResponse("Unauthorized")
    res.status_code = 401
    return res

@ajax_required
@never_cache
def github_repo_star(request, owner, repo):
    user = request.user
    if user.is_authenticated():
        try:
            github_provider = GithubProvider(user)
            github_provider.star(owner, repo)
            data= {'outcome':'success'}
            github_username = None
            bitbucket_username = None
            try:
                github_username = user.social_auth.get(provider='github').extra_data['username']
                github_prefix = github_username
            except:
                github_prefix = ''
            try:
                bitbucket_username = user.social_auth.get(provider='bitbucket').extra_data['username']
                bitbucket_prefix=bitbucket_username
            except:
                bitbucket_prefix = ''
            custom_prefix = '.'.join((hashlib.md5(github_prefix).hexdigest(),hashlib.md5(bitbucket_prefix).hexdigest()))
            expire_view_cache('repowatcher.main.views.github_repo', kwargs = {'owner':owner,'repo':repo}, key_prefix=custom_prefix)
            return HttpResponse(json.dumps(data),mimetype="application/json")
        except ObjectDoesNotExist:
            pass
    res = HttpResponse("Unauthorized")
    res.status_code = 401
    return res

@ajax_required
@never_cache
def github_repo_unwatch(request, owner, repo):
    repo_link_type, _ = LinkType.objects.get_or_create(name = "watched")
    user = request.user
    if user.is_authenticated():
        try:
            host_slug = ('/'.join(('github',owner,repo))).lower()
            profile = user.get_profile()
            repository = Repository.objects.get(host_slug= host_slug)
            UserRepositoryLink.objects.filter(user = profile).filter(repository = repository).filter(link_type = repo_link_type).delete()
            github_provider = GithubProvider(user)
            github_provider.unwatch(owner, repo)
            data= {'outcome':'success'}
            github_username = None
            bitbucket_username = None
            try:
                github_username = user.social_auth.get(provider='github').extra_data['username']
                github_prefix = github_username
            except:
                github_prefix = ''
            try:
                bitbucket_username = user.social_auth.get(provider='bitbucket').extra_data['username']
                bitbucket_prefix=bitbucket_username
            except:
                bitbucket_prefix = ''
            custom_prefix = '.'.join((hashlib.md5(github_prefix).hexdigest(),hashlib.md5(bitbucket_prefix).hexdigest()))
            expire_view_cache('repowatcher.main.views.github_repo', kwargs = {'owner':owner,'repo':repo}, key_prefix=custom_prefix)
            return HttpResponse(json.dumps(data),mimetype="application/json")
        except ObjectDoesNotExist:
            pass
    res = HttpResponse("Unauthorized")
    res.status_code = 401
    return res

@ajax_required
@never_cache
def github_repo_unstar(request, owner, repo):
    repo_link_type, _ = LinkType.objects.get_or_create(name = "starred")
    user = request.user
    if user.is_authenticated():
        try:
            host_slug = ('/'.join(('github',owner,repo))).lower()
            profile = user.get_profile()
            repository = Repository.objects.get(host_slug= host_slug)
            UserRepositoryLink.objects.filter(user = profile).filter(repository = repository).filter(link_type = repo_link_type).delete()
            github_provider = GithubProvider(user)
            github_provider.unstar(owner, repo)
            data= {'outcome':'success'}
            github_username = None
            bitbucket_username = None
            try:
                github_username = user.social_auth.get(provider='github').extra_data['username']
                github_prefix = github_username
            except:
                github_prefix = ''
            try:
                bitbucket_username = user.social_auth.get(provider='bitbucket').extra_data['username']
                bitbucket_prefix=bitbucket_username
            except:
                bitbucket_prefix = ''
            custom_prefix = '.'.join((hashlib.md5(github_prefix).hexdigest(),hashlib.md5(bitbucket_prefix).hexdigest()))
            expire_view_cache('repowatcher.main.views.github_repo', kwargs = {'owner':owner,'repo':repo}, key_prefix=custom_prefix)
            return HttpResponse(json.dumps(data),mimetype="application/json")
        except ObjectDoesNotExist:
            pass
    res = HttpResponse("Unauthorized")
    res.status_code = 401
    return res

@cache_control(max_age=60 * 60 * 24)
def github_watched_popular(request):
    repositories_by_language = defaultdict(list)
    repositories = Repository.objects.filter(watchers__isnull=False).filter(private=False).filter(host='github')[:50]
    for repository in repositories:
        repositories_by_language[repository.language].append(repository)
    return render_to_response('github_watched_popular.html', {'repositories_by_language':sorted(dict(repositories_by_language).iteritems(),key=lambda (k, v): len(v),reverse = True)},context_instance=RequestContext(request))

@cache_control(max_age=60 * 60 * 24)
def github_watched_language_popular(request, language):
    language = urllib.unquote(language.lower())
    repositories = Repository.objects.filter(language=language).filter(watchers__isnull=False).filter(private=False).filter(host='github')[:20]
    return render_to_response('github_watched_language_popular.html', {'language':language, 'repositories':repositories}, context_instance=RequestContext(request))

