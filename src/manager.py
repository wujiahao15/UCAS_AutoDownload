# -*- encoding: utf-8 -*-
'''
@Filename   : manager.py
@Description: Manager class for managing file downloading and reporting.
@Date       : 2020/03/13 11:31:56
@Author     : Wu Jiahao
@Contact    : https://github.com/flamywhale
'''

import asyncio
import json
import os
import re
import sqlite3
import sys
from aiohttp import ClientSession
from bs4 import BeautifulSoup
from datetime import datetime
from getpass import getpass
from sys import exit
from time import ctime
from urllib import parse

from src.configs import (HTTP_HDRS, SQL_CMD, TARGET_PAGE_TAG)
from src.downloader import (CoursewareDownloader, VideoDownloader)


async def fetch(session, url, timeout=10, params=None):
    async with session.get(url, headers=HTTP_HDRS['normal'], timeout=timeout, params=params) as response:
        return await response.text()


class Manager(object):
    def __init__(self, session, databasePath):
        self.databasePath = databasePath
        self.sess = session
        self.coursesList = []
        self.username = ''
        self.password = ''
        self.downloadPath = ''
        try:
            self.checkDatebase()
        except Exception as e:
            print('[checkDatebase]:', type(e), e)
            exit(1)

    def checkDatebase(self):
        if not os.path.exists(self.databasePath):
            self.db = sqlite3.connect(self.databasePath)
            c = self.db.cursor()
            # list(map(lambda table: c.execute(table['create']), SQL_CMD))
            dict(map(lambda item: (item[0], c.execute(item[1]['create'])), SQL_CMD.items()))
            self.db.commit()
        else:
            self.db = sqlite3.connect(self.databasePath)

    async def checkUser(self):
        while True:
            c = self.db.cursor()
            result = c.execute(SQL_CMD["user"]["lookup"]).fetchone()
            if result == None:
                insertValues = self.getUserInfo()
                c.execute(SQL_CMD["user"]["insert"], insertValues)
                self.db.commit()
            else:
                self.username, self.password, self.downloadPath, _ = result
            self.loginInfo = {
                'username': self.username,
                'password': self.password,
                'remember': 'checked'
            }
            success = await self.tryToLogin()
            if not success:
                self.updateUserInfo()
            else:
                break

    def updateUserInfo(self):
        print("Failed to login.\nPlease enter your username and password again, and make sure it is right!")
        values = self.getUserInfo()
        c = self.db.cursor()
        c.execute(SQL_CMD["user"]["update"], values[:-1])
        self.db.commit()

    async def tryToLogin(self):
        async with self.sess.post(
                'http://onestop.ucas.ac.cn/Ajax/Login/0', headers=HTTP_HDRS['post'], data=self.loginInfo) as res:
            resJson = json.loads(await res.text())
            return resJson['f']

    def getUserInfo(self):
        self.username = input('username: ')
        self.password = getpass('password: ')
        self.downloadPath = input('Where to save coursewares: ')
        return [self.username, self.password, self.downloadPath, 'default']

    def printLoginInfo(self, soup):
        nameTag = soup.find(
            "li", {"class": "btnav-info", "title": "当前用户所在单位"})
        if nameTag is None:
            print("[ERROR]: 登录失败，请核对用户名和密码")
            exit(0)
        name = nameTag.get_text()
        match = re.compile(r"\s*(\S*)\s*(\S*)\s*").match(name)
        if not match:
            print("[ERROR]: 脚本运行错误")
            exit("找不到用户名和单位")
        institute = match.group(1)
        name = match.group(2)
        print(f'[{ctime()}] {institute} {name} 登录成功！')

    async def login(self):
        async with self.sess.post(
                'http://onestop.ucas.ac.cn/Ajax/Login/0', headers=HTTP_HDRS['post'], data=self.loginInfo) as res:
            resJson = json.loads(await res.text())
            if resJson['f']:
                url, parm = resJson['msg'].split('?')
            else:
                print(f"{resJson['msg']}！\n请重新运行并输入账号密码。")
                self.updateUserInfo()
                exit(0)
        async with self.sess.get(url, headers=HTTP_HDRS['get'], params=parm) as res:
            soup = BeautifulSoup(await res.text(), 'html.parser')
            self.printLoginInfo(soup)
        await fetch(self.sess, "http://sep.ucas.ac.cn/appStore")

    async def fetchCourseUrls(self):
        """ Get all the course information. """
        print(f'[{ctime()}] Fetch course urls...')
        try:
            text = await fetch(self.sess, "http://sep.ucas.ac.cn/portal/site/16/801")
            bsObj = BeautifulSoup(text, "html.parser")
            courseWebsiteUrl = bsObj.find(
                'noscript').meta.get("content")[6:]
            # print(courseWebsiteUrl)
            text = await fetch(self.sess, courseWebsiteUrl)
            bsObj = BeautifulSoup(text, "html.parser")
            allCoursesUrl = bsObj.find(
                'a', {'class': "Mrphs-toolsNav__menuitem--link", 'title': "我的课程 - 查看或加入站点"}).get("href")
            # print(allCoursesUrl)
            text = await fetch(self.sess, allCoursesUrl)
            bsObj = BeautifulSoup(text, "html.parser")
            allCoursesInfo = bsObj.find(
                'ul', {'class': "otherSitesCategorList favoriteSiteList"}).find_all('div', {'class': "fav-title"})
            for courseInfo in allCoursesInfo:
                course = {}
                course["name"] = courseInfo.find('a').get('title')
                course["url"] = courseInfo.find('a').get('href')
                print(f'[{ctime()}] Find course {course["name"]}')
                self.coursesList.append(course)
        except:
            print("[ERROR]: 请检查网络连接！（可能网速较慢）")
            exit(0)

    def setupCourseware(self):
        self.coursewareManager = CoursewareManager(self.sess, self.downloadPath, self.coursesList, self.db)
    
    def setupVideo(self):
        self.videoManager = VideoManager(self.sess, self.downloadPath, self.coursesList, self.db)

    async def initialize(self):
        await self.checkUser()
        await self.login()
        await self.fetchCourseUrls()
        commandLine = "Please choose download objects:\n\t1: 下载课件\n\t2: 下载视频\n\t3: 下载课件和视频\nMode = "
        mode = int(input(commandLine))
        if (mode & 0b01):
            self.coursewareManager = CoursewareManager(self.sess, self.downloadPath, self.coursesList, self.db)
        if (mode & 0b10):
            self.videoManager = VideoManager(self.sess, self.downloadPath, self.coursesList, self.db)

    async def run(self):
        """Run the pipeline"""
        start = datetime.now()
        await self.initialize()
        try:
            # print(f'[{ctime()}] Going to arrange downloading tasks.')
            # await self.runDownloaders()
            await self.coursewareManager.run()
            await self.videoManager.run()
            # self.report()
            stop = datetime.now()
            print(f'[{ctime()}] All downloaders cost',
                  (stop-start).total_seconds(), 'seconds.')
            # self.report()
        except Exception as e:
            print(f"[{sys._getframe().f_code.co_name}:{sys._getframe().f_lineno}] Exception", e, type(e))
            exit(0)

