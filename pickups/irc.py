import asyncio

from . import constants


def make_protocol(server):
    class IRCProtocol(asyncio.Protocol):

        def connection_made(self, transport):
            print("Connection received!")
            self.transport = transport
            self.nick = 'default'

        def data_received(self, data):
            lines = data.decode('utf-8').split('\r\n')
            for line in lines:
                line.strip()
                if not line:
                    continue

                print('Received:', repr(line))
                if line.startswith('NICK'):
                    self.nick = line.split(' ', 1)[1]
                elif line.startswith('USER'):
                    server.on_client_connect(self)
                elif line.startswith('LIST'):
                    server.on_client_list(self)
                elif line.startswith('PRIVMSG'):
                    channel, message = line.split(' ', 2)[1:]
                    server.on_client_message(self, channel, message[1:])

        def connection_lost(self, exc):
            print("Connection lost!")
            server.on_client_lost(self)

        def write(self, sender, command, *args):
            """Sends a message to the client on behalf of another client."""
            params = ' '.join('{}'.format(arg) for arg in args)
            line = ':{} {} {}\r\n'.format(sender, command, params)
            print('Sent:', repr(line))
            self.transport.write(line.encode('utf-8'))

        def swrite(self, command, *args):
            """Sends a message from the server to the client."""
            self.write('pickups', command, *args)

        def uwrite(self, command, *args):
            """Sends a message on behalf of the client."""
            self.write(self.nick, command, *args)

        # IRC Stuff

        def list_channels(self, info):
            """Tells the client what channels are available."""
            self.swrite(constants.RPL_LISTSTART, self.nick)
            for channel, num_users, topic in info:
                self.swrite(constants.RPL_LIST, self.nick,
                            channel, num_users, ':{}'.format(topic))
            self.swrite(constants.RPL_LISTEND, self.nick, ':End of /LIST')

        def join(self, channel):
            """Tells the client to join a channel."""
            self.write(self.nick, 'JOIN', ':{}'.format(channel))

        def list_nicks(self, channel, nicks):
            """Tells the client what nicks are in channel."""
            for nick in nicks:
                self.swrite(constants.RPL_NAMREPLY, self.nick, '@', channel,
                            ':{}'.format(nick))
            self.swrite(constants.RPL_ENDOFNAMES, self.nick, ':End of /NAMES')

        def topic(self, channel, topic):
            """Tells the client the topic of the channel."""
            self.swrite(constants.RPL_TOPIC, self.nick, channel,
                        ':{}'.format(topic))

        def privmsg(self, sender, target, message):
            """Sends the client a message from someone."""
            self.write(sender, 'PRIVMSG', target, ':{}'.format(message))

        def tell_nick(self, nick):
            """Tells the client its actual nick."""
            self.uwrite('NICK', nick)
            self.nick = nick

    return IRCProtocol
