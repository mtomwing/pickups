import argparse
import logging
import os
import sys

import appdirs
import hangups.auth

from .server import Server

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    logging.getLogger('hangups').setLevel(logging.WARNING)
    dirs = appdirs.AppDirs('hangups', 'hangups')
    default_cookies_path = os.path.join(dirs.user_cache_dir, 'cookies.json')
    cookies = hangups.auth.get_auth_stdin(default_cookies_path)

    parser = argparse.ArgumentParser(description='IRC Gateway for Hangouts')
    parser.add_argument('--address', help='bind address', default='127.0.0.1')
    parser.add_argument('--port', help='bind port', default=6667)
    args = parser.parse_args()

    Server(cookies=cookies).run(args.address, args.port)
