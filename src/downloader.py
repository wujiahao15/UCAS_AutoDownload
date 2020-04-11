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
from src.logger import logger


class BasicDownloader(object):
    def __init__(self, manager, name, url, path, date, db, d_type="basic"):
        self.sql = SQL_CMD[d_type]
        self.manager = manager
        self.course = name
        self.path = path
        self.url = url
        self.date = date
        self.record_date = ""
        self.db = db
        try:
            self.cursor = self.db.cursor()
        except Exception as e:
            logger.error(f'{type(e)}, {e}')
            sys.exit(1)

    def add_message(self, mode, msg):
        self.manager.add_report_message(mode, msg)

    def update(self):
        self.cursor.execute(self.sql['update'],
                            [self.date, self.path])
        self.db.commit()

    def insert(self):
        self.cursor.execute(self.sql['insert'],
                            [self.path, self.url, self.date])
        self.db.commit()

    def need_update(self):
        tag = True
        if self.date == self.record_date:
            tag = False
        return tag

    def is_file_in_datebase(self):
        tag = True
        try:
            self.record_date = self.cursor.execute(
                self.sql['lookup'], [self.path]).fetchone()[0]
        except:
            # logger.error(f'{type(e)}, {e}')
            tag = False
        return tag

    def need_download(self):
        """ Download conditions: 
            1. file not in db
            2. file in db but need to update
        """
        tag = True
        if not self.is_file_in_datebase():
            # print(f'{self.path} does not exist and insert it into database.')
            self.add_message(
                'new', f"{self.course}/{os.path.basename(self.path)}")
            self.insert()
        elif self.need_update():
            self.add_message(
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
            manager, name, url, path, date, db, d_type="courseware")
        self.chunk_size = (1 << 10)

    def create_task(self, session):
        return asyncio.create_task(self.run(session))

    async def run(self, session):
        """ Run the main downloading task. """
        if not self.need_download():
            return
        try:
            logger.info(
                f"Downloading {self.course}/{os.path.basename(self.path)}...")
            async with session.get(self.url, headers=HTTP_HDRS['normal'], timeout=20) as resp:
                with open(self.path, 'wb') as fd:
                    while True:
                        chunk = await resp.content.read(self.chunk_size)
                        if not chunk:
                            break
                        fd.write(chunk)
        except Exception as e:
            self.add_message(
                'error', f"Please manually check {self.course}/{os.path.basename(self.path)}.")
            logger.error(f'{type(e)}, {e}')


class VideoDownloader(BasicDownloader):
    def __init__(self, manager, name, url, path, date, db):
        super(VideoDownloader, self).__init__(
            manager, name, url, path, date, db, d_type="video")

    def create_task(self):
        return asyncio.create_task(self.run())

    async def run(self):
        if not self.need_download():
            return
        try:
            cmd = f"youtube-dl -o {self.path} {self.url}"
            # cmd = f"echo 'youtube-dl -o {self.path}.mp4 {self.url}'"
            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE)
            _, __ = await proc.communicate()
        except Exception as e:
            self.add_message(
                'error', f"Please manually check {self.course}/{os.path.basename(self.path)}.")
            logger.error(f'{type(e)}, {e}')
