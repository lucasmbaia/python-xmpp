from sleekxmpp.plugins.base import register_plugin

from sleekxmpp.plugins.docker.stanza import Docker
from sleekxmpp.plugins.docker.register import DOCKER


register_plugin(DOCKER)


# Retain some backwards compatibility
docker = DOCKER
