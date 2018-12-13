# -*- mode: python -*-

import os
import sys


block_cipher = None


project_path = os.getcwd()
pkgs = [project_path]
for filename in os.listdir(project_path):
	filepath = os.path.join(project_path, filename)
	if os.path.isdir(filepath):
		if '__init__.py' in os.listdir(filepath):
			pkgs.append(filepath)


a = Analysis(['ui/app.py'],
             pathex=pkgs,
             binaries=[],
             datas=[('res','.')],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)  

import version
VERSION = version.VERSION   

if sys.platform == 'win32':
	exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='UISpy',
          icon='res\\qt4i_win.ico',
          debug=False,
          strip=False,
          upx=True,
          console=False )
else:
	exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='UISpy',
          debug=False,
          strip=False,
          upx=True,
          console=True )
	
	coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='UISpy')
    
	app = BUNDLE(coll,
             name='UISpy.app',
             icon='res/qt4i_osx.icns',
             info_plist={
            		'CFBundleName': 'UISpy',
        			'CFBundleDisplayName': 'UISpy',
        			'CFBundleGetInfoString': "QT4i UISpy",
        			'CFBundleIdentifier': "com.tencent.ios.uispy",
        			'CFBundleVersion': VERSION,
        			'CFBundleShortVersionString': VERSION,
        			'NSHumanReadableCopyright': u"Copyright(c)2010-2017 Tencent All Rights Reserved."
			},
		)
