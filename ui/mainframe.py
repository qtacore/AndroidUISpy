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

import io
import os
import sys
import threading
import time

import wx

from PIL import Image
from qt4a.androiddriver.adb import ADB
from qt4a.androiddriver.devicedriver import DeviceDriver
from qt4a.androiddriver.util import ControlExpiredError

from manager.controlmanager import EnumWebViewType, ControlManager, WebView
from manager.devicemanager import DeviceManager
from manager.windowmanager import WindowManager
from utils import run_in_thread
from utils.logger import Log
from utils.workthread import WorkThread

default_size = [1360, 800]

try:
    from version import version_info
except ImportError:
    version_info = "v3.0.0"


def create(parent):
    return MainFrame(parent)


def run_in_main_thread(func):
    """主线程运行"""

    def wrap_func(*args, **kwargs):
        wx.CallAfter(func, *args, **kwargs)

    return wrap_func


class MainFrame(wx.Frame):
    """ """

    def __init__(self, parent):
        self._window_size = self._get_window_size()
        self._init_ctrls(parent)
        self._enable_inspect = False
        self._tree_list = []
        self._select_device = None
        self._device_host = None
        self._scale_rate = 1  # 截图缩放比例
        self._mouse_move_enabled = False
        self._image_path = None
        self._device_manager = DeviceManager()
        self._device_manager.register_callback(
            self.on_device_inserted, self.on_device_removed
        )
        self._work_thread = WorkThread()
        self.Bind(wx.EVT_SIZE, self.on_resize)

    def _get_window_size(self):
        width, height = default_size
        screen_width, screen_height = wx.DisplaySize()
        Log.i(
            self.__class__.__name__,
            "Screen size: %d x %d" % (screen_width, screen_height),
        )
        if screen_height > 1000:
            height = screen_height - 100
            width = min(screen_width - 100, default_size[0] * height // default_size[1])
        Log.i(self.__class__.__name__, "Window size: %d x %d" % (width, height))
        return width, height

    def _init_ctrls(self, prnt):
        # generated method, don't edit

        wx.Frame.__init__(
            self,
            id=wx.ID_ANY,
            name="",
            parent=prnt,
            pos=wx.Point(0, 0),
            size=wx.Size(*self._window_size),
            style=wx.DEFAULT_FRAME_STYLE,
            title="AndroidUISpy " + version_info,
        )

        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.statusbar = self.CreateStatusBar()
        # 将状态栏分割为3个区域,比例为1:2:3
        self.statusbar.SetFieldsCount(3)
        self.statusbar.SetStatusWidths([-3, -2, -1])

        self.panel = wx.Panel(
            self, size=(self._window_size[0] - 20, self._window_size[1] - 70)
        )
        self.font = wx.SystemSettings.GetFont(wx.SYS_SYSTEM_FONT)
        self.font.SetPointSize(9)

        main_panel_width = 900
        main_panel_height = self.panel.Size[1]
        self.main_panel = wx.Panel(
            self.panel, size=(main_panel_width, main_panel_height)
        )

        device_panel_height = 90
        property_panel_height = 130
        device_panel = wx.Panel(
            self.main_panel, size=(main_panel_width, device_panel_height)
        )
        self._init_device_panel(device_panel)

        self._tree_panel_width = main_panel_width
        self._tree_panel_height = (
            main_panel_height - device_panel_height - property_panel_height
        )
        self.tree_panel = wx.Panel(
            self.main_panel,
            pos=(0, device_panel_height),
            size=(self._tree_panel_width, self._tree_panel_height),
        )

        self.property_panel = wx.Panel(
            self.main_panel,
            pos=(0, main_panel_height - property_panel_height),
            size=(main_panel_width, property_panel_height),
        )
        self._init_property_panel(self.property_panel)

        self.screen_panel = wx.Panel(
            self.panel,
            pos=(main_panel_width, 5),
            size=(self.panel.Size[0] - main_panel_width, self.main_panel.Size[1]),
        )
        # self.screen_panel.SetBackgroundColour(wx.BLUE)
        self._init_screen_panel(self.screen_panel)

    def _init_device_panel(self, panel):
        self.btn_inspect = wx.Button(
            panel, label="+", name="btn_inspect", pos=(5, 5), size=wx.Size(20, 20)
        )
        self.btn_inspect.SetFont(self.font)
        self.btn_inspect.Bind(wx.EVT_BUTTON, self.on_inspect_btn_click)
        self.btn_inspect.Enable(False)

        wx.StaticText(panel, label="设备ID:", pos=(40, 7))
        self.cb_device = wx.ComboBox(panel, wx.ID_ANY, pos=(100, 5), size=(200, 20))
        self.cb_device.Bind(wx.EVT_COMBOBOX, self.on_select_device)

        self.btn_refresh = wx.Button(
            panel, label="刷新", name="btn_refresh", pos=(310, 5), size=(50, 20)
        )
        self.btn_refresh.Enable(False)
        self.btn_refresh.Bind(wx.EVT_BUTTON, self.on_refresh_btn_click)

        wx.StaticText(self.panel, label="选择Activity: ", pos=(400, 7))
        self.cb_activity = wx.ComboBox(
            panel, id=wx.ID_ANY, pos=(500, 5), size=(300, 20)
        )
        self.cb_activity.Bind(wx.EVT_COMBOBOX, self.on_select_window)
        self.cb_activity.Bind(wx.EVT_COMBOBOX_DROPDOWN, self.on_window_list_dropdown)

        self.btn_getcontrol = wx.Button(
            panel, label="获取控件", name="btn_getcontrol", pos=(810, 5), size=(75, 20)
        )
        self.btn_getcontrol.Bind(wx.EVT_BUTTON, self.on_getcontrol_btn_click)
        self.btn_getcontrol.Enable(False)

        wx.StaticBox(panel, label="高级选项", pos=(5, 30), size=(890, 50))
        self.rb_local_device = wx.RadioButton(
            panel, label="本地设备", pos=(10, 52), size=wx.DefaultSize
        )
        self.rb_local_device.SetValue(True)
        self.rb_local_device.Bind(wx.EVT_RADIOBUTTON, self.on_local_device_selected)

        self.rb_remote_device = wx.RadioButton(
            panel, label="远程设备", pos=(90, 52), size=wx.DefaultSize
        )
        self.rb_remote_device.Bind(wx.EVT_RADIOBUTTON, self.on_remote_device_selected)

        wx.StaticText(
            panel, label="远程设备主机名: ", pos=(160, 52), size=wx.DefaultSize
        )
        self.tc_dev_host = wx.TextCtrl(panel, pos=(255, 50), size=(150, 20))
        self.tc_dev_host.Enable(False)
        self.tc_dev_host.SetToolTip(wx.ToolTip("输入要调试设备所在的主机名"))
        self.btn_set_device_host = wx.Button(
            panel, label="确定", pos=(410, 50), size=wx.Size(60, 20)
        )
        self.btn_set_device_host.Enable(False)
        self.btn_set_device_host.Bind(wx.EVT_BUTTON, self.on_set_device_host_btn_click)

        self.cb_auto_refresh = wx.CheckBox(
            panel, label="自动刷新屏幕", pos=(500, 52), size=wx.DefaultSize
        )
        self.cb_auto_refresh.Bind(wx.EVT_CHECKBOX, self.on_auto_fresh_checked)
        wx.StaticText(panel, label="刷新频率: ", pos=(610, 52), size=wx.DefaultSize)
        self.tc_refresh_interval = wx.TextCtrl(
            panel, pos=(670, 50), size=wx.Size(30, 20)
        )
        self.tc_refresh_interval.SetValue("1")
        wx.StaticText(panel, label="秒", pos=(710, 52), size=wx.DefaultSize)

        self.refresh_timer = wx.Timer(self)
        self.Bind(
            wx.EVT_TIMER, self.on_refresh_timer, self.refresh_timer
        )  # 绑定一个计时器

    def _init_property_panel(self, panel):
        wx.StaticBox(
            panel,
            label="控件属性",
            pos=(5, 5),
            size=(panel.Size[0] - 10, panel.Size[1] - 4),
        )
        wx.StaticText(panel, label="ID", pos=(15, 27), size=wx.DefaultSize)
        wx.StaticText(panel, label="Type", pos=(15, 52), size=wx.DefaultSize)
        wx.StaticText(panel, label="Visible", pos=(15, 77), size=wx.DefaultSize)
        wx.StaticText(panel, label="Text", pos=(15, 102), size=wx.DefaultSize)

        self.tc_id = wx.TextCtrl(panel, pos=(65, 25), size=(120, 20))
        self.tc_type = wx.TextCtrl(panel, pos=(65, 50), size=(120, 20))
        self.tc_visible = wx.TextCtrl(panel, pos=(65, 75), size=(120, 20))
        self.tc_text = wx.TextCtrl(panel, pos=(65, 100), size=(120, 20))
        self.tc_text.Enable(False)
        self.tc_text.Bind(wx.EVT_TEXT, self.on_node_text_changed)

        wx.StaticText(panel, label="HashCode", pos=(210, 27), size=wx.DefaultSize)
        wx.StaticText(panel, label="Rect", pos=(210, 52), size=wx.DefaultSize)
        wx.StaticText(panel, label="Enabled", pos=(210, 77), size=wx.DefaultSize)
        self.btn_set_text = wx.Button(
            panel, label="修改文本", pos=(190, 100), size=(70, 20)
        )
        self.btn_set_text.Enable(False)
        self.btn_set_text.Bind(wx.EVT_BUTTON, self.on_set_text_btn_click)
        self.cb_show_hex = wx.CheckBox(panel, label="显示16进制", pos=(280, 102))

        self.tc_hashcode = wx.TextCtrl(panel, pos=(280, 25), size=(120, 20))
        self.tc_rect = wx.TextCtrl(panel, pos=(280, 50), size=(120, 20))
        self.tc_enable = wx.TextCtrl(panel, pos=(280, 75), size=(120, 20))

        wx.StaticText(panel, label="Clickable", pos=(420, 27), size=wx.DefaultSize)
        wx.StaticText(panel, label="Checkable", pos=(420, 52), size=wx.DefaultSize)
        wx.StaticText(panel, label="Checked", pos=(420, 77), size=wx.DefaultSize)
        self.tc_clickable = wx.TextCtrl(panel, pos=(490, 25), size=(120, 20))
        self.tc_checkable = wx.TextCtrl(panel, pos=(490, 50), size=(120, 20))
        self.tc_checked = wx.TextCtrl(panel, pos=(490, 75), size=(120, 20))

        wx.StaticText(panel, label="ProcessName", pos=(640, 27), size=wx.DefaultSize)
        wx.StaticText(panel, label="Descriptions", pos=(640, 52), size=wx.DefaultSize)
        self.tc_process_name = wx.TextCtrl(panel, pos=(730, 25), size=(150, 20))
        self.tc_desc = wx.TextCtrl(panel, pos=(730, 50), size=(150, 20))

    def _init_screen_panel(self, panel):
        self.image = wx.StaticBitmap(panel)
        self.image.Bind(wx.EVT_MOUSE_EVENTS, self.on_mouse_move)

        self.mask_panel = CanvasPanel(parent=panel)
        self.mask_panel.Bind(wx.EVT_MOUSE_EVENTS, self.on_mouse_move)

    def on_close(self, event):
        """ """
        import atexit

        atexit._exithandlers = []  # 禁止退出时弹出错误框
        event.Skip()

    def on_resize(self, event):
        prev_window_size = self._window_size
        window_size = self.GetSize()
        if (
            abs(window_size[0] - prev_window_size[0]) <= 2
            and abs(window_size[1] - prev_window_size[1]) <= 2
        ):
            event.Skip()
            return

        if window_size[0] < default_size[0] or window_size[1] < default_size[1]:
            self.SetSize(
                (
                    max(window_size[0], default_size[0]),
                    max(window_size[1], default_size[1]),
                )
            )
            event.Skip()
            return

        self._window_size = window_size
        width_delta = self._window_size[0] - prev_window_size[0]
        height_delta = self._window_size[1] - prev_window_size[1]
        self.panel.SetSize(
            (self.panel.Size[0] + width_delta, self.panel.Size[1] + height_delta)
        )
        if height_delta:
            self.main_panel.SetSize(
                (self.main_panel.Size[0], self.main_panel.Size[1] + height_delta)
            )
            self.tree_panel.SetSize(
                (self.tree_panel.Size[0], self.tree_panel.Size[1] + height_delta)
            )
            self.tree.SetSize((self.tree.Size[0], self.tree.Size[1] + height_delta))
            self.property_panel.SetPosition(
                (0, self.property_panel.Position[1] + height_delta)
            )
        self.screen_panel.SetSize(
            (self.panel.Size[0] - self.main_panel.Size[0], self.main_panel.Size[1])
        )

        if self._image_path and os.path.isfile(self._image_path):
            image = Image.open(self._image_path)
            self._show_image(image)

        event.Skip()

    def on_select_window(self, event):
        """选择了一个窗口"""
        window_title = self.cb_activity.GetValue()
        if window_title.endswith(" "):
            window_title = window_title.strip()
            run_in_main_thread(self.cb_activity.SetLabelText)(window_title)

    def on_window_list_dropdown(self, event):
        """ """
        cur_sel = self.cb_activity.GetSelection()
        self.cb_activity.Select(cur_sel)

    def on_device_inserted(self, device_name):
        """新设备插入回调"""
        self.statusbar.SetStatusText("设备：%s 已插入" % device_name, 0)
        self.cb_device.Append(device_name)
        if self.cb_device.GetSelection() < 0:
            self.cb_device.SetSelection(0)
            self.on_select_device(None)

    def on_device_removed(self, device_name):
        """设备移除回调"""
        self.statusbar.SetStatusText("设备：%s 已断开" % device_name, 0)
        for index, it in enumerate(self.cb_device.Items):
            if it == device_name:
                self.cb_device.Delete(index)
                break

    @run_in_main_thread
    def on_select_device(self, event):
        """选中的某个设备"""
        new_dev = self.cb_device.GetValue()
        if new_dev != self._select_device:
            self._select_device = new_dev
            device_id = self._select_device
            if self._device_host:
                device_id = self._device_host + ":" + device_id
            self._device = DeviceDriver(ADB.open_device(device_id))
            self.statusbar.SetStatusText("当前设备：%s" % self._select_device, 0)
            for tree in self._tree_list:
                # 先删除之前创建的控件树
                tree["root"] = None
                tree["tree"].DeleteAllItems()
                tree["tree"].Destroy()
            self._tree_list = []
            self._tree_idx = 0
            self.image.Hide()
            self.cb_activity.SetValue("")
            self._window_manager = WindowManager.get_instance(self._device)
            self._control_manager = ControlManager.get_instance(self._device)
            wx.CallLater(
                1000, lambda: self.on_getcontrol_btn_click(None)
            )  # 自动获取控件树

        self.btn_refresh.Enable(True)
        self.btn_getcontrol.Enable(True)

    def on_getcontrol_btn_click(self, event):
        """点击获取控件按钮"""
        self.btn_getcontrol.Enable(False)
        if not self.cb_activity.GetValue():
            # 先刷新窗口列表
            self.on_refresh_btn_click(None)

        if self.cb_activity.GetValue() == "Keyguard":
            # 锁屏状态
            dlg = wx.MessageDialog(
                self,
                "设备：%s 处于锁屏状态，请手动解锁后点击OK按钮"
                % self.cb_device.GetValue(),
                "提示",
                style=wx.YES_NO | wx.YES_DEFAULT | wx.ICON_QUESTION,
            )
            result = dlg.ShowModal()
            if result == wx.ID_YES:
                self.on_refresh_btn_click(None)
            dlg.Destroy()

        self.statusbar.SetStatusText("正在获取控件树……", 0)

        def _update_control_tree():
            time0 = time.time()
            try:
                controls_dict = (
                    self._control_manager.get_control_tree()
                )  # self.cb_activity.GetValue().strip(), index
                if not controls_dict:
                    return
            except RuntimeError as e:
                msg = e.args[0]

                # if not isinstance(msg, str):
                #     msg = msg.decode("utf8")
                def _show_dialog():
                    dlg = wx.MessageDialog(
                        self, msg, "查找控件失败", style=wx.OK | wx.ICON_ERROR
                    )
                    dlg.ShowModal()
                    dlg.Destroy()

                run_in_main_thread(_show_dialog)()
                return

            used_time = time.time() - time0
            run_in_main_thread(
                lambda: self.statusbar.SetStatusText(
                    "获取控件树完成，耗时：%s S" % used_time, 0
                )
            )()
            msg = ""
            for key in controls_dict:
                msg += "\n%s: %d" % (key, len(controls_dict[key]) - 1)
            Log.i("MainFrame", "get control tree cost %s S%s" % (used_time, msg))
            self._show_control_tree(controls_dict)

        run_in_thread(_update_control_tree)()

        t = threading.Thread(target=self._refresh_device_screenshot)
        t.setDaemon(True)
        t.start()

    @run_in_main_thread
    def _show_control_tree(self, controls_dict):
        """显示控件树"""
        self.show_controls(controls_dict)

        self._mouse_move_enabled = True
        self.btn_inspect.Enable(True)
        self.tree.SelectItem(self.root)
        self.tree.SetFocus()
        self.btn_getcontrol.Enable(True)

    def on_refresh_btn_click(self, event):
        """刷新按钮点击回调"""
        self.statusbar.SetStatusText("正在获取窗口列表……", 0)
        time0 = time.time()
        self.show_windows()
        used_time = time.time() - time0
        self.statusbar.SetStatusText("获取窗口列表完成，耗时：%s S" % used_time, 0)

    def show_windows(self):
        """显示Window列表"""
        self.cb_activity.Clear()
        self._control_manager.update()
        current_window = self._window_manager.get_current_window()

        if current_window is None:
            dlg = wx.MessageDialog(
                self,
                "请确认手机是否出现黑屏或ANR",
                "无法获取当前窗口",
                style=wx.OK | wx.ICON_ERROR,
            )
            dlg.ShowModal()
            dlg.Destroy()
            return

        index = 0
        last_title = ""
        for window in self._window_manager.get_window_list():
            if last_title == window.title:
                index += 1
            else:
                index = 0
                last_title = window.title
            idx = self.cb_activity.Append(
                window.title + " " * index
            )  # 避免始终选择到第一项
            data = window.title + (("::%d" % index) if index > 0 else "")

            self.cb_activity.SetClientData(idx, data)
            if window.hashcode == current_window.hashcode:
                self.cb_activity.SetSelection(idx)
                run_in_main_thread(lambda: self.cb_activity.SetLabelText(window.title))

    @property
    def tree(self):
        """当前操作的控件树"""
        return self._tree_list[self._tree_idx]["tree"]

    @property
    def root(self):
        """当前操作的控件树的根"""
        return self._tree_list[self._tree_idx]["root"]

    def show_controls(self, controls_dict):
        """显示控件树"""
        self._build_control_trees(controls_dict)

    def switch_control_tree(self, index):
        """切换控件树"""
        if index < 0 or index >= len(self._tree_list):
            return
        self._tree_idx = index
        for i in range(len(self._tree_list)):
            if i == self._tree_idx:
                self._tree_list[i]["tree"].Show()
                self.cb_activity.SetValue(self._tree_list[i]["window_title"])
                self.tc_process_name.SetValue(self._tree_list[i]["process_name"])
            else:
                self._tree_list[i]["tree"].Hide()

    def on_tree_node_right_click(self, event):
        """ """
        if hasattr(event, "Point"):
            point = event.Point
        else:
            point = event.GetPosition()
        item, _ = self.tree.HitTest(point)
        self.tree.PopupMenu(TreeNodePopupMenu(self, item), point)
        event.Skip()

    def _draw_mask(self, control):
        """绘制高亮区域"""
        if not self._scale_rate:
            return
        item_data = self.tree.GetItemData(control)
        rect = item_data["Rect"]
        p1 = rect["Left"] * self._scale_rate, rect["Top"] * self._scale_rate
        p2 = (rect["Left"] + rect["Width"]) * self._scale_rate, (
            rect["Top"] + rect["Height"]
        ) * self._scale_rate
        self.mask_panel.draw_rectangle(p1, p2)

    def on_tree_node_click(self, event):
        """点击控件树节点"""
        self.cb_show_hex.SetValue(False)
        item_id = event.GetItem()
        self._draw_mask(item_id)
        item_data = self.tree.GetItemData(item_id)
        self.tc_id.SetValue(self._handle_control_id(item_data["Id"]))
        if "ConfusedId" in item_data:
            self.tc_id.SetHint(self._handle_control_id(item_data["ConfusedId"]))
        else:
            self.tc_id.SetHint("")
        self.tc_type.SetValue(item_data["Type"])
        self.tc_visible.SetValue("True" if item_data["Visible"] else "False")
        self.tc_text.SetValue("")
        if "Text" in item_data:
            self.tc_text.SetValue(item_data["Text"])
            self.tc_text.Enable(True)
            self.cb_show_hex.Enable(True)
        else:
            self.tc_text.Enable(False)
            self.cb_show_hex.Enable(False)
        self.btn_set_text.Enable(False)
        self.tc_hashcode.SetValue("0x%.8X" % item_data["Hashcode"])
        rect = "(%s, %s, %s, %s)" % (
            item_data["Rect"]["Left"],
            item_data["Rect"]["Top"],
            item_data["Rect"]["Width"],
            item_data["Rect"]["Height"],
        )
        self.tc_rect.SetValue(rect)
        self.tc_enable.SetValue("True" if item_data["Enabled"] else "False")
        if "Clickable" in item_data:
            self.tc_clickable.SetValue("True" if item_data["Clickable"] else "False")
        else:
            self.tc_clickable.SetValue("")
        if "Checkable" in item_data:
            self.tc_checkable.SetValue("True" if item_data["Checkable"] else "False")
        else:
            self.tc_checkable.SetValue("")
        if "Checked" in item_data:
            self.tc_checked.SetValue("True" if item_data["Checked"] else "False")
        else:
            self.tc_checked.SetValue("")
        self.tc_desc.SetValue(item_data["Desc"])

    def _handle_control_id(self, _id):
        """处理控件ID"""
        if _id == "NO_ID":
            _id = "None"
        elif _id.startswith("id/"):
            _id = _id[3:]
        return _id

    def _add_child(self, process_name, tree, parent, child, is_weex_node=False):
        """添加树形控件节点"""
        node_name = self._handle_control_id(child["Id"])
        if is_weex_node:
            if not child["Type"].startswith("android.") and not child[
                "Type"
            ].startswith("com.android."):
                driver = self._control_manager._get_driver(process_name)
                try:
                    node_name = driver.get_object_field_value(
                        child["Hashcode"], "mTest"
                    )
                except Exception as e:
                    Log.ex("MainFrame", "get field mTest failed")
                else:
                    if not node_name:
                        node_name = "None"
        elif child["Type"].endswith(".WeexView"):
            is_weex_node = True
        node = tree.AppendItem(parent, node_name, data=child)
        for subchild in child["Children"]:
            self._add_child(process_name, tree, node, subchild, is_weex_node)

    def _build_control_trees(self, controls_dict):
        """构建控件树"""
        for tree in self._tree_list:
            # 先删除之前创建的控件树
            tree["root"] = None
            tree["tree"].DeleteAllItems()
            tree["tree"].Destroy()

        self._tree_list = []
        index = -1
        for idx, key in enumerate(controls_dict.keys()):
            if index < 0:
                index = idx
            process_name = controls_dict[key][0]
            for i in range(1, len(controls_dict[key])):
                tree = wx.TreeCtrl(
                    self.tree_panel,
                    id=wx.ID_ANY,
                    pos=(5, 0),
                    size=(self._tree_panel_width - 10, self._tree_panel_height),
                )
                tree_root = controls_dict[key][i]
                root = tree.AddRoot(
                    self._handle_control_id(tree_root["Id"]), data=tree_root
                )
                for child in tree_root["Children"]:
                    self._add_child(process_name, tree, root, child)
                tree.Bind(wx.EVT_TREE_SEL_CHANGED, self.on_tree_node_click)
                # tree.Bind(wx.EVT_MOUSE_EVENTS, self.on_tree_mouse_event)
                tree.Bind(wx.EVT_RIGHT_DOWN, self.on_tree_node_right_click)

                # tree.Bind(wx.EVT_TREE_ITEM_RIGHT_CLICK, self.on_tree_node_right_click)

                item = {
                    "process_name": process_name,
                    "window_title": key,
                    "tree": tree,
                    "root": root,
                }
                self._tree_list.append(item)
        self.switch_control_tree(index)

    def _take_screen_shot(self, tmp_path, path, use_cmd=True):
        """屏幕截图"""
        if use_cmd:
            self._device.adb.run_shell_cmd("rm -f %s" % tmp_path)
            self._device.adb.run_shell_cmd("screencap %s" % tmp_path)
            self._device.adb.run_shell_cmd("chmod 444 %s" % tmp_path)
            self._device.adb.pull_file(tmp_path, path)
        else:
            self._device.take_screen_shot(path, 10)

    def _refresh_device_screenshot(self, use_cmd=False):
        """设置手机屏幕截图"""
        path = os.path.join(os.path.abspath(os.curdir), "screen.png")
        # Log.d('Screenshot', path)
        tmp_path = "/data/local/tmp/screen.png"

        if self._device.adb.get_sdk_version() >= 29:
            use_cmd = True
        try:
            self._take_screen_shot(tmp_path, path, use_cmd)
        except:
            Log.ex("take_screen_shot error")
            return

        if not os.path.exists(path):
            Log.w("Screenshot", "file not exist")

        # image = Image.open(path)
        # image = image.rotate(90, expand=True)
        # image.save(path)
        run_in_main_thread(self._set_image)(path)

    def _set_image(self, image_path):
        try:
            return self.__set_image(image_path)
        except:
            Log.ex("Set image failed")

    def _show_image(self, image):
        img_width, img_height = image.size
        panel_width, panel_height = self.screen_panel.Size
        print(panel_width, panel_height, img_width, img_height)
        if panel_width < img_width or panel_height < img_height:
            x_radio = panel_width / img_width
            y_radio = panel_height / img_height
            self._scale_rate = min(x_radio, y_radio)
            img_width = int(self._scale_rate * img_width)
            img_height = int(self._scale_rate * img_height)
            self.image.SetSize((img_width, img_height))
            self.mask_panel.SetSize((img_width, img_height))
            image = image.resize((img_width, img_height), Image.LANCZOS)

        x = (panel_width - img_width) // 2
        y = (panel_height - img_height) // 2

        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        image = wx.Bitmap.FromPNGData(buffer.getvalue())
        self.image.SetBitmap(image)
        self.image.Refresh()
        self.image.SetPosition((x, y))
        self.mask_panel.SetPosition((x, y))

    def __set_image(self, image_path):
        """设置图片"""
        print("set image %s" % image_path)
        if not os.path.exists(image_path):
            Log.w(self.__class__.__name__, "Image file %s not exist" % image_path)
            return
        if self.cb_auto_refresh.IsChecked():
            tmp_path = "%d.png" % int(time.time())
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            os.rename(image_path, tmp_path)
            image_path = tmp_path
        try:
            image = Image.open(image_path)
            image.verify()  # 验证完之后需要重新打开
            image = Image.open(image_path)
        except Exception as e:
            Log.ex("ImageError", image_path, e)
            return
        else:
            self._image_path = image_path
        self._show_image(image)
        self.image.Show()
        self.mask_panel.Show()

        # if self.cb_auto_refresh.IsChecked():
        #     os.remove(temp_path)
        #     os.remove(image_path)

    def on_inspect_btn_click(self, event):
        """探测按钮点击回调"""
        self.btn_inspect.Enable(False)
        self._enable_inspect = True

    def on_mouse_move(self, event):
        """mouse move in screen area"""
        if not self._scale_rate:
            return

        x = event.x
        y = event.y
        if x < 0:
            x = 0
        if y < 0:
            y = 0
        if x >= self.image.Size[0]:
            x = self.image.Size[0] - 1
        if y >= self.image.Size[1]:
            y = self.image.Size[1] - 1

        x = int(x / self._scale_rate)
        y = int(y / self._scale_rate)
        self.statusbar.SetStatusText("(%d, %d)" % (x, y), 2)

        if not self._mouse_move_enabled:
            return

        if not hasattr(self, "_last_mouse_pos"):
            self._last_mouse_pos = x, y
        else:
            if (
                abs(x - self._last_mouse_pos[0]) <= 5
                and abs(y - self._last_mouse_pos[1]) <= 5
            ):
                return

        web_inspect_enabled = (
            hasattr(self, "_current_webview") and self._current_webview is not None
        )
        web_inspect_enabled &= (
            hasattr(self, "_chrome")
            and self._chrome is not None
            and not self._chrome.is_closed()
        )
        if web_inspect_enabled:
            item_data = self.tree.GetItemData(self._current_webview)
            rect = item_data["Rect"]
            if (
                x > rect["Left"]
                and x < rect["Left"] + rect["Width"]
                and y > rect["Top"]
                and y < rect["Top"] + rect["Height"]
            ):
                try:
                    webview = WebView(
                        self._control_manager.get_driver(self.cb_activity.GetValue()),
                        item_data["Hashcode"],
                    )
                except ControlExpiredError:
                    # 页面已关闭
                    self._close_remote_web_debug()
                    return
                except RuntimeError as e:
                    Log.ex("onmouseover error")
                    self._close_remote_web_debug()
                    return

                if event.EventType == wx.EVT_LEFT_UP.typeId:
                    # 点击事件
                    if self._chrome:
                        # 在Native层点击
                        Log.i("WebViewDebugging", "click %d %d" % (x, y))
                        webview._driver.click(item_data["Hashcode"], x, y)
                    else:
                        script = (
                            r"""if(qt4a_web_inspect._inspect_mode){qt4a_web_inspect.fire_mouse_event('click', (%s)/window.devicePixelRatio, (%s)/window.devicePixelRatio)};"""
                            % (x - rect["Left"], y - rect["Top"])
                        )
                        webview.eval_script([], script)
                    self._chrome.bring_to_front()
                else:
                    if not self._chrome:
                        script = (
                            r"""if(qt4a_web_inspect._inspect_mode){qt4a_web_inspect.fire_mouse_event('mouseover', (%s)/window.devicePixelRatio, (%s)/window.devicePixelRatio)};"""
                            % (x - rect["Left"], y - rect["Top"])
                        )  #
                        webview.eval_script([], script)
                return

        if not self._enable_inspect:
            return

        result = []
        for i in range(len(self._tree_list)):
            tree = self._tree_list[i]["tree"]
            root = self._tree_list[i]["root"]
            controls = self._get_current_control(tree, root, x, y)
            if len(controls) > 0:
                min_area = 0xFFFFFFFF
                min_item = None
                for item in controls:
                    item_data = self.tree.GetItemData(item)
                    area = item_data["Rect"]["Width"] * item_data["Rect"]["Height"]
                    if area < min_area:
                        min_area = area
                        min_item = item
                if min_item:
                    result.append({"index": i, "item": min_item, "area": min_area})

        if len(result) == 0:
            print("find control failed")
            return

        # 控件树之间比较
        min_area = 0xFFFFFFFF
        min_item = None
        index = None
        for item in result:
            if item["area"] < min_area:
                min_area = item["area"]
                min_item = item["item"]
                index = item["index"]

        if index != self._tree_idx:
            # 需要切换控件树
            print("switch control tree from %s to %s" % (self._tree_idx, index))
            self._tree_list[index]["tree"].Show()
            self._tree_list[self._tree_idx]["tree"].Hide()
            self.cb_activity.SetValue(self._tree_list[index]["window_title"])
            self.tc_process_name.SetValue(self._tree_list[index]["process_name"])
            self._tree_idx = index

        self._draw_mask(min_item)

        if event.EventType == wx.EVT_LEFT_UP.typeId:
            # 点击事件
            self._expand_tree(min_item)
            self.tree.SelectItem(min_item)
            self.tree.SetFocus()
            self._enable_inspect = False
            self.btn_inspect.Enable(True)
            # self.cb_show_hex.SetValue(False)

    def _get_current_control(self, tree, parent, x, y):
        """获取坐标（x，y）所在的控件"""
        item_data = tree.GetItemData(parent)
        if item_data is None:
            return []

        rect = item_data["Rect"]
        if x < rect["Left"] or x >= rect["Left"] + rect["Width"]:
            return []
        if y < rect["Top"] or y >= rect["Top"] + rect["Height"]:
            return []
        if not item_data["Visible"]:
            return []

        if tree.GetChildrenCount(parent) == 0:
            return [parent]

        result = []
        item, cookie = tree.GetFirstChild(parent)
        while item:
            result.extend(self._get_current_control(tree, item, x, y))
            if sys.platform == "win32":
                item, cookie = tree.GetNextChild(item, cookie)
            else:
                item = tree.GetNextSibling(item)

        if len(result) == 0:
            return [parent]
        else:
            return result

    def _expand_tree(self, item):
        """展开树形控件节点"""
        if item != self.root:
            parent = self.tree.GetItemParent(item)
            self._expand_tree(parent)
            self.tree.Expand(item)
        else:
            self.tree.Expand(self.root)

    def on_local_device_selected(self, event):
        """选择本地设备"""
        self._device_host = "127.0.0.1"
        self.tc_dev_host.Enable(False)
        self.btn_set_device_host.Enable(False)

    def on_remote_device_selected(self, event):
        """选择远程设备"""
        self.tc_dev_host.Enable(True)
        self.btn_set_device_host.Enable(True)

    def on_set_device_host_btn_click(self, event):
        """设置设备主机按钮点击回调"""
        hostname = self.tc_dev_host.GetValue()
        if hostname != self._device_host:
            self.statusbar.SetStatusText("正在检查设备主机: %s……" % hostname, 0)
            if not self._check_device_host(hostname):
                dlg = wx.MessageDialog(
                    self,
                    "设备主机无法访问！\n请确认设备主机名是否正确，以及网络是否连通",
                    "设备主机名错误",
                    style=wx.OK | wx.ICON_ERROR,
                )
                result = dlg.ShowModal()
                dlg.Destroy()
            else:
                self._device_host = hostname
                self.statusbar.SetStatusText("检查设备主机: %s 完成" % hostname, 0)

    def on_auto_fresh_checked(self, event):
        """选择了自动刷新"""
        if self.cb_auto_refresh.IsChecked():
            if not self._device:
                dlg = wx.MessageDialog(
                    self, "尚未选择设备", "错误", style=wx.OK | wx.ICON_ERROR
                )
                result = dlg.ShowModal()
                dlg.Destroy()
                self.cb_auto_refresh.SetValue(False)
                return
            sec = self.tc_refresh_interval.GetValue()
            self.refresh_timer.Start(int(float(sec) * 1000))
            self.btn_getcontrol.Enable(False)
            self.rb_local_device.Enable(False)
            self.rb_remote_device.Enable(False)
            self.tc_dev_host.Enable(False)
            self.btn_set_device_host.Enable(False)
            self.tc_refresh_interval.Enable(False)
        else:
            self.refresh_timer.Stop()
            self.btn_getcontrol.Enable(True)
            self.rb_local_device.Enable(True)
            self.rb_remote_device.Enable(True)
            self.tc_refresh_interval.Enable(True)
            if self._device_host:
                self.tc_dev_host.Enable(True)
                self.btn_set_device_host.Enable(True)

    def on_refresh_timer(self, event):
        """ """
        self._work_thread.post_task(self._refresh_device_screenshot, False)

    def on_node_text_changed(self, event):
        """ """
        self.btn_set_text.Enable(True)

    def on_set_text_btn_click(self, event):
        """ """
        window_title = self.cb_activity.GetValue()
        hashcode = int(self.tc_hashcode.GetValue(), 16)
        text = self.tc_text.GetValue()
        self._control_manager.set_control_text(window_title, hashcode, text)
        self.statusbar.SetStatusText("设置控件文本成功", 0)
        time.sleep(0.5)
        t = threading.Thread(target=self._refresh_device_screenshot, args=(True,))
        t.setDaemon(True)
        t.start()

    def find_webview_control(self, parent):
        """查找WebView节点"""
        item_data = self.tree.GetItemData(parent)
        result = []
        if not item_data["Visible"]:
            return []
        if item_data["Rect"]["Width"] == 0 or item_data["Rect"]["Height"] == 0:
            return []
        if (
            not item_data["Type"].startswith("android.widget.")
            and item_data["Type"]
            != "com.android.internal.policy.impl.PhoneWindow$DecorView"
            and item_data["Type"] != "android.view.View"
        ):
            if WebView.is_webview(
                self._control_manager,
                self.cb_activity.GetValue(),
                item_data["Hashcode"],
            ):
                self._current_webview = parent
                result.append(parent)
                return result

        item, cookie = self.tree.GetFirstChild(parent)
        while item:
            result.extend(self.find_webview_control(item))
            if sys.platform == "win32":
                item, cookie = self.tree.GetNextChild(item, cookie)
            else:
                item = self.tree.GetNextSibling(item)
        return result

    def _get_control_by_hashcode(self, parent, hashcode):
        """根据hashcode找到控件"""
        item_data = self.tree.GetItemData(parent)
        if item_data["Hashcode"] == hashcode:
            return parent
        item, cookie = self.tree.GetFirstChild(parent)
        while item:
            ret = self._get_control_by_hashcode(item, hashcode)
            if ret:
                return ret
            if sys.platform == "win32":
                item, cookie = self.tree.GetNextChild(item, cookie)
            else:
                item = self.tree.GetNextSibling(item)
        return None

    def _focus_control_by_hashcode(self, hashcode):
        """将焦点放到hashcode指定的控件上"""
        control = self._get_control_by_hashcode(self.root, hashcode)
        if not control:
            raise RuntimeError("查找控件失败：%s" % hashcode)
        self._draw_mask(control)
        self._expand_tree(control)
        self.tree.SelectItem(control)
        self.tree.SetFocus()


class CanvasPanel(wx.Panel):
    """绘图面板"""

    def __init__(self, *args, **kwargs):
        wx.Panel.__init__(self, *args, **kwargs)
        self.Bind(wx.EVT_PAINT, self.on_paint)
        self._draw_points = None
        self._last_draw_points = None
        # self.SetBackgroundColour(wx.RED)

    def draw_rectangle(self, p1, p2):
        """画长方形"""
        p1 = (int(p1[0]), int(p1[1]))
        p2 = (int(p2[0]), int(p2[1]))
        self._draw_points = (p1, p2)
        if (
            self._last_draw_points
            and self._last_draw_points[0] == p1
            and self._last_draw_points[1] == p2
        ):
            pass
        else:
            # self.Refresh()
            self.Hide()
            self.Show()

    def on_paint(self, evt):
        if self._draw_points:
            left, top = self._draw_points[0]
            right, bottom = self._draw_points[1]
            dc = wx.PaintDC(self)
            dc.SetPen(wx.Pen("red", 2))
            dc.DrawLine(left, top, right, top)
            dc.DrawLine(right, top, right, bottom)
            dc.DrawLine(right, bottom, left, bottom)
            dc.DrawLine(left, bottom, left, top)
            self._last_draw_points = self._draw_points
            self._draw_points = None


class EnumControlType(object):
    """控件类型"""

    ScrollView = 1
    ListView = 2
    GridView = 3
    WebView = 4
    PossiableListView = 5


class TreeNodePopupMenu(wx.Menu):
    """树形控件节点弹出菜单"""

    def __init__(self, parent, select_node, *args, **kwargs):
        super(TreeNodePopupMenu, self).__init__(*args, **kwargs)
        self._parent = parent
        self._select_node = select_node

        item1 = wx.MenuItem(self, wx.NewId(), "生成控件QPath")
        self.Append(item1)
        self.Bind(wx.EVT_MENU, self.on_gen_qpath_menu_click, item1)
        if not select_node:
            item1.Enable(False)

        item2 = wx.MenuItem(self, wx.NewId(), "输入QPath定位")
        self.Append(item2)
        self.Bind(wx.EVT_MENU, self.on_locate_by_qpath_menu_click, item2)

        #         item3 = wx.MenuItem(self, wx.NewId(), u'查找控件')
        #         self.AppendItem(item3)

        item4 = wx.MenuItem(self, wx.NewId(), "查找WebView控件")
        self.Append(item4)
        self.Bind(wx.EVT_MENU, self.on_find_webview_control_menu_click, item4)

        item5 = wx.MenuItem(self, wx.NewId(), "启动WebView调试")
        self.Append(item5)
        self.Bind(wx.EVT_MENU, self.on_open_webview_debug_menu_click, item5)

        item6 = wx.MenuItem(self, wx.NewId(), "打开WebView命令行")
        self.Append(item6)
        self.Bind(wx.EVT_MENU, self.on_open_webview_console_menu_click, item6)

        menu_title = "切换控件树[%d/%d]" % (
            self._parent._tree_idx + 1,
            len(self._parent._tree_list),
        )
        item7 = wx.MenuItem(self, wx.NewId(), menu_title)
        self.Append(item7)
        self.Bind(wx.EVT_MENU, self.on_switch_control_tree_menu_click, item7)

        if not select_node:
            item5.Enable(False)
            item6.Enable(False)
        else:
            item_data = self._parent.tree.GetItemData(select_node)

            process_name = self._parent._tree_list[self._parent._tree_idx][
                "process_name"
            ]
            try:
                webview = self._parent._control_manager.get_webview(
                    process_name, item_data["Hashcode"]
                )  # self._parent.cb_activity.GetValue()
                self._webview_type = webview.get_webview_type()
            except ControlExpiredError:
                dlg = wx.MessageDialog(
                    self._parent,
                    "请重新刷新控件树",
                    "WebView控件已失效",
                    style=wx.OK | wx.ICON_ERROR,
                )
                result = dlg.ShowModal()
                dlg.Destroy()
                self.Destroy()
                return
            if self._webview_type == EnumWebViewType.NotWebView:
                item5.Enable(False)
                item6.Enable(False)
            else:
                item5.Enable(True)
                item6.Enable(True)

    def _locate_qpath(self, window_title, root_hashcode, qpath, target_hashcode=None):
        """使用QPath定位"""
        hashcode = self._parent._control_manager.get_control(
            window_title, root_hashcode, qpath
        )
        if hashcode == 0:
            return None
            # raise RuntimeError('It\'s impossible!')
        elif isinstance(hashcode, int):
            # 能够唯一确定控件
            return qpath
        else:
            # 使用Instance定位
            if not target_hashcode:
                return None
            for idx in range(len(hashcode)):
                _qpath = qpath + " && Instance=%d" % idx
                hashcode = self._parent._control_manager.get_control(
                    window_title, root_hashcode, _qpath
                )
                if hashcode == target_hashcode:
                    return _qpath
        return None

    def _gen_qpath_by_attrs(self, control, window_title, root):
        """根据属性生成QPath"""
        item_data = self._parent.tree.GetItemData(control)
        root_hashcode = None
        qpath = ""
        if root:
            if not isinstance(root, str):
                root_item_data = self._parent.tree.GetItemData(root)
                root_hashcode = root_item_data["Hashcode"]
            else:
                qpath = root + " "
        min_qpath_len = 0

        _id = self._parent._handle_control_id(item_data["Id"])
        if _id != "None":
            # 存在ID
            qpath += '/Id="%s"' % _id
            if self._locate_qpath(window_title, root_hashcode, qpath):
                return True, qpath
        else:
            qpath += "/"
            min_qpath_len = len(qpath)  # 用于判断是否需要添加&&

        text = item_data.get("Text")
        if text:
            # 使用文本定位
            if len(qpath) > min_qpath_len:
                qpath += " && "
            qpath += 'Text="%s"' % text
            if self._locate_qpath(window_title, root_hashcode, qpath):
                return True, qpath

        type = item_data["Type"]
        if "." in type:
            type = type.split(".")[-1]
            if len(type) > 3:
                # 不处理混淆情况
                if len(qpath) > min_qpath_len:
                    qpath += " && "
                qpath += 'Type="%s"' % type
                if self._locate_qpath(window_title, root_hashcode, qpath):
                    return True, qpath

        #         if len(qpath) > min_qpath_len: qpath += ' && '
        #         qpath += 'Visible="True"'
        #         if self._locate_qpath(window_title, root_hashcode, qpath): return True, qpath

        if len(qpath) == min_qpath_len:
            qpath = None
        return False, qpath

    def _get_special_control(self, control, window_title):
        """获取ListView等特殊控件"""
        parent = control
        while True:
            if parent == self._parent.root:
                return None
            parent = self._parent.tree.GetItemParent(parent)
            parent_data = self._parent.tree.GetItemData(parent)
            parent_type = self._parent._control_manager.get_control_type(
                window_title, parent_data["Hashcode"]
            )
            for type in parent_type:
                control_type = None
                if (
                    type == "android.widget.ListView"
                    or type == "android.widget.AbsListView"
                ):
                    control_type = EnumControlType.ListView
                elif type == "android.widget.GridView":
                    control_type = EnumControlType.GridView
                elif (
                    type.endswith(".ListView")
                    or type.endswith(".AbsListView")
                    or type == "com.tencent.widget.AdapterView"
                ):
                    control_type = EnumControlType.PossiableListView

                if control_type:
                    return parent, control_type

    def _gen_long_qpath(self, control, root, window_title):
        """生成长QPath"""

        qpath = ""

        root_hash = None
        if root:
            root_data = self._parent.tree.GetItemData(root)
            root_hash = root_data["Hashcode"]

        last_ctrl = None  # qpath定位到的控件
        depth = 0
        parent = control
        prev_pos = -1  # 上一次插入QPath的位置，用于加入MaxDepth字段
        while True:
            if parent == self._parent.root or parent == root:
                break
            ctrl_data = self._parent.tree.GetItemData(parent)
            _id = self._parent._handle_control_id(ctrl_data["Id"])
            if _id != "None":
                # 存在ID
                if not last_ctrl:
                    last_ctrl = parent  # 第一个有ID的控件
                _qpath = '/Id="%s"' % _id
                if len(qpath) > 0 and prev_pos > 0:
                    # 不是最底层控件
                    if depth > 1:
                        qpath = (
                            qpath[:prev_pos]
                            + " && MaxDepth=%d" % depth
                            + qpath[prev_pos:]
                        )
                    qpath = _qpath + " " + qpath
                    depth = 0
                    if self._locate_qpath(window_title, root_hash, qpath):
                        return last_ctrl, qpath
                else:
                    qpath = _qpath
                prev_pos = len(_qpath)
            parent = self._parent.tree.GetItemParent(parent)
            depth += 1
        return None, qpath

    def _get_nearest_co_ancestor(self, controls):
        """获取多个控件的最近共同祖先"""
        ancestor_list = [[] for _ in range(len(controls))]
        for i in range(len(controls)):
            control = controls[i]
            while True:
                if control == self._parent.root:
                    break
                ancestor_list[i].insert(0, control)
                control = self._parent.tree.GetItemParent(control)

        idx = 0
        while True:
            for i in range(len(controls) - 1):
                if ancestor_list[i][idx] != ancestor_list[i + 1][idx]:
                    return ancestor_list[i][idx - 1]
            idx += 1

    def _get_control_depth(self, parent, control, depth=0):
        """获取控件深度"""
        if parent == control:
            return depth
        depth += 1
        item, cookie = self._parent.tree.GetFirstChild(parent)
        while item:
            result = self._get_control_depth(item, control, depth)
            if result:
                return result
            item, cookie = self._parent.tree.GetNextChild(item, cookie)

    def _gen_qpath(self, control):
        """生成QPath
        1、如果控件可以使用ID|Text|Type唯一定位，则使用ID|Text|Type生成QPath
        2、从该控件向根节点判断是否存在ListView等特殊节点，如果是，则先计算ListView节点的QPath, 再计算该节点与ListView节点的关系
        3、判断父控件是否可唯一定位，如果是则计算该节点与父节点间的QPath
        4、从该控件向根节点不断使用ID生成链式QPath，直到能唯一定位或到达根节点
        5、如果链式ID无法唯一定位，则获取重复的控件的最近共同祖先，使用Instance进行区分
        """
        window_title = self._parent.cb_activity.GetValue()
        item_data = self._parent.tree.GetItemData(control)

        # --------- 1 --------------
        Log.i("GetQPath", "使用属性定位")
        result, qpath = self._gen_qpath_by_attrs(control, window_title, None)
        if result:
            return qpath

        # --------- 2 --------------
        Log.i("GetQPath", "判断是否有特殊控件")
        result = self._get_special_control(control, window_title)
        if result:
            # 存在特殊类型控件
            ctrl, ctrl_type = result
            Log.i("GetQPath", "存在特殊控件：%s" % ctrl_type)
            ctrl_path = self._gen_qpath(ctrl)
            if not ctrl_path:
                Log.e("GetQPath", "获取控件%sQPath失败" % ctrl_type)
                return None
            ret, qpath = self._gen_qpath_by_attrs(control, window_title, ctrl)
            if ret:
                return ctrl_type, ctrl_path, qpath
            item, cookie = self._parent.tree.GetFirstChild(ctrl)
            while item:
                ret, qpath = self._gen_qpath_by_attrs(control, window_title, item)
                if ret:
                    return ctrl_type, ctrl_path, qpath
                item = self._parent.tree.GetNextSibling(item)
            Log.e("GetQPath", "获取控件QPath失败")
            return None

        # --------- 3 --------------
        Log.i("GetQPath", "判断父控件是否可以定位")
        parent = self._parent.tree.GetItemParent(control)
        result, qpath = self._gen_qpath_by_attrs(parent, window_title, None)
        if result:
            ret, child_qpath = self._gen_qpath_by_attrs(control, window_title, qpath)
            if ret:
                return child_qpath
            # 只能使用Instance定位了
            return self._locate_qpath(
                window_title, None, child_qpath, item_data["Hashcode"]
            )
            # raise NotImplementedError(qpath)

        # 没有特殊容器节点,再遍历一次
        # --------- 4 --------------
        Log.i("GetQPath", "使用长ID定位")
        ret, qpath = self._gen_long_qpath(control, None, window_title)
        if ret:
            return qpath
        else:
            # 寻找最近公共祖先
            return None
            # Log.i('GetQPath', '寻找最近公共祖先')
            # hashcode_list = self._parent._control_manager.get_control(window_title, None, qpath)
            # controls = [self._parent._get_control_by_hashcode(self._parent.root, hashcode) for hashcode in hashcode_list]
            # ancestor = self._get_nearest_co_ancestor(controls)
            # ancestor_qpath = self._gen_qpath(ancestor)  # 获取祖先节点的QPath
            # print ancestor_qpath
            # depth = self._get_control_depth(ancestor, control)
            # ret, child_qpath = self._gen_qpath_by_attrs(control, window_title, ancestor_qpath)
            # if ret: return child_qpath
            # if depth != None and depth > 1: child_qpath += ' && MaxDepth=%d' % depth
            # return self._locate_qpath(window_title, None, child_qpath, item_data['Hashcode'])

    def _copy_to_clipboard(self, text):
        """拷贝到剪切板"""
        if not isinstance(text, str):
            text = text.decode("utf8")
        if sys.platform == "win32":
            import win32con, win32clipboard

            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, text)
            win32clipboard.CloseClipboard()
        elif sys.platform == "darwin":
            import subprocess

            process = subprocess.Popen(
                "pbcopy", env={"LANG": "en_US.UTF-8"}, stdin=subprocess.PIPE
            )
            process.communicate(text.encode("utf-8"))
        else:
            raise NotImplementedError

    def on_gen_qpath_menu_click(self, event):
        """生成QPath"""
        control = self._parent.tree.GetSelection()
        result = self._gen_qpath(control)
        if result == None:
            dlg = wx.MessageDialog(
                self._parent,
                "此控件过于复杂，请人工处理",
                "QPath生成失败",
                style=wx.OK | wx.ICON_ERROR,
            )
            result = dlg.ShowModal()
            dlg.Destroy()
        elif not isinstance(result, tuple):
            dlg = wx.MessageDialog(
                self._parent,
                "%s\n\n警告：自动生成的QPath仅供参考，不保证一定正确或最优！\n点击“OK”将QPath拷贝到剪切板中"
                % result,
                "QPath生成成功",
                style=wx.OK | wx.ICON_INFORMATION,
            )
            dlg.ShowModal()
            self._copy_to_clipboard(result)
            dlg.Destroy()
        else:
            control_type, root_qpath, child_qpath = result
            msg = ""
            if control_type == EnumControlType.ListView:
                msg = "发现该控件在ListView中，需要先定义ListView控件，然后将该控件设置为ListView控件的子控件\n\nListView控件QPath: %s"
            elif control_type == EnumControlType.GridView:
                msg = "发现该控件在GridView中，需要先定义GridView控件，然后将该控件设置为GridView控件的子控件\n\nGridView控件QPath: %s"
            elif control_type == EnumControlType.PossiableListView:
                msg = "该控件可能在自定义ListView中，需要先定义ListView控件，然后将该控件设置为ListView控件的子控件\n\nListView控件QPath: %s"

            msg = msg % root_qpath
            msg += "\n当前节点QPath: %s" % child_qpath
            dlg = wx.MessageDialog(
                self._parent,
                "%s\n\n警告：自动生成的QPath仅供参考，不保证一定正确或最优！\n点击“OK”将QPath拷贝到剪切板中"
                % msg,
                "QPath生成成功",
                style=wx.OK | wx.ICON_INFORMATION,
            )
            result = dlg.ShowModal()
            text = root_qpath
            if text:
                text += "\r\n"
            text += child_qpath
            self._copy_to_clipboard(text)
            dlg.Destroy()

    def on_locate_by_qpath_menu_click(self, event):
        """QPath定位"""
        dlg = wx.TextEntryDialog(
            self._parent,
            "输入要定位的QPath，将返回该QPath能否正确定位到您期望的控件",
            "输入要定位的QPath",
            '/Id="title"',
        )
        if dlg.ShowModal() == wx.ID_OK:
            response = dlg.GetValue()
            try:
                self._parent.locate_by_qpath(response)
            except ControlNotFoundError as e:
                err_msg = str(e)
                if not isinstance(err_msg, str):
                    err_msg = err_msg.decode("utf8")
                dlg = wx.MessageDialog(
                    self._parent, err_msg, "查找控件失败", style=wx.OK | wx.ICON_ERROR
                )
                dlg.ShowModal()
                dlg.Destroy()
            except:
                Log.ex("Mainframe", "QPath error")
                dlg = wx.MessageDialog(
                    self._parent, response, "QPath语法错误", style=wx.OK | wx.ICON_ERROR
                )
                dlg.ShowModal()
                dlg.Destroy()

    def on_find_webview_control_menu_click(self, event):
        """查找并定位到WebView控件"""
        webview_list = self._parent.find_webview_control(self._parent.root)

        if len(webview_list) == 0:
            dlg = wx.MessageDialog(
                self._parent,
                "当前界面未找到WebView控件",
                "查找WebView控件失败",
                style=wx.OK | wx.ICON_ERROR,
            )
            result = dlg.ShowModal()
            dlg.Destroy()
            return
        elif len(webview_list) == 1:
            webview = webview_list[0]
            item_data = self._parent.tree.GetItemData(webview)
            self._parent._focus_control_by_hashcode(item_data["Hashcode"])
        else:
            for webview in webview_list:
                item_data = self._parent.tree.GetItemData(webview)
                self._parent._focus_control_by_hashcode(item_data["Hashcode"])

    def on_open_webview_debug_menu_click(self, event):
        """点击开启WebView调试菜单"""
        from utils.chrome import Chrome

        chrome_path = Chrome._get_browser_path()
        if not os.path.exists(chrome_path):
            dlg = wx.MessageDialog(
                self._parent,
                "使用WebView调试必须要安装Chrome浏览器",
                "无法使用WebView调试",
                style=wx.OK | wx.ICON_ERROR,
            )
            result = dlg.ShowModal()
            dlg.Destroy()
            return

        item_data = self._parent.tree.GetItemData(self._select_node)
        process_name = self._parent._tree_list[self._parent._tree_idx]["process_name"]

        def on_multi_pages(page_list):
            if not page_list:
                self._parent._control_manager.enable_webview_debugging(
                    process_name, item_data["Hashcode"]
                )
                dlg = wx.MessageDialog(
                    self._parent,
                    "可能是Web内核状态导致，请重启应用后再次尝试！",
                    "未找到可调试页面",
                    style=wx.OK | wx.ICON_INFORMATION,
                )
                result = dlg.ShowModal()
                dlg.Destroy()
                return None

            title_black_patterns = [r"^wx.+:INVISIBLE$"]
            url_black_patterns = []  # r'https://servicewechat.com/.+page-frame.html'
            for i in range(len(page_list) - 1, -1, -1):
                page = page_list[i]
                title = page["title"]
                url = page["url"]
                if title:
                    for pattern in title_black_patterns:
                        if re.match(pattern, title):
                            del page_list[i]
                            break
                elif url:
                    for pattern in url_black_patterns:
                        if re.match(pattern, url):
                            del page_list[i]
                            break

            if len(page_list) == 1:
                return page_list[0]["devtoolsFrontendUrl"]

            dlg = SelectPageDialog(self._parent, page_list)
            result = dlg.ShowModal()
            if result < 0 or result >= len(page_list):
                return None
            page = page_list[result]
            return page["devtoolsFrontendUrl"]

        self._parent._chrome = self._parent._control_manager.open_webview_debug(
            process_name, item_data["Hashcode"], self._webview_type, on_multi_pages
        )  # self._parent.cb_activity.GetValue()
        if self._parent._chrome:
            self._parent.refresh_timer.Start(int(1000))

    def on_open_webview_console_menu_click(self, event):
        """点击打开WebView命令行菜单"""
        dlg = WebViewConsoleDialog(self._parent, self._select_node, self._webview_type)
        dlg.Show()

    def on_switch_control_tree_menu_click(self, event):
        """点击切换控件树菜单"""
        index = self._parent._tree_idx
        index += 1
        if index >= len(self._parent._tree_list):
            index = 0
        print("switch from %d to %d" % (self._parent._tree_idx, index))
        self._parent.switch_control_tree(index)


