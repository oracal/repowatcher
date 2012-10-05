from django.contrib.auth.models import User
from django.db import models
from django.db.models.fields import EmailField, URLField, CharField, TextField, \
    PositiveIntegerField, SlugField, DateTimeField, BooleanField
from django.db.models.fields.related import ForeignKey
from django.db.models.signals import post_save, pre_save
from repowatcher.main.utils import expire_view_cache
from social_auth.fields import JSONField
import hashlib
import logging
logger = logging.getLogger(__name__)

HOST_CHOICES = (
    (u'github', u'github'),
    (u'bitbucket', u'bitbucket'),
)

SCM_CHOICES = (
               (u'git',u'git'),
               (u'hg',u'mercurial'))

class Repository(models.Model):
    owner = CharField(max_length=100)
    name = CharField(max_length=100)
    slug = SlugField(max_length=201)
    host_slug = SlugField(max_length=302,unique = True)
    language = CharField(max_length=100,null = True)
    html_url = URLField(null = True, max_length=400)
    homepage = URLField(null = True, max_length=400)
    watchers = PositiveIntegerField(null = True)
    created_at = DateTimeField(null = True)
    pushed_at = DateTimeField(null = True)
    description = TextField(null = True)
    extra_data = JSONField(null = True)
    last_modified = DateTimeField(auto_now=True)
    scm = CharField(max_length=100,choices=SCM_CHOICES,null = True)
    host = CharField(max_length=100,choices=HOST_CHOICES)
    private = BooleanField(default = False)
    
    class Meta:
        unique_together = ("owner", "name", "host")
        ordering = ['-watchers']
        

    def save(self, *args, **kwargs):
        self.slug = self.owner.lower() + '/' + self.name.lower()
        self.host_slug = self.host+'/'+self.slug
        if (self.html_url == None or self.html_url =='') and self.host =='bitbucket':
            self.html_url = 'https://bitbucket.org/%s/%s' % (self.owner,self.name)
        
        super(Repository, self).save(*args, **kwargs)


class RepositoryCategory(models.Model):
    name = CharField(max_length=100)
        
class RepositoryUser(models.Model):
    login = CharField(max_length=100,db_index = True)
    name = CharField(max_length=100, null = True)
    slug = SlugField(max_length=201, unique = True)
    email = EmailField(max_length=254, null = True)
    blog = URLField(null = True)
    followers = PositiveIntegerField(null = True)
    following = PositiveIntegerField(null = True)
    public_repos = PositiveIntegerField(null = True)
    created_at = DateTimeField(null=True)
    extra_data = JSONField(null = True)
    last_modified = DateTimeField(auto_now=True)
    repositories = models.ManyToManyField(Repository, through='RepositoryUserRepositoryLink')
    watched = PositiveIntegerField(null = True)
    host = CharField(max_length=100,choices=HOST_CHOICES,db_index = True)
    
    class Meta:
        unique_together = ("login", "host")
        
    def save(self, *args, **kwargs):
        self.slug = self.host + '/' + self.login.lower()
        super(RepositoryUser, self).save(*args, **kwargs)
        
    
class RepositoryUserRepositoryLink(models.Model):
    user = ForeignKey(RepositoryUser)
    repository = ForeignKey(Repository)
    owned = BooleanField(default = False)
    last_modified = DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['repository__language', '-repository__watchers']
        unique_together = ("user", "repository", "owned")
    
class UserProfile(models.Model):
    user = models.OneToOneField(User)
    repositories = models.ManyToManyField(Repository, through='UserRepositoryLink')
    last_modified = DateTimeField(auto_now=True)
    
class UserRepositoryLink(models.Model):
    user = ForeignKey(UserProfile)
    repository = ForeignKey(Repository)
    order = PositiveIntegerField()
    repository_category = ForeignKey(RepositoryCategory)
    owned = BooleanField(default = False)
    last_modified = DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['repository_category__name','order']
        unique_together = ("user", "repository", 'owned')
        
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
     
def expire_cache(sender, instance, **kwargs):
    try:
        github_username = None
        bitbucket_username = None
        try:
            github_username = instance.user.social_auth.get(provider='github').extra_data['username']
            github_prefix = github_username
        except:
            github_prefix = ''
        try:
            bitbucket_username = instance.user.social_auth.get(provider='bitbucket').extra_data['username']
            bitbucket_prefix=bitbucket_username
        except:
            bitbucket_prefix = ''
        custom_prefix = '.'.join((hashlib.md5(github_prefix).hexdigest(),hashlib.md5(bitbucket_prefix).hexdigest()))
        expire_view_cache('authed_owned', key_prefix=custom_prefix)
        expire_view_cache('authed_watched', key_prefix=custom_prefix)
        if github_username:
            expire_view_cache('github_username_owned', kwargs = {'username':github_username}, key_prefix=custom_prefix)
            expire_view_cache('github_username_watched', kwargs = {'username':github_username}, key_prefix=custom_prefix)
        if bitbucket_username:
            expire_view_cache('bitbucket_username_owned', kwargs = {'username':bitbucket_username}, key_prefix=custom_prefix)
            expire_view_cache('bitbucket_username_watched', kwargs = {'username':bitbucket_username}, key_prefix=custom_prefix)
    
        category_links = instance.userrepositorylink_set.order_by('repository_category').distinct('repository_category') 
        for category_link in category_links:
            expire_view_cache('authed_category_owned', kwargs = {'category':category_link.repository_category.name}, key_prefix=custom_prefix)
            expire_view_cache('authed_category_watched', kwargs = {'category':category_link.repository_category.name}, key_prefix=custom_prefix)
            if github_username:
                expire_view_cache('github_username_category_owned', kwargs = {'username':github_username,'category':category_link.repository_category.name}, key_prefix=custom_prefix)
                expire_view_cache('github_username_category_watched', kwargs = {'username':github_username,'category':category_link.repository_category.name}, key_prefix=custom_prefix)
            if bitbucket_username:
                expire_view_cache('bitbucket_username_category_owned', kwargs = {'username':bitbucket_username,'category':category_link.repository_category.name}, key_prefix=custom_prefix)
                expire_view_cache('bitbucket_username_category_watched', kwargs = {'username':bitbucket_username,'category':category_link.repository_category.name}, key_prefix=custom_prefix)
    except Exception as e:
        logger.error(e)

post_save.connect(create_user_profile, sender=User)

pre_save.connect(expire_cache, sender=UserProfile)