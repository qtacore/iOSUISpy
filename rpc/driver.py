# -*- coding:utf-8 -*-
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
'''
'''

import base64
import ConfigParser
from functools import wraps
import os
import socket
import sys
import subprocess
import threading

from rpc.client import RPCClientProxy
from settings import RESOURCE_PATH

ENCODING = "utf-8"


def sync(lockname):
    '''方法同步锁，保证driverserver的接口一次只访问一个
    '''
    
    def _synched(func):
        @wraps(func)
        def _synchronizer(self,*args, **kwargs):
            tlock = self.__getattribute__(lockname)
            tlock.acquire()
            try:
                return func(self, *args, **kwargs)
            finally:
                tlock.release()
        return _synchronizer
    return _synched


class HostDriver(object):
    '''设备主机的Driver
    '''


    def __init__(self, host_ip, host_port):
        self._host_ip = host_ip
        self._host_url = 'http://%s:%s' % (host_ip, host_port)
        self._driver = RPCClientProxy('/'.join([self._host_url, 'host/']), allow_none=True, encoding=ENCODING)
        self._devices = None
        self._qt4i_manage = None

    @property
    def host_url(self):
        return self._host_url
    
    @property
    def devices(self):
        return self._devices

    @property
    def qt4i_manage(self):
        if sys.platform == 'darwin':
            config_parser = ConfigParser.ConfigParser()
            settings_file = os.path.join(RESOURCE_PATH, 'uispy.conf')
            config_parser.read(settings_file)
            try:
                self._qt4i_manage = config_parser.get('uispy', 'qt4i-manage')
            except ConfigParser.NoOptionError:
                self._qt4i_manage = os.path.expanduser("~/Library/Python/2.7/bin/qt4i-manage")
                config_parser.set("uispy", "qt4i-manage", self._qt4i_manage)
                with open(settings_file, 'w') as fd:
                    config_parser.write(fd)
            return self._qt4i_manage
        else:
            raise Exception("Unsupported platform!")
        
    def connect_to_host(self, driver_type):
        socket.setdefaulttimeout(3)
        is_connected = False
        try:
            is_connected = self._driver.echo()
        except:
            is_connected = self.restart_host_driver(driver_type)
        finally:
            socket.setdefaulttimeout(None)  
        return is_connected
    
    def restart_host_driver(self, driver_type):
        socket.setdefaulttimeout(3)
        is_connected = False
        if sys.platform == 'darwin' and self._host_ip == '127.0.0.1':
            try:
                if driver_type == 'instruments':
                    subprocess.check_call('killall -9 instruments')
                xctestagent_path = os.path.join(os.path.expanduser('~'), 'XCTestAgent')
                if driver_type == 'xctest' and not os.path.exists(xctestagent_path):
                    unzip_agent_cmd = '%s setup' % self.qt4i_manage
                    subprocess.call(unzip_agent_cmd, shell=True)
                subprocess.call('%s restartdriver -t %s' % (self.qt4i_manage, driver_type), shell=True)
                self._driver = RPCClientProxy('/'.join([self.host_url, 'host/']), allow_none=True, encoding=ENCODING)
                is_connected = self._driver.echo()
            except:
                pass
        socket.setdefaulttimeout(None)        
        return is_connected
    
    def list_devices(self):
        self._devices = self._driver.list_devices()
        return self._devices
    
    def start_simulator(self, udid):
        self._driver.start_simulator(udid)    


