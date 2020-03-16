# -*- encoding: utf-8 -*-
'''
@Filename   : configs.py
@Description: parameters used in this project
@Date       : 2020/03/13 11:32:18
@Author     : Wu Jiahao
@Contact    : https://github.com/flamywhale
'''


HEADERS = {
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.122 Safari/537.36 Edg/80.0.361.62'
}

POST_HDRS = {
    'connection': 'keep-alive',
    'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'dnt': '1',
    'host': 'onestop.ucas.ac.cn',
    'origin': 'http://onestop.ucas.ac.cn',
    'Referer': 'http://onestop.ucas.ac.cn/',
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.122 Safari/537.36 Edg/80.0.361.62',
    'X-Requested-With': 'XMLHttpRequest'
}

GET_HDRS = {
    'connection': 'keep-alive',
    'dnt': '1',
    'host': 'sep.ucas.ac.cn',
    'Referer': 'http://onestop.ucas.ac.cn/',
    'Upgrade-Insecure-Requests': '1',
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.122 Safari/537.36 Edg/80.0.361.62'
}


# USER_LOGIN_ROOT = '.default.ini'
DATABASE_NAME = 'courses.db'


CREATE_USERS_TABLE = """
                        CREATE TABLE USERS (
                            USERNAME TEXT PRIMARY KEY NOT NULL,
                            PASSWORD TEXT,
                            STOREPATH TEXT,
                            MODE TEXT
                        );
                     """
LOOKUP_USERS_TABLE = "SELECT * from USERS WHERE MODE = 'default'"
INSERT_USERS_TABLE = "INSERT INTO USERS(   \
                                    USERNAME, PASSWORD,  \
                                    STOREPATH,  MODE \
                                  ) VALUES (?, ?, ?, ?)"
UPDATE_USERS_TABLE = "UPDATE USERS set USERNAME = ?, PASSWORD = ?, STOREPATH = ? where MODE = 'default'"

CREATE_FILES_TABLE = """
                        CREATE TABLE FILES(
                            FILENAME TEXT PRIMARY KEY NOT NULL,
                            UPDATE_TIME TEXT NOT NULL
                        );
                     """
INSERT_FILES_TABLE = "INSERT INTO FILES (FILENAME, UPDATE_TIME) VALUES (?, ?)"
LOOKUP_FILES_TABLE = "SELECT UPDATE_TIME from FILES WHERE FILENAME = ?"
UPDATE_FILES_TABLE = "UPDATE FILES set UPDATE_TIME = ? where FILENAME = ?"

CREATE_VIDEO_TABLE = """
                        CREATE TABLE VIDEO(
                            FILENAME TEXT PRIMARY KEY NOT NULL,
                            URL TEXT NOT NULL
                        );
                     """
INSERT_VIDEO_TABLE = "INSERT INTO VIDEO (FILENAME, URL) VALUES (?, ?)"
LOOKUP_VIDEO_TABLE = "SELECT URL from VIDEO WHERE FILENAME = ?"
UPDATE_VIDEO_TABLE = "UPDATE VIDEO set URL = ? where FILENAME = ?"
