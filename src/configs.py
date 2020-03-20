# -*- encoding: utf-8 -*-
'''
@Filename   : configs.py
@Description: parameters used in this project
@Date       : 2020/03/13 11:32:18
@Author     : Wu Jiahao
@Contact    : https://github.com/flamywhale
'''

DATABASE_NAME = 'courses.db'

SQL_CMD = {
    "basic": {
        "create": "",
        "lookup": "",
        "insert": "",
        "update": ""
    },
    "user": {
        "create": "CREATE TABLE USERS (USERNAME TEXT PRIMARY KEY NOT NULL, PASSWORD TEXT, STOREPATH TEXT, MODE TEXT);",
        "lookup": "SELECT * from USERS WHERE MODE = 'default'",
        "insert": "INSERT INTO USERS (USERNAME, PASSWORD, STOREPATH, MODE) VALUES (?, ?, ?, ?)",
        "update": "UPDATE USERS set USERNAME = ?, PASSWORD = ?, STOREPATH = ? where MODE = 'default'"
    },
    "courseware": {
        "create": "CREATE TABLE FILES (FILENAME TEXT PRIMARY KEY NOT NULL, URL TEXT NOT NULL, UPDATE_TIME TEXT NOT NULL);",
        "lookup": "SELECT UPDATE_TIME from FILES WHERE FILENAME = ?",
        "insert": "INSERT INTO FILES (FILENAME, URL, UPDATE_TIME) VALUES (?, ?, ?)",
        "update": "UPDATE FILES set UPDATE_TIME = ? where FILENAME = ?"
    },
    "video": {
        "create": "CREATE TABLE VIDEO (FILENAME TEXT PRIMARY KEY NOT NULL, URL TEXT NOT NULL, UPDATE_TIME TEXT NOT NULL);",
        "lookup": "SELECT UPDATE_TIME from VIDEO WHERE FILENAME = ?",
        "insert": "INSERT INTO VIDEO (FILENAME, URL, UPDATE_TIME) VALUES (?, ?, ?)",
        "update": "UPDATE VIDEO set UPDATE_TIME = ? where FILENAME = ?"
    }
}


HTTP_HDRS = {
    "normal": {
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.122 Safari/537.36 Edg/80.0.361.62'
    },
    "post": {
        'connection': 'keep-alive',
        'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'dnt': '1',
        'host': 'onestop.ucas.ac.cn',
        'origin': 'http://onestop.ucas.ac.cn',
        'Referer': 'http://onestop.ucas.ac.cn/',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.122 Safari/537.36 Edg/80.0.361.62',
        'X-Requested-With': 'XMLHttpRequest'
    },
    "get": {
        'connection': 'keep-alive',
        'dnt': '1',
        'host': 'sep.ucas.ac.cn',
        'Referer': 'http://onestop.ucas.ac.cn/',
        'Upgrade-Insecure-Requests': '1',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.122 Safari/537.36 Edg/80.0.361.62'
    }
}

TARGET_PAGE_TAG = {
    "basic": {},
    "courseware": {"title": "资源 - 上传、下载课件，发布文档，网址等信息"},
    "video": {"title": "课程视频 - 课程视频"}
}