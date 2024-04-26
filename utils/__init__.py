# -*- coding: UTF-8 -*-
#
# Tencent is pleased to support the open source community by making QTA available.
# Copyright (C) 2016THL A29 Limited, a Tencent company. All rights reserved.
# Licensed under the BSD 3-Clause License (the "License"); you may not use this
# file except in compliance with the License. You may obtain a copy of the License at
#
# https://opensource.org/licenses/BSD-3-Clause
#
# Unless required by applicable law or agreed to in writing, software distributed
# under the License is distributed on an "AS IS" basis, WITHOUT WARRANTIES OR CONDITIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.
#

"""公共模块
"""

import os, sys
import threading
from .logger import Log


def get_driver_root_path():
    """获取测试桩根目录"""
    if hasattr(sys, "_MEIPASS"):
        print(sys._MEIPASS)
    elif not hasattr(sys, "frozen"):
        return os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "qt4a",
            "androiddriver",
            "tools",
        )
    else:
        return os.path.join(os.environ["temp"], "tools_%d" % os.getpid())


def run_in_thread(func):
    """在线程中执行函数"""
    def safe_func(*args):
        try:
            Log.i(func.__name__, "Invoke method in thread")
            return func(*args)
        except Exception:
            Log.ex(func.__name__, "Invoke method failed")

    def wrap_func(*args):
        t = threading.Thread(target=safe_func, args=args)
        t.setDaemon(True)
        t.start()

    return wrap_func


if __name__ == "__main__":
    pass
