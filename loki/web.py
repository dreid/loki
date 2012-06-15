import urlparse

from twisted.internet import reactor
from twisted.internet.defer import Deferred
from twisted.internet.protocol import Protocol
from twisted.web.resource import Resource
from twisted.web.server import NOT_DONE_YET
from twisted.web.client import IResponse
from twisted.web.client import Agent, HTTPConnectionPool, FileBodyProducer
from twisted.python import log


def url(req):
    if not req.uri.startswith('/'):
        return req.uri

    return urlparse.urlunsplit((
        'http%s' % (req.isSecure() and 's' or ''),
        req.getHeader('host'),
        '/'.join(req.prepath + req.postpath),
        '',
        ''
    ))


def add_trick_header(request, trick):
    request.responseHeaders.addRawHeader('x-loki-trick',
                                         'name=%r;regex=%r;p=%r' % (
                                            trick.trickStr,
                                            trick.regexStr,
                                            trick.probability
                                        ))


class RequestWriter(Protocol):
    def __init__(self, request):
        self.d = Deferred()
        self.request = request

    def dataReceived(self, data):
        self.request.write(data)

    def connectionLost(self, reason):
        self.d.callback(None)


class TrickProxyResource(Resource):
    isLeaf = True

    def __init__(self, requestTricks=None, responseTricks=None):
        Resource.__init__(self)
        self.agent = Agent(reactor, pool=HTTPConnectionPool(reactor, True))

        self.requestTricks = requestTricks or []
        self.responseTricks = responseTricks or []

    def selectTricks(self, req_url):
        def random_trick(tricks):
            for trick in tricks:
                if trick.match(req_url):
                    return trick

        return (random_trick(self.requestTricks), random_trick(self.responseTricks))

    def _handle_response(self, response, request, responseTrick):
        if responseTrick:
            responseTrick.apply(request, response)
            add_trick_header(request, responseTrick)

        request.setResponseCode(response.code)

        for header, values in response.headers.getAllRawHeaders():
            request.setHeader(header, ', '.join(values))

        rwp = RequestWriter(request)
        response.deliverBody(rwp)
        return rwp.d

    def render(self, request):
        req_url = url(request)
        (requestTrick, responseTrick) = self.selectTricks(req_url)

        if requestTrick:
            requestTrick.apply(request)
            add_trick_header(request, requestTrick)

        if not request.finished:
            d = self.agent.request(request.method, req_url, request.requestHeaders,
                                   FileBodyProducer(request.content))
            d.addCallback(self._handle_response, request, responseTrick)
            d.addErrback(log.err)
            d.addBoth(lambda _: request.finish())

        return NOT_DONE_YET
