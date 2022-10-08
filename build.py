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

"""打包成可执行文件
"""

import os
import sys

import qt4a


def main(version):
    qt4a_tools_path = qt4a.__path__[0] + "/androiddriver/tools"
    if "/" in version:
        # handle refs/tags/x.x.x.x
        version = version.split("/")[-1]
    version_items = version.split(".")
    for i in range(len(version_items)):
        version_items[i] = int(version_items[i])

    with open("version.py", "w") as fp:
        fp.write('version_info=u"%s"' % version)

    if sys.platform == "win32":
        version_file_path = "version_file.txt"
        with open(os.path.join("res", "file_version_info.txt"), "r") as fp:
            text = fp.read()
            text = text % {
                "main_ver": version_items[0],
                "sub_ver": version_items[1],
                "min_ver": version_items[2],
                "build_num": version_items[3] if len(version_items) > 3 else 0,
            }
        with open(version_file_path, "w") as fp:
            fp.write(text)
        cmdline = (
            "pyinstaller -F -w ui/app.py -n AndroidUISpy_v%s -i res/androiduispy.ico --add-data=%s;qt4a/androiddriver/tools --version-file %s"
            % (version, qt4a_tools_path, version_file_path)
        )
    else:
        cmdline = (
            "pyinstaller -F -w ui/app.py -n AndroidUISpy -i res/androiduispy.icns --add-data=%s:qt4a/androiddriver/tools"
            % qt4a_tools_path
        )

    os.system(cmdline)

    if sys.platform == "darwin":
        os.system(
            'hdiutil create /tmp/tmp.dmg -ov -volname "AndroidUISpy" -fs HFS+ -srcfolder "dist/AndroidUISpy.app"'
        )
        os.system("hdiutil convert /tmp/tmp.dmg -format UDZO -o dist/AndroidUISpy.dmg")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print >>sys.stderr, "usage: python build.py versions"
        exit()
    main(sys.argv[1])