class BasicManager(object):
    def __init__(self, session, downloadPath, coursesList, db, dType="basic"):
        self._type = dType
        self._downloaders = []
        self._messages = {'update': [], 'new': [], 'error': []}
        self.sess = session
        self.downloadPath = downloadPath
        self.coursesList = coursesList
        self.db = db
        self.chooseCourses()

    def chooseCourses(self):
        print(f"\n{'*' * 6} {self._type.upper()} MANAGER INFO {'*' * 6}")
        print(f"Please choose courses to download {self._type}.")
        for i, course in enumerate(self.coursesList):
            print(f"\t{i}\t{course['name']}")
        downloadAll = input(f"Do you want to download {self._type}s of all courses?('Y' or 'N'): ")
        if downloadAll.upper() == "Y":
            return
        print("Please type serial numbers of courses in one line and seperate them with *SPACE*.")
        print("e.g. '1 2 3 4 5'")
        ""
        courseNum = len(self.coursesList)
        numbers = list(filter(lambda x: x.isdigit() and int(x) < courseNum, input().split(' ')))
        numbers = list(map(lambda x: int(x), numbers))
        self.coursesList = [self.coursesList[idx] for idx in numbers]
        print("Chosen courses are as follows:")
        for course in self.coursesList:
            print(f"{course['name']}")

    def addReportMessage(self, mode, msg):
        self._messages[mode].append(msg)

    def report(self):
        print(f"\n[{ctime()}] {'*'*6} REPORT OF {self._type.upper()} MANAGER START {'*'*6}.")
        for key, messages in self._messages.items():
            for msg in messages:
                print(f"[{ctime()}] {key.upper()}: {msg}")
            if len(messages) == 0:
                print(f"[{ctime()}] There are no {key} {self._type}s.")
        print(f"[{ctime()}] {'*'*6} REPORT OF {self._type.upper()} MANAGER END {'*'*6}.")

    async def reDirectToTargetPage(self, courseUrl):
        """ Redirect page to target page.

        Redirect the page from course website main page to target page,
        in order to get something.

        Args:
            courseUrl: String, the url of course main page

        Returns:
            resourcePageObj: BeatifulSoup Object, parse the resource page
        """
        text = await fetch(self.sess, courseUrl)
        bsObj = BeautifulSoup(text, "html.parser")
        try:
            resourcePageUrl = bsObj.find(
                'a', TARGET_PAGE_TAG[self._type]).get("href")
            text = await fetch(self.sess, resourcePageUrl)
            resourcePageObj = BeautifulSoup(text, 'html.parser')
            if self._type == "video":
                return [resourcePageUrl, resourcePageObj]
            return resourcePageObj
        except Exception as e:
            print(f"[{sys._getframe().f_code.co_name}:{sys._getframe().f_lineno}] Exception", e, type(e))
            return None

    async def getTargetInfo(self, course):
        pass

    async def runDownloaders(self):
        pass

    async def getResourceInfoList(self):
        for course in self.coursesList:
            await self.getTargetInfo(course)

    async def run(self):
        """Run the pipeline"""
        await self.getResourceInfoList()
        start = datetime.now()
        try:
            print(f'[{ctime()}] Going to arrange downloading {self._type} tasks.')
            await self.runDownloaders()
            stop = datetime.now()
            print(f'[{ctime()}] All downloaders cost',
                  (stop-start).total_seconds(), 'seconds.')
            self.report()
        except Exception as e:
            print(f"[{sys._getframe().f_code.co_name}:{sys._getframe().f_lineno}] Exception", e, type(e))
            exit(0)

