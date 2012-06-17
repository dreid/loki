import urlparse

from twisted.internet import reactor
from twisted.internet.defer import Deferred
from twisted.internet.protocol import Protocol
from twisted.web.resource import Resource
from twisted.web.server import NOT_DONE_YET
from twisted.web.client import Agent, HTTPConnectionPool, FileBodyProducer
from twisted.python import log

from loki.requestlog import publish


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

    def _write_response(self, response, request):
        request.setResponseCode(response.code)

        for header, values in response.headers.getAllRawHeaders():
            request.setHeader(header, ', '.join(values))

        rwp = RequestWriter(request)
        response.deliverBody(rwp)
        rwp.d.addCallback(lambda _: response)
        return rwp.d

    def _handle_response(self, response, request, requestTrick, responseTrick):
        if responseTrick:
            d = responseTrick.apply(request, response)
            d.addCallback(lambda _: add_trick_header(request, responseTrick))
            d.addCallback(lambda _: publish((request, response, (requestTrick, responseTrick))))
            d.addCallback(lambda _: response)
            return d

        publish((request, response, (requestTrick, responseTrick)))
        return response

    def _proxy_request(self, request, req_url, requestTrick, responseTrick):
        d = self.agent.request(request.method, req_url, request.requestHeaders,
                               FileBodyProducer(request.content))
        d.addCallback(self._handle_response, request, requestTrick, responseTrick)
        d.addCallback(self._write_response, request)
        d.addErrback(log.err)
        d.addBoth(lambda _: request.finish())

        return d

    def render(self, request):
        req_url = url(request)
        (requestTrick, responseTrick) = self.selectTricks(req_url)

        log.msg(
            format="Applying %(requestTrick)s and %(responseTrick)s to %(request)s.",
            request=request,
            requestTrick=requestTrick,
            responseTrick=responseTrick
        )

        if requestTrick:
            rd = requestTrick.apply(request)
            rd.addCallback(lambda _: add_trick_header(request, requestTrick))
            rd.addCallback(lambda _: self._proxy_request(request, req_url, requestTrick, responseTrick))
            rd.addErrback(log.err)
        else:
            self._proxy_request(request, req_url, requestTrick, responseTrick)

        return NOT_DONE_YET
