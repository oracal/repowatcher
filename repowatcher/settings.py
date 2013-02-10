# Django settings for repowatcher project.

# Replace all ********** with custom options, app folder located inside /home/oracal/webapps/

DEBUG = False
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS


# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

USE_TZ = False

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = '/home/oracal/webapps/repowatcher/media/'

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = '/media/'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = ''

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# URL prefix for admin static files -- CSS, JavaScript and images.
# Make sure to use a trailing slash.
# Examples: "http://foo.com/static/admin/", "/static/admin/".
ADMIN_MEDIA_PREFIX = '/static/admin/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': '**********',
        'USER': '**********',
        'PASSWORD':'**********',
    }
}

# Make this unique, and don't share it with anybody.
SECRET_KEY = '**********'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'repowatcher.main.middleware.CustomUpdateCacheMiddleware',
    #'django.middleware.csrf.CsrfViewMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware', # Djsngo 1.4
    'django.middleware.common.CommonMiddleware',
    'repowatcher.main.middleware.CustomFetchFromCacheMiddleware',
    #'debug_toolbar.middleware.DebugToolbarMiddleware',
)

ROOT_URLCONF = 'repowatcher.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'repowatcher.wsgi.application'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    '/home/oracal/webapps/repowatcher/repowatcher/main/templates/authed',
    '/home/oracal/webapps/repowatcher/repowatcher/main/templates/bitbucket',
    '/home/oracal/webapps/repowatcher/repowatcher/main/templates/general',
    '/home/oracal/webapps/repowatcher/repowatcher/main/templates/github',
    '/home/oracal/webapps/repowatcher/repowatcher/main/templates/social_auth'
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'repowatcher.main',
    'social_auth',
    'djcelery',
    #'debug_toolbar',
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
)

# When using TCP connections
CACHES = {
    'default': {
        'BACKEND': 'redis_cache.RedisCache',
        'LOCATION': '**********',
        'VERSION': 1,
        'OPTIONS': {
            'DB': 0,
        },
    },
}

CACHE_MIDDLEWARE_ANONYMOUS_ONLY = False
CACHE_MIDDLEWARE_SECONDS = 500

SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'

AUTH_PROFILE_MODULE = 'main.UserProfile'

AUTHENTICATION_BACKENDS = (
    'social_auth.backends.contrib.github.GithubBackend',
    #'django.contrib.auth.backends.ModelBackend',
    'social_auth.backends.contrib.bitbucket.BitbucketBackend',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.contrib.messages.context_processors.messages',
    'social_auth.context_processors.social_auth_by_name_backends',
    #'django.core.context_processors.csrf',
)

SOCIAL_AUTH_ENABLED_BACKENDS = ('github','bitbucket')
SOCIAL_AUTH_EXTRA_DATA = True
GITHUB_EXTRA_DATA = [
    ('html_url', 'home'),
    ('login', 'username'),
    ('avatar_url', 'avatar_url'),
]

GITHUB_AUTH_EXTRA_ARGUMENTS = {'scope': 'public_repo'}

TWITTER_CONSUMER_KEY         = ''
TWITTER_CONSUMER_SECRET      = ''
FACEBOOK_APP_ID              = ''
FACEBOOK_API_SECRET          = ''
LINKEDIN_CONSUMER_KEY        = ''
LINKEDIN_CONSUMER_SECRET     = ''
ORKUT_CONSUMER_KEY           = ''
ORKUT_CONSUMER_SECRET        = ''
GOOGLE_CONSUMER_KEY          = ''
GOOGLE_CONSUMER_SECRET       = ''
GOOGLE_OAUTH2_CLIENT_ID      = ''
GOOGLE_OAUTH2_CLIENT_SECRET  = ''
FOURSQUARE_CONSUMER_KEY      = ''
FOURSQUARE_CONSUMER_SECRET   = ''
GITHUB_APP_ID                = '**********'
GITHUB_API_SECRET            = '**********'
DROPBOX_APP_ID               = ''
DROPBOX_API_SECRET           = ''
FLICKR_APP_ID                = ''
FLICKR_API_SECRET            = ''
INSTAGRAM_CLIENT_ID          = ''
INSTAGRAM_CLIENT_SECRET      = ''
BITBUCKET_CONSUMER_KEY       = '**********'
BITBUCKET_CONSUMER_SECRET    = '**********'

SOCIAL_AUTH_ERROR_KEY = 'social_errors'

SOCIAL_AUTH_EXPIRATION = 'expires'

LOGIN_REDIRECT_URL = '/authed/'
LOGIN_URL = '/'
LOGIN_ERROR_URL = '/error/'
SOCIAL_AUTH_DISCONNECT_REDIRECT_URL = '/authed/logout/'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
        'null': {
            'level':'DEBUG',
            'class':'django.utils.log.NullHandler',
        },
        'console':{
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
        'log_file':{
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/home/oracal/webapps/repowatcher/logs/django.log',
            'maxBytes': '2048', # 2megabytes
            'formatter': 'verbose'
        },
        'complete_log_file':{
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/home/oracal/webapps/repowatcher/logs/django_complete.log',
            'maxBytes': '16384', # 16megabytes
            'formatter': 'verbose'
        },
    },
    'loggers': {
        'repowatcher.main': {
            'handlers': ['log_file','console'],
            'level': 'DEBUG',
            'propagate': True,
        },
        '': {
             'handlers': ['complete_log_file'],
            'level': 'DEBUG',
            'propagate': True,
             }
    }
}

INTERNAL_IPS = ('**********',)

BROKER_URL = "redis://**********/0"
CELERY_RESULT_BACKEND = "redis"
CELERY_REDIS_PORT = "**********"
CELERY_REDIS_DB = 0
CELERY_IMPORTS = ("repowatcher.main.tasks", )
CELERYD_CONCURRENCY = 4
CELERYD_SOFT_TASK_TIME_LIMIT = 20
import djcelery
djcelery.setup_loader()
