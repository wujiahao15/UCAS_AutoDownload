# UCAS_AutoDownload

批量下载课件的GUI脚本

## Declaration

1. 该脚本基于[苗师兄](https://github.com/vastskymiaow)的项目[UCAS-Course_Resource-Download](https://github.com/vastskymiaow/UCAS-Course_Resource-Download)，在其基础上添加了验证码的输入以及相应的图形化界面，并重构了部分代码。
2. UI部分的样式采用了项目[BreezeStyleSheets](https://github.com/Alexhuszagh/BreezeStyleSheets)。
3. 使用[fbs](https://build-system.fman.io/)进行应用的打包。

## Usage

### Windows

#### 1. Build From Source (Not recommended)

1. 首先，**确保**`Python`的路径在系统**环境变量**中。
2. 接着，双击`scripts`文件夹中的`WindowsInstall.bat`进行Python环境的预安装。
3. 最后，双击`scripts`文件夹中的`WindowsRun.bat`启动程序。

#### 2. Use App Installer

1. 下载[Release](https://github.com/flamywhale/UCAS_AutoDownload/releases)中的安装包，安装使用，点击[这里](https://github.com/flamywhale/UCAS_AutoDownload/releases/download/version0.1/Windows_Installer.exe)下载。

#### Roadmap 

* [x] windows下编译成`exe`可执行文件，并通过多台PC设备的测试。

### MacOS (Use Python script)

打开Mac的终端，cd到`UCAS_AutoDownload`目录下，在终端中执行以下命令。
``` bash
# 确保当前目录为 UCAS_AutoDownload
## 先安装需要的环境
./scripts/MacOsInstall.sh
## 运行↓
./scripts/MacOsRun.sh
```
