# -*- encoding: utf-8 -*-
"""
@Filename   : manager.py
@Description: Manager class for managing file downloading and reporting.
@Date       : 2020/03/13 11:31:56
@Author     : Wu Jiahao
@Contact    : https://github.com/flamywhale
"""

import asyncio
import json
import os
import re
import sqlite3
import sys
from bs4 import BeautifulSoup
from datetime import datetime
from getpass import getpass
from sys import exit
from urllib import parse

from src.configs import (HTTP_HDRS, SQL_CMD, TARGET_PAGE_TAG, LOGIN_URL)
from src.downloader import (CoursewareDownloader, VideoDownloader)
from src.logger import logger


async def fetch(session, url, timeout=10, params=None):
    async with session.get(url, headers=HTTP_HDRS['normal'], timeout=timeout, params=params, ssl=False) as response:
        return await response.text()


class Manager(object):
    def __init__(self, session, database_path):
        self._managers = {}
        self.database_path = database_path
        self.sess = session
        self.courses_list = []
        self.username = ''
        self.password = ''
        self.download_path = ''
        self.is_from_ucas = 'N'
        self.student_id = ''
        self.use_cache = 'Y'
        self.login_info = {}
        # check and connect database
        if not os.path.exists(self.database_path):
            self.db = sqlite3.connect(self.database_path)
            c = self.db.cursor()
            dict(map(lambda item: (item[0], c.execute(
                item[1]['create'])), SQL_CMD.items()))
            self.db.commit()
        else:
            self.db = sqlite3.connect(self.database_path)

    async def check_user(self):
        self.use_cache = input("Do you want to use cache? (Y/N): ").upper()
        c = self.db.cursor()
        while True:
            if self.use_cache == "Y":
                result = c.execute(SQL_CMD["user"]["lookup"]).fetchone()
                if result is not None:
                    self.username, self.password, self.download_path, self.is_from_ucas, self.student_id, _ = result
                    logger.info('Cached information loaded.')
                else:
                    insert_values = self.get_user_info()
                    c.execute(SQL_CMD["user"]["insert"], insert_values)
                    self.db.commit()
                    logger.info('Login information cached.')
            else:
                self.get_user_info()
            self.set_login_info()
            success = await self.try_login()
            if not success:
                print(
                    "Failed to login.\nPlease enter your username and password again, and make sure they are right!")
                if self.use_cache == "Y":
                    self.update_user_info()
            else:
                break

    def set_login_info(self):
        self.login_info = {
            'username': self.username,
            'password': self.password,
            'remember': 'checked'
        }

    def update_user_info(self):
        values = self.get_user_info()
        if self.use_cache == "Y":
            c = self.db.cursor()
            c.execute(SQL_CMD["user"]["update"], values[:-1])
            self.db.commit()
            logger.info('User information is updated.')

    async def try_login(self):
        try:
            async with self.sess.post(LOGIN_URL, headers=HTTP_HDRS['post'], data=self.login_info, timeout=10) as res:
                res_json = json.loads(await res.text())
                return res_json['f']
        except Exception as e:
            logger.error(f'{type(e)}, {e} login failed.')
            exit()

    def get_user_info(self):
        self.username = input('username: ')
        self.password = getpass('password: ')
        self.download_path = input('Where to save coursewares: ')
        return [self.username, self.password, self.download_path, self.is_from_ucas, self.student_id, 'default']

    def print_login_info(self, soup):
        name_tag = soup.find(
            "li", {"class": "btnav-info", "title": "当前用户所在单位"})
        if name_tag is None:
            logger.error("登录失败，请核对用户名和密码")
            exit(0)
        name = name_tag.get_text()
        match = re.compile(r"\s*(\S*)\s*(\S*)\s*").match(name)
        if not match:
            logger.error("脚本运行错误")
            exit("找不到用户名和单位")
        institute = match.group(1)
        name = match.group(2)
        logger.info(f'{institute} {name} 登录成功！')

    async def login(self):
        async with self.sess.post(
                LOGIN_URL, headers=HTTP_HDRS['post'], data=self.login_info) as res:
            res_json = json.loads(await res.text())
            url, parm = res_json['msg'].split('?')
        async with self.sess.get(url, headers=HTTP_HDRS['get'], params=parm) as res:
            soup = BeautifulSoup(await res.text(), 'html.parser')
            self.print_login_info(soup)
        await fetch(self.sess, "http://sep.ucas.ac.cn/appStore")

    def check_another_user(self, soup):
        another_user = ''
        tabs = soup.find_all(
            'li', {'class': 'Mrphs-userNav__submenuitem Mrphs-userNav__submenuitem-indented'})
        tabs = list(map(lambda x: x.find('a'), tabs))
        pattern = re.compile(r'^\d{4}[k,\d]\d{10}$')
        another_user_list = list(
            filter(lambda x: pattern.match(x.get_text()) != None, tabs))
        try:
            another_user = another_user_list[0].get_text()
        except Exception as e:
            another_user = ''
            logger.error(f'{type(e)}, {e}')
        return another_user

    async def fetch_course_urls(self):
        """ Get all the course information. """
        try:
            text = await fetch(self.sess, "http://sep.ucas.ac.cn/portal/site/16/801")
            soup = BeautifulSoup(text, "html.parser")
            course_website_url = soup.find(
                'noscript').meta.get("content")[6:]
            text = await fetch(self.sess, course_website_url)
            if self.is_from_ucas.upper() == 'Y':
                # Must use https here
                text = await fetch(self.sess, "https://course.ucas.ac.cn/portal",
                                   params={'anotherUser': self.student_id})
            soup = BeautifulSoup(text, "html.parser")
            another_user = self.check_another_user(soup)
            if another_user is not None and self.is_from_ucas.upper() != 'Y':
                print("Another user detected.")
                current_user = soup.find('div', {'class': 'Mrphs-userNav__submenuitem--displayid'}).get_text().strip()
                print(f"Current user: {current_user}")
                print(f"Another user: {another_user}")
                change = input("Do you want to change to another user and set it as default(if use cache)? (Y/N): ")
                if change.upper() == "Y":
                    # Must use https here
                    text = await fetch(self.sess, "https://course.ucas.ac.cn/portal",
                                       params={'anotherUser': another_user})
                    soup = BeautifulSoup(text, "html.parser")
                    if self.use_cache.upper() == "Y":
                        self.is_from_ucas = "Y"
                        self.student_id = another_user
                        c = self.db.cursor()
                        values = [self.username, self.password, self.download_path, self.is_from_ucas, self.student_id]
                        c.execute(SQL_CMD["user"]["update"], values)
                        self.db.commit()
            # below is to find course urls
            logger.info(f'Fetching course urls...')
            all_courses_tab = soup.find(
                'a', {'class': "Mrphs-toolsNav__menuitem--link", 'title': "我的课程 - 查看或加入站点"}).get("href")
            # logDebug(f"all_courses_tab = {all_courses_tab}")
            text = await fetch(self.sess, all_courses_tab)
            soup = BeautifulSoup(text, "html.parser")
            all_courses_info = soup.find(
                'ul', {'class': "otherSitesCategorList favoriteSiteList"}).find_all('div', {'class': "fav-title"})
            for course_info in all_courses_info:
                course = {}
                course["name"] = course_info.find('a').get('title')
                course["url"] = course_info.find('a').get('href')
                logger.info(f'Find course {course["name"]}')
                # print(f'[{ctime()}] Find course {course["name"]}')
                self.courses_list.append(course)
        except Exception as e:
            logger.error(f'{type(e)}, {e}')
            exit(0)

    async def initialize(self):
        await self.check_user()
        await self.login()
        await self.fetch_course_urls()
        command_line = "Please choose download objects:\n\t1: 下载课件\n\t2: 下载视频\n\t3: 下载课件和视频\n\t4: 检查作业提交情况\nMode = "
        mode = int(input(command_line))
        if (mode & 0b01):
            self._managers['courseware'] = CoursewareManager(
                self.sess, self.download_path, self.courses_list, self.db)
        if (mode & 0b10):
            self._managers['video'] = VideoManager(
                self.sess, self.download_path, self.courses_list, self.db)
        if (mode & 0b100):
            self._managers['homework'] = HomeworkManager(
                self.sess, self.download_path, self.courses_list, self.db)

    async def run(self):
        """Run the pipeline"""
        await self.initialize()
        try:
            for _, manager in self._managers.items():
                await manager.run()
        except Exception as e:
            logger.error(f'{type(e)}, {e}')
            exit(0)


