import asyncio

from hangups.ui.utils import get_conv_name
import hangups
import hangups.auth

from . import util
from .irc import make_protocol


class Server(object):

    def __init__(self, host='localhost', port='6667', cookies=None):
        Protocol = make_protocol(self)
        self.clients = []

        loop = asyncio.get_event_loop()
        self._server = loop.run_until_complete(
            loop.create_server(Protocol, host, port))

        self._hangups = hangups.Client(cookies)
        self._hangups.on_connect.add_observer(self._on_hangups_connect)

    def run(self):
        loop = asyncio.get_event_loop()
        asyncio.async(self._server.wait_closed())
        print('Waiting for hangups to connect...')
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
        print('Hangups connected. Connect your IRC clients!')

    def _on_hangups_event(self, conv_event):
        """Called when a hangups conversation event occurs."""
        if isinstance(conv_event, hangups.ChatMessageEvent):
            conv = self._conv_list.get(conv_event.conversation_id)
            sender = conv.get_user(conv_event.user_id)
            for client in self.clients:
                client.privmsg(util.get_nick(sender), util.get_channel(conv),
                               conv_event.text)

    # Client Callbacks

    def on_client_connect(self, client):
        """Called when a client connects."""
        self.clients.append(client)
        client.tell_nick(util.get_nick(self._user_list._self_user))

        for conv in self._conv_list.get_all():
            channel = util.get_channel(conv)
            client.join(channel)
            client.topic(channel, get_conv_name(conv))
            client.list_nicks(channel,
                              (util.get_nick(user) for user in conv.users))

    def on_client_lost(self, client):
        """Called when a client disconnects."""
        self.clients.remove(client)

    def on_client_list(self, client):
        """Called when a client requests a list of channels."""
        info = ((util.get_channel(conv), len(conv.users), get_conv_name(conv))
                for conv in self._conv_list.get_all())
        client.list_channels(info)

    def on_client_message(self, client, channel, message):
        """Called when the client sends a message."""
        conv = self._conv_list.get(channel.split('-', 1)[1])
        segments = [hangups.ChatMessageSegment(message)]
        asyncio.async(conv.send_message(segments))
