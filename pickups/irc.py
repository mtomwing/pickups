import logging

RPL_WELCOME = 1
RPL_WHOISUSER = 311
RPL_ENDOFWHO = 315
RPL_LISTSTART = 321
RPL_LIST = 322
RPL_LISTEND = 323
RPL_TOPIC = 332
RPL_WHOREPLY = 352
RPL_NAMREPLY = 353
RPL_ENDOFNAMES = 366
RPL_MOTD = 372
RPL_MOTDSTART = 375
RPL_ENDOFMOTD = 376


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
        """Tells the client a welcome message."""
        self.swrite(RPL_WELCOME, self.nickname, ':Welcome to pickups!')

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
        self.swrite(RPL_NAMREPLY, '=', channel, ':{}'.format(' '.join(nicks)))
        self.swrite(RPL_ENDOFNAMES, channel, ':End of NAMES list')

    def who(self, query, responses):
        """Tells the client a list of information matching a query."""
        for response in responses:
            self.swrite(
                RPL_WHOREPLY, response['channel'],
                '~{}'.format(response['user']), 'localhost', 'pickups',
                response['nick'], 'H', ':0', response['real_name']
            )
        self.swrite(RPL_ENDOFWHO, query, ':End of WHO list')

    def topic(self, channel, topic):
        """Tells the client the topic of the channel."""
        self.swrite(RPL_TOPIC, channel, ':{}'.format(topic))

    def privmsg(self, hostmask, target, message):
        """Sends the client a message from someone."""
        for line in message.splitlines():
            if line:
                self.write(hostmask, 'PRIVMSG', target, ':{}'.format(line))

    def tell_nick(self, nickname):
        """Tells the client its actual nick."""
        self.uwrite('NICK', nickname)
        self.nickname = nickname
