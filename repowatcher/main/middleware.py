from django.middleware.cache import UpdateCacheMiddleware, \
    FetchFromCacheMiddleware
from django.utils.cache import get_max_age, patch_response_headers, \
    learn_cache_key, get_cache_key
import datetime
import hashlib
import logging
logger = logging.getLogger(__name__)

class CustomUpdateCacheMiddleware(UpdateCacheMiddleware):
    
    def process_response(self, request, response):
        """Sets the cache, if needed."""
        if not self._should_update_cache(request, response):
            # We don't need to update the cache, just return.
            return response
        if not response.status_code == 200:
            return response
        # Try to get the timeout from the "max-age" section of the "Cache-
        # Control" header before reverting to using the default cache_timeout
        # length.
        timeout = get_max_age(response)
        if timeout == None:
            timeout = self.cache_timeout
        elif timeout == 0:
            # max-age was set to 0, don't bother caching.
            return response
        patch_response_headers(response, timeout)
        
        user = request.user
        try:
            github_prefix = user.social_auth.get(provider='github').extra_data['username']
        except:
            github_prefix = ''
        try:
            bitbucket_prefix=user.social_auth.get(provider='bitbucket').extra_data['username']
        except:
            bitbucket_prefix = ''
        custom_prefix = '.'.join((hashlib.md5(github_prefix).hexdigest(),hashlib.md5(bitbucket_prefix).hexdigest()))

        if timeout:
            cache_key = learn_cache_key(request, response, timeout, custom_prefix, cache=self.cache)
            if hasattr(response, 'render') and callable(response.render):
                response.add_post_render_callback(
                    lambda r: self.cache.set(cache_key, r, timeout)
                )
            else:
                self.cache.set(cache_key, response, timeout)
        return response
    
class CustomFetchFromCacheMiddleware(FetchFromCacheMiddleware):
    
    def process_request(self, request):
        """
        Checks whether the page is already cached and returns the cached
        version if available.
        """
        if not request.method in ('GET', 'HEAD'):
            request._cache_update_cache = False
            return None # Don't bother checking the cache.
        
        user = request.user
        try:
            profile = user.get_profile()
        
            if datetime.datetime.now() - profile.last_modified < datetime.timedelta(seconds = self.cache_timeout):
                request._cache_update_cache = True
                return None
        except:
            pass
        try:
            github_prefix = user.social_auth.get(provider='github').extra_data['username']
        except:
            github_prefix = ''
        try:
            bitbucket_prefix=user.social_auth.get(provider='bitbucket').extra_data['username']
        except:
            bitbucket_prefix = ''
        custom_prefix = '.'.join((hashlib.md5(github_prefix).hexdigest(),hashlib.md5(bitbucket_prefix).hexdigest()))

        # try and get the cached GET response
        cache_key = get_cache_key(request, custom_prefix, 'GET', cache=self.cache)
        if cache_key is None:
            request._cache_update_cache = True
            return None # No cache information available, need to rebuild.
        response = self.cache.get(cache_key, None)
        # if it wasn't found and we are looking for a HEAD, try looking just for that
        if response is None and request.method == 'HEAD':
            cache_key = get_cache_key(request, custom_prefix, 'HEAD', cache=self.cache)
            response = self.cache.get(cache_key, None)

        if response is None:
            request._cache_update_cache = True
            return None # No cache information available, need to rebuild.

        # hit, return cached response
        request._cache_update_cache = False
        return response