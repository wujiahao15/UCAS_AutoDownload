# -*- encoding: utf-8 -*-
'''
@Filename   : downloader.py
@Description: Downloader class for downloading files
@Date       : 2020/03/13 11:31:46
@Author     : Wu Jiahao
@Contact    : https://github.com/flamywhale
'''

import asyncio
import json
import hashlib
import os
import requests
import sqlite3
from aiohttp import ClientSession
from bs4 import BeautifulSoup
from configs import (INSERT_FILES_TABLE,
                     LOOKUP_FILES_TABLE,
                     UPDATE_FILES_TABLE,
                     HEADERS)


class CourseDownloader(object):
    def __init__(self, manager, name, url, path, date, conn):
        self.manager = manager
        self.course = name
        self.url = url
        self.path = path
        self.date = date
        self.conn = conn
        self.cursor = self.conn.cursor()
        self.chuckSize = 1024

    def addMessage(self, mode, msg):
        self.manager.addReportMessage(mode, msg)

    def update(self):
        self.cursor.execute(UPDATE_FILES_TABLE, [self.date, self.path])
        self.conn.commit()

    def insertToDatabase(self):
        self.cursor.execute(INSERT_FILES_TABLE, [self.path, self.date])
        self.conn.commit()

    def needUpdate(self):
        # print(f'current date: {self.date}')
        # print(f' record date: {self.recordDate}')
        if self.date == self.recordDate:
            return False
        return True

    def isFileInDatebase(self):
        try:
            self.recordDate = self.cursor.execute(
                LOOKUP_FILES_TABLE, [self.path]).fetchone()[0]
            return True
        except:
            # print('[ERROR]', self.path, type(e), e)
            return False

    def createTask(self, session):
        return asyncio.create_task(self.run(session))

    async def run(self, session):
        """ Run the main downloading task. """
        """ Download conditions: 
            1. file not in db
            2. file in db but need to update
        """
        if not self.isFileInDatebase():
            # print(f'{self.path} does not exist and insert it into database.')
            self.addMessage(
                'new', f"{self.course}/{os.path.basename(self.path)}")
            self.insertToDatabase()
        elif self.needUpdate():
            self.addMessage(
                'update', f"{self.course}/{os.path.basename(self.path)}")
            # print(f'{self.path} already exists but need to be updated.')
            self.update()
        else:
            # print(f'{self.path} already exists and does not need to be updated.')
            return
        try:
            async with session.get(self.url, 
                                    headers=HEADERS, timeout=20) as resp:
                with open(self.path, 'wb') as fd:
                    while True:
                        chunk = await resp.content.read(self.chuckSize)
                        if not chunk:
                            break
                        fd.write(chunk)
        except Exception as e:
            print('[ERROR]', self.path, type(e), e)


def VideoDownloader(object):
    def __init__(self, manager, name, url, path, conn):
        self.manager = manager
        self.course = name
        self.url = url
        self.path = path
        self.conn = conn
        self.cursor = self.conn.cursor()

    def addMessage(self, mode, msg):
        self.manager.addReportMessage(mode, msg)

    def update(self):
        self.cursor.execute(UPDATE_FILES_TABLE, [self.date, self.path])
        self.conn.commit()

    def insertToDatabase(self):
        self.cursor.execute(INSERT_FILES_TABLE, [self.path, self.date])
        self.conn.commit()

    def needUpdate(self):
        # print(f'current date: {self.date}')
        # print(f' record date: {self.recordDate}')
        if self.date == self.recordDate:
            return False
        return True

    def isFileInDatebase(self):
        try:
            self.recordDate = self.cursor.execute(
                LOOKUP_FILES_TABLE, [self.path]).fetchone()[0]
            return True
        except:
            # print('[ERROR]', self.path, type(e), e)
            return False

    def createTask(self, session):
        return asyncio.create_task(self.run(session))

    async def run(self, session):
        pass