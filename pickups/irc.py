import asyncio

from hangups.ui.utils import get_conv_name

from . import constants


def make_protocol(server):
    class IRCProtocol(asyncio.Protocol):

        def connection_made(self, transport):
            print("Connection received!")
            self.transport = transport
            self.nick = 'default'
            server.on_client_connect(self)

        def data_received(self, data):
            lines = data.decode('utf-8').split('\r\n')
            for line in lines:
                line.strip()
                if not line:
                    continue

                print('Received:', repr(line))
                if line.startswith('NICK'):
                    self.nick = line.split(' ', 1)[1]
                elif line.startswith('LIST'):
                    self.send_convos_list()

        def connection_lost(self, exc):
            print("Connection lost!")
            server.on_client_lost(self)

        def swrite(self, command, *args):
            """Sends a message from the server to the client."""
            params = ' '.join('{}'.format(arg) for arg in args)
            line = ':pickups {} {}\r\n'.format(command, params)
            print('Sent:', repr(line))
            self.transport.write(line.encode('utf-8'))

        def cwrite(self, command, *args):
            """Sends a message to the client on behalf of another client."""
            params = ' '.join('{}'.format(arg) for arg in args)
            line = ':{} {} {}\r\n'.format(self.nick, command, params)
            print('Sent:', repr(line))
            self.transport.write(line.encode('utf-8'))

        # IRC Stuff

        def send_convos_list(self):
            self.swrite(constants.RPL_LISTSTART, self.nick)
            for conv in server._conv_list.get_all():
                channel = '#Hangout-{}'.format(conv.id_)
                topic = ':{}'.format(get_conv_name(conv))
                self.swrite(constants.RPL_LIST, self.nick,
                            channel, len(conv.users), topic)
            self.swrite(constants.RPL_LISTEND, self.nick, ':End of /LIST')

    return IRCProtocol
