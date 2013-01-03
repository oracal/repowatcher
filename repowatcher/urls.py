from django.conf import settings
from django.conf.urls import patterns, include, url # Django 1.4

urlpatterns = patterns('repowatcher.main.views',

    # static pages

    url(r'^$', 'index'),
    url(r'^about/$', 'about'),

    # authed user account page

    url(r'^authed/$', 'authed'),
    url(r'^authed/owned/$', 'authed_owned',{},'authed_owned'),
    url(r'^authed/starred/$', 'authed_watched',{},'authed_starred'),
    url(r'^authed/logout/$', 'authed_logout',{},'authed_logout'),

    url(r'authed/(?P<category>[^/]+)/starred/$', 'authed_category_watched',{},'authed_category_starred'),
    url(r'authed/(?P<category>[^/]+)/owned/$', 'authed_category_owned',{},'authed_category_owned'),

    # github public user page

    url(r'^github/(?P<username>[^/]+)/$', 'github_username'),
    url(r'^github/$', 'github'),

    # github public repository page

    url(r'^github/repo/(?P<owner>[^/]+)/(?P<repo>[^/]+)/$', 'github_repo'),
    url(r'^github/repo/(?P<owner>[^/]+)/(?P<repo>[^/]+)/watch/$', 'github_repo_watch', {}, 'github_repo_watch'),
    url(r'^github/repo/(?P<owner>[^/]+)/(?P<repo>[^/]+)/unwatch/$', 'github_repo_unwatch',{}, 'github_repo_unwatch'),
    url(r'^github/repo/(?P<owner>[^/]+)/(?P<repo>[^/]+)/star/$', 'github_repo_star', {}, 'github_repo_star'),
    url(r'^github/repo/(?P<owner>[^/]+)/(?P<repo>[^/]+)/unstar/$', 'github_repo_unstar', {}, 'github_repo_unstar'),



    # github watched

    url(r'^github/(?P<username>[^/]+)/watched/$', 'github_username_watched',{"link_type":"watched",},'github_username_watched'),
    url(r'^github/(?P<username>[^/]+)/watched/save/$', 'github_username_watched_save',{"link_type":"watched",},'github_username_watched_save'),
    url(r'^github/(?P<username>[^/]+)/watched/update/$', 'github_username_watched_update',{"link_type":"watched",},'github_username_watched_update'),
    url(r'^github/(?P<username>[^/]+)/watched/refresh/$', 'github_username_watched_refresh',{"link_type":"watched",},'github_username_watched_refresh'),

    url(r'^github/(?P<username>[^/]+)/starred/$', 'github_username_watched',{"link_type":"starred"},'github_username_starred'),
    url(r'^github/(?P<username>[^/]+)/starred/save/$', 'github_username_watched_save',{"link_type":"starred"},'github_username_starred_save'),
    url(r'^github/(?P<username>[^/]+)/starred/update/$', 'github_username_watched_update',{"link_type":"starred"},'github_username_starred_update'),
    url(r'^github/(?P<username>[^/]+)/starred/refresh/$', 'github_username_watched_refresh',{"link_type":"starred"},'github_username_starred_refresh'),

    # github owned

    url(r'^github/(?P<username>[^/]+)/owned/$', 'github_username_watched',{"link_type":"owned",},'github_username_owned'),
    url(r'^github/(?P<username>[^/]+)/owned/save/$', 'github_username_watched_save',{"link_type":"owned",},'github_username_owned_save'),
    url(r'^github/(?P<username>[^/]+)/owned/update/$', 'github_username_watched_update',{"link_type":"owned",},'github_username_owned_update'),
    url(r'^github/(?P<username>[^/]+)/owned/refresh/$', 'github_username_watched_refresh',{"link_type":"owned",},'github_username_owned_refresh'),

    # github authed individual category watched

    url(r'^github/(?P<username>[^/]+)/(?P<category>[^/]+)/watched/$', 'github_username_category_watched',{"link_type":"watched",},'github_username_category_watched'),
    url(r'^github/(?P<username>[^/]+)/(?P<category>[^/]+)/watched/save/$', 'github_username_category_watched_save',{"link_type":"watched"},'github_username_category_watched_save'),
    url(r'^github/(?P<username>[^/]+)/(?P<category>[^/]+)/watched/update/$', 'github_username_category_watched_update',{"link_type":"watched",},'github_username_category_watched_update'),
    url(r'^github/(?P<username>[^/]+)/(?P<category>[^/]+)/watched/refresh/$', 'github_username_category_watched_refresh',{"link_type":"watched",},'github_username_category_watched_refresh'),

    url(r'^github/(?P<username>[^/]+)/(?P<category>[^/]+)/starred/$', 'github_username_category_watched',{"link_type":"starred"},'github_username_category_starred'),
    url(r'^github/(?P<username>[^/]+)/(?P<category>[^/]+)/starred/save/$', 'github_username_category_watched_save',{"link_type":"starred"},'github_username_category_starred_save'),
    url(r'^github/(?P<username>[^/]+)/(?P<category>[^/]+)/starred/update/$', 'github_username_category_watched_update',{"link_type":"starred"},'github_username_category_starred_update'),
    url(r'^github/(?P<username>[^/]+)/(?P<category>[^/]+)/starred/refresh/$', 'github_username_category_watched_refresh',{"link_type":"starred"},'github_username_category_starred_refresh'),

    # github authed individual category owned

    url(r'^github/(?P<username>[^/]+)/(?P<category>[^/]+)/owned/$', 'github_username_category_watched',{"link_type":"owned",},'github_username_category_owned'),
    url(r'^github/(?P<username>[^/]+)/(?P<category>[^/]+)/owned/save/$', 'github_username_category_watched_save',{"link_type":"owned",},'github_username_category_owned_save'),
    url(r'^github/(?P<username>[^/]+)/(?P<category>[^/]+)/owned/update/$', 'github_username_category_watched_update',{"link_type":"owned",},'github_username_category_owned_update'),
    url(r'^github/(?P<username>[^/]+)/(?P<category>[^/]+)/owned/refresh/$', 'github_username_category_watched_refresh',{"link_type":"owned",},'github_username_category_owned_refresh'),

    # public entry to site

    url(r'^anonymous/$', 'anonymous_github_user'),

    # search views

    url(r'^typeahead/$', 'typeahead' , {}, 'typeahead'),
    url(r'^typeahead/(?P<value>[^/]+)/$', 'typeahead', {}, 'typeahead_value'),
    url(r'^search/$', 'search'),
    url(r'^github/watched/popular/$', 'github_watched_popular'),
    url(r'^bitbucket/watched/popular/$', 'bitbucket_watched_popular'),
    url(r'^watched/popular/$', 'watched_popular'),
    url(r'^github/watched/(?P<language>[^/]+)/popular/$', 'github_watched_language_popular'),
    url(r'^bitbucket/watched/(?P<language>[^/]+)/popular/$', 'bitbucket_watched_language_popular'),
    url(r'^watched/(?P<language>[^/]+)/popular/$', 'watched_language_popular'),

    # django-social-auth

    url(r'^error/$', 'error'),
    url(r'^logout/$', 'logout'),
    url(r'', include('social_auth.urls')),

    # github public user page

    url(r'^bitbucket/(?P<username>[^/]+)/$', 'bitbucket_username'),
    url(r'^bitbucket/$', 'bitbucket'),

    # bitbucket public repository page

    url(r'^bitbucket/repo/(?P<owner>[^/]+)/(?P<repo>[^/]+)/$', 'bitbucket_repo'),

    # bitbucket watched

    url(r'^bitbucket/(?P<username>[^/]+)/starred/$', 'bitbucket_username_watched',{},'bitbucket_username_starred'),
    url(r'^bitbucket/(?P<username>[^/]+)/starred/save/$', 'bitbucket_username_watched_save',{"link_type":"starred",},'bitbucket_username_starred_save'),
    url(r'^bitbucket/(?P<username>[^/]+)/starred/update/$', 'bitbucket_username_watched_update',{},'bitbucket_username_starred_update'),
    url(r'^bitbucket/(?P<username>[^/]+)/starred/refresh/$', 'bitbucket_username_watched_refresh',{"link_type":"starred",},'bitbucket_username_starred_refresh'),

    # bitbucket owned

    url(r'^bitbucket/(?P<username>[^/]+)/owned/$', 'bitbucket_username_owned',{},'bitbucket_username_owned'),
    url(r'^bitbucket/(?P<username>[^/]+)/owned/save/$', 'bitbucket_username_watched_save',{"link_type":"owned",},'bitbucket_username_owned_save'),
    url(r'^bitbucket/(?P<username>[^/]+)/owned/update/$', 'bitbucket_username_owned_update',{},'bitbucket_username_owned_update'),
    url(r'^bitbucket/(?P<username>[^/]+)/owned/refresh/$', 'bitbucket_username_watched_refresh',{"link_type":"owned",},'bitbucket_username_owned_refresh'),

    # bitbucket authed individual category watched

    url(r'^bitbucket/(?P<username>[^/]+)/(?P<category>[^/]+)/starred/$', 'bitbucket_username_category_watched',{},'bitbucket_username_category_starred'),
    url(r'^bitbucket/(?P<username>[^/]+)/(?P<category>[^/]+)/starred/save/$', 'bitbucket_username_category_watched_save',{"link_type":"starred",},'bitbucket_username_category_starred_save'),
    url(r'^bitbucket/(?P<username>[^/]+)/(?P<category>[^/]+)/starred/update/$', 'bitbucket_username_category_watched_update',{},'bitbucket_username_category_starred_update'),
    url(r'^bitbucket/(?P<username>[^/]+)/(?P<category>[^/]+)/starred/refresh/$', 'bitbucket_username_category_watched_refresh',{"link_type":"starred",},'bitbucket_username_category_starred_refresh'),

    # bitbucket authed individual category owned

    url(r'^bitbucket/(?P<username>[^/]+)/(?P<category>[^/]+)/owned/$', 'bitbucket_username_category_owned',{},'bitbucket_username_category_owned'),
    url(r'^bitbucket/(?P<username>[^/]+)/(?P<category>[^/]+)/owned/save/$', 'bitbucket_username_category_watched_save',{"link_type":"owned",},'bitbucket_username_category_owned_save'),
    url(r'^bitbucket/(?P<username>[^/]+)/(?P<category>[^/]+)/owned/update/$', 'bitbucket_username_category_owned_update',{},'bitbucket_username_category_owned_update'),
    url(r'^bitbucket/(?P<username>[^/]+)/(?P<category>[^/]+)/owned/refresh/$', 'bitbucket_username_category_watched_refresh',{"link_type":"owned",},'bitbucket_username_category_owned_refresh'),


)

urlpatterns +=patterns('',

 (r'^media/(?P<path>.*)$', 'django.views.static.serve',{ 'document_root': settings.MEDIA_ROOT}),
 )

