import os

from twisted.web.template import Element, XMLFile, renderer, renderElement, flattenString
from twisted.web.server import NOT_DONE_YET
from twisted.web.resource import Resource
from twisted.web import static


from loki import version
from loki import requestlog


def template(base):
    return XMLFile(os.path.join(os.path.dirname(__file__), 'templates', base + '.xml'))


def render(request, element):
    return renderElement(request, Base(element))


class Base(Element):
    loader = template('base')

    def __init__(self, body):
        self._body = body

    @renderer
    def version(self, request, tag):
        return version

    @renderer
    def body(self, request, tag):
        return self._body


class RequestLog(Element):
    loader = template('requestlog')

    def __init__(self, request, response, tricks):
        self._request = request
        self._response = response
        self._tricks = tricks

    @renderer
    def tricked(self, request, tag):
        if self._tricks == (None, None):
            return 'not-tricked'

        return 'tricked'

    @renderer
    def request_method(self, request, tag):
        return tag(self._request.method)

    @renderer
    def request_uri(self, request, tag):
        return tag(self._request.uri)

    @renderer
    def response_code(self, request, tag):
        return tag(str(self._response.code))

    @renderer
    def tricks(self, request, tag):
        for trick in self._tricks:
            if trick:
                yield tag(trick.trickStr)


class EventSource(Resource):
    isLeaf = True

    def __init__(self, publisher):
        Resource.__init__(self)
        self._publisher = publisher

    def _formatEvent(self, message, destination):
        for line in message.split('\n'):
            destination.write('data: ' + line + '\r\n')
        destination.write('\r\n')

    def _eventWriter(self, request):
        def _writer((req, resp, tricks)):
            d = flattenString(request, RequestLog(req, resp, tricks))
            d.addCallback(self._formatEvent, request)

        return _writer

    def render_GET(self, request):
        request.setHeader('content-type', 'text/event-stream')

        self._publisher.subscribe(self._eventWriter(request))

        return NOT_DONE_YET


class Root(Resource):
    def render_GET(self, request):
        return render(request, Base('foo'))

    def getChild(self, child, request):
        if child == 'static':
            return static.File(os.path.join(os.path.dirname(__file__), 'static'))
        elif child == "requestlog":
            return EventSource(requestlog)
        else:
            return self
