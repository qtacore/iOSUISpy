# -*- coding: utf-8 -*-
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
'''UISpy窗口控件
'''


import ConfigParser
import os
import StringIO
import sys
import threading
import traceback
import wx
import subprocess
import time

from util.logger import Log
from rpc.driver import HostDriver
from rpc.driver import DeviceDriver
from ui.sandboxframe import TreeFrame
from version import VERSION
from settings import RESOURCE_PATH


DEFAULT_BUNDLE_ID = 'com.tencent.sng.test.gn'
DEBUG_PATH = 'UISpy.app/Contents/MacOS/UISpy'
TIMER_ID = 10010


class EnumDriverType(object):
    '''定义iOS测试框架的类型
    '''
    XCTest, Instruments = ('xctest', 'instruments')
    

class MainFrame(wx.Frame):
    
    def __init__(self):
        self._init_controls()
        self._driver_type = EnumDriverType.XCTest
        self._device = None 
        self._host_driver = None
        self._device_driver = None
        self._element_tree = None
        self._focused_element = None
        self._app_started = False
        self._orientation = 1
        self._app_type = 'user'
        self._process_dlg_running = False
        self.treeframe = None
    
    def _init_controls(self):
        #设置MacOS X的偏移
        if sys.platform == 'darwin':
            osx_offset = 5
        else:
            osx_offset = 0
        uispy_stype = wx.DEFAULT_FRAME_STYLE & ~wx.MAXIMIZE_BOX & ~wx.RESIZE_BORDER #屏蔽掉最大化按钮和窗口缩放功能
        wx.Frame.__init__(self, None, wx.ID_ANY, "UISpy "+VERSION, size=(900, 750-osx_offset*6), style=uispy_stype)
        
        # 设置左上角图标(仅限windows系统)
        if sys.platform == 'win32':
            logo = wx.Icon(os.path.join(RESOURCE_PATH, 'qt4i_win.ico'), wx.BITMAP_TYPE_ICO)
            self.SetIcon(logo)
            
        # 设置菜单栏
        menu_bar = wx.MenuBar()
        #应用菜单
        app_menu = wx.Menu()
        install_menu = app_menu.Append(wx.ID_ANY, u"安装App", u"安装app到被测手机")
        uninstall_menu = app_menu.Append(wx.ID_ANY, u"卸载App", u"卸载被测手机上的app")
        sandbox_menu = app_menu.Append(wx.ID_ANY, u"浏览App沙盒", u"打开并查看设备的沙盒目录")
        app_menu.AppendSeparator()
        menu_bar.Append(app_menu, u'应用')
        #高级菜单
        advance_menu = wx.Menu()
        log_menu = advance_menu.Append(wx.ID_ANY, u"查看日志", u"打开日志文件夹")
        debug_menu = advance_menu.Append(wx.ID_ANY, u"Debug模式", u"使用Debug模式运行UISpy")
        setting_menu = advance_menu.Append(wx.ID_ANY, u"设置", u"环境参数设置")
        self.show_qpath_menu = advance_menu.Append(wx.ID_ANY, u'显示QPath', u"打开即可显示控件Qpath",kind=wx.ITEM_CHECK)
        self.remote_operator_menu = advance_menu.Append(wx.ID_ANY, u'远程控制', u"打开即可远程控制手机",kind=wx.ITEM_CHECK)

        advance_menu.AppendSeparator()
        menu_bar.Append(advance_menu, u'高级')
        
        self.Bind(wx.EVT_MENU, self.on_select_install_pkg, install_menu) 
        self.Bind(wx.EVT_MENU, self.on_uninstall, uninstall_menu)
        self.Bind(wx.EVT_MENU, self.on_log, log_menu)
        self.Bind(wx.EVT_MENU, self.on_debug, debug_menu)
        self.Bind(wx.EVT_MENU, self.on_settings, setting_menu)
        self.Bind(wx.EVT_MENU, self.on_sandbox_view, sandbox_menu)
        self.SetMenuBar(menu_bar)
        
        # 设置主面板
        self.panel = wx.Panel(self, wx.ID_ANY)
        self.Bind(wx.EVT_CLOSE, self.on_close)
        
        # 第一行控件
        line1_y = 10
        wx.StaticText(self.panel, wx.ID_ANY, u"设备主机:", pos=(10,line1_y+osx_offset/2), size=wx.DefaultSize)
        self.tc_device_host_ip = wx.TextCtrl(self.panel, wx.ID_ANY, pos=(80, line1_y), size=(140, 24), style=wx.TE_LEFT)
        self.tc_device_host_ip.SetValue('127.0.0.1')
        self.tc_device_host_ip.SetToolTip(u"请输入设备主机或者设备DriverServer的IP")
        wx.StaticText(self.panel, wx.ID_ANY, u":", pos=(225, line1_y), size=wx.DefaultSize)
        self.tc_device_host_port = wx.TextCtrl(self.panel, wx.ID_ANY, pos=(235, line1_y), size=(60, 24), style=wx.TE_LEFT)
        self.tc_device_host_port.SetValue('12306')
        self.tc_device_host_port.SetToolTip(u"请输入设备主机或者设备DriverServer的端口号")
        self.btn_connect_device_host = wx.Button(self.panel, wx.ID_ANY, label=u'连接', pos=wx.Point(310, line1_y), size=wx.Size(50, 24), style=0)
        self.btn_connect_device_host.Bind(wx.EVT_BUTTON, self.on_connect_device_host)
        
        # 第二行控件
        line2_y = 45
        wx.StaticText(self.panel, wx.ID_ANY, u"设备:", pos=(10,line2_y+osx_offset/2), size=wx.DefaultSize)
        self.cb_devicelist = wx.ComboBox(self.panel, wx.ID_ANY, pos=(50, line2_y), size=(245+osx_offset/2, 24), style=wx.CB_READONLY)
        self.cb_devicelist.Bind(wx.EVT_COMBOBOX, self.on_select_device)
        self.btn_refresh = wx.Button(self.panel, wx.ID_ANY, u'刷新', pos=wx.Point(310, line2_y), size=wx.Size(50, 25), style=0)
        self.btn_refresh.Bind(wx.EVT_BUTTON, self.on_update_device_list)
        self.btn_refresh.Enable(False)
        
        # 第三行控件
        line3_y = 80
        wx.StaticText(self.panel, wx.ID_ANY, u"BundleID:", pos=(10,line3_y+osx_offset/2), size=wx.DefaultSize)
        self.tc_bundle_id = wx.ComboBox(self.panel, wx.ID_ANY, pos=(80-osx_offset, line3_y), size=(230+osx_offset*2, 24))
        self._config_file_path = os.path.join(RESOURCE_PATH, 'uispy.conf') 
        if os.path.exists(self._config_file_path):
            config_parser = ConfigParser.ConfigParser()
            config_parser.read(self._config_file_path)
            try:
                bunlde_id = config_parser.get('uispy', 'bundle_id')
            except ConfigParser.NoOptionError:
                bunlde_id = 'com.tencent.sng.test.gn'
        else:
            with open(self._config_file_path, 'w+') as fd:
                config_parser = ConfigParser.ConfigParser()
                config_parser.add_section('uispy')
                config_parser.write(fd)
            bunlde_id = DEFAULT_BUNDLE_ID
        self.tc_bundle_id.SetValue(bunlde_id)
        self.tc_bundle_id.SetToolTip(u"请选择被测App的Bundle ID")
        self.tc_bundle_id.Bind(wx.EVT_COMBOBOX, self.on_select_bundle_id)
        self.btn_refresh_applist = wx.Button(self.panel, wx.ID_ANY, u'刷新', pos=wx.Point(320, line3_y), size=wx.Size(40, 25), style=0)
        self.btn_refresh_applist.Bind(wx.EVT_BUTTON, self.on_update_app_list)
        self.btn_refresh_applist.Enable(False)
        self.tc_bundle_all = wx.CheckBox(self.panel, label = 'All',pos = (370, line3_y+osx_offset/2))
        self.tc_bundle_all.Bind(wx.EVT_CHECKBOX, self.on_select_bundle_all)
        self.btn_start_app = wx.Button(self.panel, wx.ID_ANY, label=u'启动App', pos=wx.Point(420, line3_y), size=wx.Size(80, 24), style=0)
        self.btn_start_app.Bind(wx.EVT_BUTTON, self.on_start_app)
        
        # 第四行控件  
        line4_y = 115
        wx.StaticText(self.panel, wx.ID_ANY, u"QPath:", pos=(10,line4_y+osx_offset/2), size=wx.DefaultSize)
        self.tc_qpath = wx.TextCtrl(self.panel, wx.ID_ANY, pos=(70-osx_offset, line4_y), size=(340, 24), style=wx.TE_LEFT)
        self.tc_qpath.SetValue('')
        self.btn_get_uitree = wx.Button(self.panel, wx.ID_ANY, label=u'获取控件', pos=wx.Point(420, line4_y), size=wx.Size(80, 24), style=0)
        self.btn_get_uitree.Bind(wx.EVT_BUTTON, self.on_get_uitree)
        
        #截屏区域的控件
        self.image_shown_width = 375
        self.image_shown_height = 667
        self.image_screenshot = wx.StaticBitmap(parent=self.panel, id=wx.ID_ANY, pos=(520, 5), size=(self.image_shown_width, self.image_shown_height))   
        self.image_screenshot.Bind(wx.EVT_MOUSE_EVENTS, self.on_screenshot_mouse_event)
        self.image_screenshot.Bind(wx.EVT_SET_FOCUS, self.on_screenshot_focus)
        startup_image = wx.Image(os.path.join(RESOURCE_PATH, 'startup.png'), wx.BITMAP_TYPE_ANY, index=-1)
        startup_image = startup_image.Scale(self.image_shown_width, self.image_shown_height)
        self.image_screenshot.SetBitmap(wx.Bitmap(startup_image))
        self.mask_panel = CanvasPanel(self.panel, id=wx.ID_ANY, pos=(520, 5), size=(self.image_shown_width, self.image_shown_height))
        self.mask_panel.Bind(wx.EVT_MOUSE_EVENTS, self.on_screenshot_mouse_event)
        #文件拖拽
        self.drop_target = FileDropTarget(self, self.image_screenshot)  
        self.image_screenshot.SetDropTarget(self.drop_target)
         
        #控件树
        line5_y = 150
        self.tc_uitree = wx.TreeCtrl(self.panel, wx.ID_ANY,pos=(10, line5_y), size=(500, 380))
        self.tc_uitree.Bind(wx.EVT_TREE_SEL_CHANGED, self.on_uitree_node_click)
        self.tc_uitree.Bind(wx.EVT_TREE_ITEM_RIGHT_CLICK, self.on_uitree_node_right_click)
        
        #控件详细属性
        line6_y = 525
        st_control_properties = wx.StaticBox(self.panel, wx.ID_ANY, u"控件属性", pos=(10, line6_y+osx_offset*2), size=(500, 140))
        wx.StaticText(st_control_properties, wx.ID_ANY, u"name", pos=(10, 30-osx_offset*2), size=wx.DefaultSize)
        self.tc_id = wx.TextCtrl(st_control_properties, wx.ID_ANY, pos=(55, 30-osx_offset*2), size=(135, 24), style=wx.TE_LEFT)
        wx.StaticText(st_control_properties, wx.ID_ANY, u"classname", pos=(200, 30-osx_offset*2), size=wx.DefaultSize)
        self.tc_classname = wx.TextCtrl(st_control_properties, wx.ID_ANY, pos=(280, 30-osx_offset*2), size=(160, 24), style=wx.TE_LEFT)
        wx.StaticText(st_control_properties, wx.ID_ANY, u"label", pos=(10, 65-osx_offset*2), size=wx.DefaultSize)
        self.tc_label = wx.TextCtrl(st_control_properties, wx.ID_ANY, pos=(55, 65-osx_offset*2), size=(135, 24), style=wx.TE_LEFT)
        wx.StaticText(st_control_properties, wx.ID_ANY, u"rect", pos=(200, 65-osx_offset*2), size=wx.DefaultSize)
        self.tc_rect = wx.TextCtrl(st_control_properties, wx.ID_ANY, pos=(250, 65-osx_offset*2), size=(190, 24), style=wx.TE_LEFT)
        wx.StaticText(st_control_properties, wx.ID_ANY, u"value", pos=(10, 100-osx_offset*2), size=wx.DefaultSize)
        self.tc_value = wx.TextCtrl(st_control_properties, wx.ID_ANY, pos=(55, 100-osx_offset*2), size=(135, 24), style=wx.TE_LEFT)
        wx.StaticText(st_control_properties, wx.ID_ANY, u"visible", pos=(200, 100-osx_offset*2), size=wx.DefaultSize)
        self.tc_visible = wx.TextCtrl(st_control_properties, wx.ID_ANY, pos=(250, 100-osx_offset*2), size=(50, 24), style=wx.TE_LEFT)  
        wx.StaticText(st_control_properties, wx.ID_ANY, u"enable", pos=(310, 100-osx_offset*2), size=wx.DefaultSize)
        self.tc_enable = wx.TextCtrl(st_control_properties, wx.ID_ANY, pos=(370, 100-osx_offset*2), size=(50, 24), style=wx.TE_LEFT)            
  
        #状态栏
        self.statusbar = self.CreateStatusBar()
        # 将状态栏分割为3个区域,比例为1:2:3
        self.statusbar.SetFieldsCount(3)
        self.statusbar.SetStatusWidths([-6, -6, -1])
        
    def on_close(self, event):
        if self.treeframe:
            self.treeframe.Destroy()
        config_parser = ConfigParser.ConfigParser()   
        config_parser.read(self._config_file_path)
        config_parser.set("uispy", "bundle_id", self.tc_bundle_id.GetValue())
        with open(self._config_file_path, 'w') as fd:
            config_parser.write(fd)
        import atexit
        atexit._exithandlers = []  # 禁止退出时弹出错误框
        event.Skip()
        
    def create_tip_dialog(self, msg, title=u"错误"):
        dialog = wx.MessageDialog(self, msg, title, style=wx.OK)
        dialog.ShowModal()
        dialog.Destroy()
        
    def show_process_dialog(self, msg):
        progress_max = 100
        dialog = wx.ProgressDialog(u"提示", msg, progress_max, parent=self.panel, style=wx.PD_CAN_ABORT|wx.PD_APP_MODAL|wx.PD_AUTO_HIDE)
        count = 0
        while self._process_dlg_running and count < progress_max:
            count = (count + 1) % 100
            wx.MilliSleep(100)
            if not dialog.Update(count)[0]:
                break
        dialog.Destroy()
        
    def _run_in_main_thread(self, func, *args, **kwargs):
        wx.CallAfter(func, *args, **kwargs)
        
    def _run_in_work_thread(self, func, *args, **kwargs):
        t = threading.Thread(target=func, args=args, kwargs=kwargs)
        t.setDaemon(True)
        t.start()

    def _update_device_list(self):
        self._run_in_main_thread(self.statusbar.SetStatusText, u"正在获取设备列表......", 0)
        time.sleep(2)
        try:
            start_time = time.time()
            devices = self._host_driver.list_devices()
            end_time = time.time()
            print 'cost time:',(end_time - start_time)
        except:
            error = traceback.format_exc()
            Log.e('update_device_list', error)
            self._run_in_main_thread(self.statusbar.SetStatusText, u"更新设备列表失败", 0)
            self._run_in_main_thread(self.create_tip_dialog, error.decode('utf-8'))
            return
        self.cb_devicelist.Clear()
        for dev in devices:
            self.cb_devicelist.Append(dev['name'].decode('utf-8'), dev)
        self._device = devices[0]
        self._run_in_main_thread(self.btn_refresh.Enable)
        self._run_in_main_thread(self.btn_refresh_applist.Enable)
        self._run_in_main_thread(self.cb_devicelist.Select, 0)
        self._run_in_main_thread(self.statusbar.SetStatusText, u"更新设备列表完毕", 0)
        self._update_bundle_id_list()
    
    def _update_bundle_id_list(self):
        '''
        在连接设备或者更换设备时，更新bundle_id列表
        '''
        print self._device
        self._device_driver = DeviceDriver(self._host_driver.host_url, self._device['udid'])
        original_bundle_id = self.tc_bundle_id.GetValue()
        self.tc_bundle_id.Clear()
        if self._device['simulator']:
            self._host_driver.start_simulator(self._device['udid'])
        self._app_list = self._device_driver.get_app_list(self._app_type)
        Log.i('app_list:', str(self._app_list))
        bundle_list = []
        remove_dev = None
        if self._app_list:
            for dev in self._app_list:
                bundle = dev.keys()[0]
                if bundle == 'com.apple.test.XCTestAgent-Runner':
                    remove_dev = dev
                    continue
                bundle_list.append(bundle)
                self.tc_bundle_id.Append(bundle.decode('utf-8'), dev)
            index = bundle_list.index(original_bundle_id) if original_bundle_id and original_bundle_id in bundle_list else 0
            self._run_in_main_thread(self.tc_bundle_id.Select, index)
            if remove_dev:
                self._app_list.remove(dev)
            if self.treeframe:
                self._run_in_main_thread(self.on_update_sandbox_view)
        else:
            self.create_tip_dialog(u'设备未启动或无可用APP')
            return
    
    def on_connect_device_host(self, event):
        '''连接设备主机
        '''
        self.statusbar.SetStatusText(u"正在连接设备主机......", 0)
        host_ip = self.tc_device_host_ip.GetValue()
        host_port = self.tc_device_host_port.GetValue()
        self._host_driver = HostDriver(host_ip, host_port)
        if not self._host_driver.connect_to_host(self._driver_type):
            self.statusbar.SetStatusText(u"连接设备主机异常！", 0)
            config_parser = ConfigParser.ConfigParser()
            config_parser.read(os.path.join(RESOURCE_PATH, 'uispy.conf'))
            qt4i_manage = config_parser.get('uispy', 'qt4i-manage')
            if not os.path.exists(qt4i_manage):
                self.create_tip_dialog(u"请检查qt4i是否安装或者qt4i-manage路径是否配置正确！\n"
                                       u"1.qt4i安装方法:pip install qt4i --user\n"
                                       u"2.qt4i-manage配置方法:高级->设置")
            else:
                self.create_tip_dialog(u"连接设备主机异常，请检查设备主机地址")
            return
        self._run_in_work_thread(self._update_device_list)
    
    def on_select_device(self, event):
        '''从设备列表中选择设备
        '''
        index = self.cb_devicelist.GetSelection()
        selected_device = self.cb_devicelist.GetClientData(index)
        
        if self._device != selected_device:
            self._device = selected_device
            print 'current_device:', self._device
            self._run_in_work_thread(self._update_bundle_id_list)
        
    def on_update_device_list(self, event):
        '''刷新设备列表
        '''
        self.statusbar.SetStatusText(u"正在更新设备列表......", 0)
        self._run_in_work_thread(self._update_device_list)
    
    def _update_screenshot(self, img_data):
        image = wx.Image(StringIO.StringIO(img_data))
        if self._orientation == 3 and image.GetWidth() > image.GetHeight():
            image = image.Rotate90()
        w = image.GetWidth()
        h = image.GetHeight()
        print 'Width:', w
        print 'Height:', h
        image = image.Scale(self.image_shown_width, self.image_shown_height)
        self.image_screenshot.SetBitmap(wx.Bitmap(image)) 
    
    def _add_child(self, parent, children, depth):
        for child in children: 
            properties = dict.copy(child)
            del properties['children']
            new_item = self.tc_uitree.AppendItem(parent, child['classname'], data = properties) 
            child['item_id'] = new_item
            child['depth'] = depth
            self._add_child(new_item, child['children'], depth+1)
    
    def _update_uitree(self):
        self.tc_uitree.DeleteAllItems()
        if 'UIATarget' == self._element_tree['classname']:
            self._element_tree = self._element_tree['children'][0]
        app = dict.copy(self._element_tree)
        del app['children']
        
        self._app_shown_width = app['rect']['size']['width']
        self._app_shown_height = app['rect']['size']['height']
        
        if self._scale_rate is None:
            self._scale_rate = ((self.image_shown_width * 1.0) / self._app_shown_width,
                                (self.image_shown_height * 1.0) / self._app_shown_height)
