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
from aiohttp import ClientSession
from bs4 import BeautifulSoup
from configparser import ConfigParser
from datetime import datetime
from getpass import getpass
from sys import exit
from time import ctime
from urllib import parse

from configs import (CREATE_FILES_TABLE, CREATE_USERS_TABLE, DATABASE_NAME,
                     GET_HDRS, HEADERS, INSERT_USERS_TABLE, LOOKUP_USERS_TABLE,
                     UPDATE_USERS_TABLE, POST_HDRS)
from downloader import CourseDownloader


class Manager(object):
    def __init__(self, session):
        self.sess = session
        self.coursesList = []
        self.resourceInfos = []
        self.videoInfos = []
        self.messages = {'update': [], 'new': []}
        self._downloaders = []
        self.downloadPath = ''
        self.username = ''
        self.password = ''

        self.checkDatebase()
        self.checkUser()

    def checkDatebase(self):
        if not os.path.exists(DATABASE_NAME):
            self.conn = sqlite3.connect(DATABASE_NAME)
            c = self.conn.cursor()
            c.execute(CREATE_FILES_TABLE)
            c.execute(CREATE_USERS_TABLE)
            self.conn.commit()
        else:
            self.conn = sqlite3.connect(DATABASE_NAME)

    def updateUserInfo(self):
        values = self.getUserInfo()
        c = self.conn.cursor()
        c.execute(UPDATE_USERS_TABLE, values)

    def checkUser(self):
        c = self.conn.cursor()
        result = c.execute(LOOKUP_USERS_TABLE).fetchone()
        if result == None:
            insertValues = self.getUserInfo()
            c.execute(INSERT_USERS_TABLE, insertValues)
            self.conn.commit()
        else:
            self.username, self.password, self.downloadPath = result[0:3]

        self.loginInfo = {
            'username': self.username,
            'password': self.password,
            'remember': 'checked'
        }

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

    def addReportMessage(self, mode, msg):
        self.messages[mode].append(msg)

    def report(self):
        for msg in self.messages['new']:
            print(f"[{ctime()} NEW]：{msg}")
        if len(self.messages['new']) == 0:
            print(f"[{ctime()}] No new coursewares are found.")
        for msg in self.messages['update']:
            print(f"[{ctime()} UPDATE]：{msg}")
        if len(self.messages['update']) == 0:
            print(f"[{ctime()}] No coursewares are updated.")

    async def fetch(self, session, url, timeout=10, params=None):
        async with session.get(url, headers=HEADERS, timeout=timeout, params=params) as response:
            return await response.text()

    async def login(self):
        async with self.sess.post(
                'http://onestop.ucas.ac.cn/Ajax/Login/0', headers=POST_HDRS, data=self.loginInfo) as res:
            resJson = json.loads(await res.text())
            if resJson['f']:
                url, parm = resJson['msg'].split('?')
            else:
                print(f"{resJson['msg']}！\n请重新运行并输入账号密码。")
                self.updateUserInfo()
                exit(0)
        async with self.sess.get(url, headers=GET_HDRS, params=parm) as res:
            soup = BeautifulSoup(await res.text(), 'html.parser')
            self.printLoginInfo(soup)
        await self.fetch(self.sess, "http://sep.ucas.ac.cn/appStore")

    async def fetchCourseUrls(self):
        """ Get all the course information. """
        print(f'[{ctime()}] Fetch course urls...')
        try:
            text = await self.fetch(self.sess, "http://sep.ucas.ac.cn/portal/site/16/801")
            bsObj = BeautifulSoup(text, "html.parser")
            courseWebsiteUrl = bsObj.find(
                'noscript').meta.get("content")[6:]
            # print(courseWebsiteUrl)
            text = await self.fetch(self.sess, courseWebsiteUrl)
            bsObj = BeautifulSoup(text, "html.parser")
            allCoursesUrl = bsObj.find(
                'a', {'class': "Mrphs-toolsNav__menuitem--link", 'title': "我的课程 - 查看或加入站点"}).get("href")
            # print(allCoursesUrl)
            text = await self.fetch(self.sess, allCoursesUrl)
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

    async def reDirectToVideoPage(self, courseUrl):
        """ Redirect page to video page.

        Redirect the page from course website main page to its video page,
        in order to get video urls.

        Args:
            courseUrl: String, the url of course main page

        Returns:
            resourcePageObj: BeatifulSoup Object, parse the resource page
        """
        text = await self.fetch(self.sess, courseUrl)
        bsObj = BeautifulSoup(text, "html.parser")
        try:
            resourcePageUrl = bsObj.find(
                'a', {"title": "课程视频 - 课程视频"}).get("href")
            # print(resourcePageUrl)
            text = await self.fetch(self.sess, resourcePageUrl)
            resourcePageObj = BeautifulSoup(text, 'html.parser')
            return [resourcePageUrl, resourcePageObj]
        except Exception as e:
            print("ERROR: ", e, type(e))
            return None

    async def reDirectToResourcePage(self, courseUrl):
        """ Redirect page to resource page.

        Redirect the page from course website main page to its resource page,
        in order to get coursewares.

        Args:
            courseUrl: String, the url of course main page

        Returns:
            resourcePageObj: BeatifulSoup Object, parse the resource page
        """
        text = await self.fetch(self.sess, courseUrl)
        bsObj = BeautifulSoup(text, "html.parser")
        try:
            resourcePageUrl = bsObj.find(
                'a', {"title": "资源 - 上传、下载课件，发布文档，网址等信息"}).get("href")
            text = await self.fetch(self.sess, resourcePageUrl)
            resourcePageObj = BeautifulSoup(text, 'html.parser')
            return resourcePageObj
        except:
            return None

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

    def getIdsOfVideos(self, soup):
        ids = []
        videoDivs = soup.find_all("div", {"class": "col"})
        videoTagAs = [div.find("a") for div in videoDivs]
        for a in videoTagAs:
            videoId = a.get('onclick').strip(
                "gotoPlay('").split(',')[0].strip("'")
            ids.append(videoId)
        return ids

    async def getUrlByVideoId(self, videoId, apiUrl):
        try:
            text = await self.fetch(self.sess, apiUrl+'/video/play', params={
                            "id": videoId, "type": "u"})
            soup = BeautifulSoup(text, "html.parser")
            url = soup.find("video").find("source").get("src")
            name = soup.find("h2", {"style": "margin-left: 2em;margin-top: 10px"}).get_text()
            return name, url
        except Exception as e:
            print("ERROR: ", e, type(e))
            return "",""

    async def getUrlsOfOneCourse(self, courseInfo):
        courseName = courseInfo["name"]
        courseDir = os.path.join(self.downloadPath, courseName, 'Videos')
        print(f"Course: {courseName}")
        if not os.path.exists(courseDir):
            os.makedirs(courseDir)
        # redirect to the resource page of the course website
        apiUrl, resourcePageObj = await self.reDirectToVideoPage(courseInfo["url"])
        if resourcePageObj == None:
            return False
        videoIds = self.getIdsOfVideos(resourcePageObj)
        for videoId in videoIds:
            name, url = await self.getUrlByVideoId(videoId, apiUrl)
            # print(name, url)
            if name == "" or url == "":
                continue
            self.videoInfos.append((name, url))
        return True

    async def getUrlsOfAllCourses(self):
        for course in self.coursesList:
            await self.getUrlsOfOneCourse(course)
        # with open("urls.txt", "w") as f:
        #     for name, url in self.videoInfos:
        #         f.writelines(f"{name},{url}\n")
        return self.videoInfos

    async def getCoursewareInfo(self, courseInfo):
        self.resourceInfos = []
        # Get Course directory
        courseName = courseInfo["name"]
        courseDir = os.path.join(self.downloadPath, courseName)
        if not os.path.exists(courseDir):
            os.makedirs(courseDir)
        # redirect to the resource page of the course website
        resourcePageObj = await self.reDirectToResourcePage(courseInfo["url"])
        if resourcePageObj == None:
            return False
        self.getUnfoldPostPattern(resourcePageObj)
        await self.getResourceInfos(resourcePageObj)
        # print(self.resourceInfos)
        for courseware in self.resourceInfos:
            self.addDownloader(courseName, courseDir, courseware)
        return True

    async def getCoursewaresInfoList(self):
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
        for course in self.coursesList:
            await self.getCoursewareInfo(course)

    def addDownloader(self, courseName, courseDir, courseware):
        subDirName = os.path.join(courseDir, courseware["subDir"])
        if not os.path.exists(subDirName):
            os.makedirs(subDirName)
        path = os.path.join(subDirName, courseware["fileName"])
        # print(f"[{courseware['date']}]: {courseware['fileName']}")
        self._downloaders.append(CourseDownloader(
            self, courseName, courseware['url'], path, courseware['date'], self.conn))

    async def runDownloaders(self):
        tasks = [downloader.createTask(self.sess)
                 for downloader in self._downloaders]
        await asyncio.gather(*tasks)

    async def initialize(self):
        await self.login()
        await self.fetchCourseUrls()
        await self.getCoursewaresInfoList()

    async def run(self):
        """Run the pipeline"""
        start = datetime.now()
        await self.initialize()
        try:
            print(f'[{ctime()}] Going to arrange downloading tasks.')
            await self.runDownloaders()
            stop = datetime.now()
            print(f'[{ctime()}] All downloaders cost',
                  (stop-start).total_seconds(), 'seconds.')
            self.report()
        except Exception as e:
            print(e)
            exit(0)
        # stop_time = datetime.now()

        # return (stop_time - start_time).total_seconds()
