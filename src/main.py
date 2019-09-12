# -*- coding: utf-8 -*-

import os
import re
import sys
import requests
import configparser

from urllib import parse
from bs4 import BeautifulSoup
from PyQt5.QtCore import QFile, QTextStream
from PyQt5.QtGui import (QImage, QPixmap)
from PyQt5.QtWidgets import (QLineEdit, QDialog, QApplication, QFileDialog)

import breeze_resources
from dialog import Ui_Dialog
from work_threads import (LoginThread, DownloadThread,
                          GetCourseThread, CertCodeThread)


class Ui(QDialog):
    def __init__(self):
        super(Ui, self).__init__()
        self.downloadPath = os.path.abspath('.')
        self.configParser = configparser.ConfigParser()
        self.configPath = ".config"
        self.md5LogName = os.path.join(self.configPath, "md5log.json")
        if not os.path.exists(self.configPath):
            os.makedirs(self.configPath)
        self.confName = os.path.join(self.configPath,"cache.cfg")
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
        self.ui.certCode.setPlaceholderText("验证码")
        self.ui.hintInfo.setText("以下是你选修的课程：")
        # check login configurations
        self.checkConf()
        self.ui.showPath.setText(self.downloadPath)
        # show the certification code image
        self.showCertImage()
        # initialize the status of the progress bar
        self.ui.progressBar.setRange(0, 0)
        self.ui.subProgressBar.setRange(0, 0)
        self.ui.fileProcessBar.setRange(0, 0)
        # set window title
        self.setWindowTitle("UCAS Coursewares AutoDownloader")

    def checkConf(self):
        """ Check login configurations """
        if not os.path.exists(self.confName):
            return
        self.configParser.read(self.confName)
        username = self.configParser.get('Default', 'usrname')
        password = self.configParser.get('Default', 'passwd')
        self.downloadPath = self.configParser.get('Default', 'downloadPath')
        self.ui.userName.setText(username)
        self.ui.passwd.setText(password)
        self.ui.remPasswd.setChecked(True)

    def updateConfig(self):
        """ Update config file. """
        if self.ui.remPasswd.isChecked():
            self.configParser['Default'] = {
                'usrname': self.login["userName"],
                'passwd': self.login["pwd"],
                'downloadPath': self.downloadPath
            }
            with open(self.confName, 'w') as f:
                self.configParser.write(f)

    def showCertImage(self):
        """ Show the certification image on the UI. """
        self.certCodeThread = CertCodeThread(self.sess)
        self.certCodeThread.updateUiSignal.connect(self.updateCertCode)
        self.certCodeThread.killSignal.connect(self.killShowCertCode)
        self.certCodeThread.start()

    def updateCertCode(self, signalDict):
        """ Update the certification image on the UI window. """
        self.ui.logInfo.setText(signalDict["text"])
        if signalDict["scene"] != "":
            self.ui.certImage.setScene(signalDict["scene"])

    def killShowCertCode(self):
        """ Kill show certification code image thread. """
        self.certCodeThread.terminate()

    def onClickLogin(self):
        """ Click to login. """
        self.login["userName"] = self.ui.userName.text()
        self.login["pwd"] = self.ui.passwd.text()
        self.login["certCode"] = self.ui.certCode.text()
        self.login["sb"] = "sb"
        self.login["rememberMe"] = "1"
        # print(self.login)
        self.updateConfig()
        self.loginThread = LoginThread(self.sess, self.login)
        self.loginThread.loginSignal.connect(self.updateLogInfoText)
        self.loginThread.failSignal.connect(self.failToLogin)
        self.loginThread.start()

    def updateLogInfoText(self, signalDict):
        """ Update log information window by getting signal from thread. """
        self.ui.logInfo.setText(signalDict["text"])
        self.sess = signalDict["session"]
        self.ui.certCode.setReadOnly(True)
        self.ui.userName.setReadOnly(True)
        self.ui.passwd.setReadOnly(True)
        self.ui.remPasswd.setDisabled(True)
        self.ui.getCourses.setEnabled(True)
        self.loginThread.terminate()
    
    def failToLogin(self, text):
        """ Work when login fails. """
        self.ui.logInfo.setText(text)
        self.loginThread.terminate()

    def onClickChoosePath(self):
        """ Choose the path to store coursewares. """
        path = QFileDialog.getExistingDirectory(
            self, "选择文件夹", ".")
        if path == "":
            self.ui.showPath.setText("请选择文件夹~！")
            return
        self.downloadPath = path
        self.ui.showPath.setText(self.downloadPath)
        self.ui.choosePath.setDefault(False)

    def onClickGetCourses(self):
        """ Get all the course information. """
        self.updateConfig()
        self.getCoursesThread = GetCourseThread(self.sess)
        self.getCoursesThread.getCourseSignal.connect(self.updateCoursesList)
        self.getCoursesThread.finishSignal.connect(self.killCourseThread)
        self.getCoursesThread.error.connect(self.showError)
        self.getCoursesThread.start()
        self.ui.getCourses.setDefault(False)
        self.ui.downloadAll.setDefault(True)

    def updateCoursesList(self, signalDict):
        """ Update course list by getting signal from thread. """
        self.sess = signalDict["session"]
        course = signalDict["course"]
        self.coursesList.append(course)
        self.ui.coursesList.addItem(
            "{:02d}\t{:s}".format(signalDict["idx"], course["name"]))
        # self.getCoursesThread.terminate()

    def killCourseThread(self):
        """ Kill get courese thread. """
        self.ui.downloadAll.setEnabled(True)
        self.getCoursesThread.terminate()

    def showError(self, text):
        """ Show error information on GUI. """
        self.ui.logInfo.setText(text)

    def onClickDownloadAll(self):
        """ Download all the coursewares of all courses after catch the click. """
        self.ui.progressBar.setRange(0, len(self.coursesList))
        self.downloadThread = DownloadThread(
            self.sess, self.coursesList, self.downloadPath, self.md5LogName)
        self.downloadThread.updateUiSignal.connect(self.updateProgress)
        self.downloadThread.updateSubBar.connect(self.updateSubProgress)
        self.downloadThread.updateFileBar.connect(self.updateFileProgress)
        self.downloadThread.killSignal.connect(self.killDownloadThread)
        self.downloadThread.start()

    def updateProgress(self, signalDict):
        """ Update the progress of main processbar. """
        self.ui.progressBar.setValue(signalDict["value"])
        self.ui.progressInfo.setText(signalDict["text"])

    def updateSubProgress(self, signalDict):
        """ Update the progress of sub processbar. """
        self.ui.subProgressBar.setRange(0, signalDict["max"])
        self.ui.subProgressBar.setValue(signalDict["value"])

    def updateFileProgress(self, signalDict):
        """ Update the progress of file downloading processbar. """
        self.ui.fileProcessBar.setRange(0, signalDict["max"])
        self.ui.fileProcessBar.setValue(signalDict["value"])

    def killDownloadThread(self):
        """ Kill download files thread. """
        self.ui.downloadAll.setEnabled(False)
        self.downloadThread.terminate()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    # set stylesheet
    file = QFile(":/light.qss")
    file.open(QFile.ReadOnly | QFile.Text)
    stream = QTextStream(file)
    app.setStyleSheet(stream.readAll())
    # start main UI window
    window = Ui()
    sys.exit(app.exec_())