class CustomMessageDialog(wx.Dialog):
    """自定义消息对话框"""

    def __init__(
        self,
        parent,
        title,
        message,
        btn1_title,
        btn2_title,
        size=(300, 150),
        pos=wx.DefaultPosition,
        style=wx.DEFAULT_DIALOG_STYLE,
        useMetal=False,
    ):
        super(CustomMessageDialog, self).__init__(parent, -1, title, pos, size, style)
        self._parent = parent
        wx.StaticText(self, -1, message, pos=(20, 20), size=(260, 30))
        self.left_button = wx.Button(
            id=wx.ID_ANY,
            label=btn1_title,
            parent=self,
            pos=wx.Point(50, 60),
            size=wx.Size(70, 30),
            style=0,
        )
        self.left_button.Bind(wx.EVT_BUTTON, self.on_left_button_click)
        self.right_button = wx.Button(
            id=wx.ID_ANY,
            label=btn2_title,
            parent=self,
            pos=wx.Point(150, 60),
            size=wx.Size(70, 30),
            style=0,
        )
        self.right_button.Bind(wx.EVT_BUTTON, self.on_right_button_click)
        self.Center()

    def on_left_button_click(self, event):
        """ """
        pass

    def on_right_button_click(self, event):
        """ """
        pass


class SwitchNodeDialog(CustomMessageDialog):
    """ """

    def __init__(self, repeat_list, *args, **kwargs):
        super(SwitchNodeDialog, self).__init__(*args, **kwargs)
        self._repeat_list = repeat_list
        self._cur_idx = 0
        self._parent._focus_control_by_hashcode(self._repeat_list[self._cur_idx])

    def on_left_button_click(self, event):
        """ """
        self._cur_idx -= 1
        if self._cur_idx < 0:
            self._cur_idx += len(self._repeat_list)
        self._parent._focus_control_by_hashcode(self._repeat_list[self._cur_idx])

    def on_right_button_click(self, event):
        """ """
        self._cur_idx += 1
        if self._cur_idx >= len(self._repeat_list):
            self._cur_idx -= len(self._repeat_list)
        self._parent._focus_control_by_hashcode(self._repeat_list[self._cur_idx])