class BasicManager(object):
    def __init__(self, session, download_path, courses_list, db, m_type="basic"):
        self._type = m_type
        self._downloaders = []
        self._messages = {'update': [], 'new': [], 'error': []}
        self.sess = session
        self.download_path = download_path
        self.courses_list = courses_list
        self.db = db
        self.chooseCourses()

    def chooseCourses(self):
        print(f"\n{'*' * 6} {self._type.upper()} MANAGER INFO {'*' * 6}")
        print(f"Please choose courses to download {self._type}.")
        for i, course in enumerate(self.courses_list):
            print(f"\t{i}\t{course['name']}")
        download_all = input(
            f"Do you want to check {self._type}s of all courses?('Y' or 'N'): ")
        if download_all.upper() == "Y":
            return
        print("Please type serial numbers of courses in one line and seperate them with *SPACE*.")
        print("e.g. '1 2 3 4 5'")
        ""
        course_num = len(self.courses_list)
        numbers = list(filter(lambda x: x.isdigit() and int(x)
                                        < course_num, input().split(' ')))
        numbers = list(map(lambda x: int(x), numbers))
        self.courses_list = [self.courses_list[idx] for idx in numbers]
        print("Chosen courses are as follows:")
        for course in self.courses_list:
            print(f"{course['name']}")
        print()

    def add_report_message(self, mode, msg):
        self._messages[mode].append(msg)

    def report(self):
        logger.info(
            f"{'*' * 6} REPORT OF {self._type.upper()} MANAGER START {'*' * 6}.")
        for key, messages in self._messages.items():
            for msg in messages:
                logger.info(f"{key.upper()}: {msg}")
            if len(messages) == 0:
                logger.info(f"There are no {key} {self._type}s.")
        logger.info(
            f"{'*' * 6} REPORT OF {self._type.upper()} MANAGER END {'*' * 6}.")

    async def redirect_to_target_page(self, courseUrl):
        """ Redirect page to target page.

        Redirect the page from course website main page to target page,
        in order to get something.

        Args:
            courseUrl: String, the url of course main page

        Returns:
            resource_page_obj: BeatifulSoup Object, parse the resource page
        """
        text = await fetch(self.sess, courseUrl)
        soup = BeautifulSoup(text, "html.parser")
        try:
            resource_page_url = soup.find(
                'a', TARGET_PAGE_TAG[self._type]).get("href")
            text = await fetch(self.sess, resource_page_url)
            resource_page_obj = BeautifulSoup(text, 'html.parser')
            # if self._type == "video":
            # return [resource_page_url, resource_page_obj]
            return resource_page_url, resource_page_obj
        except Exception as e:
            print(
                f"[{sys._getframe().f_code.co_name}:{sys._getframe().f_lineno}] Exception", e, type(e))
            return None, None

    async def get_target_info(self, course):
        pass

    async def run_downloaders(self):
        pass

    async def get_resource_info_list(self):
        for course in self.courses_list:
            await self.get_target_info(course)

    async def run(self):
        """Run the pipeline"""
        await self.get_resource_info_list()
        start = datetime.now()
        try:
            logger.info(f'Going to arrange downloading {self._type} tasks.')
            await self.run_downloaders()
            stop = datetime.now()
            logger.info(
                f'All downloaders cost {(stop - start).total_seconds()} seconds.')
            self.report()
        except Exception as e:
            logger.error(f'{type(e)}, {e}')
            exit(0)


