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

"""控件管理
"""

import os
import re
import json
import time

from qt4a.androiddriver.util import ControlAmbiguousError

from manager import BaseManager
from .activitymanager import ActivityManager
from .windowmanager import WindowManager
from utils.logger import Log


class EnumWebViewType(object):
    """WebView类型"""

    NotWebView = 0
    SystemWebView = 1
    X5WebView = 2
    XWalkWebView = 3


class ControlManager(BaseManager):
    """控件管理"""

    def __init__(self, device):
        self._device = device
        self._activity_manager = ActivityManager.get_instance(device)
        self._window_manager = WindowManager.get_instance(device)
        self._driver_dict = {}

    def _get_driver(self, process_name):
        """获取AndroidDriver实例"""
        from qt4a.androiddriver.androiddriver import AndroidDriver

        if not process_name in self._driver_dict:
            driver = AndroidDriver.create(process_name, self._device)
            self._driver_dict[process_name] = driver
        return self._driver_dict[process_name]

    def get_driver(self, window_title):
        """获取AndroidDriver实例"""
        process_name = self._get_window_process(window_title)
        return self._get_driver(process_name)

    def update(self):
        """ """
        self._activity_manager.update()
        self._window_manager.update()

    def _get_window_process(self, window_hashcode_or_title):
        """获取窗口所在的进程名"""
        from .windowmanager import Window

        target_window = None
        pattern = re.compile(r"^\w{6,8}$")
        if isinstance(window_hashcode_or_title, Window):
            target_window = window_hashcode_or_title
            if target_window.attached_window != None:
                target_window = target_window.attached_window
        else:
            is_hashcode = pattern.match(window_hashcode_or_title) != None
            if window_hashcode_or_title == "StatusBar":
                return "com.android.systemui"
            for window in self._window_manager.get_window_list():
                if (is_hashcode and window.hashcode == window_hashcode_or_title) or (
                    not is_hashcode and window.title == window_hashcode_or_title
                ):
                    if window.attached_window != None:
                        target_window = window.attached_window
                    else:
                        target_window = window
                    break
            else:
                raise RuntimeError(u"查找窗口： %s 失败" % window_hashcode_or_title)

        for activity in self._activity_manager.get_activity_list():
            if activity.name == target_window.title:
                return activity.process_name

    def _get_control_tree(self, process_name):
        """获取指定进程中的所有控件树

        :param process_name: 进程名
        :type process_name:  string
        """
        driver = self._get_driver(process_name)
        Log.i("ControlManager", "get control tree in process %s" % process_name)
        result = driver._get_control_tree("", -1)
        Log.i("ControlManager", "get control tree complete")
        # for key in result.keys():
        for key in list(result):
            if not result[key]:
                result.pop(key)
                continue
            if not "Visible" in result[key]:
                print(result[key])
            if not result[key]["Visible"]:
                # 过滤掉不可见的窗口
                print("ignor window %s" % key)
                result.pop(key)
        pattern = re.compile(r"^(.+)#(\d+)$")
        output_result = {}  # 窗口名相同的放到list中
        # for key in result.keys():
        for key in list(result):
            window_title = key
            ret = pattern.match(key)
            if ret:
                window_title = ret.group(1)
            if not window_title in output_result:
                output_result[window_title] = [process_name]
            output_result[window_title].append(result.pop(key))

        return output_result

    def get_control_tree(self):
        """获取当前需要获取的所有控件树列表"""
        process_list = []  # 已经抓取过控件树的进程列表
        self._window_manager.update()
        self._activity_manager.update()
        current_window = self._window_manager.get_current_window()
        if current_window == None:
            # 获取当前Activity
            current_activity = self._device._send_command("GetCurrentActivity")
            self._window_manager.update()
            for window in self._window_manager.get_window_list():
                if window.title == current_activity:
                    current_window = window
                    break
            else:
                raise RuntimeError("find window %s failed" % current_activity)
        package_name = current_window.package_name  # 只获取该包名对应的窗口
        if package_name == None:
            raise RuntimeError("get %s package name failed" % current_window)

        result = {}

        def update_control_tree(process_name):
            """更新控件树"""
            try:
                control_tree = self._get_control_tree(process_name)
            except:
                Log.ex("ControlManager", "get control tree in %s failed" % process_name)
                return
            result.update(control_tree)  # 相同窗口名的窗口必然在同一进程中，所以不会冲突
            process_list.append(process_name)

        current_process = self._get_window_process(current_window)

        if current_process == None:
            Log.w("ControlManager", "get process of %s failed" % current_window)
            current_process = package_name
        result = self._get_control_tree(current_process)  # 先获取当前窗口所在进程中的所有控件树
        process_list.append(current_process)

        ################################################
        #         if not package_name in process_list:
        #             control_tree = self._get_control_tree(package_name)
        #             result.update(control_tree)  # 相同窗口名的窗口必然在同一进程中，所以不会冲突
        #             process_list.append(package_name)
        ################################################

        for window in self._window_manager.get_window_list():
            # print window.title, window.package_name, window._attrs
            if window.package_name != package_name and not window.is_popup_window():
                continue  # 过滤掉非预期的窗口
            if (
                window.package_name == "com.android.systemui"
                and not self._device.adb.is_rooted()
            ):
                continue  # 过滤掉非root手机中的部分应用
            if window.title == "Toast":
                if window.title in result:
                    continue
                # 不在当前进程中，尝试在主进程中查找
                if not package_name in process_list:
                    update_control_tree(package_name)
                    if window.title in result:
                        continue
                # 遍历所有进程抓取Toast控件
                target_process_list = []
                all_process_list = self._device.adb.list_process()
                for process in all_process_list:
                    if (
                        process["proc_name"].startswith(package_name + ":")
                        and not process["proc_name"] in process_list
                    ):
                        target_process_list.append(process["proc_name"])
                for process_name in target_process_list:
                    update_control_tree(process_name)
                    if window.title in result:
                        break
            elif window.is_popup_window():
                # 一般弹出窗口都是需要探测的
                print("popup", window)
                process_name = self._get_window_process(window)
                # print process_name
                if process_name == None:
                    Log.w(
                        "ControlManager",
                        "find process of window %s failed" % window.title,
                    )
                    for it in self._device.adb.list_process():
                        if it["proc_name"] == window.package_name or it[
                            "proc_name"
                        ].startswith(window.package_name + ":"):
                            if not it["proc_name"] in process_list:
                                update_control_tree(it["proc_name"])
                    continue
                if process_name in process_list:
                    continue
                update_control_tree(process_name)

        return result

    def get_control(self, window_title, parent, qpath, get_err_pos=False):
        """查找控件"""
        from utils.qpath import QPath

        # if isinstance(qpath, str): qpath = qpath.encode('utf8')
        qpath = QPath(qpath)

        process_name = self._get_window_process(window_title)
        driver = self._get_driver(process_name)
        try:
            return driver.get_control(
                window_title, parent, qpath._parsed_qpath, get_err_pos
            )
        except ControlAmbiguousError as e:
            repeat_list = []
            for line in e.args[0].split("\n")[1:]:
                if not line:
                    continue
                pos = line.find("[")
                pos2 = line.find("]", pos)
                repeat_list.append(line[pos + 1 : pos2])
                return [int(item, 16) for item in repeat_list]
            else:
                raise e

    def set_control_text(self, window_title, hashcode, text):
        """设置控件文本"""
        process_name = self._get_window_process(window_title)
        driver = self._get_driver(process_name)
        driver.set_control_text(hashcode, text)

    def get_control_type(self, window_title, hashcode):
        """获取控件类型，包含基类类型"""
        process_name = self._get_window_process(window_title)
        driver = self._get_driver(process_name)
        result = driver.get_control_type(hashcode, True)
        if not isinstance(result, list):
            return [result]
        return result

    def enable_webview_debugging(self, process_name, hashcode):
        """开启WebView调试开关"""
        driver = self._get_driver(process_name)
        driver.set_webview_debugging_enabled(hashcode, True)

    def open_webview_debug(
        self, process_name, hashcode, webview_type, multi_page_callback
    ):
        """开启WebView调试"""
        from utils.logger import Log
        from webinspect.debugging_tool import WebViewDebuggingTool
        from qt4a.androiddriver.util import get_process_name_hash
        from utils.chrome import Chrome

        # process_name = self._get_window_process(window_title)
        pid = self._device.adb.get_pid(process_name)
        webview = self.get_webview(process_name, hashcode)
        webview_type = webview.get_webview_type()
        debugging_url = None
        service_name = ""
        if webview_type == EnumWebViewType.XWalkWebView:
            debugging_tool = WebViewDebuggingTool(self._device)
            if not debugging_tool.is_webview_debugging_opened(process_name):
                driver = self._get_driver(process_name)
                driver.call_static_method(
                    "org.xwalk.core.internal.XWalkPreferencesBridge",
                    "setValue",
                    hashcode,
                    "",
                    "remote-debugging",
                    True,
                )
            debugging_url = debugging_tool.get_debugging_url(
                process_name, multi_page_callback, None
            )
            service_name = "xweb_devtools_remote_%d" % pid
        elif (
            webview_type == EnumWebViewType.X5WebView
            or self._device.adb.get_sdk_version() >= 19
        ):
            # 支持Chrome远程调试
            debugging_tool = WebViewDebuggingTool(self._device)
            if not debugging_tool.is_webview_debugging_opened(process_name):
                self.enable_webview_debugging(process_name, hashcode)
            # webview.eval_script([], (ChromeInspectWebSocket.base_script % 'false') + ';qt4a_web_inspect._inspect_mode=true;')

            debugging_url = debugging_tool.get_debugging_url(
                process_name, multi_page_callback, None
            )
            service_name = "webview_devtools_remote_%d" % pid

        if debugging_url == None:
            return None
        pos = debugging_url.find("?ws=")
        if pos <= 0:
            raise RuntimeError("Invalid debugging url: %s" % debugging_url)
        port = get_process_name_hash(process_name, self._device._device_id)
        port = self._device.adb.forward(port, service_name, "localabstract")
        debugging_url = (
            debugging_url[: pos + 4]
            + ("127.0.0.1:%d" % port)
            + debugging_url[pos + 4 :]
        )
        return Chrome.open_url(debugging_url)

    def get_webview(self, process_name, hashcode):
        """获取WebView实例"""
        # process_name = self._get_window_process(window_title)
        driver = self._get_driver(process_name)
        return WebView(driver, hashcode)


