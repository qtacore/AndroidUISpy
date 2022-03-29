# Android控件探测器

本工具可用于探测Android设备中的应用控件，可代替`UIAutomator`等工具

使用限制：

* Root设备中可以探测任意应用的控件
* 非Root设备中只能探测debug应用的控件


## PREPARE ENVIRONMENT

1. `cd $project_root`
2. `virtualenv .env --python=python2.7`
3. Windows:  
    `.env\Scripts\activate.bat`  
    Others:  
    `source .env/bin/activate`
3. `pip install -r requirements.txt`


## HOW TO DEBUG

```bash
$ python ui/app.py
```

## HOW TO BUILD

```bash
$ python build.py ${versions}(2.5.1.0)
```

## HOW TO RELEASE

```bash
$ git tag ${version}
$ git push origin ${version}
```

## QUESTIONS

* 如果macos上执行python脚本遇到以下报错：


> This program needs access to the screen. Please run with a
Framework build of python, and only when you are logged in
on the main display of your Mac.


可以将以下内容写入文件：`.env/bin/python`

```
#!/bin/bash

# what real Python executable to use
PYVER=2.7
PYTHON=/System/Library/Frameworks/Python.framework/Versions/$PYVER/bin/python$PYVER

# find the root of the virtualenv, it should be the parent of the dir this script is in
ENV=`$PYTHON -c "import os; print os.path.abspath(os.path.join(os.path.dirname(\"$0\"), '..'))"`

# now run Python with the virtualenv set as Python's HOME
export PYTHONHOME=$ENV 
exec $PYTHON "$@"
```

并添加可以执行权限：`chmod 775 .env/bin/python`

