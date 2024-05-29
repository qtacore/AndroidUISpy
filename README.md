# Android控件探测器

本工具可用于探测Android设备中的应用控件，可代替`UIAutomator`等工具

使用限制：

* Root设备中可以探测任意应用的控件
* 非Root设备中只能探测debug应用的控件

## PREPARE ENVIRONMENT

1. `cd $project_root`
2. `python3 -m virtualenv .env3`
3. Windows:  
    `.env3\Scripts\activate.bat`
    Others:  
    `source .env3/bin/activate`
4. `pip install -r requirements.txt`

## HOW TO DEBUG

```bash
$ export PYTHONPATH=.
$ python ui/app.py
```

## HOW TO BUILD

```bash
$ python build.py ${versions}(3.0.0)
```

## HOW TO RELEASE

```bash
$ git tag ${version}
$ git push origin ${version}
```

## QUESTIONS

* 如果macos上执行python脚本遇到以下报错：

```
This program needs access to the screen. Please run with a
Framework build of python, and only when you are logged in
on the main display of your Mac.
```

可以将以下内容写入文件：`.env3/bin/python`

```bash
#!/bin/bash

# what real Python executable to use
PYVER=3.11
PYTHON=/System/Library/Frameworks/Python.framework/Versions/$PYVER/bin/python$PYVER

# find the root of the virtualenv, it should be the parent of the dir this script is in
ENV=`$PYTHON -c "import os; print os.path.abspath(os.path.join(os.path.dirname(\"$0\"), '..'))"`

# now run Python with the virtualenv set as Python's HOME
export PYTHONHOME=$ENV 
exec $PYTHON "$@"
```

并添加可以执行权限：`chmod 775 .env3/bin/python`
