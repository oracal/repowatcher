from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.http import HttpRequest
from django.utils.cache import get_cache_key
import logging
logger = logging.getLogger(__name__)


def expire_view_cache(view_name, args = [], kwargs={}, namespace=None, key_prefix=None):
    """
    This function allows you to invalidate any view-level cache. 
        view_name: view function you wish to invalidate or it's named url pattern
        args: any arguments passed to the view function
        namepace: optioal, if an application namespace is needed
        key prefix: for the @cache_page decorator for the function (if any)
    """

    # create a fake request object
    request = HttpRequest()
    # Loookup the request path:
    if namespace:
        view_name = namespace + ":" + view_name
    request.path = reverse(view_name, args = args, kwargs=kwargs)
    logger.debug(request.path)
    logger.debug(key_prefix)
    # get cache key, expire if the cached item exists:
    key = cache.make_key(get_cache_key(request, key_prefix=key_prefix))
    logger.debug(key)
    if key:
        if cache.get(key):
            cache.delete(key)
            return True
    return False