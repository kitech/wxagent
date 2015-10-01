
from .imrelay import IMRelay
from .toxrelay import ToxRelay
from .xmpprelay import XmppRelay


class IMRelayFactory():

    # @param relay str
    def create(relay):
        orelay = None

        if relay == 'tox':
            orelay = ToxRelay()
        elif relay == 'xmpp':
            orelay = XmppRelay()
        else:
            pass
        return orelay
