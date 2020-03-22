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

from src.configs import (HTTP_HDRS, SQL_CMD, TARGET_PAGE_TAG, LOGIN_URL)
from src.downloader import (CoursewareDownloader, VideoDownloader)
from src.logger import (logError, logInfo, logDebug)


async def fetch(session, url, timeout=10, params=None):
    async with session.get(url, headers=HTTP_HDRS['normal'], timeout=timeout, params=params) as response:
        return await response.text()


class Manager(object):
    def __init__(self, session, databasePath):
        self._managers = {}
        self.databasePath = databasePath
        self.sess = session
        self.coursesList = []
        self.username = ''
        self.password = ''
        self.downloadPath = ''
        self.isFromUCAS = 'N'
        self.studentID = ''
        try:
            self.checkDatebase()
        except Exception as e:
            logError(f'{type(e)}, {e}')
            exit(1)

    def checkDatebase(self):
        if not os.path.exists(self.databasePath):
            self.db = sqlite3.connect(self.databasePath)
            c = self.db.cursor()
            dict(map(lambda item: (item[0], c.execute(
                item[1]['create'])), SQL_CMD.items()))
            self.db.commit()
        else:
            self.db = sqlite3.connect(self.databasePath)

    async def checkUser(self):
        self.useCache = input("Do you want to use cache? (Y/N): ").upper()
        c = self.db.cursor()
        while True:
            if self.useCache == "Y":
                result = c.execute(SQL_CMD["user"]["lookup"]).fetchone()
                if result != None:
                    self.username, self.password, self.downloadPath, self.isFromUCAS, self.studentID, _ = result
                    logInfo('Cached information loaded.')
                else:
                    insertValues = self.getUserInfo()
                    c.execute(SQL_CMD["user"]["insert"], insertValues)
                    self.db.commit()
                    logInfo('Login information cached.')
            else:
                self.getUserInfo()
            self.setLoginInfo()
            success = await self.tryToLogin()
            if not success:
                print(
                    "Failed to login.\nPlease enter your username and password again, and make sure they are right!")
                if self.useCache == "Y":
                    self.updateUserInfo()
            else:
                break

    def setLoginInfo(self):
        self.loginInfo = {
            'username': self.username,
            'password': self.password,
            'remember': 'checked'
        }

    def updateUserInfo(self):
        values = self.getUserInfo()
        if self.useCache == "Y":
            c = self.db.cursor()
            c.execute(SQL_CMD["user"]["update"], values[:-1])
            self.db.commit()
            logInfo('User information is updated.')

    async def tryToLogin(self):
        async with self.sess.post(
                LOGIN_URL, headers=HTTP_HDRS['post'], data=self.loginInfo) as res:
            resJson = json.loads(await res.text())
            return resJson['f']

    def getUserInfo(self):
        self.username = input('username: ')
        self.password = getpass('password: ')
        self.downloadPath = input('Where to save coursewares: ')
        # self.isFromUCAS = input(
            # 'Whether you are graduated from UCAS(for UCAS undergraduates) Y/N: ').upper()
        # if self.isFromUCAS.upper() == 'Y':
            # self.studentID = input('Your current student ID: ')
        return [self.username, self.password, self.downloadPath, self.isFromUCAS, self.studentID, 'default']

    def printLoginInfo(self, soup):
        nameTag = soup.find(
            "li", {"class": "btnav-info", "title": "当前用户所在单位"})
        if nameTag is None:
            logError("登录失败，请核对用户名和密码")
            exit(0)
        name = nameTag.get_text()
        match = re.compile(r"\s*(\S*)\s*(\S*)\s*").match(name)
        if not match:
            logError("脚本运行错误")
            exit("找不到用户名和单位")
        institute = match.group(1)
        name = match.group(2)
        logInfo(f'{institute} {name} 登录成功！')

    async def login(self):
        async with self.sess.post(
                LOGIN_URL, headers=HTTP_HDRS['post'], data=self.loginInfo) as res:
            resJson = json.loads(await res.text())
            url, parm = resJson['msg'].split('?')
        async with self.sess.get(url, headers=HTTP_HDRS['get'], params=parm) as res:
            soup = BeautifulSoup(await res.text(), 'html.parser')
            self.printLoginInfo(soup)
        await fetch(self.sess, "http://sep.ucas.ac.cn/appStore")

    def checkAnotherUser(self, soup):
        tabs = soup.find_all(
            'li', {'class': 'Mrphs-userNav__submenuitem Mrphs-userNav__submenuitem-indented'})
        tabs = list(map(lambda x: x.find('a'), tabs))
        pattern = re.compile(r'^\d{4}[k,\d]\d{10}$')
        anotherUserList = list(
            filter(lambda x: pattern.match(x.get_text()) != None, tabs))
        if len(anotherUserList) == 0:
            return None
        try:
            anotherUser = anotherUserList[0].get_text()
        except Exception as e:
            logError(f'{type(e)}, {e}')
            exit(0)
        return anotherUser

    async def fetchCourseUrls(self):
        """ Get all the course information. """
        try:
            text = await fetch(self.sess, "http://sep.ucas.ac.cn/portal/site/16/801")
            bsObj = BeautifulSoup(text, "html.parser")
            courseWebsiteUrl = bsObj.find(
                'noscript').meta.get("content")[6:]
            text = await fetch(self.sess, courseWebsiteUrl)
            if self.isFromUCAS.upper() == 'Y':
                # Must use https here
                text = await fetch(self.sess, "https://course.ucas.ac.cn/portal", params={'anotherUser': self.studentID})
            bsObj = BeautifulSoup(text, "html.parser")
            anotherUser = self.checkAnotherUser(bsObj)
            if anotherUser != None and self.isFromUCAS.upper() != 'Y':
                print("Another user detected.")
                currentUser = bsObj.find('div', {'class': 'Mrphs-userNav__submenuitem--displayid'}).get_text().strip()
                print(f"Current user: {currentUser}")
                print(f"Another user: {anotherUser}")
                change = input("Do you want to change to another user and set it as default(if use cache)? (Y/N): ")
                if change.upper() == "Y":
                    # Must use https here
                    text = await fetch(self.sess, "https://course.ucas.ac.cn/portal", params={'anotherUser': anotherUser})
                    bsObj = BeautifulSoup(text, "html.parser")
                    if self.useCache.upper() == "Y":
                        self.isFromUCAS = "Y"
                        self.studentID = anotherUser
                        c = self.db.cursor()
                        values = [self.username, self.password, self.downloadPath, self.isFromUCAS, self.studentID]
                        c.execute(SQL_CMD["user"]["update"], values)
                        self.db.commit()
            # below is to find course urls
            logInfo(f'Fetching course urls...')
            allCoursesTab = bsObj.find(
                'a', {'class': "Mrphs-toolsNav__menuitem--link", 'title': "我的课程 - 查看或加入站点"}).get("href")
            # logDebug(f"allCoursesTab = {allCoursesTab}")
            text = await fetch(self.sess, allCoursesTab)
            bsObj = BeautifulSoup(text, "html.parser")
            allCoursesInfo = bsObj.find(
                'ul', {'class': "otherSitesCategorList favoriteSiteList"}).find_all('div', {'class': "fav-title"})
            # print("allCoursesInfo" , allCoursesInfo)
            for courseInfo in allCoursesInfo:
                course = {}
                course["name"] = courseInfo.find('a').get('title')
                course["url"] = courseInfo.find('a').get('href')
                logInfo(f'Find course {course["name"]}')
                # print(f'[{ctime()}] Find course {course["name"]}')
                self.coursesList.append(course)
        except Exception as e:
            logError(f'{type(e)}, {e}')
            exit(0)

    async def initialize(self):
        await self.checkUser()
        await self.login()
        await self.fetchCourseUrls()
        commandLine = "Please choose download objects:\n\t1: 下载课件\n\t2: 下载视频\n\t3: 下载课件和视频\nMode = "
        mode = int(input(commandLine))
        if (mode & 0b01):
            self._managers['courseware'] = CoursewareManager(
                self.sess, self.downloadPath, self.coursesList, self.db)
        if (mode & 0b10):
            self._managers['video'] = VideoManager(
                self.sess, self.downloadPath, self.coursesList, self.db)

    async def run(self):
        """Run the pipeline"""
        await self.initialize()
        try:
            for _, manager in self._managers.items():
                await manager.run()
        except Exception as e:
            logError(f'{type(e)}, {e}')
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
        downloadAll = input(
            f"Do you want to download {self._type}s of all courses?('Y' or 'N'): ")
        if downloadAll.upper() == "Y":
            return
        print("Please type serial numbers of courses in one line and seperate them with *SPACE*.")
        print("e.g. '1 2 3 4 5'")
        ""
        courseNum = len(self.coursesList)
        numbers = list(filter(lambda x: x.isdigit() and int(x)
                              < courseNum, input().split(' ')))
        numbers = list(map(lambda x: int(x), numbers))
        self.coursesList = [self.coursesList[idx] for idx in numbers]
        print("Chosen courses are as follows:")
        for course in self.coursesList:
            print(f"{course['name']}")
        print()

    def addReportMessage(self, mode, msg):
        self._messages[mode].append(msg)

    def report(self):
        logInfo(
            f"{'*'*6} REPORT OF {self._type.upper()} MANAGER START {'*'*6}.")
        for key, messages in self._messages.items():
            for msg in messages:
                logInfo(f"{key.upper()}: {msg}")
            if len(messages) == 0:
                logInfo(f"There are no {key} {self._type}s.")
        logInfo(
            f"{'*'*6} REPORT OF {self._type.upper()} MANAGER END {'*'*6}.")

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
            print(
                f"[{sys._getframe().f_code.co_name}:{sys._getframe().f_lineno}] Exception", e, type(e))
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
            logInfo(f'Going to arrange downloading {self._type} tasks.')
            await self.runDownloaders()
            stop = datetime.now()
            logInfo(
                f'All downloaders cost {(stop-start).total_seconds()} seconds.')
            self.report()
        except Exception as e:
            logError(f'{type(e)}, {e}')
            exit(0)


class CoursewareManager(BasicManager):
    def __init__(self, session, downloadPath, coursesList, db):
        super(CoursewareManager, self).__init__(
            session, downloadPath, coursesList, db, dType="courseware")

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
        super(VideoManager, self).__init__(
            session, downloadPath, coursesList, db, dType="video")

    def getVideoIdAndDate(self, soup):
        infos = []
        videoDivs = soup.find_all("div", {"class": "col"})
        # videoTagAs = [div.find("a") for div in videoDivs]
        for div in videoDivs:
            videoId = div.find("a").get('onclick').strip(
                "gotoPlay('").split(',')[0].strip("'")
            date = list(filter(lambda x: "上传时间" in x.get_text(),
                               div.find_all("div", {"class": "col_1"})))
            limit = list(filter(lambda x: "视频预计" in x.get_text(),
                                div.find_all("div", {"class": "col_1"})))
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
            logError(f'{type(e)}, {e}')
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
