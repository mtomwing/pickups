import asyncio

import hangups
import hangups.auth

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

    def _on_hangups_event(self, conv_event):
        """Called when a hangups conversation event occurs."""
        if isinstance(conv_event, hangups.ChatMessageEvent):
            print('Event:', conv_event)

    # Client Callbacks

    def on_client_connect(self, client):
        """Called when a client connects."""
        self.clients.append(client)

    def on_client_lost(self, client):
        """Called when a client disconnects."""
        self.clients.remove(client)
