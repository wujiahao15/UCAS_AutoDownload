# -*- coding: utf-8 -*-

import os
import re
import sys
import requests
import configparser

from urllib import parse
from bs4 import BeautifulSoup
from PyQt5.QtGui import (QImage, QPixmap)
from PyQt5.QtWidgets import (QLineEdit, QDialog, QApplication, QFileDialog)

from dialog import Ui_Dialog
from work_threads import (LoginThread, DownloadThread,
                          GetCourseThread, CertCodeThread)


class Ui(QDialog):
    def __init__(self):
        super(Ui, self).__init__()
        self.downloadPath = os.path.abspath('.')
        self.configPath = "config"
        if not os.path.exists(self.configPath):
            os.makedirs(self.configPath)
        self.confName = os.path.join(self.configPath,"cache.cfg")
        self.certImageName = os.path.join(self.configPath, "certcode.jpg")
        self.login = {}
        self.coursesList = []
        self.resourceInfos = []
        self.sess = requests.session()
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)
        self.initUI()
        self.show()

    def initUI(self):
        """ Initialize UI by adding more attributes to it. """
        # add button events
        self.ui.loginButton.clicked.connect(self.onClickLogin)
        self.ui.loginButton.setDefault(True)
        self.ui.getCourses.clicked.connect(self.onClickGetCourses)
        self.ui.choosePath.clicked.connect(self.onClickChoosePath)
        self.ui.downloadAll.clicked.connect(self.onClickDownloadAll)
        self.ui.refreshCertCode.clicked.connect(self.showCertImage)
        # set text editer properties
        self.ui.passwd.setEchoMode(QLineEdit.Password)
        self.ui.getCourses.setEnabled(False)
        self.ui.downloadAll.setEnabled(False)
        self.ui.logInfo.setReadOnly(True)
        self.ui.progressInfo.setReadOnly(True)
        self.ui.certCode.setPlaceholderText("请输入验证码")
        self.ui.hintInfo.setText("以下是你选修的课程：")
        self.ui.showPath.setText(self.downloadPath)
        # check login configurations
        self.checkConf()
        # show the certification code image
        self.showCertImage()
        # initialize the status of the progress bar
        self.ui.progressBar.setRange(0, 0)
        self.ui.subProgressBar.setRange(0, 0)
        # set window title
        self.setWindowTitle("批量下载课件脚本")

    def checkConf(self):
        """ Check login configurations """
        if not os.path.exists(self.confName):
            return
        conf = configparser.ConfigParser()
        conf.read(self.confName)
        username = conf.get('Default', 'usrname')
        password = conf.get('Default', 'passwd')
        self.ui.userName.setText(username)
        self.ui.passwd.setText(password)
        self.ui.remPasswd.setChecked(True)

    def updateCertCode(self, signalDict):
        self.ui.logInfo.setText(signalDict["text"])
        if signalDict["scene"] != "":
            self.ui.certImage.setScene(signalDict["scene"])

    def killShowCertCode(self):
        self.certCodeThread.terminate()

    def showCertImage(self):
        """ Show the certification image on the UI. """
        self.certCodeThread = CertCodeThread(self.sess, self.certImageName)
        self.certCodeThread.updateUiSignal.connect(self.updateCertCode)
        self.certCodeThread.killSignal.connect(self.killShowCertCode)
        self.certCodeThread.start()

    def onClickChoosePath(self):
        """ Choose the path to store coursewares. """
        self.downloadPath = QFileDialog.getExistingDirectory(
            self, "选择文件夹", ".")
        self.ui.showPath.setText(self.downloadPath)
        self.ui.choosePath.setDefault(False)
        self.ui.getCourses.setDefault(True)

    def updateProgress(self, signalDict):
        self.ui.progressBar.setValue(signalDict["value"])
        self.ui.progressInfo.setText(signalDict["text"])

    def updateSubProgress(self, signalDict):
        self.ui.subProgressBar.setRange(0, signalDict["max"])
        self.ui.subProgressBar.setValue(signalDict["value"])

    def killDownloadThread(self):
        self.downloadThread.terminate()

    def onClickDownloadAll(self):
        """ Download all the coursewares of all courses after catch the click. """
        self.ui.progressBar.setRange(0, len(self.coursesList))
        self.downloadThread = DownloadThread(self.sess, self.coursesList, self.downloadPath)
        self.downloadThread.updateUiSignal.connect(self.updateProgress)
        self.downloadThread.updateSubBar.connect(self.updateSubProgress)
        self.downloadThread.killSignal.connect(self.killDownloadThread)
        self.downloadThread.start()

    def updateCoursesList(self, signalDict):
        self.sess = signalDict["session"]
        course = signalDict["course"]
        self.coursesList.append(course)
        self.ui.coursesList.addItem(
            "{:02d}\t{:s}".format(signalDict["idx"], course["name"]))
        # self.getCoursesThread.terminate()

    def killCourseThread(self):
        self.ui.downloadAll.setEnabled(True)
        self.getCoursesThread.terminate()

    def onClickGetCourses(self):
        """ Get all the course information. """
        self.getCoursesThread = GetCourseThread(self.sess)
        self.getCoursesThread.getCourseSignal.connect(self.updateCoursesList)
        self.getCoursesThread.finishSignal.connect(self.killCourseThread)
        self.getCoursesThread.start()
        self.ui.getCourses.setDefault(False)
        self.ui.downloadAll.setDefault(True)

    def updateLogInfoText(self, signalDict):
        self.ui.logInfo.setText(signalDict["text"])
        self.sess = signalDict["session"]
        self.ui.getCourses.setEnabled(True)
        self.loginThread.terminate()
    
    def failToLogin(self, text):
        self.ui.logInfo.setText(text)
        self.loginThread.terminate()

    def onClickLogin(self):
        """ Click to login. """
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
        self.loginThread = LoginThread(self.sess, self.login)
        self.loginThread.loginSignal.connect(self.updateLogInfoText)
        self.loginThread.failSignal.connect(self.failToLogin)
        self.loginThread.start()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Ui()
    sys.exit(app.exec_())
