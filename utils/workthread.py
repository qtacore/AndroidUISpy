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

"""工作线程
"""

import time
import threading

try:
    from Queue import Queue
except ImportError:
    from queue import Queue


class Task(object):
    """任务"""

    def __init__(self, func, *args, **kwargs):
        self._func = func
        self._args = args
        self._kwargs = kwargs

    def run(self):
        return self._func(*self._args, **self._kwargs)


class WorkThread(object):
    """ """

    def __init__(self):
        self._thread = threading.Thread(target=self._work_thread)
        self._thread.setDaemon(True)
        self._run = True
        self._task_queue = Queue()
        self._thread.start()

    def _work_thread(self):
        """ """
        while self._run:
            if self._task_queue.empty():
                time.sleep(0.1)
                continue
            task = self._task_queue.get()
            try:
                task.run()
            except:
                import traceback

                traceback.print_exc()

    def post_task(self, func, *args, **kwargs):
        """发送任务"""
        task = Task(func, *args, **kwargs)
        self._task_queue.put(task)
