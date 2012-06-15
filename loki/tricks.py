def fail(request, response=None, status=500):
    print status
    request.setResponseCode(status)
    request.finish()


def missing_headers(request, response, headers=None):
    for header in headers or []:
        response.headers.removeHeader(header)

    return response

#
# Implementation
#

import re
import yaml
import random
from twisted.python.reflect import namedAny


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
                random.uniform(0, 1) < self.probability)

    def apply(self, *args):
        return self._trick(*args, **self.kwargs)


def make_tricks(trickDict):
    for regex, trick in trickDict.iteritems():
        yield Trick(regex, trick['probability'], trick['trick'], trick['args'])


def load_tricks(stream):
    tricks = yaml.load(stream)

    requestTricks = tricks.get('request', {})
    requestTrickObjects = list(make_tricks(requestTricks))

    responseTricks = tricks.get('response', {})
    responseTrickObjects = list(make_tricks(responseTricks))

    return (requestTrickObjects, responseTrickObjects)