class CoursewareManager(BasicManager):
    def __init__(self, session, downloadPath, coursesList, db):
        super(CoursewareManager, self).__init__(session, downloadPath, coursesList, db, dType="courseware")

    async def getResourceInfos(self, resourcePageObj, parentDir=""):
        """ Get the information of coursewares.
        Get the information of coursewares, e.g. the filename of the courseware,
        the url of the courseware.

        The process of this function is as follows:

                ┌──── 获取当前文件夹下的所有文件的信息（文件名+文件下载链接）
                │            │
                │     获取当前文件夹下的所有文件夹
                │            │
                │        1. 根据当前页面发POST请求
                │        2. 获得子文件夹的页面
                │        3. 调用自己
                │            │
                └────────────┘

        The information of the resources is stored in self.resourceInfos, 
        which is a list.

        Args:
            resourcePageObj: BeautifulSoup Object, parse the current web page
            parentDir: String, the path of the parrent directory

        Returns:
            None
        """
        # get urls of files under current directory
        self.getFileInfosOfCurrentDir(resourcePageObj, parentDir)
        # get urls of files under subfolders
        subDirPageInfoList = await self.getSubDirPageObjs(resourcePageObj, parentDir)
        for subDirPageObj, subDir in subDirPageInfoList:
            await self.getResourceInfos(subDirPageObj, subDir)

    def getFileInfosOfCurrentDir(self, resourcePageObj, parentDir):
        """ Get the information of files in the current web page.
        Args:
            resourcePageObj: BeautifulSoup Object, parse the current web page
            parentDir: String, the path of the parrent directory

        Returns:
            None
        """
        rows = resourcePageObj.find_all("tr")
        resourceList = []
        for row in rows:
            link = row.find("a").get('href')
            if link == '#':
                continue
            date = row.find(
                "td", {"class": "modified hidden-sm hidden-xs"}).get_text().strip()
            resourceList.append({"href": link, "date": date})
        for resource in resourceList:
            resourceInfo = {}
            resourceInfo["subDir"] = parentDir
            resourceInfo["url"] = resource['href']
            resourceInfo["fileName"] = parse.unquote(os.path.basename(
                resource['href']))
            resourceInfo["date"] = resource['date']
            self.resourceInfos.append(resourceInfo)

    async def getSubDirPageObjs(self, resourcePageObj, parentDir):
        """ Get the information of files in the subfolder web page.
        Args:
            resourcePageObj: BeautifulSoup Object, parse the current web page
            parentDir: String, the path of the parrent directory

        Returns:
            subDirPageObjs: BeautifulSoup Object List, all the subfolders' parsered object
        """
        subDirPageObjs = []
        # To find whether there exist subdirs
        subDirResourceList = resourcePageObj.find_all(
            'td', {'class': 'attach', 'headers': 'checkboxes'})
        # print(subDirResourceList)
        if len(subDirResourceList) == 0:
            return
        subDirResourceList.pop(0)
        for subDirResourceObj in subDirResourceList:
            collectionId = subDirResourceObj.input.get('value')
            if collectionId[-1] != '/':
                continue
            # fileBaseName = os.path.basename(collectionId)
            folderName = os.path.join(
                parentDir, collectionId.split("/")[-2])
            # print("发现子文件夹 {:s}".format(folderName))
            formData = {
                'source': '0', 'collectionId': collectionId,
                'navRoot': '', 'criteria': 'title',
                'sakai_action': 'doNavigate', 'rt_action': '', 'selectedItemId': '', 'itemHidden': 'false',
                'itemCanRevise': 'false',
                'sakai_csrf_token': self.sakai_csrf_token
            }
            async with self.sess.post(
                    self.functionUrl, data=formData, allow_redirects=True) as res:
                subPageObj = BeautifulSoup(await res.text(), "html.parser")
                subDirPageObjs.append((subPageObj, folderName))
        return subDirPageObjs

    def getUnfoldPostPattern(self, resourcePageObj):
        """ Get the data form of post for unfolding subdirectories.
        Args:
            resourcePageObj: BeautifulSoup Object, parse the current web page

        Returns:
            None
        """
        # to get the option url
        self.functionUrl = resourcePageObj.find('form').get('action')
        # to get the sakai_csrf_token,
        #    which is a param of the post packets in HTTP requests
        self.sakai_csrf_token = resourcePageObj.find(
            'input', {'name': 'sakai_csrf_token'}).get('value')

    async def getTargetInfo(self, courseInfo):
        """ Get information of coursewares of single course.
        Given by the url of the course main page, get all the information of coursewares of this course.

        Args:
            courseInfo: Dictionary {
                            "url": url of the course main page,
                            "name": the name of the course
                        }

        Returns:
            None
        """
        self.resourceInfos = []
        # Get Course directory
        courseName = courseInfo["name"]
        courseDir = os.path.join(self.downloadPath, courseName, 'Lectures')
        if not os.path.exists(courseDir):
            os.makedirs(courseDir)
        # redirect to the resource page of the course website
        resourcePageObj = await self.reDirectToTargetPage(courseInfo["url"])
        if resourcePageObj == None:
            return False
        self.getUnfoldPostPattern(resourcePageObj)
        await self.getResourceInfos(resourcePageObj)
        # print(self.resourceInfos)
        for courseware in self.resourceInfos:
            self.addDownloader(courseName, courseDir, courseware)
        return True

    def addDownloader(self, courseName, courseDir, courseware):
        subDirName = os.path.join(courseDir, courseware["subDir"])
        if not os.path.exists(subDirName):
            os.makedirs(subDirName)
        path = os.path.join(subDirName, courseware["fileName"])
        # print(f"[{courseware['date']}]: {courseware['fileName']}")
        self._downloaders.append(CoursewareDownloader(
            self, courseName, courseware['url'], path, courseware['date'], self.db))

    async def runDownloaders(self):
        tasks = [downloader.createTask(self.sess)
                 for downloader in self._downloaders]
        await asyncio.gather(*tasks)


