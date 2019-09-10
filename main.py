# -*- coding: utf-8 -*-

import os
import re
import sys
import requests
import configparser
from urllib import parse
from bs4 import BeautifulSoup
from PIL import Image
from PIL.ImageQt import ImageQt
from PyQt5.QtCore import (QThread, pyqtSignal)
from PyQt5.QtGui import (QImage, QPixmap)
from PyQt5.QtWidgets import (
    QMessageBox, QLineEdit, QGraphicsScene,
    QGraphicsPixmapItem, QDialog, QApplication, QFileDialog)
from dialog import Ui_Dialog

class DownloadThread(QThread):
    def __init__(self):
        super(DownloadThread, self).__init__()
        self.resourceInfos = []
    def run(self):
        pass


class LoginThread(QThread):
    def __init__(self):
        super(LoginThread, self).__init__()

    def run(self):
        pass


class GetCourseThread(QThread):
    def __init__(self):
        super(GetCourseThread, self).__init__()

    def run(self):
        pass


class Ui(QDialog):
    def __init__(self):
        super(Ui, self).__init__()
        # set downloading path as the current path
        self.downloadPath = os.path.abspath('.')
        self.confName = "cache.cfg"
        self.certImageName = "certcode.jpg"
        self.login = {}
        self.coursesList = []
        self.resourceInfos = []
        self.sess = requests.session()
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)
        self.initUI()
        self.show()

    def initUI(self):
        """ Initialize UI by adding more attributes to it 
        Args:
            None

        Returns:
            None
        """
        # add button events
        self.ui.loginButton.clicked.connect(self.onClickLogin)
        self.ui.loginButton.setDefault(True)
        self.ui.getCourses.clicked.connect(self.onClickGetCourses)
        self.ui.choosePath.clicked.connect(self.onClickChoosePath)
        self.ui.downloadAll.clicked.connect(self.onClickDownloadAll)
        self.ui.refreshCertCode.clicked.connect(self.showCertImage)
        # set text editer properties
        self.ui.passwd.setEchoMode(QLineEdit.Password)
        self.ui.logInfo.setReadOnly(True)
        self.ui.progressInfo.setReadOnly(True)
        self.ui.certCode.setPlaceholderText("请输入验证码")
        self.ui.showPath.setText(self.downloadPath)
        # check login configurations
        self.checkConf()
        # show the certification code image
        self.showCertImage()
        # initialize the status of the progress bar
        self.ui.progressBar.setRange(0, 0)
        # set window title
        self.setWindowTitle("批量下载课件脚本")

    def checkConf(self):
        """ Check login configurations

        Check whether the default login configuration file exists.
        If exists, read configurarions into in-memory.
        Else, return.

        Args:
            None

        Returns:
            None
        """
        if not os.path.exists(self.confName):
            return
        conf = configparser.ConfigParser()
        conf.read(self.confName)
        username = conf.get('Default', 'usrname')
        password = conf.get('Default', 'passwd')
        self.ui.userName.setText(username)
        self.ui.passwd.setText(password)
        self.ui.remPasswd.setChecked(True)

    def reDirectToResourcePage(self, courseUrl):
        """ Redirect page to resource page.

        Redirect the pagefrom course website main page to its resource page,
        in order to get coursewares.

        Args:
            courseUrl: String, the url of course main page

        Returns:
            resourcePageObj: BeatifulSoup Object, parse the resource page
        """
        res = self.sess.get(courseUrl)
        bsObj = BeautifulSoup(res.text, "html.parser")
        resourcePageUrl = bsObj.find(
            'a', {"title": "资源 - 上传、下载课件，发布文档，网址等信息"}).get("href")
        res = self.sess.get(resourcePageUrl)
        resourcePageObj = BeautifulSoup(res.text, 'html.parser')
        return resourcePageObj

    def getResourceInfos(self, resourcePageObj, parentDir=""):
        """ Get the information of coursewares.
        Get the information of coursewares, e.g. the filename of the courseware,
        the url of the courseware.

        The process of this function is as follows:

                ┌──── 获取当前文件夹下的所有文件
                │            │
                │     获取当前文件夹下的所有文件夹
                │            │
                │         1. 根据当前页面发POST请求
                │         2. 获得子文件夹的页面
                │         3. 调用自己
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
        subDirPageInfoList = self.getSubDirPageObjs(resourcePageObj, parentDir)
        for subDirPageObj, subDir in subDirPageInfoList:
            self.getResourceInfos(subDirPageObj, subDir)

    def getFileInfosOfCurrentDir(self, resourcePageObj, parentDir):
        """ Get the information of files in the current web page.
        Args:
            resourcePageObj: BeautifulSoup Object, parse the current web page
            parentDir: String, the path of the parrent directory

        Returns:
            None
        """
        resourceList = resourcePageObj.find_all(
            "td", {"class": "specialLink title"})
        if len(resourceList) > 0:
            resourceList.pop(0)  # remove unuseful node
            resourceUrlList = [item.find('a').get("href")
                               for item in resourceList]
            resourceUrlList = [url for url in resourceUrlList if url != '#']
            for resourceUrl in resourceUrlList:
                resourceInfo = {}
                resourceInfo["subDir"] = parentDir
                resourceInfo["url"] = resourceUrl
                resourceInfo["fileName"] = parse.unquote(os.path.basename(
                    resourceUrl))
                # print(
                #     "发现文件: {:s}/{:s} ({:s})".format(
                #         parentDir, resourceInfo["fileName"], resourceUrl)
                # )
                self.resourceInfos.append(resourceInfo)

    def getSubDirPageObjs(self, resourcePageObj, parentDir):
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
        if len(subDirResourceList) > 0:
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

                res = self.sess.post(
                    self.functionUrl, data=formData, allow_redirects=True)
                subPageObj = BeautifulSoup(res.text, "html.parser")
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

    def downloadFile(self, fileName, resourceUrl):
        """ Download file from the given url.
        Get the file from the given url and write it as local file.

        Args:
            fileName: String, the filename of the local file
            resourceUrl: String, the url of file to be downloaded

        Returns:
            None
        """
        if os.path.exists(fileName):
            return
        res = self.sess.get(resourceUrl)
        with open(fileName, "wb") as f:
            for chunk in res.iter_content(chunk_size=512):
                f.write(chunk)

    def downloadCourseware(self, courseInfo):
        """ Download courseware of single course.
        Given by the url of the course main page, download all the coursewares of this course.

        Args:
            courseInfo: Dictionary {
                            "url": url of the course main page,
                            "name": the name of the course
                        }

        Returns:
            None
        """
        self.resourceInfos = []
        courseDir = os.path.join(self.downloadPath, courseInfo["name"])
        if not os.path.exists(courseDir):
            os.makedirs(courseDir)
        resourcePageObj = self.reDirectToResourcePage(courseInfo["url"])
        self.getUnfoldPostPattern(resourcePageObj)
        self.getResourceInfos(resourcePageObj)
        for i, resourceInfo in enumerate(self.resourceInfos):
            # print("sub folder: {:s}".format(resourceInfo["subDir"]))
            subDirName = os.path.join(courseDir, resourceInfo["subDir"])
            if not os.path.exists(subDirName):
                os.makedirs(subDirName)
            fileName = os.path.join(subDirName, resourceInfo["fileName"])
            # print("File name: {:s}\nFile url: {:s}".format(fileName, resourceInfo["url"]))
            self.downloadFile(fileName, resourceInfo["url"])

    def jpgToQImage(self):
        """ Read the downloaded certification image and convert it to QImage.
        Args:
            None

        Returns:
            None
        """
        certImg = Image.open(self.certImageName).convert("RGB")
        x, y = certImg.size
        data = certImg.tobytes("raw", "RGB")
        qim = QImage(data, x, y, QImage.Format_RGB888)
        return qim

    def showCertImage(self):
        """ Show the certification image on the UI.
        Args:
            None

        Returns:
            None
        """
        try:
            self.sess.post("http://sep.ucas.ac.cn")
            html = self.sess.get("http://sep.ucas.ac.cn/changePic")
            self.ui.logInfo.setText("欢迎使用下载课件脚本。\n^_^\n请先登录。")
        except:
            self.ui.logInfo.setText('网页超时 请重新获取验证码')
            return
        with open(self.certImageName, "wb") as f:
            f.write(html.content)
        qim = self.jpgToQImage()
        pix = QPixmap.fromImage(qim)
        item = QGraphicsPixmapItem(pix)
        scene = QGraphicsScene()
        scene.addItem(item)
        self.ui.certImage.setScene(scene)

    def postLogin(self):
        """ Post to login.
        Args:
            None

        Returns:
            None        
        """
        res = self.sess.get("http://sep.ucas.ac.cn/slogin", params=self.login)
        bsObj = BeautifulSoup(res.text, "html.parser")
        nameTag = bsObj.find(
            "li", {"class": "btnav-info", "title": "当前用户所在单位"})
        if nameTag is None:
            self.ui.logInfo.setText("[ERROR]: 登录失败，请核对用户名密码\n")
            exit()
        name = nameTag.get_text()
        match = re.compile(r"\s*(\S*)\s*(\S*)\s*").match(name)
        if not match:
            print('[ERROR]:脚本运行错误，请重新尝试')
            exit()
        institute = match.group(1)
        name = match.group(2)
        self.ui.logInfo.setText(
            "{:s}\n{:s}\n登陆成功！".format(institute, name))
        self.ui.certCode.setReadOnly(True)
        self.ui.passwd.setReadOnly(True)
        self.ui.userName.setReadOnly(True)

    def onClickChoosePath(self):
        """ Choose the path to store coursewares.
        Args:
            None

        Returns:
            None        
        """
        self.downloadPath = QFileDialog.getExistingDirectory(
            self, "选择文件夹", ".")
        self.ui.showPath.setText(self.downloadPath)
        self.ui.choosePath.setDefault(False)
        self.ui.getCourses.setDefault(True)

    def onClickDownloadAll(self):
        """ Download all the coursewares of all courses.
        Args:
            None

        Returns:
            None        
        """
        outStr = ""
        self.ui.downloadAll.setDefault(False)
        self.ui.progressBar.setRange(0, len(self.coursesList))
        for i, course in enumerate(self.coursesList):
            outStr += "正在下载{:s}的课件...\n".format(course["name"])
            self.ui.progressBar.setValue(i+1)
            self.ui.progressInfo.setText(outStr)
            self.downloadCourseware(course)
        outStr += "下载完毕！\n"
        self.ui.progressInfo.setText(outStr)

    def onClickGetCourses(self):
        """ Get all the course information.
        Args:
            None

        Returns:
            None        
        """
        res = self.sess.get("http://sep.ucas.ac.cn/portal/site/16/801")
        bsObj = BeautifulSoup(res.text, "html.parser")
        courseWebsiteUrl = bsObj.find('noscript').meta.get("content")[6:]
        res = self.sess.get(courseWebsiteUrl)
        bsObj = BeautifulSoup(res.text, "html.parser")
        allCoursesUrl = bsObj.find(
            'a', {'class': "Mrphs-toolsNav__menuitem--link", 'title': "我的课程 - 查看或加入站点"}).get("href")
        res = self.sess.get(allCoursesUrl)
        bsObj = BeautifulSoup(res.text, "html.parser")
        allCoursesInfo = bsObj.find(
            'ul', {'class': "otherSitesCategorList favoriteSiteList"}).find_all('div', {'class': "fav-title"})
        self.ui.hintInfo.setText("以下是你选修的课程：")
        for (idx, courseInfo) in enumerate(allCoursesInfo):
            course = {}
            course["name"] = courseInfo.find('a').get('title')
            course["url"] = courseInfo.find('a').get('href')
            print(course["name"])
            self.ui.coursesList.addItem(
                "{:02d}\t".format(idx+1)+course["name"])
            self.coursesList.append(course)
        self.ui.getCourses.setDefault(False)
        self.ui.downloadAll.setDefault(True)

    def onClickLogin(self):
        """ Click to login.
        Args:
            None

        Returns:
            None        
        """
        self.login["userName"] = self.ui.userName.text()
        self.login["pwd"] = self.ui.passwd.text()
        self.login["certCode"] = self.ui.certCode.text()
        self.login["sb"] = "sb"
        self.login["rememberMe"] = "1"
        print(self.login)
        if self.ui.remPasswd.isChecked():
            config = configparser.ConfigParser()
            config['Default'] = {
                'usrname': self.login["userName"],
                'passwd': self.login["pwd"]
            }
            with open(self.confName, 'w') as f:
                config.write(f)
        self.ui.logInfo.setText("登陆账号：{0}".format(self.login["userName"]))
        self.postLogin()
        self.ui.loginButton.setDefault(False)
        self.ui.choosePath.setDefault(True)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Ui()
    sys.exit(app.exec_())
