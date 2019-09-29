# UCAS AutoDownloader

批量下载及更新课件的GUI程序。

## 声明

1. 该脚本基于[vastskymiaow](https://github.com/vastskymiaow)的项目[UCAS-Course_Resource-Download](https://github.com/vastskymiaow/UCAS-Course_Resource-Download)，在其基础上添加了验证码的输入以及相应的图形化界面，并重构了部分代码。
2. UI部分的样式采用了项目[BreezeStyleSheets](https://github.com/Alexhuszagh/BreezeStyleSheets)。
3. 使用[fbs](https://build-system.fman.io/)进行应用的打包。

## 使用说明

### 1. 使用安装包安装软件（推荐）

#### `Windows`系统

* 请下载[Release](https://github.com/flamywhale/UCAS_AutoDownload/releases)中的`Windows_Installer.exe`安装包，进行安装使用，点击[这里](https://github.com/flamywhale/UCAS_AutoDownload/releases/download/version0.1/Windows_Installer.exe)下载。

#### `macOS`系统

* 请下载[Release](https://github.com/flamywhale/UCAS_AutoDownload/releases)中的`macOS_Installer.dmg`安装包，进行安装使用，点击[这里](https://github.com/flamywhale/UCAS_AutoDownload/releases/download/version0.1/macOS_Installer.dmg)下载。

### 2. 直接运行Python代码 (不推荐)

#### `Windows`系统

**确保**`Python`的路径在系统**环境变量**中。
``` bat
.\scripts\WindowsInstall.bat
.\scripts\WindowsRun.bat
```

#### `macOS`系统

打开Mac的终端，cd到`UCAS_AutoDownload`目录下，在终端中执行以下命令。
``` bash
# 确保当前目录为 UCAS_AutoDownload
## 先安装需要的环境
./scripts/MacOsInstall.sh
## 运行↓
./scripts/MacOsRun.sh
```

## Roadmap

* [x] `windows`下编译成`exe`可执行文件，并通过多台PC设备的测试。
* [x] `macOS`下编译成应用，并生成安装包。

## 更新日志

* 2019-09-28
  * 成功将软件打包成安装包，方便开箱即用。
* 2019-09-26
  * 添加md5校验机制，使得已下载的文件如果md5值不变，不会重复下载。
  * 下载更新完毕后，添加了已更新课件的消息提示框。
* 2019-09-25
  * 已完成GUI界面及其CSS配置。
  * 将逻辑和界面渲染分离，使得GUI界面不会变成“无响应”状态。
  * 多线程下载更新课件。
  * 基本功能已经完成。

