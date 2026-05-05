1.运行：
```
python ./main.py
```
运行python代码需要将pikafish的engine文件（pikafish.exe）和nnue文件（pikafish.nnue）放在main.py同路径。

2.打包exe：
```
pyinstaller --onefile --noconsole --clean `
  --upx-dir "$env:TEMP\upx\upx-5.0.0-win64" `
  --name "ChineseChess" `
  --exclude-module matplotlib --exclude-module numpy --exclude-module scipy `
  --exclude-module pandas --exclude-module PIL --exclude-module cv2 `
  --exclude-module jupyter --exclude-module IPython --exclude-module sqlite3 `
  --exclude-module email --exclude-module http --exclude-module xmlrpc `
  --exclude-module pydoc --exclude-module unittest --exclude-module test `
  --exclude-module multiprocessing --exclude-module ctypes `
  main.py

--onefile：单 EXE
--noconsole：无黑窗
--upx-dir：UPX 路径（不指定则跳过压缩，体积多约 30%）
--exclude-module：排除用不到的库，减小体积
```
运行exe需要将pikafish的engine文件（pikafish.exe）和nnue文件（pikafish.nnue）放在exe同路径。

3.备注：

（1）本项目完全基于deepseek V4 pro生成。

（2）pikafish权重下载地址：https://github.com/official-pikafish/Pikafish
