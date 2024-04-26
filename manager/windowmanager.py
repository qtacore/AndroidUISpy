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

"""窗口管理
"""

import re
from manager import BaseManager
from utils.logger import Log


class Window(object):
    """窗口类"""

    def __init__(self, win_manager, _id, hashcode, title):
        self._win_manager = win_manager
        self._id = _id
        self._hashcode = hashcode
        if not isinstance(title, str):
            title = title.decode("utf8")
        self._title = title
        self._attrs = {}

    def __str__(self):
        result = "<Window id=%d hashcode=0x%s title=%s " % (
            self._id,
            self._hashcode,
            self._title,
        )
        for attr in self._attrs:
            result += "%s=%s " % (attr, self._attrs[attr])
        result += ">"
        return result

    def __eq__(self, win):
        """ """
        if win == None:
            return False
        return self._hashcode == win.hashcode

    def __setitem__(self, key, val):
        self._attrs[key] = val
        if key in ("x", "y", "w", "h"):
            self._attrs[key] = int(self._attrs[key])

    @property
    def hashcode(self):
        return self._hashcode

    @property
    def position(self):
        x = y = 0
        if "x" in self._attrs:
            x = self._attrs["x"]
        if "y" in self._attrs:
            y = self._attrs["y"]
        return x, y

    @property
    def size(self):
        w = h = 0
        if "w" in self._attrs:
            w = self._attrs["w"]
        if "h" in self._attrs:
            h = self._attrs["h"]
        return w, h

    @property
    def title(self):
        if "/" in self._title:
            pkg, self._title = self._title.split("/")
            if self._title[0] == ".":
                self._title = pkg + self._title
        return self._title

    @property
    def package_name(self):
        """包名"""
        result = self._attrs.get("package")
        if result != None and result != "null":
            return result
        if "/" in self._title:
            return self._title.split("/")[0]
        attach_window = self.attached_window
        if attach_window:
            return attach_window.package_name
        return None

    @property
    def attached_window(self):
        """所依附的窗口"""
        return self._attrs.get("mAttachedWindow")

    def is_popup_window(self):
        """是否是弹出窗口"""
        if self._title == "SurfaceView":
            return False  # 暂不支持SurfaceView
        w, h = self.size
        if w == 0 or h == 0:
            return False
        if w < 20 or h < 20:
            return False
        if self.title in [
            "Heads",
            "StatusBar",
            "InputMethod",
            "NavigationBar",
            "KeyguardScrim",
            "com.android.launcher2.Launcher",
            "RecentsPanel",
        ]:
            return False
        if not "x" in self._attrs or not "y" in self._attrs:
            return False
        if self._attrs["x"] > 0 or self._attrs["y"] > 0:
            return True
        screen_width, screen_height = self._win_manager.get_screen_size()
        if (
            w >= screen_width
            and h >= screen_height - 100
            or w >= screen_height
            and h >= screen_width
        ):
            return False
        # TODO: 排除掉虚拟按键的高度
        return True


class WindowManager(BaseManager):
    """窗口管理"""

    def __init__(self, device):
        self._device = device
        self._current_window = None
        self._current_input_target = None
        self._window_list = []

    def _update_window_info(self, window):
        """更新窗口信息"""
        if window is not None:
            for win in self._window_list:
                if window == win:
                    for attr in win._attrs:
                        window[attr] = win._attrs[attr]
                    break

    def update(self):
        """刷新数据"""
        self._window_list = self._get_windows_data()
        for window in self._window_list:
            # 修复attached_window的部分信息
            self._update_window_info(window.attached_window)
        if self._current_window is not None:
            self._update_window_info(self._current_window)
        if self._current_input_target is not None:
            self._update_window_info(self._current_input_target)

    def get_screen_size(self):
        """获取屏幕大小"""
        w = h = 0
        for win in self.get_window_list():
            if win.title.endswith(".Launcher"):
                continue  # 桌面的高可能会包含虚拟机按键
            x, y = win.position
            if x != 0 or y != 0:
                continue
            w1, h1 = win.size
            if w1 > h1:
                w1, h1 = h1, w1
            if w1 > w:
                w = w1
            if h1 > h:
                h = h1
        return w, h

    def get_current_window(self):
        """当前拥有焦点的窗口"""
        if not self._window_list:
            self.update()
        return self._current_window

    def get_window_list(self, update=False):
        """ """
        if not self._window_list or update:
            self.update()
        return self._window_list

    def _get_windows_data(self):
        """获取windows数据并解析"""
        result = self._device.adb.run_shell_cmd("dumpsys window")
        result = result.replace("\r", "")
        # print result
        windows = []
        window = {}
        p1 = re.compile(r"^  Window #(\d+) Window{(\w{6,9}) (.*)}:$")
        p2 = re.compile(r"Window{(\w{6,9}) (u0 ){0,1}(\S+).*}")
        # p2 =re.compile(r'Window{(\w+) (u0 ){0,1}(\S+).*}')
        p3 = re.compile(
            r"mShownFrame=\[([-\d\.]+),([-\d\.]+)\]\[([-\d\.]+),([-\d\.]+)\]"
        )
        for line in result.split("\n")[1:]:
            # print repr(line)
            ret = p1.match(line)
            if ret:
                title = ret.group(3)
                if " " in title:
                    items = title.split(" ")
                    if "u0" == items[0]:
                        title = items[1]
                    else:
                        title = items[0]
                window = Window(
                    self, int(ret.group(1)), ret.group(2), title
                )  # 此逻辑可能有bug
                windows.append(window)
            elif "mHoldScreenWindow" in line:
                ret = p2.search(line)
                if ret:
                    title = ret.group(3)
                    self._current_window = Window(self, 0, ret.group(1), title)
                else:
                    Log.w("WindowManager", line)
            elif "mObscuringWindow" in line:
                ret = p2.search(line)
                if ret:
                    title = ret.group(3)
                    self._current_window = Window(self, 0, ret.group(1), title)
                else:
                    Log.w("WindowManager", line)
            elif "mCurrentFocus" in line:
                ret = p2.search(line)
                if ret:
                    title = ret.group(3)
                    self._current_window = Window(self, 0, ret.group(1), title)
                else:
                    Log.w("WindowManager", line)
                    self._current_window = None
            elif "mInputMethodTarget" in line or "imeInputTarget" in line:
                ret = p2.search(line)
                self._current_input_target = Window(
                    self,
                    0,
                    ret.group(1),
                    ret.group(2)
                    if ret.group(2) and len(ret.group(2)) > 5
                    else ret.group(3),
                )
            elif line.startswith("    "):
                if "mShownFrame" in line:
                    ret = p3.search(line)
                    window["x"] = int(float(ret.group(1)))
                    window["y"] = int(float(ret.group(2)))
                elif "mAttachedWindow" in line:
                    ret = p2.search(line)
                    window["mAttachedWindow"] = Window(
                        self,
                        0,
                        ret.group(1),
                        ret.group(2)
                        if ret.group(2) and len(ret.group(2)) > 5
                        else ret.group(3),
                    )
                else:
                    items = line.split(" ")
                    for item in items:
                        if "=" not in item:
                            continue
                        pos = item.find("=")
                        key = item[:pos]
                        val = item[pos + 1 :]
                        if key in ["package", "w", "h"]:
                            window[key] = val
            else:
                pass

        return windows


if __name__ == "__main__":
    pass
