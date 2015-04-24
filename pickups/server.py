import asyncio
import logging

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
            user = conv.get_user(conv_event.user_id)
            sender = util.get_nick(user)
            hostmask = util.get_hostmask(user)
            channel = util.conversation_to_channel(conv)
            message = conv_event.text
            for client in self.clients.values():
                if message in client.sent_messages and sender == client.nickname:
                    client.sent_messages.remove(message)
                else:
                    client.privmsg(hostmask, channel, conv_event.text)

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
                    (util.conversation_to_channel(conv), len(conv.users),
                     util.get_topic(conv))
                    for conv in sorted(self._conv_list.get_all(),
                                       key=lambda x: len(x.users))
                )
                client.list_channels(info)
            elif line.startswith('PRIVMSG'):
                channel, message = line.split(' ', 2)[1:]
                conv = util.channel_to_conversation(channel, self._conv_list)
                client.sent_messages.append(message[1:])
                segments = hangups.ChatMessageSegment.from_str(message[1:])
                asyncio.async(conv.send_message(segments))
            elif line.startswith('JOIN'):
                channel = line.split(' ')[1]
                conv = util.channel_to_conversation(channel, self._conv_list)
                # If a JOIN is successful, the user receives a JOIN message as
                # confirmation and is then sent the channel's topic (using
                # RPL_TOPIC) and the list of users who are on the channel (using
                # RPL_NAMREPLY), which MUST include the user joining.
                client.write(util.get_nick(self._user_list._self_user),
                             'JOIN', channel)
                client.topic(channel, util.get_topic(conv))
                client.list_nicks(channel,
                                  (util.get_nick(user) for user in conv.users))
            elif line.startswith('WHO'):
                query = line.split(' ')[1]
                if query.startswith('#'):
                    conv = util.channel_to_conversation(channel,
                                                         self._conv_list)
                    responses = [{
                        'channel': query,
                        'user': util.get_nick(user),
                        'nick': util.get_nick(user),
                        'real_name': user.full_name,
                    } for user in conv.users]
                    client.who(query, responses)
            elif line.startswith('PING'):
                client.pong()

            if not welcomed and client.nickname and username:
                welcomed = True
                client.swrite(irc.RPL_WELCOME, ':Welcome to pickups!')
                client.tell_nick(util.get_nick(self._user_list._self_user))

                # Sending the MOTD seems be required for Pidgin to connect.
                client.swrite(irc.RPL_MOTDSTART,
                              ':- pickups Message of the Day - ')
                client.swrite(irc.RPL_MOTD, ':- insert MOTD here')
                client.swrite(irc.RPL_ENDOFMOTD, ':End of MOTD command')
