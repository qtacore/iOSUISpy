# iOSUISpy
 
iOSUISpy is a UI Tool for [QT4i](https://github.com/tencent/qt4i) to inspect QPath of iOS controls for iOS App.
 
## Features
 * Inspect QPath or id of controls for any app in iOS device
 * Support sandbox viewing of iOS app
 * Support iOS app installation and uninstallation
 * Supoort iOS device remote control

 
## Get Started

### How to run from iOSUISpy project

- Make sure that you are in Python 2.7 environment on MacOS system

- Enter iOSUISpy project directory and install requirements library in terminal:
    ```shell
    $ pip install -i requirements.txt --user
    ```
    
- Select 'ui/app.py' file and run 
 
### How to build iOSUISpy Release Tool

Run command line  in Terminal in iOSUISpy project root directory
```shell
$ pyinstaller --windowed  --clean --noconfirm  --onedir uispy.spec
```