class CoursewareManager(BasicManager):
    def __init__(self, session, download_path, courses_list, db):
        super(CoursewareManager, self).__init__(
            session, download_path, courses_list, db, m_type="courseware")

    async def get_resources_info(self, resource_page_obj, parent_dir=""):
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
        The information of the resources is stored in self.resource_infos,
        which is a list.
        Args:
            resource_page_obj: BeautifulSoup Object, parse the current web page
            parent_dir: String, the path of the parrent directory
        Returns:
            None
        """
        # get urls of files under current directory
        self.get_files_info_of_current_dir(resource_page_obj, parent_dir)
        # get urls of files under subfolders
        subDirPageInfoList = await self.get_subdir_page_objects(resource_page_obj, parent_dir)
        for subDirPageObj, subDir in subDirPageInfoList:
            await self.get_resources_info(subDirPageObj, subDir)

    def get_files_info_of_current_dir(self, resource_page_obj, parent_dir):
        """ Get the information of files in the current web page.
        Args:
            resource_page_obj: BeautifulSoup Object, parse the current web page
            parent_dir: String, the path of the parrent directory
        Returns:
            None
        """
        rows = resource_page_obj.find_all("tr")
        resource_list = []
        for row in rows:
            link = row.find("a").get('href')
            if link == '#':
                continue
            date = row.find(
                "td", {"class": "modified hidden-sm hidden-xs"}).get_text().strip()
            resource_list.append({"href": link, "date": date})
        for resource in resource_list:
            resource_info = {}
            resource_info["subDir"] = parent_dir
            resource_info["url"] = resource['href']
            resource_info["fileName"] = parse.unquote(os.path.basename(
                resource['href']))
            resource_info["date"] = resource['date']
            self.resource_infos.append(resource_info)

    async def get_subdir_page_objects(self, resource_page_obj, parent_dir):
        """ Get the information of files in the subfolder web page.
        Args:
            resource_page_obj: BeautifulSoup Object, parse the current web page
            parent_dir: String, the path of the parrent directory
        Returns:
            sub_dir_page_objs: BeautifulSoup Object List, all the subfolders' parsered object
        """
        sub_dir_page_objs = []
        # To find whether there exist subdirs
        sub_dir_resource_list = resource_page_obj.find_all(
            'td', {'class': 'attach', 'headers': 'checkboxes'})
        # print(sub_dir_resource_list)
        if len(sub_dir_resource_list) == 0:
            return
        sub_dir_resource_list.pop(0)
        for sub_dir_resource_obj in sub_dir_resource_list:
            collection_id = sub_dir_resource_obj.input.get('value')
            if collection_id[-1] != '/':
                continue
            # fileBaseName = os.path.basename(collectionId)
            folder_name = os.path.join(
                parent_dir, collection_id.split("/")[-2])
            print("发现子文件夹 {:s}".format(folder_name))
            form_data = {
                'source': '0', 'collectionId': collection_id,
                'navRoot': '', 'criteria': 'title',
                'sakai_action': 'doNavigate', 'rt_action': '', 'selectedItemId': '', 'itemHidden': 'false',
                'itemCanRevise': 'false',
                'sakai_csrf_token': self.sakai_csrf_token
            }
            async with self.sess.post(
                    self.function_url, data=form_data, allow_redirects=True) as res:
                sub_page_obj = BeautifulSoup(await res.text(), "html.parser")
                sub_dir_page_objs.append((sub_page_obj, folder_name))
        return sub_dir_page_objs

    def get_unfold_post_pattern(self, resourcePageObj):
        """ Get the data form of post for unfolding subdirectories.
        Args:
            resourcePageObj: BeautifulSoup Object, parse the current web page
        Returns:
            None
        """
        # to get the option url
        self.function_url = resourcePageObj.find('form').get('action')
        # to get the sakai_csrf_token,
        #    which is a param of the post packets in HTTP requests
        self.sakai_csrf_token = resourcePageObj.find(
            'input', {'name': 'sakai_csrf_token'}).get('value')

    async def get_target_info(self, course_info):
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
        self.resource_infos = []
        # Get Course directory
        course_name = course_info["name"]
        course_dir = os.path.join(self.download_path, course_name, 'Lectures')
        if not os.path.exists(course_dir):
            os.makedirs(course_dir)
        # redirect to the resource page of the course website
        _, resource_page_obj = await self.redirect_to_target_page(course_info["url"])
        if resource_page_obj is None:
            return False
        self.get_unfold_post_pattern(resource_page_obj)
        await self.get_resources_info(resource_page_obj)
        # print(self.resource_infos)
        for courseware in self.resource_infos:
            self.add_downloader(course_name, course_dir, courseware)
        return True

    def add_downloader(self, course_name, course_dir, courseware):
        sub_dir_name = os.path.join(course_dir, courseware["subDir"])
        if not os.path.exists(sub_dir_name):
            os.makedirs(sub_dir_name)
        path = os.path.join(sub_dir_name, courseware["fileName"])
        # print(f"[{courseware['date']}]: {courseware['fileName']}")
        self._downloaders.append(CoursewareDownloader(
            self, course_name, courseware['url'], path, courseware['date'], self.db))

    async def run_downloaders(self):
        tasks = [downloader.create_task(self.sess)
                 for downloader in self._downloaders]
        await asyncio.gather(*tasks)


class VideoManager(BasicManager):
    def __init__(self, session, download_path, courses_list, db):
        super(VideoManager, self).__init__(
            session, download_path, courses_list, db, m_type="video")

    def get_video_id_and_date(self, soup):
        infos = []
        video_divs = soup.find_all("div", {"class": "col"})
        # videoTagAs = [div.find("a") for div in video_divs]
        for div in video_divs:
            video_id = div.find("a").get('onclick').strip(
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
            # print("video_id && date: ", video_id, date)
            infos.append((video_id, date))
        return infos

    async def get_url_by_video_id(self, videoId, apiUrl):
        try:
            text = await fetch(self.sess, apiUrl + '/video/play', params={
                "id": videoId, "type": "u"})
            soup = BeautifulSoup(text, "html.parser")
            url = soup.find("video").find("source").get("src")
            name = soup.find(
                "h2", {"style": "margin-left: 2em;margin-top: 10px"}).get_text()
            return name, url
        except Exception as e:
            logger.error(f'{type(e)}, {e}')
            return "", ""

    async def get_target_info(self, course_info):
        self.videos_info = []
        course_name = course_info["name"]
        course_dir = os.path.join(self.download_path, course_name, 'Videos')
        # print(f"Course: {course_name}")
        if not os.path.exists(course_dir):
            os.makedirs(course_dir)
        # redirect to the resource page of the course website
        api_url, resource_page_obj = await self.redirect_to_target_page(course_info["url"])
        if resource_page_obj == None:
            return False
        videos_info = self.get_video_id_and_date(resource_page_obj)
        for video_id, video_date in videos_info:
            name, url = await self.get_url_by_video_id(video_id, api_url)
            self.videos_info.append((name, url, video_date))
        self.videos_info = list(filter(lambda x: "" not in x, self.videos_info))
        for video_info in self.videos_info:
            self.add_downloader(course_name, course_dir, video_info)
        return True

    def add_downloader(self, course_name, course_dir, video_info):
        name, url, date = video_info
        # avoid the existance of space in file name
        name = name.replace(' ', '_').replace('/', '')
        path = os.path.join(course_dir, f"{name}.mp4")
        # print(f"[{courseware['date']}]: {courseware['fileName']}")
        self._downloaders.append(VideoDownloader(
            self, course_name, url, path, date, self.db))

    async def run_downloaders(self):
        tasks = [downloader.create_task()
                 for downloader in self._downloaders]
        await asyncio.gather(*tasks)


class HomeworkManager(BasicManager):
    def __init__(self, session, download_path, courses_list, db):
        super(HomeworkManager, self).__init__(
            session, download_path, courses_list, db, m_type="homework")
        self._messages = {"warning": []}

    async def get_target_info(self, course_info):
        course_name = course_info["name"]
        # redirect to the resource page of the course website
        _, resource_page_obj = await self.redirect_to_target_page(course_info["url"])
        if resource_page_obj == None:
            return False
        try:
            homeworks = resource_page_obj.find_all("tr")[1:]
            for homework in homeworks:
                status = homework.find("td", {"headers": "status"}).get_text().strip()
                if status == "尚未提交":
                    name = homework.find("td", {"headers": "title"}).find("a").get_text()
                    due_date = homework.find("td", {"headers": "dueDate"}).find("span").get_text()
                    self.add_report_message("warning", f"{course_name}/{name}未提交，截止日期：{due_date}")
        except Exception as e:
            logger.error(f'{type(e)}, {e}, in {course_name}')

    async def run(self):
        await self.get_resource_info_list()
        self.report()
