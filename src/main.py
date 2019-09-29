# -*- coding: utf-8 -*-

import sys
from PyQt5.QtCore import (QFile, QTextStream)
from PyQt5.QtWidgets import QApplication

import breeze_resources
from ui import (Ui, SecondUi)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # set stylesheet
    file = QFile(":/light.qss")
    file.open(QFile.ReadOnly | QFile.Text)
    stream = QTextStream(file)
    app.setStyleSheet(stream.readAll())
    # Set up UI windows
    window = Ui()
    secWindow = SecondUi()
    window.showUpdate.connect(secWindow.showResult)
    sys.exit(app.exec_())
