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

    return 'http%s://%s%s' % (
        req.isSecure() and 's' or '',
        req.getHeader('host'),
        req.uri
    )


class RequestWritingProtocol(Protocol):
    def __init__(self, request):
        self.d = Deferred()
        self.request = request

    def dataReceived(self, data):
        print data
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

    def _handle_response(self, response, request):
        req_url = url(request)
        for trick in self.responseTricks:
            print trick.regexStr
            if trick.match(req_url):
                request.setHeader('x-loki-trick-regex', trick.regexStr)
                request.setHeader('x-loki-trick', trick.trickStr)
                request.setHeader('x-loki-trick-probability', trick.probability)
                trickResult = trick.apply(request, response)

                if IResponse.providedBy(trickResult):
                    request.setResponseCode(response.code)

                    for header, values in response.headers.getAllRawHeaders():
                        request.setHeader(header, ', '.join(values))

                    rwp = RequestWritingProtocol(request)
                    response.deliverBody(rwp)
                    return rwp.d

        request.setResponseCode(response.code)

        for header, values in response.headers.getAllRawHeaders():
            request.setHeader(header, ', '.join(values))

        rwp = RequestWritingProtocol(request)
        response.deliverBody(rwp)
        return rwp.d

    def render(self, request):
        req_url = url(request)
        for trick in self.requestTricks:
            if trick.match(req_url):
                request.setHeader('x-loki-trick-regex', trick.regexStr)
                request.setHeader('x-loki-trick', trick.trickStr)
                request.setHeader('x-loki-trick-probability', trick.probability)
                trick.apply(request)
                break

        print self.responseTricks
        if not request.finished:
            d = self.agent.request(request.method, req_url, request.requestHeaders,
                                   FileBodyProducer(request.content))
            d.addCallback(self._handle_response, request)
            d.addErrback(log.err)
            d.addBoth(lambda _: request.finish())

        return NOT_DONE_YET
