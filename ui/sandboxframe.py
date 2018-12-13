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
sandbox界面
'''
import wx
import os
import sys
import base64
import traceback

from util.logger import Log
from settings import RESOURCE_PATH



SANDBOX_FILE_READ_FORM = ('.log', '.txt', '.plist', 'json', '.Indexed', '.conf', '.array', '.data', 'config')

class TreeFrame(wx.Frame):
    
    def __init__(self, main_frame, root_path, title, device_driver, bundle_id):
        self._root_path = root_path
        self._main_frame = main_frame
        self._device_driver = device_driver
        self._bundle_id = bundle_id
        self._init_frame(title)
        
    def _init_frame(self, title):
        wx.Frame.__init__(self, None, -1, title, size=(950, 620), style=wx.DEFAULT_FRAME_STYLE & ~wx.MAXIMIZE_BOX & ~wx.RESIZE_BORDER)
        self.Bind(wx.EVT_CLOSE, self.on_close)
        
        self.directory_tree = {}
        self.image_list = wx.ImageList(14, 14)
        self.image_list.Add(wx.Image(os.path.join(RESOURCE_PATH, 'folder.png'), wx.BITMAP_TYPE_PNG).Scale(14,14).ConvertToBitmap())
        self.image_list.Add(wx.Image(os.path.join(RESOURCE_PATH, 'file.png'), wx.BITMAP_TYPE_PNG).Scale(14,14).ConvertToBitmap())
        
        self.treectrl = wx.TreeCtrl(self, wx.ID_ANY, size=(220, 600))
        self.treectrl.AssignImageList(self.image_list)
        self.treectrl.Bind(wx.EVT_TREE_SEL_CHANGED, self.on_tree_node_click)
        self.update_directory_tree()
        
        self.lbl = wx.TextCtrl(self, -1, pos=(220, 0), size=(730, 600), style=wx.TE_READONLY | wx.TE_MULTILINE) 

    def update_tree_frame(self, title, device_driver, bundle_id):
        self.SetTitle(title)
        self.directory_tree = {}
        self._device_driver = device_driver
        self._bundle_id = bundle_id
        print 'bundle_id:%s' % self._bundle_id
        self.update_directory_tree()
    
    def update_directory_tree(self, bundle_id=None):
        self.treectrl.DeleteAllItems()
        if bundle_id:
            self._bundle_id = bundle_id
        self.treeroot = self.treectrl.AddRoot(self._bundle_id)
        self.treectrl.SetItemImage(self.treeroot, 0, which=wx.TreeItemIcon_Normal)
        # 添加子目录
        self.directory_tree[self.treeroot] = {'path':self._root_path, 'is_dir':True, 'expanded':True}
        self.add_item(self.treeroot, self._root_path)

    def on_tree_node_click(self, event):
        item_id = event.GetItem()
        path = self.directory_tree[item_id]['path']
        print path
        if self.directory_tree[item_id]['is_dir']:
            if not self.directory_tree[item_id]['expanded']:
                self.add_item(item_id, path)
        else:
            if os.path.splitext(path)[1] in SANDBOX_FILE_READ_FORM:
                try:
                    content = self._device_driver.get_sandbox_file_content(self._bundle_id, path)
                    self.lbl.SetValue(base64.b64decode(content))
                except:
                    msg = traceback.format_exc() # 方式1  
                    print (msg)
                    self.lbl.SetValue('该文件可能存在某些字符导致无法base64编码')
            else:
                self.lbl.SetValue('不支持该格式的文件显示')
    
    def add_item(self, root, path):
        self.directory_tree[root]['expanded'] = True
        try:
            file_list = self._device_driver.get_sandbox_path_files(self._bundle_id, path)
            for i in file_list:
                # 获得绝对路径
                tmpdir = os.path.join(path, i['path'])
                tmpdict = {}
                # 如果是路径的话 还需对该路径进行一次操作
                if i['is_dir']:
                    child = self.treectrl.AppendItem(root, os.path.basename(i['path']))
                    tmpdict['path'] = tmpdir
                    tmpdict['is_dir'] = i['is_dir']
                    tmpdict['expanded'] = False
                    self.directory_tree[child] = tmpdict
                    self.treectrl.SetItemImage(child, 0, which=wx.TreeItemIcon_Normal)
                    tmpdict = {}
                # 如果是目录的话
                else:
                    child = self.treectrl.AppendItem(root, os.path.basename(i['path']))
                    tmpdict['path'] = tmpdir
                    tmpdict['is_dir'] = i['is_dir']
                    tmpdict['expanded'] = False
                    self.directory_tree[child] = tmpdict
                    self.treectrl.SetItemImage(child, 1, which=wx.TreeItemIcon_Normal)
                    tmpdict = {}
        except:
            error = traceback.format_exc()
            Log.e('add_item', error)
            self._main_frame.create_tip_dialog(error.decode('utf-8'))

    def on_close(self, event):
        self._main_frame.on_close_treeFrame()
        self._device_driver.close_sandbox_client()
        event.Skip()