class WebView(object):
    """WebView功能封装"""

    def __init__(self, driver, hashcode):
        self._driver = driver
        self._hashcode = hashcode
        self._type = self.get_webview_type()

    @staticmethod
    def is_webview(control_manager, window_title, hashcode):
        """是否是WebView控件"""
        webview = WebView(control_manager.get_driver(window_title), hashcode)
        return webview._type != EnumWebViewType.NotWebView

    def get_webview_type(self):
        """获取控件WebView类型"""
        result = self._driver.get_control_type(self._hashcode, True)
        if not isinstance(result, list):
            result = [result]

        for tp in result:
            if tp.startswith("org.xwalk.core.internal.XWalkContent$"):
                return EnumWebViewType.XWalkWebView
            elif tp in ["org.xwalk.core.internal.XWalkViewBridge"]:
                return EnumWebViewType.XWalkWebView
            elif tp in [
                "com.tencent.smtt.webkit.WebView",
                "com.tencent.tbs.core.webkit.WebView",
            ]:
                return EnumWebViewType.X5WebView
            elif tp == "android.webkit.WebView":
                return EnumWebViewType.SystemWebView
        return EnumWebViewType.NotWebView

    def eval_script(self, frame_xpaths, script):
        """执行JavaScript代码"""
        return self._driver.eval_script(self._hashcode, frame_xpaths, script)


if __name__ == "__main__":
    pass
