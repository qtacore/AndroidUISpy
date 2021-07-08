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

"""管理界面需要的各种数据
"""


class BaseManager(object):
    """Manager基类"""

    instance_dict = {}

    def __init__(self, device):
        self._device = device

    @classmethod
    def get_instance(cls, device):
        """获取实例"""
        key = "%s:%s" % (device._device_id, cls.__name__)
        if not key in cls.instance_dict:
            cls.instance_dict[key] = cls(device)
        return cls.instance_dict[key]

    def update(self):
        """刷新数据"""
        pass
