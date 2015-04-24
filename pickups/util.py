"""Utility functions."""

from hangups.ui.utils import get_conv_name
import hashlib
import re

CONV_HASH_LEN = 7


def conversation_to_channel(conv):
    """Return channel name for hangups.Conversation."""
    # Must be 50 characters max and not contain space or comma.
    conv_hash = hashlib.sha1(conv.id_.encode()).hexdigest()
    name = get_conv_name(conv).replace(',', '_').replace(' ', '')
    return '#{}[{}]'.format(name[:50 - CONV_HASH_LEN - 3],
                            conv_hash[:CONV_HASH_LEN])


def channel_to_conversation(channel, conv_list):
    """Return hangups.Conversation for channel name."""
    conv_hash = re.search(r'\[([a-f0-9]+)\]$', channel).group(1)
    return {hashlib.sha1(conv.id_.encode()).hexdigest()[:CONV_HASH_LEN]: conv
            for conv in conv_list.get_all()}[conv_hash]


def get_nick(user):
    """Return nickname for a hangups.User."""
    # Remove disallowed characters and limit to max length 15
    return re.sub(r'[^\w\[\]\{\}\^`|_\\-]', '', user.full_name)[:15]


def get_hostmask(user):
    """Return hostmask for a hangups.User."""
    return '{}!{}@hangouts'.format(get_nick(user), user.id_.chat_id)


def get_topic(conv):
    """Return IRC topic for a conversation."""
    return 'Hangouts conversation: {}'.format(get_conv_name(conv))
