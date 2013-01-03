from abc import ABCMeta, abstractmethod
from collections import defaultdict
from datetime import datetime, timedelta
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.aggregates import Max, Min
from repowatcher.main.models import RepositoryUser, RepositoryCategory, \
    Repository, UserRepositoryLink, RepositoryUserRepositoryLink, LinkType
import logging
import urllib
logger = logging.getLogger(__name__)

class ProviderBase(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def get_user_details(self, username):
        return

    @abstractmethod
    def create_or_update_user_details(self, user_dict, repository_user = None):
        return

    @abstractmethod
    def retrieve_user_details(self, username):
        return

    @abstractmethod
    def get_user_events(self, username):
        return

    @abstractmethod
    def get_repository_details(self, owner, repository):
        return

    @abstractmethod
    def create_or_update_repository_details(self, repository_dict, repository = None):
        return

    @abstractmethod
    def retrieve_repository_details(self, owner, repository):
        return

    @abstractmethod
    def get_repository_events(self, owner, repository):
        return

    @abstractmethod
    def get_repositories_events(self, repository_list):
        return

    @abstractmethod
    def get_repositories(self, username, owned, link_type):
        return

    def get_watched_repositories(self, username):
        return self.get_repositories(username = username, link_type = "watched")

    def get_owned_repositories(self, username):
        return self.get_repositories(username = username, link_type = "owned")

    def get_starred_repositories(self, username):
        return self.get_repositories(username = username, link_type = "starred")

    def save_repositories(self, repositories_dict, link_type):
        profile = self.user.get_profile()
        for category_name,value in repositories_dict.iteritems():
            update = False
            if category_name == '':
                category_name = 'other'
            repository_category,_ = RepositoryCategory.objects.get_or_create(name = category_name)
            for order, item in enumerate(value,start=1):
                if item !='':
                    try:
                        repository = Repository.objects.get(host_slug=self.host+'/'+item.lower())
                    except ObjectDoesNotExist:
                        repository = Repository()
                        update = True
                    if update or (datetime.now() - repository.last_modified) > timedelta(days = 1):
                        owner, repository_name = item.split('/')
                        repository_dict = self.get_repository_details(owner, repository_name)
                        repository = self.create_or_update_repository_details(repository_dict, repository)
                        if not repository.private:
                            repository.save()
                    repo_link_type, _ = LinkType.objects.get_or_create(name = link_type)
                    try:
                        user_repository_link = UserRepositoryLink.objects.get(user = profile,repository = repository, link_type = repo_link_type)
                    except ObjectDoesNotExist:
                        user_repository_link = UserRepositoryLink(user = profile,repository = repository, link_type = repo_link_type)
                    user_repository_link.repository_category = repository_category
                    user_repository_link.order = order
                    user_repository_link.save()

    def save_watched_repositories(self, repositories_dict):
        self.save_repositories(repositories_dict = repositories_dict, link_type = "watched")

    def save_owned_repositories(self, repositories_dict):
        self.save_repositories(repositories_dict = repositories_dict, link_type = "owned")

    def save_starred_repositories(self, repositories_dict):
        self.save_repositories(repositories_dict = repositories_dict, link_type = "starred")

    def retrieve_repositories_list(self, username, link_type):
        repositories = []
        api_only = True
        repo_link_type, _ = LinkType.objects.get_or_create(name = link_type)
        if self.user.is_authenticated():
            try:
                if username == self.user.social_auth.get(provider=self.host).extra_data['username']:
                    profile = self.user.get_profile()
                    links = profile.userrepositorylink_set.filter(link_type = repo_link_type).filter(repository__host=self.host).select_related('repository').select_related('repository','repository_category')
                    if len(links) != 0:
                        for link in links:
                            repositories.append(link.repository)
                        api_only = False
                    else:
                        api_only = True
            except ObjectDoesNotExist:
                pass
        try:
            repository_user = RepositoryUser.objects.get(slug=self.host+'/'+username.lower())
            if api_only:
                repository_links = repository_user.repositoryuserrepositorylink_set.filter(link_type = repo_link_type).filter(repository__host=self.host).select_related('repository')
                oldest_modification = repository_links.aggregate(oldest_modification=Min('last_modified'))['oldest_modification']
                repository_links_size = len(repository_links)
                if repository_links_size==0 or (datetime.now() - oldest_modification) > timedelta(days = 1):
                    repository_links.delete()
                else:
                    if repo_link_type.name == "owned":
                        pass
                    elif repo_link_type.name == "starred":
                        repository_user.starred = repository_links_size
                    elif repo_link_type.name == "watched":
                        repository_user.watched = repository_links_size
                    for repository_link in repository_links:
                        repositories.append(repository_link.repository)
        except ObjectDoesNotExist:
            user_dict = self.get_user_details(username)
            repository_user = self.create_or_update_user_details(user_dict)
        return repositories, repository_user

    def retrieve_repositories_dict(self, username, link_type):
        repositories_by_language = defaultdict(list)
        repo_link_type, _ = LinkType.objects.get_or_create(name = link_type)
        api_only = True
        if self.user.is_authenticated():
            try:
                if username == self.user.social_auth.get(provider=self.host).extra_data['username']:
                    profile = self.user.get_profile()
                    links = profile.userrepositorylink_set.filter(link_type = repo_link_type).filter(repository__host=self.host).select_related('repository').select_related('repository','repository_category')
                    if len(links) != 0:
                        for link in links:
                            repositories_by_language[link.repository_category.name].append(link.repository)
                        api_only = False
                    else:
                        api_only = True
            except ObjectDoesNotExist:
                pass
        try:
            repository_user = RepositoryUser.objects.get(slug=self.host+'/'+username.lower())
            if api_only:
                repository_links = repository_user.repositoryuserrepositorylink_set.filter(link_type = repo_link_type).filter(repository__host=self.host).select_related('repository')
                oldest_modification = repository_links.aggregate(oldest_modification=Min('last_modified'))['oldest_modification']
                if len(repository_links)==0 or (datetime.now() - oldest_modification) > timedelta(days = 1):
                    repository_links.delete()
                else:
                    for repository_link in repository_links:
                        repositories_by_language[repository_link.repository.language].append(repository_link.repository)
        except ObjectDoesNotExist:
            user_dict = self.get_user_details(username)
            repository_user = self.create_or_update_user_details(user_dict)
        return repositories_by_language, repository_user

    def retrieve_watched_repositories_list(self, username):
        return self.retrieve_repositories_list(username = username, link_type = "watched")

    def retrieve_starred_repositories_list(self, username):
        return self.retrieve_repositories_list(username = username, link_type = "starred")

    def retrieve_owned_repositories_list(self, username):
        return self.retrieve_repositories_list(username = username, link_type = "owned")

    def retrieve_watched_repositories_dict(self, username):
        return self.retrieve_repositories_dict(username = username, link_type = "watched")

    def retrieve_owned_repositories_dict(self, username):
        return self.retrieve_repositories_dict(username = username, link_type = "owned")

    def retrieve_starred_repositories_dict(self, username):
        return self.retrieve_repositories_dict(username = username, link_type = "starred")

    def retrieve_watched_category_repositories(self, username, category):
        return self.retrieve_category_repositories(username = username, category = category, link_type = "watched")

    def retrieve_owned_category_repositories(self, username, category):
        return self.retrieve_category_repositories(username = username, category = category, link_type = "owned")

    def retrieve_starred_repositories_dict(self, username):
        return self.retrieve_repositories_dict(username = username, link_type = "starred")

    def retrieve_starred_repositories_dict(self, username):
        return self.retrieve_repositories_dict(username = username, link_type = "starred")

    def retrieve_starred_category_repositories(self, username, category):
        return self.retrieve_category_repositories(username = username, category = category, link_type = "starred")


    def retrieve_category_repositories(self, username, category, link_type):
        repo_link_type, _ = LinkType.objects.get_or_create(name = link_type)
        watched_filtered = []
        username = urllib.unquote(username)
        api_only = True
        if self.user.is_authenticated():
            try:
                if username == self.user.social_auth.get(provider=self.host).extra_data['username']:
                    profile = self.user.get_profile()
                    links = profile.userrepositorylink_set.filter(link_type = repo_link_type).filter(repository__host=self.host).filter(repository_category__name__iexact=category).select_related('repository','repository_category')
                    if len(links)!=0:
                        for link in links:
                            watched_filtered.append(link.repository)
                        api_only = False
                    else:
                        api_only = True
            except ObjectDoesNotExist:
                pass
        try:
            repository_user = RepositoryUser.objects.get(slug=self.host+'/'+username.lower())
            if api_only:
                repository_links = repository_user.repositoryuserrepositorylink_set.filter(repository__host=self.host).filter(repository__language__iexact=category).filter(link_type = repo_link_type).select_related('repository')
                oldest_modification = repository_links.aggregate(oldest_modification=Min('last_modified'))['oldest_modification']
                watched_length = len(repository_links)
                if watched_length==0 or (datetime.now() - oldest_modification) > timedelta(days = 1):
                    repository_links.delete()
                else:
                    for repository_link in repository_links:
                        watched_filtered.append(repository_link.repository)
        except ObjectDoesNotExist:
            user_dict = self.get_user_details(username)
            repository_user = self.create_or_update_user_details(user_dict)
        return watched_filtered, repository_user

    def update_repositories(self, username, link_type):
        repo_link_type, _ = LinkType.objects.get_or_create(name = link_type)
        try:
            repository_user = RepositoryUser.objects.get(slug=self.host+'/'+username.lower())
            repository_links = repository_user.repositoryuserrepositorylink_set.filter(link_type = repo_link_type).filter(repository__host=self.host).select_related('repository')
            repository_links.delete()
        except ObjectDoesNotExist:
            user_dict = self.get_user_details(username)
            repository_user = self.create_or_update_user_details(user_dict, repository_user)
        watched = list(self.get_repositories(username, link_type))
        profile = self.user.get_profile()
        # Removes repisotory links that are no longer watched from the api
        saved = Repository.objects.filter(userrepositorylink__user=profile).filter(userrepositorylink__link_type=repo_link_type).filter(host=self.host)
        saved_slugs = (e.slug for e in saved)
        saved_slugs_set = set(saved_slugs)
        watched_slugs =(e['owner'] + '/' + e['name'] for e in watched)
        watched_slugs_set = set(watched_slugs)
        removed_slugs = saved_slugs_set - watched_slugs_set
        for slug in removed_slugs:
            repository = Repository.objects.get(host_slug = self.host+'/'+slug)
            UserRepositoryLink.objects.get(user = profile, repository = repository, link_type = repo_link_type).delete()

        # finds the highest order value for each category in user repository links
        category_query = RepositoryCategory.objects.filter(userrepositorylink__user = profile).filter(userrepositorylink__link_type=repo_link_type).distinct()
        order_category = {}
        for category in category_query:
            user_repositories = UserRepositoryLink.objects.filter(user=profile).filter(link_type = repo_link_type).filter(repository_category=category)
            order_category[category.name] = user_repositories.aggregate(max_order=Max('order'))['max_order']

        # saves the repositories and adds any new ones at an order value above the max for each category
        for repo in watched:
            try:
                repository = Repository.objects.get(host_slug=self.host+'/'+repo['owner'].lower()+'/'+repo['name'].lower())
            except ObjectDoesNotExist:
                repository = Repository()
            repository = self.create_or_update_repository_details(repo, repository)
            if not repository.private:
                repository.save()
            try:
                user_repository_link = UserRepositoryLink.objects.get(user = profile,repository = repository, link_type = repo_link_type)
            except ObjectDoesNotExist:
                if repository.language in order_category:
                    order_category[repository.language] = order_category[repository.language] + 1
                else:
                    order_category[repository.language] = 1
                user_repository_link = UserRepositoryLink(user = profile,repository = repository, order = order_category[repository.language.lower()], link_type = repo_link_type)
                user_repository_link.repository_category, _ = RepositoryCategory.objects.get_or_create(name = repository.language)
                user_repository_link.save()
#            if not repository.private:
#                RepositoryUserRepositoryLink.objects.get_or_create(user = repository_user, repository = repository, owned = owned, starred = starred)
        if repo_link_type.name == "owned":
            repository_user.public_repos = len(watched)
        elif repo_link_type.name == "starred":
            repository_user.starred = len(watched)
        elif repo_link_type.name == "watched":
            repository_user.watched = len(watched)
        return repository_user

    def update_watched_repositories(self, username):
        return self.update_repositories(username, link_type = "watched")

    def update_owned_repositories(self, username):
        return self.update_repositories(username, link_type = "owned")

    def update_starred_repositories(self, username):
        return self.update_repositories(username, link_type = "starred")

    def update_category_repositories(self, username, category, link_type):
        repo_link_type, _ = LinkType.objects.get_or_create(name = link_type)
        profile = self.user.get_profile()
        try:
            repository_user = RepositoryUser.objects.get(slug=self.host+'/'+username.lower())
            repository_links = repository_user.repositoryuserrepositorylink_set.filter(link_type = repo_link_type).filter(repository__host=self.host).select_related('repository')
            repository_links.delete()
        except ObjectDoesNotExist:
            user_dict = self.get_user_details(username)
            repository_user = self.create_or_update_user_details(user_dict)
        category_object,_ = RepositoryCategory.objects.get_or_create(name = category.lower())
        watched = list(self.get_repositories(username, link_type))
        category_lower = category.lower()

        # Removes repisotory links that are no longer watched from the api
        saved = Repository.objects.filter(userrepositorylink__user=profile).filter(userrepositorylink__link_type=repo_link_type).filter(userrepositorylink__repository_category = category_object).filter(host=self.host)
        saved_slugs = (e.slug for e in saved)
        saved_slugs_set = set(saved_slugs)
        watched_slugs =(e['owner'] + '/' + e['name'] for e in watched)
        watched_slugs_set = set(watched_slugs)
        removed_slugs = saved_slugs_set - watched_slugs_set
        for slug in removed_slugs:
            repository = Repository.objects.get(host_slug = self.host+'/'+slug)
            UserRepositoryLink.objects.get(user = profile, repository = repository, link_type = repo_link_type).delete()

        # finds the highest order value for the category in user repository links
        order = UserRepositoryLink.objects.filter(user=profile).filter(userrepositorylink__link_type = repo_link_type).filter(repository_category=category_object).aggregate(max_order=Max('order'))['max_order']

        # saves the repositories and adds any new ones at an order value above the max for the category
        watched_filtered = []
        for repo in watched:
            try:
                repository = Repository.objects.get(host_slug=self.host+'/'+repo['owner'].lower()+'/'+repo['name'].lower())
            except ObjectDoesNotExist:
                repository = Repository()
            repository = self.create_or_update_repository_details(repo, repository)
            if not repository.private:
                repository.save()
            try:
                user_repository_link = UserRepositoryLink.objects.get(user = profile,repository = repository, link_type = repo_link_type)
            except ObjectDoesNotExist:
                if repository.language == category_lower:
                    order = order + 1
                    watched_filtered.append(repository)
                    user_repository_link = UserRepositoryLink(user = profile,repository = repository, order = order, link_type = repo_link_type)
                    user_repository_link.repository_category,_ = RepositoryCategory.objects.get_or_create(name = repository.language)
                    user_repository_link.save()
#            if not repository.private:
#                RepositoryUserRepositoryLink.objects.get_or_create(user = repository_user, repository = repository, owned = owned, starred = starred)
        if repo_link_type.name == "owned":
            repository_user.public_repos = len(watched)
        elif repo_link_type.name == "starred":
            repository_user.starred = len(watched)
        elif repo_link_type.name == "watched":
            repository_user.watched = len(watched)
        return repository_user

    def update_watched_category_repositories(self, username, category):
        return self.update_category_repositories(username, category, link_type = "watched")

    def update_owned_category_repositories(self, category, username):
        return self.update_category_repositories(username, category, link_type = "owned")

    def update_starred_category_repositories(self, category, username):
        return self.update_category_repositories(username, category, link_type = "starred")

    @abstractmethod
    def search_repository(self, repository):
        return
