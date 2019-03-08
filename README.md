# iOSUISpy
 
iOSUISpy is a UI Tool for [QT4i](https://github.com/tencent/qt4i) to inspect QPath of iOS controls for iOS App.
 
## Features
 * Inspect QPath or id of controls for any app in iOS device
 * Support sandbox viewing of iOS app
 * Support iOS app installation and uninstallation
 * Supoort iOS device remote control

 
## Get Started

### How to install iOSUISpy

- Download [iOSUISpy Release Version](https://github.com/qtacore/iOSUISpy/releases) with the suffix ".dmg".
- Move UISpy app to " /Applications" directory.

### How to use iOSUISpy

- inspect QPath of iOS controls for iOS App
  - Open iOSUISpy by click icon of iOSUISpy. 
  - Click "连接" button and wait until device is connected.
  - Select ios device and select ios app by bundle id.
  - Click "启动App" button and wait until sceenshot and ui tree of app appear.
  - Operate app to specified page and click "获取控件" button, and repeat this step for inspecting QPath.


### How to debug iOSUISpy project

#### Debug with iOSUISpy source

- Make sure that you are in Python 2.7 environment on MacOS system

- Enter iOSUISpy project directory and install requirements library in terminal:
    ```shell
    $ pip install -i requirements.txt --user
    ```
    
- Select 'ui/app.py' file and run 
 
#### Build iOSUISpy Release version

Run command line  in Terminal in iOSUISpy project root directory, and the executable app will appear in the directory of "dist".
```shell
$ pyinstaller --windowed  --clean --noconfirm  --onedir uispy.spec
```
