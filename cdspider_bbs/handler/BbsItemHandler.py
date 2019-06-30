#-*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License"),
# see LICENSE for more details: http://www.apache.org/licenses/LICENSE-2.0.

"""
:author:  Zhang Yi <loeyae@gmail.com>
:date:    2018-12-12 21:00:34
"""
import time
import copy
from cdspider.handler import GeneralItemHandler
from cdspider.libs import utils
from cdspider.database.base import ArticlesDB
from cdspider.parser import ItemParser, CustomParser
from cdspider.parser.lib import TimeParser
from cdspider.libs.constants import *
from cdspider.handler import HandlerUtils


class BbsItemHandler(GeneralItemHandler):
    """
    general item handler
    :property task 爬虫任务信息 {"mode": "item", "rid": Article rid}
                   当测试该handler，数据应为 {"mode": "item", "url": url, "forumRule": 详情规则，参考详情规则}
    支持注册的插件:
        bbs-item_handler.result_handle
            data参数为 {"save": save, "domain": domain, "subdomain": subdomain}
    """

    def init_process(self, save):
        """
        初始化爬虫流程
        :output self.process {"request": 请求设置, "parse": 解析规则, "paging": 分页规则, "unique": 唯一索引规则}
        """
        if "rid" in self.task and 'uuid' not  in self.task:
            rid = self.task['rid']
            del self.task['rid']
            self.task['parentid'] = rid
        else:
            # 根据task中的rid获取文章信息
            rid = self.task.get('parentid', None)
        if rid:
            article = self.db['ArticlesDB'].get_detail(rid, select=['acid', 'rid', 'url', 'crawlinfo'])
            if not article:
                raise CDSpiderHandlerError("aritcle: %s not exists" % rid)
            if 'ulr' not  in self.task or not self.task['url']:
                self.task["url"] = article['url']
            self.task['crawlinfo'] = article.get('crawlinfo', {})
            self.task['article'] = article
        self.task.setdefault('article', {})
        self.task.setdefault('crawlinfo', {})
        if not self.task.get("url"):
            raise CDSpiderHandlerError("url not exists")
        save['base_url'] = self.task.get("url")
        self.process = self.match_rule()
        if "extra" not in self.process or not self.process['extra']:
            self.process['extra'] = {"unique":{}, "parse": {"item":[{"cotent": None}]}}
        if 'data' not in self.process['extra']['unique'] or not self.process['extra']['unique']['data']:
            self.process['extra']['unique']['data'] = ",".join(self.process['extra']['parse']['item'].keys())
        if 'save' in self.task and self.task['save'] and 'page' in self.task['save']:
            self.page = self.task['save']['page']

    def run_parse(self, rule):
        """
        文章解析
        :param rule 解析规则
        :input self.response 爬虫结果 {"last_source": 最后一次抓取到的源码, "final_url": 最后一次请求的url}
        :output self.response {"parsed": 解析结果}
        """
        parsed = {}
        if self.page == 1:
            main_parser = ItemParser(source=self.response['content'], ruleset=copy.deepcopy(rule['parse']), log_level=self.log_level, url=self.response['final_url'])
            parsed['main'] = main_parser.parse()
        replies_rule = self.process['extra']
        replies_parser = CustomParser(source=self.response['content'], ruleset=copy.deepcopy(replies_rule), log_level=self.log_level, url=self.response['final_url'])
        parsed['replies'] = replies_parser.parse()
        self.response['parsed'] = parsed

    def _build_replies_info(self, **kwargs):
        """
        构造评论数据
        """
        result = kwargs.pop('result')
        #爬虫信息记录
        result['crawlinfo'] = {
            'pid': self.task['article']['crawlinfo'].get('pid', 0),    # project id
            'sid': self.task['article']['crawlinfo'].get('sid', 0),    # site id
            'tid': self.task['article']['crawlinfo'].get('tid', 0),    # task id
            'uid': self.task['article']['crawlinfo'].get('uid', 0),    # url id
            'kid': self.task['article']['crawlinfo'].get('kid', 0),    # keyword id
            'ruleId': self.process['uuid'],                            # forumRule id
            'list_url': kwargs.pop('final_url'),                       # 列表url
        }
        result['mediaType'] = self.process.get('mediaType', self.task['task'].get('mediaType', MEDIA_TYPE_BBS)),
        result['acid'] = self.task['article']['acid']                  # article acid
        result['rid'] = self.task['article']['rid']                    # article rid
        result['unid'] = kwargs.pop('unid')
        result['ctime'] = kwargs.pop('ctime')
        return result

    def build_replies_task(self, save):
        """
        构造回复任务
        """
        task = {
            'mediaType': self.process.get('mediaType', self.task['task'].get('mediaType', MEDIA_TYPE_BBS)),
            'mode': self.mode,                                      # handler mode
            'pid': self.task['article']['crawlinfo'].get('pid', 0), # project id
            'sid': self.task['article']['crawlinfo'].get('sid', 0), # site id
            'tid': self.task['article']['crawlinfo'].get('tid', 0), # task id
            'uid': self.task['article']['crawlinfo'].get('uid', 0), # url id
            'kid': self.task['article']['crawlinfo'].get('kid', 0), # keyword id
            'rid': self.process['uuid'],                            # rule id
            'url': self.task['url'],                                # url
            'parentid': self.task['article']['rid'],                # article id
            'status': self.db['SpiderTaskDB'].STATUS_ACTIVE,
            'frequency': str(self.process.get('rate', self.DEFAULT_RATE)),
            'expire': 0 if int(self.process['expire']) == 0 else int(time.time()) + int(self.process['expire']),
        }
        self.debug("%s build replies task: %s" % (self.__class__.__name__, str(task)))
        if not self.testing_mode:
            '''
            testing_mode打开时，数据不入库
            '''
            try:
                l = self.db['SpiderTaskDB'].get_list(self.mode, where={"parentid": task['parentid']})
                if len(list(l)) == 0:
                    uuid = self.db['SpiderTaskDB'].insert(task)
                    self.task['uuid'] = uuid
                    return uuid
                return None
            except:
                return None
        else:
            return 'testing_mode'

    def run_result(self, save):
        """
        爬虫结果处理
        :param save 保存的上下文信息
        """
        self._build_crawl_info(final_url=self.response['final_url'])
        if self.response['parsed']:
            typeinfo = utils.typeinfo(self.response['final_url'])
            if "uuid" not in self.task:
                self.result2db(save, copy.deepcopy(typeinfo))
                self.extension("result_handle", {"save": save, **typeinfo})
                if self.page == 1:
                    tid = self.build_replies_task(save)
                    if tid:
                        self.task['article']['crawlinfo']['forumRule'] = self.process['uuid']
                        self.task['article']['crawlinfo']['forumTaskId'] = tid
                        self.debug("%s new forum task: %s" % (self.__class__.__name__, str(tid)))

            self.replies2result(save)

    def replies2result(self, save):
        self.crawl_info['crawl_urls'][str(self.page)] = self.response['final_url']
        self.crawl_info['crawl_count']['page'] += 1
        if self.response['parsed']['replies']:
            ctime = self.crawl_id
            new_count = self.crawl_info['crawl_count']['new_count']
            for each in self.response['parsed']['replies']:
                self.crawl_info['crawl_count']['total'] += 1
                if self.testing_mode:
                    '''
                    testing_mode打开时，数据不入库
                    '''
                    inserted, unid = (True, {"acid": "test_mode", "ctime": ctime})
                    self.debug("%s test mode: %s" % (self.__class__.__name__, unid))
                else:
                    # 生成唯一ID, 并判断是否已存在
                    inserted, unid = self.db['RepliesUniqueDB'].insert(
                        self.get_unique_setting(self.response['url'], each), ctime)
                    self.debug("%s on_result unique: %s @ %s" % (self.__class__.__name__, str(inserted), str(unid)))
                if inserted:
                    result = self._build_replies_info(result=each, final_url=self.response['final_url'], **unid)
                    self.debug("%s result: %s" % (self.__class__.__name__, result))
                    if not self.testing_mode:
                        '''
                        testing_mode打开时，数据不入库
                        '''
                        result_id = self.db['RepliesDB'].insert(result)
                        if not result_id:
                            raise CDSpiderDBError("Result insert failed")
                    self.crawl_info['crawl_count']['new_count'] += 1
                else:
                    self.crawl_info['crawl_count']['repeat_count'] += 1
            if self.crawl_info['crawl_count']['new_count'] - new_count == 0:
                self.crawl_info['crawl_count']['repeat_page'] += 1
                self.on_repetition(save)

    def finish(self, save):
        """
        记录抓取日志
        """
        super(BbsItemHandler, self).finish(save)
        if self.page == 1:
            if self.task.get('parentid') and self.task['article'].get('crawlinfo') and not self.testing_mode:
                self.db['ArticlesDB'].update(self.task['parentid'], {"crawlinfo": self.task['article']['crawlinfo']})
                HandlerUtils.send_result_into_queue(self.queue, self.ctx.obj.get("app_config"), self.mode,
                                                    self.task['parentid'])
        if "uuid" in self.task and self.task['uuid']:
            crawlinfo = self.task.get('crawlinfo', {}) or {}
            self.crawl_info['crawl_end'] = int(time.time())
            crawlinfo[str(self.crawl_id)] = self.crawl_info
            crawlinfo_sorted = [(k, crawlinfo[k]) for k in sorted(crawlinfo.keys())]
            if len(crawlinfo_sorted) > self.CRAWL_INFO_LIMIT_COUNT:
                del crawlinfo_sorted[0]
            s = self.task.get("save")
            if not s:
                s = {}
            s.update(save)
            self.db['SpiderTaskDB'].update(
                self.task['uuid'], self.mode,
                {"crawltime": self.crawl_id, "crawlinfo": dict(crawlinfo_sorted), "save": s})
