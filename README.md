# UCAS_AutoDownload

批量下载课件的GUI脚本

## Declaration

1. 该脚本基于[苗师兄](https://github.com/vastskymiaow)的项目[UCAS-Course_Resource-Download](https://github.com/vastskymiaow/UCAS-Course_Resource-Download)，在其基础上添加了验证码的输入以及相应的图形化界面，并重构了部分代码。
2. UI部分的样式采用了项目[BreezeStyleSheets](https://github.com/Alexhuszagh/BreezeStyleSheets)。

## Usage

### Windows (Build From Source)

1. 确保`Python`的路径在系统环境变量中。
2. 打开该项目的文件夹，在地址栏输入`CMD`后，在打开的`CMD`中输入：`scripts\WindowsInstall.bat`
3. 点击`main.exe`即可运行

### MacOs

``` bash
# 确保当前目录为 UCAS_AutoDownload
## 先安装需要的环境
./scripts/MacOS_Install.sh
## 运行↓
./scripts/MacOS_Run.sh
```
