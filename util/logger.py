# -*- coding: UTF-8 -*-
#
# Tencent is pleased to support the open source community by making QTA available.
# Copyright (C) 2016THL A29 Limited, a Tencent company. All rights reserved.
# Licensed under the BSD 3-Clause License (the "License"); you may not use this 
# file except in compliance with the License. You may obtain a copy of the License at
# 
# https://opensource.org/licenses/BSD-3-Clause
# 
# Unless required by applicable law or agreed to in writing, software distributed 
# under the License is distributed on an "AS IS" basis, WITHOUT WARRANTIES OR CONDITIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.
#

'''日志模块
'''


import os, sys
import logging
from logging.handlers import RotatingFileHandler

class Log(object):
    '''
    '''
    logger = None
    log_name = 'UISpy'
        
    @staticmethod
    def gen_log_path():
        '''生成log存放路径
        '''
        if getattr(sys, 'frozen', False):
            dir_root = os.path.dirname(sys.executable)
        else:
            dir_root = os.path.dirname(os.path.abspath(__file__))
        log_name = '%s.log' % (Log.log_name)
        return os.path.join(dir_root, log_name)

    @staticmethod
    def get_logger():
        if Log.logger == None:
            Log.logger = logging.getLogger(Log.log_name)
            if len(Log.logger.handlers) == 0:
                Log.logger.setLevel(logging.DEBUG)
                Log.logger.addHandler(logging.StreamHandler(sys.stdout))
                fmt = logging.Formatter('%(asctime)s %(message)s')  # %(filename)s %(funcName)s
                Log.logger.handlers[0].setFormatter(fmt)
                
                logger_path = Log.gen_log_path()
                file_handler = RotatingFileHandler(logger_path, mode='a', maxBytes=10*1024*1024, 
                                 backupCount=2, encoding='utf-8', delay=0)
                fmt = logging.Formatter('%(asctime)s %(levelname)s %(thread)d %(message)s')  # %(filename)s %(funcName)s
                file_handler.setFormatter(fmt)
                Log.logger.addHandler(file_handler)
        return Log.logger
    
    @staticmethod
    def call(func, tag, *args):
        '''
        '''
        msg = '[%s] %s' % (tag, ' '.join([arg.encode('utf8') if isinstance(arg, unicode) else arg for arg in args]))
        func = getattr(Log.get_logger(), func)
        return func(msg)
    
    @staticmethod
    def d(tag, *args):
        return Log.call('debug', tag, *args)
    
    @staticmethod
    def i(tag, *args):
        return Log.call('info', tag, *args)
    
    @staticmethod
    def w(tag, *args):
        return Log.call('warn', tag, *args)
    
    @staticmethod
    def e(tag, *args):
        return Log.call('error', tag, *args)
    
    @staticmethod
    def ex(tag, *args):
        return Log.call('exception', tag, *args)
    
