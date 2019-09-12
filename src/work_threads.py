import os
import re
import json
import hashlib
from urllib import parse
from bs4 import BeautifulSoup
from PyQt5.QtGui import (QImage, QPixmap)
from PyQt5.QtCore import (QThread, pyqtSignal)
from PyQt5.QtWidgets import (QGraphicsScene,
                             QGraphicsPixmapItem)
from PIL import Image
from PIL.ImageQt import ImageQt


class CertCodeThread(QThread):
    updateUiSignal = pyqtSignal(dict)
    killSignal = pyqtSignal()

    def __init__(self, session, name):
        super(CertCodeThread, self).__init__()
        self.sess = session
        self.certImageName = name

    def jpgToQImage(self):
        """ Read the downloaded certification image and convert it to QImage. """
        certImg = Image.open(self.certImageName).convert("RGB")
        x, y = certImg.size
        data = certImg.tobytes("raw", "RGB")
        qim = QImage(data, x, y, QImage.Format_RGB888)
        return qim

    def run(self):
        welcome = "欢迎使用下载课件脚本。\n^_^\n请先输入验证码登录。"
        try:
            self.sess.post("http://sep.ucas.ac.cn")
            html = self.sess.get("http://sep.ucas.ac.cn/changePic")
            self.updateUiSignal.emit({"text": welcome, "scene": ""})
        except:
            error = "网页超时 请重新获取验证码"
            self.updateUiSignal.emit({"text": error, "scene": ""})
            self.killSignal.emit()
            return
        with open(self.certImageName, "wb") as f:
            f.write(html.content)
        qim = self.jpgToQImage()
        pix = QPixmap.fromImage(qim)
        item = QGraphicsPixmapItem(pix)
        scene = QGraphicsScene()
        scene.addItem(item)
        self.updateUiSignal.emit({"text": welcome, "scene": scene})
        self.killSignal.emit()


class LoginThread(QThread):
    loginSignal = pyqtSignal(dict)
    failSignal = pyqtSignal(str)

    def __init__(self, session, login):
        super(LoginThread, self).__init__()
        self.sess = session
        self.login = login

    def run(self):
        """ Post to login. """
        res = self.sess.get("http://sep.ucas.ac.cn/slogin", params=self.login)
        if res.status_code != 200:
            self.failSignal.emit("[ERROR]: 登录失败，请核对用户名、密码以及验证码\n")
            return
        bsObj = BeautifulSoup(res.text, "html.parser")
        nameTag = bsObj.find(
            "li", {"class": "btnav-info", "title": "当前用户所在单位"})
        if nameTag is None:
            self.failSignal.emit("[ERROR]: 登录失败，请核对用户名密码\n")
            return
        name = nameTag.get_text()
        match = re.compile(r"\s*(\S*)\s*(\S*)\s*").match(name)
        if not match:
            self.failSignal.emit("[ERROR]: 登录失败，请核对用户名密码\n")
            return
        institute = match.group(1)
        name = match.group(2)
        outStr = institute + '\n' + name + "\n登录成功！"
        self.loginSignal.emit({"text": outStr, "session": self.sess})


class GetCourseThread(QThread):
    getCourseSignal = pyqtSignal(dict)
    finishSignal = pyqtSignal()

    def __init__(self, session):
        super(GetCourseThread, self).__init__()
        self.sess = session
        self.coursesList = []

    def run(self):
        """ Get all the course information. """
        try:
            res = self.sess.get("http://sep.ucas.ac.cn/portal/site/16/801")
        except:
            # TODO: 
            #      add time out information
            return
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
        for (idx, courseInfo) in enumerate(allCoursesInfo):
            course = {}
            course["name"] = courseInfo.find('a').get('title')
            course["url"] = courseInfo.find('a').get('href')
            self.getCourseSignal.emit(
                {"course": course, "session": self.sess, "idx": idx})
        self.finishSignal.emit()


