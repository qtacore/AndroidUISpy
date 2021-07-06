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

"""设备管理
"""

import os
import sys
import threading
import time

from qt4a.androiddriver import adb
from qt4a.androiddriver.androiddriver import copy_android_driver


class DeviceManager(object):
    """ """

    def __init__(self, hostname=None):
        if hostname == None:
            hostname = "127.0.0.1"
        self._hostname = hostname  # 设备主机名称，为空表示是本机
        self._port = 5037
        self._running = True
        self._callbacks = []
        t = threading.Thread(target=self.monitor_thread)
        t.setDaemon(True)
        t.start()

    def register_callback(self, on_device_inserted, on_device_removed):
        """注册回调

        :param on_device_inserted: 新设备插入回调
        :type  on_device_inserted: function
        :param on_device_removed:  设备移除回调
        :type  on_device_removed:  function
        """
        self._callbacks.append((on_device_inserted, on_device_removed))

    @property
    def hostname(self):
        """ """
        return self._hostname

    def get_device_list(self):
        """获取设备列表"""
        return adb.LocalADBBackend.list_device(self._hostname)

    def monitor_thread(self):
        """监控线程"""
        device_list = []
        while self._running:
            new_device_list = self.get_device_list()

            for it in new_device_list:
                if not it in device_list:
                    # 新设备插入
                    copy_android_driver(it)
                    for cb in self._callbacks:
                        cb[0](it)

            for it in device_list:
                if not it in new_device_list:
                    # 设备已移除
                    for cb in self._callbacks:
                        cb[1](it)

            device_list = new_device_list
            time.sleep(1)


if __name__ == "__main__":
    pass
