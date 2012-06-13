from ProviderBase import ProviderBase
from datetime import datetime
from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404
from oauth_hook.hook import OAuthHook
from operator import itemgetter
from repowatcher.main.models import RepositoryUser, Repository
from repowatcher.main.tasks import get_events
import json
import requests


class BitbucketProvider(ProviderBase):
    
    def __init__(self, user):
        self.user = user
        self.tokens = None
        self.host = 'bitbucket'
        if user.is_authenticated():
            try:
                self.tokens = user.social_auth.get(provider=self.host).tokens
                oauth_hook = OAuthHook(self.tokens['oauth_token'], self.tokens['oauth_token_secret'], header_auth=False)
                self.client = requests.session(hooks={'pre_request': oauth_hook})
            except ObjectDoesNotExist:
                self.client = requests.session()
        else:
            self.client = requests.session()

    def get_user_details(self, username):
        try:
            user_dict = json.loads(self.client.get('https://api.bitbucket.org/1.0/users/%s/'%(username,)).text)['user']
        except Exception:
            user_dict = {}
        return user_dict
    
    def create_or_update_user_details(self, user_dict, repository_user = None):
        extra_data = {}
        if repository_user is None:
            repository_user = RepositoryUser()
        if ('first_name' in user_dict and user_dict['first_name']!='')  or ('last_name' in user_dict and user_dict['last_name']!=''):
            if 'first_name' in user_dict and user_dict['first_name']!='' and 'last_name' in user_dict and user_dict['last_name']!='':
                repository_user.name = ' '.join((user_dict['first_name'],user_dict['last_name']))
            elif 'first_name' in user_dict and user_dict['first_name']!='':
                repository_user.name = user_dict['first_name']
            elif 'last_name' in user_dict and user_dict['last_name']!='':
                repository_user.name = user_dict['last_name']
        for key,value in user_dict.iteritems():
                    
            if key == 'username':
                repository_user.login = value
            elif key =='first_name':
                pass
            elif key =='last_name':
                pass
            else:
                if isinstance(value, datetime):
                    extra_data[key] = value.__str__()
                else:
                    extra_data[key] = value
                    
        repository_user.extra_data = json.dumps(extra_data)
        repository_user.host = self.host
        return repository_user
    
    def retrieve_user_details(self, username):
        return RepositoryUser.objects.get(slug=self.host+'/'+username)

    def get_user_events(self, username):
        r = self.client.get('https://api.bitbucket.org/1.0/users/%s/events/'%(username.lower(),))
        try:
            user_events = json.loads(r.text)['events']
        except ValueError:
            user_events = []
        return user_events

    def get_repository_details(self, owner, repository):
        try:
            response = self.client.get('https://api.bitbucket.org/1.0/repositories/%s/%s/' % (owner.lower(), repository.lower()))
            repository_dict = json.loads(response.text)
        except Exception:
            raise Http404
        return repository_dict
  
    def create_or_update_repository_details(self, repository_dict, repository = None):
        extra_data = {}
        if repository is None:
            repository = Repository()
        key_map={'owner':'owner','name':'name', 'website':'homepage','language':'language','description':'description','created_on':'created_at','last_updated':'pushed_at','scm':'scm','is_private':'private', 'followers_count':'watchers'}
        keys = key_map.keys()
        for key,value in repository_dict.iteritems():
            if key in keys:
                setattr(repository,key_map[key],value)
            else:
                extra_data[key] = value
                    
        repository.extra_data = json.dumps(extra_data)
        if repository.language == "" or repository.language == None:
            repository.language = "other"
        repository.language = repository.language.lower()
        repository.host =self.host
        return repository

    def retrieve_repository_details(self, owner, repository):
        host_slug = '/'.join((self.host,owner,repository))
        repo = Repository.objects.get(host_slug= host_slug)
        return repo
    
    def get_repository_events(self, owner, repository):
        try:
            response = self.client.get('https://api.bitbucket.org/1.0/repositories/%s/%s/events/'%(owner.lower(),repository.lower()))
            repo_events = json.loads(response.text)['events']
        except Exception:
            repo_events =[]
        return repo_events

    def get_repositories_events(self, repository_list):
        repo_events = []
        request_urls = []
        url_requests = []
        for repo in repository_list:
            request_urls.append('https://api.bitbucket.org/1.0/repositories/%s/%s/events/'%(repo.owner.lower(),repo.name.lower()))
        for url in request_urls:
            url_requests.append(get_events.delay(url))
        for url_request in url_requests:
            get = url_request.get()
            if get is not None:
                repo_events.extend(get['events'][:30])
        repo_events = sorted(repo_events,key=itemgetter('created_on'), reverse = True)[:30]
        return repo_events

    def get_repositories(self, username, owned):
        repositories = []
        if owned:
            try:
                response = json.loads(self.client.get('https://api.bitbucket.org/1.0/users/%s/'%(username,)).text)
                repositories = response['repositories']
            except Exception:
                pass
        else:
            try:
                response = self.client.get('https://api.bitbucket.org/1.0/user/follows/')
                repositories = json.loads(response.text)
            except Exception:
                pass
        
        return repositories
        
    def get_watched_repositories(self, username):
        return self.get_repositories(username = username,owned = False)

    def get_owned_repositories(self, username):
        return self.get_repositories(username = username,owned = True)

    def retrieve_watched_repositories_list(self, username):
        return self.retrieve_repositories_list(username = username, owned = False)

    def retrieve_owned_repositories_list(self, username):
        return self.retrieve_repositories_list(username = username, owned = True)

    def retrieve_watched_repositories_dict(self, username):
        return self.retrieve_repositories_dict(username = username, owned = False)

    def retrieve_owned_repositories_dict(self, username):
        return self.retrieve_repositories_dict(username = username, owned = True)

    def search_repository(self, repository):
        try:
            response = self.client.get('https://api.bitbucket.org/1.0/repositories/',params={'name':repository,'limit':100})
            bitbucket_repositories = json.loads(response.text)['repositories'][:100]
        except Exception:
            bitbucket_repositories = []
        return bitbucket_repositories
