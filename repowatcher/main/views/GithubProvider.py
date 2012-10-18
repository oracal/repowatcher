from ProviderBase import ProviderBase
from django.conf import settings
from datetime import datetime
from django.core.exceptions import ObjectDoesNotExist
from operator import itemgetter
from pygithub3 import Github
from pygithub3.exceptions import NotFound
from repowatcher.main.models import RepositoryUser, Repository
from repowatcher.main.tasks import get_events
import json
import logging
import requests
from django.http import Http404
logger = logging.getLogger(__name__)

class GithubProvider(ProviderBase):

    base_url = "https://api.github.com/"


    def __init__(self, user):
        self.user = user
        self.host = 'github'
        self.access_token = None
        if user.is_authenticated():
            try:
                self.access_token=user.social_auth.get(provider=self.host).extra_data['access_token']
                self.client = Github(token=self.access_token)
            except ObjectDoesNotExist:
                self.client = Github(client_id=settings.GITHUB_APP_ID, client_secret=settings.GITHUB_API_SECRET)
        else:
            self.client = Github(client_id=settings.GITHUB_APP_ID, client_secret=settings.GITHUB_API_SECRET)

    def get_user_details(self, username):
        try:
            github_user = self.client.users.get(username)
            return vars(github_user)
        except:
            raise Http404

    def create_or_update_user_details(self, user_dict, repository_user = None):
        if repository_user is None:
            repository_user = RepositoryUser()
        extra_data = {}
        for key, value in user_dict.iteritems():
            if key == "_attrs":
                continue
            if key in ['login', 'name', 'email', 'blog','following','followers','public_repos','created_at']:
                setattr(repository_user, key, value)
            else:
                if isinstance(value, datetime):
                    extra_data[key] = value.__str__()
                else:
                    extra_data[key] = value
        repository_user.extra_data = json.dumps(extra_data)
        repository_user.host = self.host
        return repository_user

    def retrieve_user_details(self, username):
        return RepositoryUser.objects.get(slug=self.host+'/'+username.lower())

    def get_user_events(self, username):
        try:
            r = requests.get(GithubProvider.base_url + 'users/'+ username + '/events', params = {"client_id": settings.GITHUB_APP_ID, "client_secret": settings.GITHUB_API_SECRET})
            user_events = json.loads(r.text)
        except Exception:
            user_events = []
        return user_events

    def get_repository_details(self, owner, repository):
        try:
            repo = self.client.repos.get(user=owner,repo=repository)
            return vars(repo)
        except NotFound:
            raise Http404

    def create_or_update_repository_details(self, repository_dict, repository = None):
        if repository is None:
            repository = Repository()
        extra_data = {}
        for key, value in repository_dict.iteritems():
            if key == "_attrs":
                continue
            if key == 'owner' or key == "organization":
                try:
                    setattr(repository, key, value.login)
                    continue
                except Exception:
                    pass
            if key == 'source' or key == "parent":
                try:
                    setattr(repository, key, value.full_name)
                    continue
                except Exception:
                    pass
            if key in ['owner', 'name', 'html_url', 'homepage', 'language','description','watchers','created_at','pushed_at','private']:
                setattr(repository, key, value)
            else:
                if isinstance(value, datetime):
                    extra_data[key] = value.__str__()
                else:
                    extra_data[key] = value
        repository.extra_data = json.dumps(extra_data)
        if repository.language == "" or repository.language == None:
            repository.language = "other"
        repository.scm = 'git'
        repository.host =self.host
        repository.language = repository.language.lower()
        return repository

    def retrieve_repository_details(self, owner, repository):
        host_slug = ('/'.join((self.host, owner, repository))).lower()
        return Repository.objects.get(host_slug=host_slug)

    def get_repository_events(self, owner, repository):
        slug = (owner + '/' + repository).lower()
        try:
            r = requests.get('https://api.github.com/repos/'+ slug + '/events', params = {"client_id": settings.GITHUB_APP_ID, "client_secret": settings.GITHUB_API_SECRET})
            repo_events = json.loads(r.text)
        except Exception:
            repo_events = []
        return repo_events

    def get_repositories_events(self, repository_list):
        repo_events = []
        request_urls = []
        url_requests = []
        for repository in repository_list:
            slug = '/'.join((repository.owner, repository.name))
            request_urls.append(GithubProvider.base_url + 'repos/' + slug + '/events' + '?client_id=' + settings.GITHUB_APP_ID + '&client_secret=' + settings.GITHUB_API_SECRET)
        for url in request_urls:
            url_requests.append(get_events.delay(url))
        for url_request in url_requests:
            get = url_request.get()
            if get is not None:
                repo_events.extend(get[:30])
        repo_events = sorted(repo_events, key=itemgetter('created_at'), reverse = True)[:30]
        return repo_events

    def get_repositories(self, username, owned, starred = True):
        if owned:
            generator = self.client.repos.list(user=username)
        elif starred:
            generator = self.client.repos.stargazers.list_repos(user=username)
        else:
            generator = self.client.repos.watchers.list_repos(user=username)
        for repository in generator.iterator():
            repository_dict = vars(repository)
            repository_dict['owner'] = repository.owner.login
            yield repository_dict

    def get_watched_status(self, owner, repository, starred = True):
        watched = False
        if self.user.is_authenticated():
            try:
                if starred:
                    watched = self.client.repos.stargazers.is_starring(owner, repository)
                else:
                    watched = self.client.repos.watchers.is_watching(owner, repository)
            except Exception:
                pass
        return watched

    def watch(self, owner, repository, starred = True):
        if starred:
            self.client.repos.stargazers.star(owner, repository)
        else:
            self.client.repos.watchers.watch(owner, repository)


    def unwatch(self, owner, repository, starred = True):
        if starred:
            self.client.repos.stargazers.unstar(owner, repository)
        else:
            self.client.repos.watchers.unwatch(owner, repository)

    def search_user(self, username):
        if self.access_token is None:
            params = {"client_id": settings.GITHUB_APP_ID, "client_secret": settings.GITHUB_API_SECRET}
        else:
            params = {'access_token': self.access_token}
        try:
            r = requests.get(GithubProvider.base_url + 'legacy/user/search/'+ username,params = params)
            user_results = json.loads(r.text)['users']
        except Exception:
            user_results = []
        return user_results

    def search_repository(self, repository):
        if self.access_token is None:
            params = {"client_id": settings.GITHUB_APP_ID, "client_secret": settings.GITHUB_API_SECRET}
        else:
            params = {'access_token': self.access_token}
        try:
            r = requests.get(GithubProvider.base_url + 'legacy/repos/search/'+ repository, params = params)
            repository_results = json.loads(r.text)['repositories']
        except Exception:
            repository_results = []
        return repository_results
