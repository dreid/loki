from twisted.internet import reactor
from twisted.internet.task import deferLater


def delay_response(*args, **kwargs):
    return deferLater(reactor, kwargs['delay'], lambda: None)


# Request tricks

def strip_request_headers(request, headers=None):
    for header in headers:
        request.requestHeaders.removeHeader(header)

    request.responseHeaders.addRawHeader('x-loki-stripped-request-headers', ','.join(headers))


#response tricks

def add_content_encoding(request, response, contentEncoding=None):
    request.responseHeaders.addRawHeader('content-encoding', contentEncoding)


def strip_response_headers(request, response, headers=None):
    for header in headers:
        request.responseHeaders.removeHeader(header)
        response.headers.removeHeader(header)

    request.responseHeaders.addRawHeader('x-loki-stripped-response-headers', ','.join(headers))

#
# Implementation
#

import re
import yaml
import random
from twisted.python.reflect import namedAny
from twisted.internet.defer import maybeDeferred


class Trick(object):
    def __init__(self, regex, probability, trick, kwargs):
        self.regexStr = regex
        self._regex = re.compile(regex)
        self.probability = probability
        self.trickStr = trick
        self._trick = namedAny(trick)
        self.kwargs = kwargs

    def match(self, url):
        return (self._regex.match(url) != None and
                random.uniform(0, 1) <= self.probability)

    def apply(self, *args):
        return maybeDeferred(self._trick, *args, **self.kwargs)

    def __repr__(self):
        return '<%s: trick=%s>' % (
            self.__class__.__name__,
            self._trick
        )


def make_tricks(tricks):
    for trick in tricks or []:
        yield Trick(trick['regex'], trick['probability'], trick['trick'], trick['args'])


def load_tricks(stream):
    tricks = yaml.load(stream)

    sortP = lambda t: -t.probability

    requestTricks = tricks.get('request')
    requestTrickObjects = list(sorted(make_tricks(requestTricks), key=sortP))
    print requestTrickObjects

    responseTricks = tricks.get('response')
    responseTrickObjects = list(sorted(make_tricks(responseTricks), key=sortP))
    print responseTrickObjects

    return (requestTrickObjects, responseTrickObjects)