#         root = self.tc_uitree.AddRoot(self._element_tree['classname'], data = wx.TreeItemData(app))
        root = self.tc_uitree.AddRoot(self._element_tree['classname'], data = app)
        self._element_tree['item_id'] = root
        self._element_tree['depth'] = -1
        self._root_item = root
        self._add_child(root, self._element_tree['children'], 0)
    
    def _start_app(self): 
        bundle_id = self.tc_bundle_id.GetValue()
        
        while(True):
            if self._process_dlg_running:
                break
        dlg = self._dialog
        try:
            xcode_version = self._device_driver.get_xcode_version()
            ios_version = self._device_driver.get_ios_version()
            Log.i('xcode_version:%s ios_version:%s' % (xcode_version, ios_version))
#             增加版本检测
            self._run_in_main_thread(dlg.on_update)
            self._app_started = self._device_driver.start_app(bundle_id)
            if self._app_started:
                self._run_in_main_thread(self.statusbar.SetStatusText, u"App启动成功", 0)
                self._run_in_main_thread(dlg.on_update_title_msg, '抓取App屏幕中......')
                img_data = self._device_driver.take_screenshot()
                self._orientation = self._device_driver.get_screen_orientation()
                self._run_in_main_thread(self._update_screenshot, img_data)
                self._run_in_main_thread(dlg.on_update_title_msg, '抓取App控件树中......')
                self._element_tree = self._device_driver.get_element_tree()
                self._run_in_main_thread(self._update_uitree)
            else:
                self._run_in_main_thread(self.statusbar.SetStatusText, u"App启动失败:", 0)
        except:
            error = traceback.format_exc()
            Log.e('start_app', error)
            self._run_in_main_thread(self.create_tip_dialog, error.decode('utf-8'))
        self._process_dlg_running = False
        self._run_in_main_thread(dlg.on_destory)
        
    def on_start_app(self, event):
        if self._host_driver is None:
            self.create_tip_dialog(u"未连接设备主机，请连接设备主机")
            return
        self._device_driver = DeviceDriver(self._host_driver.host_url, self._device['udid'])
        self.statusbar.SetStatusText(u"App正在启动......", 0)
        self._scale_rate = None
        self._run_in_work_thread(self._start_app)
        self.show_dialog('App启动中......')
        
    def show_dialog(self, msg):
        self._dialog = MyProgressDialog(msg, self.panel)
        self._process_dlg_running = True
    
    def on_get_uitree(self, event):
        img_data = self._device_driver.take_screenshot()
        self._orientation = self._device_driver.get_screen_orientation()
        print 'orientation: ', self._orientation
        self._update_screenshot(img_data)
        try:
            self._element_tree = self._device_driver.get_element_tree()
        except:
            self.create_tip_dialog(u'获取控件树失败:%s' % traceback.format_exc())
            return
        self._update_uitree()
        self.statusbar.SetStatusText(u"获取控件树成功", 0)
    
    def _check_pos_in_element(self, pos, element):
        rect = element['rect']
        if pos[0] >= rect['origin']['x'] and pos[0] <= rect['origin']['x'] + rect['size']['width'] \
           and pos[1] >= rect['origin']['y'] and pos[1] <= rect['origin']['y'] + rect['size']['height'] \
           and element['visible']:
            return True
        else:
            return False
        
    def _select_closest_element(self, pos, element1, element2):
        '''选择距离最近的控件，具体规则如下：
            1、如果element1和element2的位置是包含关系（父子关系），则选择子节点
            2、如果element1和element2的位置是部分重叠，则选择距离控件中心最近的控件
        '''
        rect1 = element1['rect']
        rect2 = element2['rect']
        if rect1['origin']['x'] >= rect2['origin']['x'] and \
            rect1['origin']['x'] + rect1['size']['width'] <= rect2['origin']['x'] + rect2['size']['width'] and \
            rect1['origin']['y'] >= rect2['origin']['y'] and \
            rect1['origin']['y'] + rect1['size']['height'] <= rect2['origin']['y'] + rect2['size']['height']:
            return element1
        
        if rect2['origin']['x'] >= rect1['origin']['x'] and \
            rect2['origin']['x'] + rect2['size']['width'] <= rect1['origin']['x'] + rect1['size']['width'] and \
            rect2['origin']['y'] >= rect1['origin']['y'] and \
            rect2['origin']['y'] + rect2['size']['height'] <= rect1['origin']['y'] + rect1['size']['height']:
            return element2
        
        center1 = (rect1['origin']['x'] + rect1['size']['width'] / 2.0, rect1['origin']['y'] + rect1['size']['height'] / 2.0)
        center2 = (rect2['origin']['x'] + rect2['size']['width'] / 2.0, rect2['origin']['y'] + rect2['size']['height'] / 2.0)
        distance1 = (pos[0] - center1[0]) ** 2 + (pos[1] - center1[1]) ** 2       
        distance2 = (pos[0] - center2[0]) ** 2 + (pos[1] - center2[1]) ** 2  
        if distance1 <= distance2:
            return element1
        else:
            return element2     
    
    def _get_focused_element(self, pos, root):
        '''优先查找叶子节点的控件（深度遍历）
        '''
        for e in root['children']:
            self._get_focused_element(pos, e)
            if self._check_pos_in_element(pos, e):
                if self._focused_element is None:
                    self._focused_element = e
                else:
                    self._focused_element = self._select_closest_element(pos, self._focused_element, e)
        
