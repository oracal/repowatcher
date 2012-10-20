from GithubProvider import GithubProvider
from collections import defaultdict
from datetime import timedelta, datetime
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from django.views.decorators.cache import never_cache, cache_control
from oauth_hook import OAuthHook
from repowatcher.main.models import RepositoryCategory, Repository
from urllib import urlencode, quote
import json
import logging
import requests
import urllib
logger = logging.getLogger(__name__)

OAuthHook.consumer_key = settings.BITBUCKET_CONSUMER_KEY
OAuthHook.consumer_secret = settings.BITBUCKET_CONSUMER_SECRET

@never_cache
def index(request):
    """Home view, displays login mechanism"""
    if request.user.is_authenticated():
        return HttpResponseRedirect(reverse('repowatcher.main.views.authed'))
    else:
        return render_to_response('index.html', {}, RequestContext(request))

def about(request):
    used = [Repository(owner='django', name='django', host='github'),
            Repository(owner='omab', name='django-social-auth', host='github'),
            Repository(owner='copitux', name='python-github3', host='github'),
            Repository(owner='kennethreitz', name='requests', host='github'),
            Repository(owner='maraujop', name='requests-oauth',host='github'),
            Repository(owner='jquery', name='jquery', host='github'),
            Repository(owner='jquery', name='jquery-ui', host='github'),
            Repository(owner='twitter', name='bootstrap', host='github'),
            Repository(owner='desandro', name='masonry', host='github'),
            Repository(owner='rmm5t', name='jquery-timeago', host='github'),
            Repository(owner='ask', name='celery', host='github'),
            Repository(owner='ask', name='django-celery', host='github'),
            Repository(owner='andymccurdy', name='redis-py', host='github'),
            Repository(owner='sebleier', name='django-redis-cache', host='github'),
            Repository(owner='jackmoore', name='colorbox', host='github')
            ]
    return render_to_response('about.html', {'used': used}, context_instance=RequestContext(request))


@cache_control(max_age=60 * 60 * 24)
def typeahead(request, value = None):
    if value is None:
        repositories = Repository.objects.filter(private=False).values('name').distinct()
        users = Repository.objects.filter(private=False).values('owner').distinct()
    else:
        repositories = Repository.objects.filter(private=False).filter(name__contains=value).values('name').distinct()
        users = Repository.objects.filter(private=False).filter(owner__contains=value).values('owner').distinct()
    typeahead_list = []
    for repository in repositories:
        typeahead_list.append(repository['name'])
    for user in users:
        typeahead_list.append(user['owner'])
    return HttpResponse(json.dumps(typeahead_list), mimetype="application/json")


@cache_control(max_age=60 * 60 * 24)
def search(request):
    user = request.user
    query = request.GET['query']
    repositories_by_language = defaultdict(list)
    if query != '':
        github_provider = GithubProvider(user)
        if user.is_authenticated():
            try:
                tokens = user.social_auth.get(provider='bitbucket').tokens
                oauth_hook = OAuthHook(tokens['oauth_token'], tokens['oauth_token_secret'], header_auth=False)
                client = requests.session(hooks={'pre_request': oauth_hook})
            except ObjectDoesNotExist:
                client = requests.session()
        else:
            client = requests.session()
        if '/' in query:
            user_query = query.split('/')[0]
            repo_query = query.split('/')[1]
            github_repositories = github_provider.search_repository(repo_query)
            users = github_provider.search_user(user_query)
            try:
                response = client.get('https://api.bitbucket.org/1.0/repositories/',params={'name':repo_query,'limit':100})
                bitbucket_repositories = json.loads(response.text)['repositories'][:100]
            except Exception:
                bitbucket_repositories = []
        else:
            github_repositories = github_provider.search_repository(query)
            users = github_provider.search_user(query)
            try:
                response = client.get('https://api.bitbucket.org/1.0/repositories/',params={'name':query,'limit':100})
                bitbucket_repositories = json.loads(response.text)['repositories'][:100]
            except Exception:
                bitbucket_repositories = []
        for repo in github_repositories:
            update = False
            repo['owner'] = repo['owner'].lower().replace("/", "")
            repo['name'] = repo['name'].lower().replace("/", "")
            try:
                repository = Repository.objects.get(slug= repo['owner'].lower() + '/' + repo['name'], host ='github')
            except ObjectDoesNotExist:
                update = True
                repository = Repository()
            if update or (datetime.now() - repository.last_modified) > timedelta(days = 1):
                repository = github_provider.create_or_update_repository_details(repo, repository)
                if not repository.private:
                    repository.save()
            repositories_by_language[repository.language].append(repository)
        for repo in bitbucket_repositories:
            update = False
            repo['owner'] = repo['owner'].lower().replace("/", "")
            repo['name'] = repo['name'].lower().replace("/", "")
            try:
                repository = Repository.objects.get(slug= repo['owner'] + '/' + repo['name'], host='bitbucket')
            except ObjectDoesNotExist:
                update = True
                repository = Repository()
            if update or (datetime.now() - repository.last_modified) > timedelta(days = 1):
                extra_data = {}
                key_map={'owner':'owner','name':'name', 'website':'homepage','language':'language','description':'description','created_on':'created_at','last_updated':'pushed_at','scm':'scm','is_private':'private'}
                for key,value in repo.iteritems():
                    if key in ['owner','name', 'website','language','description','created_on','last_updated','scm','is_private']:
                        setattr(repository,key_map[key],value)
                    else:
                        extra_data[key] = value
                repository.extra_data = json.dumps(extra_data)
                if repository.language == "" or repository.language == None:
                    repository.language = "other"
                repository.host ='bitbucket'
                if not repository.private:
                    repository.save()
            for category in repositories_by_language.keys():
                RepositoryCategory.objects.get_or_create(name = category)
            repositories_by_language[repository.language].append(repository)
        return render_to_response('search.html', {'repositories_by_language':sorted(dict(repositories_by_language).iteritems(),key=lambda (k, v): len(v),reverse = True), 'users':users},context_instance=RequestContext(request))
    else:
        return render_to_response('search.html', {'repositories_by_language':{}, 'users':[]},context_instance=RequestContext(request))


@cache_control(max_age=60 * 60 * 24)
def watched_popular(request):
    repositories_by_language = defaultdict(list)
    repositories = Repository.objects.filter(watchers__isnull=False).filter(private=False).all()[:50]
    for repository in repositories:
        repositories_by_language[repository.language].append(repository)
    return render_to_response('watched_popular.html', {'repositories_by_language':sorted(dict(repositories_by_language).iteritems(),key=lambda (k, v): len(v),reverse = True)},context_instance=RequestContext(request))

@cache_control(max_age=60 * 60 * 24)
def watched_language_popular(request, language):
    language = urllib.unquote(language.lower())
    repositories = Repository.objects.filter(language=language).filter(watchers__isnull=False).filter(private=False).all()[:20]
    return render_to_response('watched_language_popular.html', {'language':language, 'repositories':repositories},context_instance=RequestContext(request))
