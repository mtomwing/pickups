import asyncio
import logging

from hangups.ui.utils import get_conv_name as get_topic
import hangups
import hangups.auth

from . import irc, util

logger = logging.getLogger(__name__)


class Server(object):

    def __init__(self, host='localhost', port='6667', cookies=None):
        self.clients = {}
        self._hangups = hangups.Client(cookies)
        self._hangups.on_connect.add_observer(self._on_hangups_connect)

    def run(self, host, port):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(
            asyncio.start_server(self._on_client_connect, host=host, port=port)
        )
        logger.info('Waiting for hangups to connect...')
        loop.run_until_complete(self._hangups.connect())

    # Hangups Callbacks

    def _on_hangups_connect(self, initial_data):
        """Called when hangups successfully auths with hangouts."""
        self._user_list = hangups.UserList(
            self._hangups, initial_data.self_entity, initial_data.entities,
            initial_data.conversation_participants
        )
        self._conv_list = hangups.ConversationList(
            self._hangups, initial_data.conversation_states, self._user_list,
            initial_data.sync_timestamp
        )
        self._conv_list.on_event.add_observer(self._on_hangups_event)
        logger.info('Hangups connected. Connect your IRC clients!')

    def _on_hangups_event(self, conv_event):
        """Called when a hangups conversation event occurs."""
        if isinstance(conv_event, hangups.ChatMessageEvent):
            conv = self._conv_list.get(conv_event.conversation_id)
            sender = util.get_nick(conv.get_user(conv_event.user_id))
            channel = util.get_channel(conv)
            message = conv_event.text
            for client in self.clients.values():
                if message in client.sent_messages and sender == client.nickname:
                    client.sent_messages.remove(message)
                else:
                    client.privmsg(sender, channel, conv_event.text)

    # Client Callbacks

    def _on_client_connect(self, client_reader, client_writer):
        """Called when an IRC client connects."""
        client = irc.Client(client_reader, client_writer)
        task = asyncio.Task(self._handle_client(client))
        self.clients[task] = client
        logger.info("New Connection")
        task.add_done_callback(self._on_client_lost)

    def _on_client_lost(self, task):
        """Called when an IRC client disconnects."""
        self.clients[task].writer.close()
        del self.clients[task]
        logger.info("End Connection")

    @asyncio.coroutine
    def _handle_client(self, client):
        username = None
        welcomed = False

        while True:
            line = yield from client.readline()
            line = line.decode('utf-8').strip('\r\n')

            if not line:
                logger.info("Connection lost")
                break
            logger.info('Received: %r', line)

            if line.startswith('NICK'):
                client.nickname = line.split(' ', 1)[1]
            elif line.startswith('USER'):
                username = line.split(' ', 1)[1]
            elif line.startswith('LIST'):
                info = (
                    (util.get_channel(conv), len(conv.users), get_topic(conv))
                    for conv in self._conv_list.get_all()
                )
                client.list_channels(info)
            elif line.startswith('PRIVMSG'):
                channel, message = line.split(' ', 2)[1:]
                conv = self._conv_list.get(channel.split('-', 1)[1])
                client.sent_messages.append(message[1:])
                segments = [hangups.ChatMessageSegment(message[1:])]
                asyncio.async(conv.send_message(segments))

            if not welcomed and client.nickname and username:
                welcomed = True
                client.swrite(irc.RPL_WELCOME, ':Welcome to pickups!')
                client.tell_nick(util.get_nick(self._user_list._self_user))
                for conv in self._conv_list.get_all():
                    channel = util.get_channel(conv)
                    client.join(channel)
                    client.topic(channel, get_topic(conv))
                    client.list_nicks(channel,
                                      (util.get_nick(user) for user in conv.users))