class DeviceDriver(object):
    '''iPhone真机或者模拟器的Driver
    '''

    def __init__(self, host_url, device_udid):
        self._driver = RPCClientProxy('/'.join([host_url, 'device', '%s/' % device_udid]), allow_none=True, encoding='utf-8')
        self.udid = device_udid
        self.devicelock = threading.RLock()
        
    @sync('devicelock')
    def start_app(self, bundle_id):
        try:
            self._driver.device.stop_app(bundle_id)
        except:
            pass
        return self._driver.device.start_app(bundle_id, None, None) 
    
    @sync('devicelock')
    def take_screenshot(self):
        base64_img = self._driver.device.capture_screen()
        return base64.decodestring(base64_img)
    
    @sync('devicelock')
    def get_element_tree(self):
        return self._driver.device.get_element_tree()
    
    @sync('devicelock')
    def install_app(self, ipa_path):
        return self._driver.device.install(ipa_path)
    
    @sync('devicelock')
    def uninstall_app(self, bundle_id):
        return self._driver.device.uninstall(bundle_id)
    
    @sync('devicelock')
    def get_screen_orientation(self):
        return self._driver.device.get_screen_orientation()
    
    @sync('devicelock')
    def get_app_list(self, app_type="user"):
        '''获取设备上的app列表
        :param app_type: app的类型(user/system/all)
        :type app_type: str 
        :returns: list  例如:[{'com.tencent.rdm': 'RDM'}]
        '''   
        return self._driver.device.get_app_list(app_type)
    
    @sync('devicelock')
    def click(self, x, y, retry = 3):
        '''
        基于屏幕的点击操作
        :param x: 横向坐标（从左向右，屏幕百分比）
        :type x: float
        :param y: 纵向坐标（从上向下，屏幕百分比）
        :type y: float
        :param retry 重试次数
        :type int
        '''
        self._driver.device.click(x, y)
    
    @sync('devicelock')    
    def double_click(self, x, y):
        self._driver.device.double_click(x, y)
        
    @sync('devicelock')
    def long_click(self, x, y, duration=3):
        self._driver.device.long_click(x, y, duration)
    
    @sync('devicelock')          
    def drag(self, x0, y0, x1, y1, duration=0, repeat=1, interval=0.5, velocity=1000, retry = 3):
        '''拖拽（全局操作）
        :param x0: 起始横向坐标（从左向右，屏幕百分比）
        :type x0: float
        :param y0: 起始纵向坐标（从上向下，屏幕百分比）
        :type y0: float
        :param x1: 终止横向坐标（从左向右，屏幕百分比）
        :type x1: float
        :param y1: 终止纵向坐标（从上向下，屏幕百分比）
        :type y1: float
        :param duration: 起始坐标按下的时间（秒）
        :type duration: float
        '''
        self._driver.device.drag(x0, y0, x1, y1, duration, repeat, interval, velocity)
    
    @sync('devicelock')
    def sendkeys(self, text):
        self._driver.device.send_keys(text)

    @sync('devicelock')   
    def get_sandbox_path_files(self, bundle_id, file_path):
        '''返回真机或者模拟器的沙盒路径
        
        :param bundle_id: 应用的bundle_id
        :type bundle_id: str
        :param file_path: 沙盒目录
        :type file_path: str
        '''
        return self._driver.device.get_sandbox_path_files(bundle_id, file_path)
    
    @sync('devicelock')
    def is_sandbox_path_dir(self, bundle_id, file_path):
        '''判断一个sandbox路径是否是一个目录
        
        :param bundle_id: 应用的bundle_id
        :type bundle_id: str
        :param file_path: 沙盒目录
        :type file_path: str
        '''
        return self._driver.device.is_sandbox_path_dir(bundle_id, file_path)
    
    @sync('devicelock')
    def get_sandbox_file_content(self, bundle_id, file_path):
        '''获取sandbox中文本文件的内容
        
        :param bundle_id: 应用的bundle_id
        :type bundle_id: str
        :param file_path: 沙盒目录
        :type file_path: str
        '''
        return self._driver.device.get_sandbox_file_content(bundle_id, file_path)
    
    @sync('devicelock')
    def close_sandbox_client(self):
        '''销毁sandboxClient对象
        '''
        self._driver.device.close_sandbox_client()
    
    @sync('devicelock')
    def get_xcode_version(self):
        '''查询Xcode版本
        
        '''
        return self._driver.device.get_xcode_version()

    @sync('devicelock')
    def get_ios_version(self):
        '''查询ios版本
        
        '''
        return self._driver.device.get_ios_version()
    