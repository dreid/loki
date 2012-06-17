from twisted.web import server

from twisted.python import usage
from twisted.application import strports
from twisted.application.service import MultiService

from loki.web.ui import Root
from loki.proxy import TrickProxyResource
from loki.tricks import load_tricks


class Options(usage.Options):
    synopsis = "[loki options]"
    optParameters = [["proxy", "p", None, "strports description of the port to "
                      "start the proxy server on."],
                     ["ui", "u", None, "strports description of the port to ",
                      "start the administrative ui server on."],
                     ["tricks", "t", None, "path to YAML tricks file."]
                    ]

    compData = usage.Completions(
                optActions={"config": usage.CompleteFiles("*.yml")}
                )

    def postOptions(self):
        if self['proxy'] is None:
            self['proxy'] = 'tcp:8080'

        if self['ui'] is None:
            self['ui'] = 'tcp:8181'

        if self['tricks'] is not None:
            (self['requestTricks'], self['responseTricks']) = load_tricks(
                file(self['tricks'], 'r')
            )


def makeService(config):
    s = MultiService()

    proxy = strports.service(
        config['proxy'],
        server.Site(TrickProxyResource(config['requestTricks'], config['responseTricks'])))
    proxy.setServiceParent(s)

    ui = strports.service(
        config['ui'],
        server.Site(Root())
    )
    ui.setServiceParent(s)

    return s
