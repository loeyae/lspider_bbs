# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License"),
# see LICENSE for more details: http://www.apache.org/licenses/LICENSE-2.0.

"""
:author:  Zhang Yi <loeyae@gmail.com>
:date:    2019/4/14 19:50
"""

from cdspider.handler import GeneralListHandler


class BbsListHandler(GeneralListHandler):
    """
    bbs list handler
    task 爬虫任务信息 {"mode": "bbs-list", "uuid": SpiderTask.list uuid}
                   当测试该handler，数据应为 {"mode": "list", "url": url, "listRule": 列表规则，参考列表规则}
    支持注册的插件:
        bbs-list_handler.mode_handle  匹配详情页的mode
            data参数为 {"save": save,"url": url}
        bbs-list_handler.finish_handle
            data参数为 {"save": save, "dao": DAO name}
    """