class VideoManager(BasicManager):
    def __init__(self, session, downloadPath, coursesList, db):
        super(VideoManager, self).__init__(session, downloadPath, coursesList, db, dType="video")

    def getVideoIdAndDate(self, soup):
        infos = []
        videoDivs = soup.find_all("div", {"class": "col"})
        # videoTagAs = [div.find("a") for div in videoDivs]
        for div in videoDivs:
            videoId = div.find("a").get('onclick').strip(
                "gotoPlay('").split(',')[0].strip("'")
            date = list(filter(lambda x: "上传时间" in x.get_text(), div.find_all("div", {"class": "col_1"})))
            limit = list(filter(lambda x: "视频预计" in x.get_text(), div.find_all("div", {"class": "col_1"})))
            if limit != []:
                continue
            try:
                date = date[0].get_text().strip("上传时间：")
            except:
                date = "Null"
            # print("videoId && date: ", videoId, date)
            infos.append((videoId, date))
        return infos

    async def getUrlByVideoId(self, videoId, apiUrl):
        try:
            text = await fetch(self.sess, apiUrl+'/video/play', params={
                "id": videoId, "type": "u"})
            soup = BeautifulSoup(text, "html.parser")
            url = soup.find("video").find("source").get("src")
            name = soup.find(
                "h2", {"style": "margin-left: 2em;margin-top: 10px"}).get_text()
            return name, url
        except Exception as e:
            print(f"[{sys._getframe().f_code.co_name}:{sys._getframe().f_lineno}] Exception", e, type(e))
            return "", ""

    async def getTargetInfo(self, courseInfo):
        self.videoInfos = []
        courseName = courseInfo["name"]
        courseDir = os.path.join(self.downloadPath, courseName, 'Videos')
        # print(f"Course: {courseName}")
        if not os.path.exists(courseDir):
            os.makedirs(courseDir)
        # redirect to the resource page of the course website
        apiUrl, resourcePageObj = await self.reDirectToTargetPage(courseInfo["url"])
        if resourcePageObj == None:
            return False
        videoInfos = self.getVideoIdAndDate(resourcePageObj)
        for videoId, videoDate in videoInfos:
            name, url = await self.getUrlByVideoId(videoId, apiUrl)
            self.videoInfos.append((name, url, videoDate))
        self.videoInfos = list(filter(lambda x: "" not in x, self.videoInfos))
        for videoInfo in self.videoInfos:
            self.addDownloader(courseName, courseDir, videoInfo)
        return True

    def addDownloader(self, courseName, courseDir, videoInfo):
        name, url, date = videoInfo
        path = os.path.join(courseDir, f"{name}.mp4")
        # print(f"[{courseware['date']}]: {courseware['fileName']}")
        self._downloaders.append(VideoDownloader(
            self, courseName, url, path, date, self.db))

    async def runDownloaders(self):
        tasks = [downloader.createTask()
                 for downloader in self._downloaders]
        await asyncio.gather(*tasks)