#         if self._check_pos_in_element(pos, root):
#                 if self._focused_element is None:
#                     self._focused_element = root
#                 else:
#                     self._focused_element = self._select_closest_element(pos, self._focused_element, root)    
    
    def _expand_uitree(self, item_id):
        '''展开控件树
        '''
        if item_id != self._root_item:
            parent = self.tc_uitree.GetItemParent(item_id)
            self._expand_uitree(parent)
            self.tc_uitree.Expand(item_id)
        else:
            self.tc_uitree.Expand(self._root_item)
            
    def _dfs_traverse(self, element_tree, element_list=None):
        if element_list is None:
            element_list = []
        element_list.append(element_tree)
        for e in element_tree['children']:
            self._dfs_traverse(e, element_list)
        return element_list
            
    def _recommend_qpath(self, element):
        '''推荐QPath，具体策略如下：
           1、id唯一，则推荐id作为QPath
           2、待补充
        '''    
        self.tc_qpath.SetValue("")    
        if element['name']:
            element_id = element['name']
            element_list = self._dfs_traverse(self._element_tree)
            count = 0
            for e in element_list:
                if e['name'] == element_id:
                    count += 1
            if count == 1:
                self.tc_qpath.SetValue(element_id.decode('utf-8'))
                return
            
        if self.show_qpath_menu.IsChecked():
            if element['classname'] == 'Other' and not element['label'] and not element['name'] and not element['value']:
                return
            
            qpath = '/classname = \'' + element['classname'] + '\''
            if element['label']:
                qpath += ' & label = \'' +element['label'] + '\''
            elif element['name']:
                qpath += ' & name = \'' +element['name'] + '\''
            elif element['value']:
                qpath += ' & value = \'' +element['value'] + '\''
                
            qpath += ' & visible = %s & maxdepth = %s' % (str(element['visible']).lower(), str(element['depth']).lower())
            self.tc_qpath.SetValue(qpath.decode('utf-8'))
            
    
    def on_screenshot_focus(self, event):
        print 'screenshot focus'