class WebViewConsoleDialog(wx.Dialog):
    """WebView命令行"""

    def __init__(
        self,
        parent,
        select_node,
        webview_type,
        size=(800, 500),
        pos=wx.DefaultPosition,
        style=wx.DEFAULT_DIALOG_STYLE,
        useMetal=False,
    ):
        super(WebViewConsoleDialog, self).__init__(
            parent, -1, "WebView Console - 初始化中……", pos, size, style
        )
        self._parent = parent
        self._select_node = select_node
        self._webview_type = webview_type
        self.tc_console = wx.TextCtrl(
            self,
            wx.ID_ANY,
            pos=(10, 5),
            size=(780, 490),
            style=wx.TE_MULTILINE | wx.TE_RICH | wx.TE_LEFT,
        )  #
        self.tc_console.Bind(
            wx.EVT_KEY_DOWN, self.on_key_press
        )  #  wx.EVT_CHAR 会导致无法禁止删除字符
        font = wx.Font(11, wx.MODERN, wx.NORMAL, wx.NORMAL, False, "Consolas")
        self.tc_console.SetFont(font)
        self._last_pos = 0
        self._input_mode = False
        self._cmd_list = []
        self._cmd_index = 0
        self._last_input_pos = -1
        item_data = self._parent.tree.GetItemData(self._select_node)
        process_name = self._parent._tree_list[self._parent._tree_idx]["process_name"]
        self._webview = self._parent._control_manager.get_webview(
            process_name, item_data["Hashcode"]
        )
        self._parent._work_thread.post_task(self.on_load)

    def eval_script(self, script):
        """执行JavaScript代码"""
        script = (
            r"""
var tmp_result = %s;
(function formatOutput(input){
    if(input == undefined) return 'undefined';
    if(input instanceof HTMLElement){
        return input.outerHTML + '\n';
    }else if(input instanceof NodeList){
        var result = '';
        for(var i=0;i<input.length;i++){
            result += formatOutput(input[i]) + '\n';
        }
        return result;
    }
    return input.toString();
})(tmp_result);
        """
            % script
        )
        result = self._webview.eval_script([], script)
        # result = json.loads(result)
        if isinstance(result, (str, unicode)):
            return result
        elif not isinstance(result, dict):
            dlg = wx.MessageDialog(
                self._parent,
                repr(result),
                "执行JavaScript失败",
                style=wx.OK | wx.ICON_ERROR,
            )
            result = dlg.ShowModal()
            dlg.Destroy()
            return
        if "Result" in result:
            return result["Result"]
        raise RuntimeError(result["Error"])

    @run_in_main_thread
    def _set_title(self, title):
        """设置标题"""
        self.SetTitle("WebView Console - %s" % title)

    @run_in_main_thread
    def _show_enter_tip_char(self):
        """显示输入提示符"""
        value = self.tc_console.GetValue()
        pos = len(value)
        self._set_console_style(pos, -1, wx.TextAttr((0x11, 0x99, 0xFF)))
        self.tc_console.WriteText(">")
        # self.tc_console.SetStyle(pos, pos + 1, wx.TextAttr("red"))
        self._last_pos = pos + 1
        self.tc_console.SetInsertionPoint(self._last_pos)
        self._input_mode = True

    def _set_console_style(self, start, end, style):
        """设置控制台字体"""
        if sys.platform == "win32":
            # mac上会有crash
            self.tc_console.SetStyle(start, end, style)

    def on_load(self):
        result = self.eval_script('"[" + document.title + "] - " + location.href')
        self._set_title(result)
        self._show_enter_tip_char()

    def on_key_press(self, event):
        key = event.GetKeyCode()
        if not self._input_mode:
            return
        self.tc_console.SetEditable(True)
        current_pos = self.tc_console.GetInsertionPoint()
        if current_pos < self._last_pos or (current_pos == self._last_pos and key == 8):
            self.tc_console.SetEditable(False)
            return

        if key == 13:
            # 回车
            self._cmd_index = 0
            value = self.tc_console.GetValue()
            pos = len(value)
            input = value[self._last_pos :].strip()
            if input in self._cmd_list:
                self._cmd_list.remove(input)
            self._cmd_list.insert(0, input)

            try:
                result = self.eval_script(input)
                self._set_console_style(pos, -1, wx.TextAttr((0xBB, 0x00, 0x22)))
                self.tc_console.WriteText("\n" + result)
            except RuntimeError as e:
                err_msg = str(e)
                self._set_console_style(pos, -1, wx.TextAttr("red"))
                self.tc_console.WriteText("\n" + err_msg)
            wx.CallAfter(self._show_enter_tip_char)  # 防止最后出现一个换行
        elif key == 315:
            # 上箭头
            if self._cmd_index >= len(self._cmd_list):
                return
            self.tc_console.Remove(self._last_pos, -1)
            self.tc_console.WriteText(self._cmd_list[self._cmd_index])
            self._cmd_index += 1
            return
        elif key == 317:
            # 下箭头
            if self._cmd_index <= 0:
                return
            self._cmd_index -= 1
            self.tc_console.Remove(self._last_pos, -1)
            self.tc_console.WriteText(self._cmd_list[self._cmd_index])
            return
        event.Skip()


