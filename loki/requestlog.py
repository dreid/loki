class RequestLog(object):
    def __init__(self):
        self._subscribers = []

    def subscribe(self, subscriber):
        self._subscribers.append(subscriber)

    def publish(self, request):
        [subscriber(request) for subscriber in self._subscribers]


_requestLog = RequestLog()

subscribe = _requestLog.subscribe
publish = _requestLog.publish
