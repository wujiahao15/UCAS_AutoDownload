# -*- encoding: utf-8 -*-
'''
@Filename   : main.py
@Description: Main entry point of the script.
@Date       : 2020/03/13 11:50:37
@Author     : Wu Jiahao
@Contact    : https://github.com/flamywhale
'''


import asyncio
from aiohttp import ClientSession
from signal import signal, SIGINT
from sys import exit
from time import (sleep, ctime)

from manager import Manager


async def main():
    while True:
        try:
            async with ClientSession() as session:
                manager = Manager(session)
                await manager.run()
                print(f'[{ctime()}] Waiting for next execution...')
                sleep(3600)
        except Exception as e:
            print('[Exception]:', type(e), e)
            return


def handler(signal_received, frame):
    print(f'\n[{ctime()}] SIGINT or CTRL-C detected. Exit!')
    exit(0)


if __name__ == '__main__':
    signal(SIGINT, handler)
    print(f'[{ctime()}] Press CTRL-C to exit.')
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
