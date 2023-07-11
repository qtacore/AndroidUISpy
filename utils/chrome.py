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

"""Chrome相关操作
"""

import sys

from .logger import Log


class Chrome(object):
    """Chrome浏览器封装"""

    def __init__(self, handle):
        self._handle = handle

    @staticmethod
    def _get_browser_path():
        import sys, os

        if sys.platform == "win32":
            if sys.getwindowsversion()[0] >= 6:
                # Vista/Win7支持这个环境变量
                path = os.getenv("LOCALAPPDATA")
            else:
                # XP下则是位于这个路径
                path = os.getenv("USERPROFILE")
                path = os.path.join(path, r"Local Settings\Application Data")
            path = os.path.join(path, r"Google\Chrome\Application\chrome.exe")
            if not os.path.exists(path):
                path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
                if not os.path.exists(path):
                    path = (
                        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
                    )
            return path
        elif sys.platform == "darwin":
            chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
            if os.path.exists(chrome_path):
                return chrome_path
            return None
        else:
            raise NotImplementedError

    @staticmethod
    def open_url(url):
        """打开URL"""
        import time

        chrome_path = Chrome._get_browser_path()
        if sys.platform == "win32":
            import win32process, win32event, win32gui

            Log.i("Chrome", chrome_path)
            cmdline = [
                '"%s"' % chrome_path,
                url,
                "--user-data-dir=remote-profile_1113",
            ]  # , '--disk-cache-dir="%sqt4a_cache"' % chrome_path[:-10]
            processinfo = win32process.CreateProcess(
                None,
                " ".join(cmdline),
                None,
                None,
                0,
                0,
                None,
                None,
                win32process.STARTUPINFO(),
            )
            win32event.WaitForInputIdle(processinfo[0], 10000)
            time.sleep(2)
            return Chrome(win32gui.GetForegroundWindow())
        elif sys.platform == "darwin":
            import subprocess

            subprocess.Popen([chrome_path, url])

    def bring_to_front(self):
        """将窗口置前"""
        if sys.platform == "win32":
            import win32gui

            win32gui.SetForegroundWindow(self._handle)
        else:
            raise NotImplementedError

    def is_closed(self):
        """是否已关闭"""
        if sys.platform == "win32":
            import win32gui

            return not win32gui.IsWindow(self._handle)
        else:
            raise NotImplementedError

    def close(self):
        """关闭Chrome"""
        if sys.platform == "win32":
            import ctypes

            ctypes.windll.user32.PostMessageA(
                self._chrome_hwnd, win32con.WM_CLOSE, 0, 0
            )  # 使用win32api py2exe会报错
        else:
            raise NotImplementedError


if __name__ == "__main__":
    pass
