# UCAS_AutoDownload

批量下载课件的GUI脚本

## Declaration

1. 该脚本基于[苗师兄](https://github.com/vastskymiaow)的项目[UCAS-Course_Resource-Download](https://github.com/vastskymiaow/UCAS-Course_Resource-Download)，在其基础上添加了验证码的输入以及相应的图形化界面，并重构了部分代码。
2. UI部分的样式采用了项目[BreezeStyleSheets](https://github.com/Alexhuszagh/BreezeStyleSheets)。

## Usage

### Windows

1. 可以使用本项目中发布的Release。
2. 也可以使用[命令](###MacOS)运行python代码。

### MacOs

* `pip install -r requirements.txt`
* `pyuic5 dialog.ui -o dialog.py`
* `python main.py`