#         self.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
    
    def on_screenshot_single_click(self, event):
        self.timer.Stop()
        click_action = 'click'
        if not self._mouse_up:
            click_action = 'long_click'
        if not self._element_tree:
            Log.e('on_screenshot_single_click', 'failed to get element tree')
            return
        self._focused_element = None
        self._get_focused_element(self._single_click_position, self._element_tree)
        print 'focus_element:', self._focused_element ['rect']
        rect = (self._focused_element ['rect']['origin']['x'], self._focused_element ['rect']['origin']['y'], \
            self._focused_element ['rect']['size']['width'], self._focused_element ['rect']['size']['height'])
        #红色标记截图中鼠标位置的控件
        if self._orientation == 3:
            rect = (self.image_shown_width/self._scale_rate[0]-rect[1] - rect[3], rect[0], rect[3], rect[2])
        self.mask_panel.highlight_element(rect, self._scale_rate)
        #展开控件树
        self._expand_uitree(self._focused_element['item_id'])
        #选中对应的控件
        self.tc_uitree.SelectItem(self._focused_element['item_id'])
        self.tc_uitree.SetFocus()
        #推荐控件的QPath
        self._recommend_qpath(self._focused_element)
        #判断是否进行远程控制
        if self.remote_operator_menu.IsChecked() and self._device_driver:
            driver_method = getattr(self._device_driver, click_action)
            driver_method(self.x, self.y)
            time.sleep(1.5)
            self._run_in_work_thread(self.on_get_uitree,event)
                
    def on_screenshot_mouse_event(self, event):
        pos = event.GetPosition()
        if self._orientation == 3:
            pos = (pos[1], self.image_shown_width - pos[0])
        
        self.statusbar.SetStatusText(str(pos),2)
        if not self._app_started:
            self.statusbar.SetStatusText(u'App未启动',0)
            return

        if event.ButtonDown():
            self._mouse_up = False
            self._event_start = time.time()
            pos = (pos[0]/self._scale_rate[0], pos[1]/self._scale_rate[1])
            self.x = float(pos[0])/self._app_shown_width
            self.y = float(pos[1])/self._app_shown_height
            if not event.RightDown():
                self.timer = wx.Timer(self)
                self.timer.Start(200) # 0.2 seconds delay
                self.Bind(wx.EVT_TIMER, self.on_screenshot_single_click, self.timer)
                
        elif event.Dragging():
            self.timer.Stop()
            
        elif event.LeftDClick():
            self.timer.Stop()

        elif event.LeftUp():
            self._mouse_up = True
            self._event_interval = time.time() - self._event_start
            new_pos = (pos[0]/self._scale_rate[0], pos[1]/self._scale_rate[1])
            x1 = float(new_pos[0])/self._app_shown_width
            y1 = float(new_pos[1])/self._app_shown_height
            self._single_click_position = new_pos
            if abs(self.x - x1) > 0.02 or abs(self.y - y1) > 0.02:
                if self.remote_operator_menu.IsChecked() and self._device_driver:
                    self._device_driver.drag(self.x, self.y, x1, y1, self._event_interval)
                    time.sleep(1.5)
                    self._run_in_work_thread(self.on_get_uitree,event)
                
    def on_uitree_node_click(self, event):
        
        item_id = event.GetItem()
        
        item_data = self.tc_uitree.GetItemData(item_id)
        
        item_data['depth'] = self.get_element_depth(item_id)
        
        self.tc_classname.SetValue(item_data['classname'])
        name = item_data['name'] if item_data['name'] else 'null'
        if isinstance(name, basestring):
            name = name.decode('utf-8')
        else:
            name = str(name)
        self.tc_id.SetValue(name)
        label = item_data['label'] if item_data['label'] else 'null'
        if isinstance(label, basestring):
            label = label.decode('utf-8')
        else:
            label = str(label)    
        self.tc_label.SetValue(label)
        value = item_data['value'] if item_data['value'] else 'null'
        if isinstance(value, basestring):
            value = value.decode('utf-8')
        else:
            value = str(value)  
        self.tc_value.SetValue(value)
        rect = (item_data['rect']['origin']['x'], item_data['rect']['origin']['y'], \
                                   item_data['rect']['size']['width'], item_data['rect']['size']['height'])
        self.tc_rect.SetValue(str(rect))
        self.tc_visible.SetValue('true' if item_data['visible'] else 'False')
        self.tc_enable.SetValue('true' if item_data['enabled'] else 'False')
        
        if self._orientation == 3:
            rect = (self.image_shown_width/self._scale_rate[0]-rect[1]-rect[3], rect[0], rect[3], rect[2])
        self.mask_panel.highlight_element(rect, self._scale_rate)
        
        self._recommend_qpath(item_data)
    
    def on_uitree_node_right_click(self, event):
        self.tc_uitree.PopupMenu(TreeNodePopupMenu(self, event.GetItem()), event.Point)    

    def on_select_install_pkg(self, event):
        if self._device is None:
            self.create_tip_dialog(u'未选择设备，请连接设备主机并选择设备！')
            return
        dlg = wx.FileDialog(self, u"选择app的安装包", "", "",
                                       "app files (*.zip,*.ipa)|*.zip;*.ipa", wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_CANCEL:
            return
        pkg_path = dlg.GetPath().encode('utf-8')
        dlg.Destroy()
        self._run_in_work_thread(self.on_install, pkg_path)

    def on_install(self, pkg_path):
        
        self._run_in_main_thread(self.show_dialog, 'APP正在安装中......')
        while(True):
            if self._process_dlg_running:
                break
        dlg = self._dialog
        self._run_in_main_thread(dlg.on_update)
        
        if not self._device_driver:
            self._device_driver = DeviceDriver(self._host_driver.host_url, self._device['udid'])
        try:
            result = self._device_driver.install_app(pkg_path)
            self._process_dlg_running = False
            self._run_in_main_thread(dlg.on_destory)
            if result:
                self._run_in_main_thread(wx.MessageBox, '安装成功', '信息提示', wx.OK|wx.ICON_INFORMATION)
                self._update_bundle_id_list()
            else:
                self._run_in_main_thread(wx.MessageBox, '安装失败', '信息提示', wx.OK|wx.ICON_INFORMATION)
        except:
            error = traceback.format_exc()
            Log.e('start_app', error)
            self.create_tip_dialog(error.decode('utf-8'))
        
    def on_uninstall(self, event):
        if self._device is None:
            self.create_tip_dialog(u'未选择设备，请连接设备主机并选择设备！')
            return
        if not self._device_driver:
            self._device_driver = DeviceDriver(self._host_driver.host_url, self._device['udid'])
        index = self.tc_bundle_id.GetSelection()
        bundle_id = self.tc_bundle_id.GetClientData(index).keys()[0]
        result = self._device_driver.uninstall_app(bundle_id)
        
        if result:
            uninstall_app = self.get_app(bundle_id)
            message_title = uninstall_app[bundle_id]+':'+bundle_id
            wx.MessageBox(u"卸载成功",message_title.decode('utf-8'))
            self._update_bundle_id_list()
        else:
            wx.MessageBox(u"卸载失败")

    def on_log(self, event):
        '''
        打开日志所在文件夹
        '''
        log_path = Log.gen_log_path()
        if os.path.exists(log_path):
            if sys.platform == 'darwin':
                log_cmd = 'open %s' % log_path
                subprocess.call(log_cmd,shell=True)
            elif sys.platform == 'win32':
                os.system("explorer.exe %s" % log_path)
        else:
            self.create_tip_dialog(u'日志文件被移除')
            return
    
    def on_select_bundle_id(self, event):
        '''
        当bundle_id切换选择时，更新沙盒目录
        '''
        if self.treeframe:
            self.treeframe.update_directory_tree(self.tc_bundle_id.GetValue())
            
    def on_update_app_list(self, event):
        '''
        更新app列表
        '''
        if self._device:
            self._run_in_work_thread(self._update_bundle_id_list)
        
    def on_select_bundle_all(self, event):
        '''
        根据按钮打开多有或者用户APP
        '''
        bundle_check = event.GetEventObject()
        if bundle_check.GetValue():
            self._app_type = 'all'
        else:
            self._app_type = 'user'
        if self._device:
            self._run_in_work_thread(self._update_bundle_id_list)
        
    def get_element_depth(self, item_id):
        '''
        获取element的depth
        :param item_id element的属性
        
        return depth
        '''
        depth = 0
        while item_id != self._root_item:
            item_id = self.tc_uitree.GetItemParent(item_id)
            depth += 1
        return depth
    
    def get_app(self, bundle_id):
        '''
        根据bundle_id从app_list中获取app信息
        '''
        for app in self._app_list:
            if app.has_key(bundle_id):
                return app

    def on_debug(self, event):
        '''
        '''
        current_path = os.getcwd()
        debug_path = os.path.join(current_path, DEBUG_PATH)
        if current_path.endswith('ui'):
            wx.MessageBox('本模式下不支持')
        else:
            self.Close(force=True)
            wx.Exit()
            cmd = 'open %s' % debug_path
            subprocess.call(cmd,shell=True)

    def on_settings(self, event):
        setting_dlg = Settings(self._config_file_path, None, title=u'环境参数设置')
        setting_dlg.ShowModal()
        setting_dlg.Destroy()

    def on_sandbox_view(self, event):
        '''
        查看沙盒的目录结构
        '''
        if self._device is None:
            self.create_tip_dialog(u'未选择设备，请连接设备主机并选择设备！')
            return
        self.treeframe = TreeFrame(self, '/', '%s沙盒目录' % self._device['name'], self._device_driver, self.tc_bundle_id.GetValue())
        self.treeframe.Show(show=True)
    
    def on_update_sandbox_view(self):
        if self.treeframe:
            self.treeframe.update_tree_frame('%s沙盒目录' % self._device['name'], self._device_driver, self.tc_bundle_id.GetValue())
    
    def on_close_treeFrame(self):
        '''监控沙盒frame是否关闭
        '''
        self.treeframe = None
    
    
class CanvasPanel(wx.Panel):
    '''绘图面板
    '''
    def __init__(self, *args, **kwargs):
        wx.Panel.__init__(self, *args, **kwargs)
        self.Bind(wx.EVT_PAINT, self.on_paint)
        self._draw_points = None
        self._last_draw_points = None
        
    def draw_rectangle(self, p1, p2):
        '''画长方形
        '''
        self._draw_points = (p1, p2)
        if self._last_draw_points and self._last_draw_points[0] == p1 and self._last_draw_points[1] == p2:
            pass
        else:
            self.Hide()
            self.Show()
    
    def highlight_element(self, rect, scale_rate):
        p1 = rect[0] * scale_rate[0], rect[1] * scale_rate[1]
        p2 = (rect[0] + rect[2]) * scale_rate[0], (rect[1] + rect[3]) * scale_rate[1]
        self.draw_rectangle(p1, p2)       
            
    def on_paint(self, evt):
        if self._draw_points:
            left, top = self._draw_points[0]
            right, bottom = self._draw_points[1]
            dc = wx.PaintDC(self)
            dc.SetPen(wx.Pen('red', 2))
            dc.DrawLine(left, top, right, top)
            dc.DrawLine(right, top, right, bottom)
            dc.DrawLine(right, bottom, left, bottom)
            dc.DrawLine(left, bottom, left, top)
            self._last_draw_points = self._draw_points
            self._draw_points = None
    

class TreeNodePopupMenu(wx.Menu):
    '''控件树节点的弹出菜单
    '''
    
    def __init__(self, parent, select_node, *args, **kwargs):
        super(TreeNodePopupMenu, self).__init__(*args, **kwargs)
        self._parent = parent
        self._select_node = select_node
        
        item1 = wx.MenuItem(self, wx.NewId(), u'打开WebInspector')
        self.AppendItem(item1)
        self.Bind(wx.EVT_MENU, self.on_open_web_inspector, item1)

    def on_open_web_inspector(self, event):
        if sys.platform == 'darwin':
            import webbrowser
            safari = webbrowser.get('safari')
            safari.open('', new=0, autoraise=True)
        else:
            self._parent.create_tip_dialog(u'WebInspector仅支持MacOS系统下Safari浏览器')


class MyProgressDialog(wx.ProgressDialog):
    '''
    弹出显示框可更新内容显示
    '''
    
    def __init__(self, msg, panel, progress_max = 100):
        super(MyProgressDialog, self).__init__(u"提示", msg, progress_max, parent=panel, style=wx.PD_CAN_ABORT|wx.PD_APP_MODAL|wx.PD_AUTO_HIDE)
        self._title_msg = msg
        self._is_destoryed = False
        self._progress_max = progress_max
        self._dialog_destory = False

    def on_update_title_msg(self, msg):
        self._title_msg = msg

    def on_destory(self):
        self._dialog_destory = True

    def on_close(self):
        if not self._is_destoryed:
            self.Destroy()
            self._is_destoryed = True
        
    def on_update(self):
        count = 0
        while not self._is_destoryed and count < self._progress_max:
            count = (count + 1) % 100
            wx.MilliSleep(100)
            if self._dialog_destory or not self.Update(count,self._title_msg)[0]:
                break
        self.on_close()


class FileDropTarget(wx.FileDropTarget):  
    def __init__(self, frame_window, target):  
        wx.FileDropTarget.__init__(self)
        self.frame_window = frame_window
        self.target = target
  
    def OnDropFiles(self,  x,  y, filepath):
        
        if self.frame_window._device is None:
            self.frame_window.create_tip_dialog(u'未选择设备，请连接设备主机并选择设备！')
            return False
        
        for path in filepath:
            path = path.encode('utf-8')
            basename = os.path.basename(path)
            if path.endswith(('.ipa', '.zip')):
                self.frame_window._run_in_work_thread(self.frame_window.on_install, path)
            else:
                self.frame_window.create_tip_dialog(u'%s格式不符合，请选择.ipa(真机)或者.zip(模拟器)类型安装包' % basename)
        return filepath is None


class Settings(wx.Dialog):
    '''设置系统参数
    '''

    def __init__(self, settings_file, *args, **kw):
        super(Settings, self).__init__(*args, **kw)
        self._settings_file = settings_file
        self._settings = {}
        self._load_settings()
        self._init_dialog()

    def _load_settings(self):
        config_parser = ConfigParser.ConfigParser()
        config_parser.read(self._settings_file)
        try:
            qt4i_manage_path = config_parser.get('uispy', 'qt4i-manage')
        except ConfigParser.NoOptionError:
            qt4i_manage_path = os.path.expanduser("~/Library/Python/2.7/bin/qt4i-manage")
        self._settings['qt4i-manage'] = qt4i_manage_path

    def _init_dialog(self):

        vertical_box = wx.BoxSizer(wx.VERTICAL)

        row_box = wx.BoxSizer(wx.HORIZONTAL)

        label = wx.StaticText(self, -1, "qt4i-manage:")
        row_box.Add(label, 0, wx.ALIGN_CENTRE | wx.ALL, 5)

        self.tc_qt4i_manage = wx.TextCtrl(self, -1, "", size=(400, -1))
        self.tc_qt4i_manage.SetToolTip(u"qt4i-manage的安装路径")
        row_box.Add(self.tc_qt4i_manage, 1, wx.ALIGN_CENTRE | wx.ALL, 5)
        self.tc_qt4i_manage.SetValue(self._settings['qt4i-manage'])

        vertical_box.Add(row_box, 0, wx.GROW | wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

        line = wx.StaticLine(self, -1, size=(20, -1), style=wx.LI_HORIZONTAL)
        vertical_box.Add(line, 0, wx.GROW | wx.ALIGN_CENTER_VERTICAL | wx.RIGHT | wx.TOP, 5)

        btnsizer = wx.StdDialogButtonSizer()

        btn_apply = wx.Button(self, wx.ID_APPLY)
        btn_apply.SetToolTip(u"设置生效")
        btn_apply.SetDefault()
        btn_apply.Bind(wx.EVT_BUTTON, self.on_apply_settings)
        btnsizer.AddButton(btn_apply)

        btn_cancel = wx.Button(self, wx.ID_CANCEL)
        btn_cancel.SetToolTip(u"取消设置")
        btnsizer.AddButton(btn_cancel)
        btnsizer.Realize()

        vertical_box.Add(btnsizer, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

        self.SetSizer(vertical_box)
        vertical_box.Fit(self)

    def on_apply_settings(self, event):
        config_parser = ConfigParser.ConfigParser()
        config_parser.read(self._settings_file)
        config_parser.set("uispy", "qt4i-manage", self.tc_qt4i_manage.GetValue())
        with open(self._settings_file, 'w') as fd:
            config_parser.write(fd)