class DownloadThread(QThread):
    updateUiSignal = pyqtSignal(dict)
    updateSubBar = pyqtSignal(dict)
    killSignal = pyqtSignal()

    def __init__(self, session, courseList, path, md5log):
        super(DownloadThread, self).__init__()
        self.sess = session
        self.coursesList = courseList
        self.downloadPath = path
        self.md5dict = {}
        self.md5log = md5log
        if os.path.exists(self.md5log):
            with open(self.md5log, "r") as f:
                self.md5dict = json.load(f)

    def isDirEmpty(self, directory):
        return (len(os.listdir(directory)) == 0)

    def deleteEmptyDirs(self):
        dirs = [os.path.join(self.downloadPath, d) for d in os.listdir(
            self.downloadPath) if os.path.isdir(d)]
        for d in dirs:
            if self.isDirEmpty(d):
                os.removedirs(d)

    def run(self):
        for i, course in enumerate(self.coursesList):
            self.downloadCourseware(i+1, course)
        self.updateUiSignal.emit(
            {"value": len(self.coursesList), "text": "下载并更新完毕！"})
        # self.deleteEmptyDirs()
        self.killSignal.emit()

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
            'a', {"title": "资源 - 上传、下载课件，发布文档，网址等信息"})
        if resourcePageUrl == None:
            return None
        resourcePageUrl = resourcePageUrl.get("href")
        res = self.sess.get(resourcePageUrl)
        resourcePageObj = BeautifulSoup(res.text, 'html.parser')
        return resourcePageObj

    def getResourceInfos(self, resourcePageObj, parentDir=""):
        """ Get the information of coursewares.
        Get the information of coursewares, e.g. the filename of the courseware,
        the url of the courseware.

        The process of this function is as follows:

                ┌──── 获取当前文件夹下的所有文件的信息（文件名+文件下载链接）
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
        if len(resourceList) == 0:
            return 
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

    def md5sum(self, fileName):
        def readChunks(fp):
            fp.seek(0)
            chunk = fp.read(8096)
            while chunk:
                yield chunk
                chunk = fp.read(8096)
            else:
                fp.seek(0)
        m = hashlib.md5()
        with open(fileName, "rb") as f:
            for chunk in readChunks(f):
                m.update(chunk)
        return m.hexdigest()

    def downloadFile(self, fileName, resourceUrl):
        """ Download file from the given url.
        Get the file from the given url and write it as local file.

        Args:
            fileName: String, the filename of the local file
            resourceUrl: String, the url of file to be downloaded

        Returns:
            None
        """
        md5sum = 0
        if os.path.exists(fileName):
            md5sum = self.md5dict[fileName]
        res = self.sess.get(resourceUrl)
        UrlFileMd5 = hashlib.md5()
        for chunk in res.iter_content(chunk_size=512):
            UrlFileMd5.update(chunk)
        if md5sum == UrlFileMd5.hexdigest():
            return "{:s} 未更新.".format(os.path.basename(fileName))
        self.md5dict[fileName] = UrlFileMd5.hexdigest()
        with open(fileName, "wb") as f:
            for chunk in res.iter_content(chunk_size=512):
                f.write(chunk)
        return "{:s} 已下载完毕。".format(os.path.basename(fileName))

    def downloadCourseware(self, idx, courseInfo):
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
        # Get Course directory
        self.resourceInfos = []
        courseDir = os.path.join(self.downloadPath, courseInfo["name"])
        # redirect to the resource page of the course website
        resourcePageObj = self.reDirectToResourcePage(courseInfo["url"])
        if resourcePageObj == None:
            return
        self.getUnfoldPostPattern(resourcePageObj)
        self.getResourceInfos(resourcePageObj)
        resourceNum = len(self.resourceInfos)
        if resourceNum > 0:
            if not os.path.exists(courseDir):
                os.makedirs(courseDir)
            outStr = "正在下载{:s}的课件...\n".format(courseInfo["name"])
            self.updateUiSignal.emit({"value": idx, "text": outStr})
            self.updateSubBar.emit({"value": 0, "max": resourceNum})
        for i, resourceInfo in enumerate(self.resourceInfos):
            # print("sub folder: {:s}".format(resourceInfo["subDir"]))
            subDirName = os.path.join(courseDir, resourceInfo["subDir"])
            if not os.path.exists(subDirName):
                os.makedirs(subDirName)
            fileName = os.path.join(subDirName, resourceInfo["fileName"])
            # print("File name: {:s}\nFile url: {:s}".format(fileName, resourceInfo["url"]))
            self.updateSubBar.emit({"value": i+1, "max": resourceNum})
            outStr = self.downloadFile(fileName, resourceInfo["url"])
            self.updateUiSignal.emit({"value": idx, "text": outStr})
        with open(self.md5log, "w") as f:
            json.dump(self.md5dict, f)
