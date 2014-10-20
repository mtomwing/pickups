import re


def get_channel(conv):
    return '#Hangout-{}'.format(conv.id_)


def get_nick(user):
    # Remove disallowed characters and limit to max length 15
    return re.sub(r'[^\w\[\]\{\}\^`|_\\-]', '', user.full_name)[:15]
