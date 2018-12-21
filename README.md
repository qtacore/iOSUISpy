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
- Move UISpy app to " /Applications" directory and open it for use.

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
