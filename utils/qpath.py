# -*- coding: utf-8 -*-
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

"""
qpath模块

详见QPath类说明
"""

import re


class EnumQPathKey(object):
    MAX_DEPTH = "MAXDEPTH"
    INSTANCE = "INSTANCE"
    UI_TYPE = "UITYPE"


class EnumUIType(object):
    WIN = "Win"
    GF = "GF"
    QPCtrl = "QPCtrl"


class QPathError(Exception):
    """QPath异常类定义"""

    pass


class QPath(object):
    """Query Path类，使用QPath字符串定位UI控件"""

    PROPERTY_SEP = "&&"
    OPERATORS = ["=", "~="]
    MATCH_FUNCS = {}
    MATCH_FUNCS["="] = lambda x, y: x == y
    MATCH_FUNCS["~="] = lambda string, pattern: re.search(pattern, string) != None
    CONTROL_TYPES = {}

    def __init__(self, qpath_string):
        """Contructor

        :type qpath_string: string
        :param qpath_string: QPath字符串
        """
        # if not isinstance(qpath_string, str):
        #     raise QPathError("输入的QPath(%s)不是字符串!" % (qpath_string))
        self._strqpath = qpath_string
        self._path_sep, self._parsed_qpath = self._parse(qpath_string)
        self._error_qpath = None

    def _parse_property(self, prop_str):
        """解析property字符串，返回解析后结构

        例如将 "ClassName='Dialog' " 解析返回 {ClassName: ['=', 'Dialog']}
        """

        parsed_pattern = "(\w+)\s*([=~!<>]+)\s*(.+)"
        match_object = re.match(parsed_pattern, prop_str)
        if match_object is None:
            raise QPathError("属性(%s)不符合QPath语法" % prop_str)
        prop_name, operator, prop_value = match_object.groups()
        prop_value = eval(prop_value)
        if not operator in self.OPERATORS:
            raise QPathError("QPath不支持操作符：%s" % operator)
        return {prop_name: [operator, prop_value]}

    def _parse(self, qpath_string):
        """解析qpath，并返回QPath的路径分隔符和解析后的结构

        将例如"| ClassName='Dialog' && Caption~='SaveAs' | UIType='GF' && ControlID='123' && Instanc='-1'"
        的QPath解析为下面结构：[{'ClassName': ['=', 'Dialog'], 'Caption': ['~=', 'SaveAs']}, {'UIType': ['=', 'GF'], 'ControlID': ['=', '123'], 'Instance': ['=', '-1']}]

        :param qpath_string: qpath 字符串
        :return: (seperator, parsed_qpath)
        """
        qpath_string = qpath_string.strip()
        seperator = qpath_string[0]
        locators = qpath_string[1:].split(seperator)

        parsed_qpath = []
        for locator in locators:
            props = locator.split(self.PROPERTY_SEP)
            parsed_locators = {}
            for prop_str in props:
                prop_str = prop_str.strip()
                if len(prop_str) == 0:
                    raise QPathError("%s 中含有空的属性。" % locator)
                parsed_props = self._parse_property(prop_str)
                parsed_locators.update(parsed_props)
            parsed_qpath.append(parsed_locators)
        return seperator, parsed_qpath

    def __str__(self):
        """返回格式化后的QPath字符串"""
        qpath_str = ""
        for locator in self._parsed_qpath:
            qpath_str += self._path_sep + " "
            delimit_str = " " + self.PROPERTY_SEP + " "
            locator_str = delimit_str.join(
                [
                    "%s %s '%s'" % (key, locator[key][0], locator[key][1])
                    for key in locator
                ]
            )
            qpath_str += locator_str
        return qpath_str

    def getErrorPath(self):
        """返回最后一次QPath.search搜索未能匹配的路径

        :rtype: string
        """
        if self._error_qpath:
            props = self._error_qpath[0]
            delimit_str = " " + self.PROPERTY_SEP + " "
            return delimit_str.join(
                ["%s %s '%s'" % (key, props[key][0], props[key][1]) for key in props]
            )


if __name__ == "__main__":
    pass
