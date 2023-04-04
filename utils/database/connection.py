import logging
import aiosqlite

from utils import Singleton
from colorama import Fore


class DBConnection(metaclass=Singleton):
    _con: aiosqlite.Connection

    def __init__(self):
        pass

    async def connect_db(self):
        self._con = await aiosqlite.connect('./data/database.db')
        print(f'{Fore.YELLOW}Database connection established')

    async def close_db(self):
        await self._con.close()
        print(f'{Fore.YELLOW}Database disconnected')

    def get_db(self):
        return self._con
