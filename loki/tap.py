from twisted.web import server
from twisted.python import usage
from twisted.application import strports

from loki.web import TrickProxyResource
from loki.tricks import load_tricks


class Options(usage.Options):
    synopsis = "[loki options]"
    optParameters = [["port", "p", None, "strports description of the port to "
                      "start the server on."],
                     ["tricks", "t", None, "path to YAML tricks file."]
                    ]

    compData = usage.Completions(
                optActions={"config": usage.CompleteFiles("*.yml")}
                )

    def postOptions(self):
        if self['port'] is None:
            self['port'] = 'tcp:8080'

        if self['tricks'] is not None:
            (self['requestTricks'], self['responseTricks']) = load_tricks(
                file(self['tricks'], 'r')
            )


def makeService(config):
    return strports.service(
        config['port'],
        server.Site(TrickProxyResource(config['requestTricks'], config['responseTricks'])))
