#-*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License"),
# see LICENSE for more details: http://www.apache.org/licenses/LICENSE-2.0.

__author__="Zhang Yi <loeyae@gmail.com>"
__date__ ="$2019-2-19 9:16:07$"


from setuptools import setup, find_packages

setup(
    name = "cdspider_bbs",
    version = "0.1",
    description = "数据采集框架论坛采集",
    author = 'Zhang Yi',
    author_email = 'loeyae@gmail.com',
    license = "Apache License, Version 2.0",
    url="https://github.com/loeyae/lspider_bbs.git",
    install_requires = [
        'cdspider>=0.1',
    ],
    packages = find_packages(),

    entry_points = {
        'cdspider.handler': [
            'bbs-list=cdspider_bbs.handler:BbsListHandler',
            'bbs-item=cdspider_bbs.handler:BbsItemHandler',
        ],
        'cdspider.dao.mongo': [
            'RepliesUniqueDB=cdspider_bbs.database.mongo:RepliesUniqueDB',
            'RepliesDB=cdspider_bbs.database.mongo:RepliesDB',
        ]
    }
)
