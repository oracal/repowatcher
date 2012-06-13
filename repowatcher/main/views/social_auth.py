from django.contrib.auth import logout as auth_logout
from django.contrib.messages.api import get_messages
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template.context import RequestContext
import logging
logger = logging.getLogger(__name__)


def error(request):
    """Error view"""
    messages = get_messages(request)
    return render_to_response('error.html', {'messages': messages}, RequestContext(request))


def logout(request):
    """Logs out user"""
    auth_logout(request)
    return HttpResponseRedirect('/')


def authed_logout(request):
    if request.user.social_auth.count() == 0:
        auth_logout(request)
    return HttpResponseRedirect('/')