class SelectPageDialog(wx.Dialog):
    """选择调试页面对话框"""

    def __init__(
        self,
        parent,
        page_list,
        size=(550, 160),
        style=wx.DEFAULT_DIALOG_STYLE,
        useMetal=False,
    ):
        super(SelectPageDialog, self).__init__(
            parent, -1, "选择调试页面", wx.DefaultPosition, size, style
        )
        self._parent = parent
        wx.StaticText(
            self,
            -1,
            "检测到%d个页面，请选择希望调试的页面" % len(page_list),
            pos=(20, 10),
            size=(400, 20),
        )
        self._cb_pages = wx.ComboBox(self, wx.ID_ANY, pos=(20, 40), size=(500, 24))
        self._items = []
        for i, page in enumerate(page_list):
            value = "%d. %s" % (
                (i + 1),
                page["title"] if page["title"] else page["url"],
            )
            self._items.append(value)
            self._cb_pages.Append(value)
            if i == 0:
                self._cb_pages.SetValue(value)
        self._btn_inspect = wx.Button(
            self,
            wx.ID_ANY,
            label="开始探测",
            pos=wx.Point(360, 80),
            size=wx.Size(100, 30),
            style=0,
        )
        # self._btn_inspect.Enable(False)
        self._btn_inspect.Bind(wx.EVT_BUTTON, self.on_click_inspect_btn)
        self.Center()

    def on_click_inspect_btn(self, event):
        """点击探测按钮"""
        value = self._cb_pages.GetValue()
        index = self._items.index(value)
        self.EndModal(index)
