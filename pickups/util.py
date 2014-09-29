import re


def get_channel(conv):
    return '#Hangout-{}'.format(conv.id_)


def get_nick(user):
    return re.sub('\W', '_', user.full_name)
