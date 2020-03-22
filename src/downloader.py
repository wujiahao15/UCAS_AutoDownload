# -*- encoding: utf-8 -*-
'''
@Filename   : downloader.py
@Description: Downloader class for downloading files
@Date       : 2020/03/13 11:31:46
@Author     : Wu Jiahao
@Contact    : https://github.com/flamywhale
'''

import asyncio
import os
import sys
from src.configs import (SQL_CMD, HTTP_HDRS)
from src.logger import (logError, logInfo, logDebug)


class BasicDownloader(object):
    def __init__(self, manager, name, url, path, date, db, dType="basic"):
        self.sql = SQL_CMD[dType]
        self.manager = manager
        self.course = name
        self.path = path
        self.url = url
        self.date = date
        self.recordDate = ""
        self.db = db
        try:
            self.cursor = self.db.cursor()
        except Exception as e:
            logError(f'{type(e)}, {e}')
            sys.exit(1)


    def addMessage(self, mode, msg):
        self.manager.addReportMessage(mode, msg)

    def update(self):
        self.cursor.execute(self.sql['update'],
                            [self.date, self.path])
        self.db.commit()

    def insert(self):
        self.cursor.execute(self.sql['insert'],
                            [self.path, self.url, self.date])
        self.db.commit()

    def needUpdate(self):
        tag = True
        if self.date == self.recordDate:
            tag = False
        return tag

    def isFileInDatebase(self):
        tag = True
        try:
            self.recordDate = self.cursor.execute(
                self.sql['lookup'], [self.path]).fetchone()[0]
        except:
            # print('[ERROR]', self.path, type(e), e)
            tag = False
        return tag

    def needDownload(self):
        tag = True
        if not self.isFileInDatebase():
            # print(f'{self.path} does not exist and insert it into database.')
            self.addMessage(
                'new', f"{self.course}/{os.path.basename(self.path)}")
            self.insert()
        elif self.needUpdate():
            self.addMessage(
                'update', f"{self.course}/{os.path.basename(self.path)}")
            # print(f'{self.path} already exists but need to be updated.')
            self.update()
        else:
            # print(f'{self.path} already exists and does not need to be updated.')
            tag = False
        return tag


class CoursewareDownloader(BasicDownloader):
    def __init__(self, manager, name, url, path, date, db):
        super(CoursewareDownloader, self).__init__(
            manager, name, url, path, date, db, dType="courseware")
        self.chuckSize = (1 << 10)

    def createTask(self, session):
        return asyncio.create_task(self.run(session))

    async def run(self, session):
        """ Run the main downloading task. """
        """ Download conditions: 
            1. file not in db
            2. file in db but need to update
        """
        if not self.needDownload():
            return
        try:
            logInfo(f"Downloading {self.course}/{os.path.basename(self.path)}...")
            async with session.get(self.url, headers=HTTP_HDRS['normal'], timeout=20) as resp:
                with open(self.path, 'wb') as fd:
                    while True:
                        chunk = await resp.content.read(self.chuckSize)
                        if not chunk:
                            break
                        fd.write(chunk)
        except Exception as e:
            self.addMessage(
                'error', f"Please manually check {self.course}/{os.path.basename(self.path)}.")
            logError(f'{type(e)}, {e}')


class VideoDownloader(BasicDownloader):
    def __init__(self, manager, name, url, path, date, db):
        super(VideoDownloader, self).__init__(
            manager, name, url, path, date, db, dType="video")

    def createTask(self):
        return asyncio.create_task(self.run())

    async def run(self):
        if not self.needDownload():
            return
        try:
            cmd = f"youtube-dl -o {self.path}.mp4 {self.url}"
            # cmd = f"echo 'youtube-dl -o {self.path}.mp4 {self.url}'"
            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE)
            _, __ = await proc.communicate()
        except Exception as e:
            self.addMessage(
                'error', f"Please manually check {self.course}/{os.path.basename(self.path)}.")
            logError(f'{type(e)}, {e}')
