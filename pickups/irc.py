import logging

RPL_WELCOME = 1
RPL_WHOISUSER = 311
RPL_LISTSTART = 321
RPL_LIST = 322
RPL_LISTEND = 323
RPL_TOPIC = 332
RPL_NAMREPLY = 353
RPL_ENDOFNAMES = 366

logger = logging.getLogger(__name__)


class Client(object):

    def __init__(self, reader, writer):
        self.reader = reader
        self.writer = writer

        self.nickname = None
        self.sent_messages = []

    def readline(self):
        return self.reader.readline()

    def write(self, sender, command, *args):
        """Sends a message to the client on behalf of another client."""
        if not isinstance(command, str):
            command = '{:03}'.format(command)
        params = ' '.join('{}'.format(arg) for arg in args)
        line = ':{} {} {}\r\n'.format(sender, command, params)
        logger.info('Sent: %r', line)
        self.writer.write(line.encode('utf-8'))

    def swrite(self, command, *args):
        """Sends a message from the server to the client."""
        self.write('pickups', command, self.nickname, *args)

    def uwrite(self, command, *args):
        """Sends a message on behalf of the client."""
        self.write(self.nickname, command, *args)

    # IRC Stuff

    def welcome(self):
        self.swrite(constants.RPL_WELCOME, self.nickname,
                    ':Welcome to pickups!')

    def list_channels(self, info):
        """Tells the client what channels are available."""
        self.swrite(RPL_LISTSTART)
        for channel, num_users, topic in info:
            self.swrite(RPL_LIST, channel, num_users, ':{}'.format(topic))
        self.swrite(RPL_LISTEND, ':End of /LIST')

    def join(self, channel):
        """Tells the client to join a channel."""
        self.write(self.nickname, 'JOIN', ':{}'.format(channel))

    def list_nicks(self, channel, nicks):
        """Tells the client what nicks are in channel."""
        for nick in nicks:
            self.swrite(RPL_NAMREPLY, '@', channel, ':{}'.format(nick))
        self.swrite(RPL_ENDOFNAMES, ':End of /NAMES')

    def topic(self, channel, topic):
        """Tells the client the topic of the channel."""
        self.swrite(RPL_TOPIC, channel, ':{}'.format(topic))

    def privmsg(self, sender, target, message):
        """Sends the client a message from someone."""
        self.write(sender, 'PRIVMSG', target, ':{}'.format(message))

    def tell_nick(self, nickname):
        """Tells the client its actual nick."""
        self.uwrite('NICK', nickname)
        self.nickname = nickname
