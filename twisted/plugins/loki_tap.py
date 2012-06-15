from twisted.application.service import ServiceMaker

Loki = ServiceMaker(
        "loki - the trickster proxy",
        "loki.tap",
        "An HTTP proxy which can be used to simulate failures of HTTP APIs",
        "loki")
