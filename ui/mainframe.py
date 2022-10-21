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

"""主界面
"""

import os
import re
import sys
import tempfile
import threading
import time
import wx
import wx.adv

from manager.devicemanager import DeviceManager
from manager.windowmanager import WindowManager
from manager.controlmanager import ControlManager, WebView
from utils import run_in_thread
from utils.exceptions import ControlNotFoundError
from utils.logger import Log
from utils.workthread import WorkThread

# root_dir = os.path.dirname(os.path.abspath(__file__))


def create(parent):
    return MainFrame(parent)


def log_uncaught_exceptions(ex_cls, ex, tb):
    import traceback

    err_msg = "".join(traceback.format_tb(tb))
    msg = str(ex)
    # if isinstance(msg, unicode): msg = msg.encode('utf8')
    if isinstance(msg, str):
        msg = msg
    err_msg += msg
    if not isinstance(err_msg, str):
        err_msg = err_msg.decode("utf8")
    err_msg += u"\n"
    Log.e("UncaughtException", err_msg)
    dlg = wx.MessageDialog(
        None, err_msg, u"AndroidUISpy出现异常", style=wx.OK | wx.ICON_ERROR
    )
    dlg.ShowModal()
    dlg.Destroy()


sys.excepthook = log_uncaught_exceptions

default_size = [1000, 700]

try:
    from version import version_info
except:
    version_info = u"v2.5.0"


def run_in_main_thread(func):
    """主线程运行"""

    def wrap_func(*args, **kwargs):
        wx.CallAfter(func, *args, **kwargs)

    return wrap_func


class MainFrame(wx.Frame):
    """ """

    def __init__(self, parent):
        self._init_ctrls(parent)
        self._work_thread = WorkThread()

    def _init_ctrls(self, prnt):
        # generated method, don't edit
        _, screen_height = wx.DisplaySize()
        if screen_height >= 800:
            global default_size
            default_size[1] = ((screen_height - 60) / 100) * 100
        wx.Frame.__init__(
            self,
            id=wx.ID_ANY,
            name="",
            parent=prnt,
            pos=wx.Point(0, 0),
            size=wx.Size(*default_size),
            style=wx.DEFAULT_FRAME_STYLE,
            title=u"AndroidUISpy " + version_info,
        )
        #         self.icon = wx.Icon(os.path.join(os.getcwd(), "res", "magent.ico"), wx.BITMAP_TYPE_ICO)
        #         self.SetIcon(self.icon)
        
        # self.window1 = wx.Window(
        #     id=wx.ID_ANY,
        #     name="window1",
        #     parent=self,
        #     pos=wx.Point(0, 0),
        #     size=wx.Size(*default_size),
        #     style=0,
        # )

        self.Bind(wx.EVT_CLOSE, self.on_close)
        
        self.statusbar = self.CreateStatusBar()
        # 将状态栏分割为3个区域,比例为1:2:3
        self.statusbar.SetFieldsCount(3)
        self.statusbar.SetStatusWidths([-3, -2, -1])
        
        self.panel = wx.Panel(self, size=default_size)
        font = wx.SystemSettings.GetFont(wx.SYS_SYSTEM_FONT)
        font.SetPointSize(9)
        self.vbox = wx.BoxSizer(wx.VERTICAL)
        self.hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        
        # ----------------------------- 上部区域 ---------------------------------------
        
        self.btn_inspect = wx.Button(self.panel, label=u"+", name="btn_inspect", size=wx.Size(30, 30))
        self.btn_inspect.SetFont(font)
        self.btn_inspect.Bind(wx.EVT_BUTTON, self.on_inspect_btn_click)
        self.btn_inspect.Enable(False)
        self.hbox1.Add(self.btn_inspect, flag=wx.LEFT|wx.RIGHT, border=10)
        
        self.label1 = wx.StaticText(self.panel, label=u"设备ID:")
        self.hbox1.Add(self.label1, flag=wx.LEFT|wx.RIGHT, border=10)
        
        self.cb_device = wx.ComboBox(self.panel, wx.ID_ANY, size=(-1, -1))
        self.cb_device.Bind(wx.EVT_COMBOBOX, self.on_select_device)
        self.hbox1.Add(self.cb_device, proportion=1, flag=wx.LEFT|wx.RIGHT, border=10)
        
        self.btn_refresh = wx.Button(self.panel, label=u"刷新", name="btn_refresh")
        self.btn_refresh.Enable(False)
        self.btn_refresh.Bind(wx.EVT_BUTTON, self.on_refresh_btn_click)
        self.hbox1.Add(self.btn_refresh, flag=wx.RIGHT, border=10)
        
        self.label2 = wx.StaticText(self.panel, label=u"选择Activity: ")
        self.hbox1.Add(self.label2, flag=wx.RIGHT, border=10)
        
        self.cb_activity = wx.ComboBox(self.panel, id=wx.ID_ANY, size=(-1, -1))
        self.cb_activity.Bind(wx.EVT_COMBOBOX, self.on_select_window)
        self.cb_activity.Bind(wx.EVT_COMBOBOX_DROPDOWN, self.on_window_list_dropdown)
        self.hbox1.Add(self.cb_activity, proportion=2, flag=wx.LEFT, border=10)
        
        self.btn_getcontrol = wx.Button(self.panel, label=u"获取控件", name="btn_getcontrol")
        self.btn_getcontrol.Bind(wx.EVT_BUTTON, self.on_getcontrol_btn_click)
        self.btn_getcontrol.Enable(False)
        self.hbox1.Add(self.btn_getcontrol, flag=wx.LEFT|wx.RIGHT, border=10)
        
        self.vbox.Add(self.hbox1, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP, border=5)

        self.vbox.Add((-1, 10))
        
        self.sb1 = wx.StaticBox(self.panel, label=u"高级选项", size=(-1, -1))
        self.st_hbox = wx.StaticBoxSizer(self.sb1, orient=wx.HORIZONTAL)
        
        self.rb_local_device = wx.RadioButton(self.panel, label=u"本地设备", size=wx.DefaultSize)
        self.rb_local_device.SetValue(True)
        self.rb_local_device.Bind(wx.EVT_RADIOBUTTON, self.on_local_device_selected)
        self.st_hbox.Add(self.rb_local_device, flag=wx.LEFT, border=10)
        
        self.rb_remote_device = wx.RadioButton(self.panel, label=u"远程设备", size=wx.DefaultSize)
        self.rb_remote_device.Bind(wx.EVT_RADIOBUTTON, self.on_remote_device_selected)
        self.st_hbox.Add(self.rb_remote_device, flag=wx.LEFT, border=10)
        
        self.label3 = wx.StaticText(self.panel, label=u"远程设备主机名: ", size=wx.DefaultSize)
        self.st_hbox.Add(self.label3, flag=wx.LEFT, border=10)
        
        self.tc_dev_host = wx.TextCtrl(self.panel, size=wx.DefaultSize)
        self.tc_dev_host.Enable(False)
        self.tc_dev_host.SetToolTip(wx.ToolTip(u"输入要调试守在所在的设备主机名"))
        self.st_hbox.Add(self.tc_dev_host, proportion=1, flag=wx.LEFT, border=10)
        
        self.btn_set_device_host = wx.Button(self.panel, label=u"确定", size=wx.Size(50, 24))
        self.btn_set_device_host.Enable(False)
        self.btn_set_device_host.Bind(wx.EVT_BUTTON, self.on_set_device_host_btn_click)
        self.st_hbox.Add(self.btn_set_device_host, flag=wx.LEFT, border=10)
        
        self.cb_auto_refresh = wx.CheckBox(self.panel, label=u"自动刷新屏幕", size=wx.DefaultSize)
        self.cb_auto_refresh.Bind(wx.EVT_CHECKBOX, self.on_auto_fresh_checked)
        self.st_hbox.Add(self.cb_auto_refresh, flag=wx.LEFT, border=5)
        
        self.label4 = wx.StaticText(self.panel, label=u"刷新频率: ", size=wx.DefaultSize)
        self.st_hbox.Add(self.label4, flag=wx.LEFT, border=5)
        
        self.tc_refresh_interval = wx.TextCtrl(self.panel, size=wx.Size(40, 20))
        self.tc_refresh_interval.SetValue("1")
        self.st_hbox.Add(self.tc_refresh_interval, flag=wx.LEFT, border=5)
        
        self.label5 = wx.StaticText(self.panel, label=u"秒", size=wx.DefaultSize)
        self.st_hbox.Add(self.label5, flag=wx.LEFT, border=5)
        
        self.refresh_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_refresh_timer, self.refresh_timer) # 绑定一个计时器
        
        self.vbox.Add(self.st_hbox, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP, border=10)
        self.vbox.Add((-1, 10))
        
        # ------------------------------- 中部区域 -----------------------------------
        self.mid_hbox = wx.BoxSizer(wx.HORIZONTAL)
        self.mid_vbox1 = wx.BoxSizer(wx.VERTICAL)
        self.mid_vbox2 = wx.BoxSizer(wx.VERTICAL)
        
        # 可能存在多个控件树
        self._tree_list = []
        
        self._main_height = default_size[1] - 310
        
        self.main_panel = wx.Panel(self.panel, pos=(10, 100), size=(960, self._main_height))
        
        self.image = wx.StaticBitmap(self.main_panel)
        self.image.Bind(wx.EVT_MOUSE_EVENTS, self.on_mouse_move)
        
        self.mask_panel = CanvasPanel(parent=self.main_panel)
        
        if sys.platform == "darwin":
            self.mask_panel.Bind(wx.EVT_MOUSE_EVENTS, self.on_mouse_move)
        
        self.mid_vbox1.Add(self.main_panel, 0, wx.CENTRE)
        self.mid_vbox2.Add(self.mask_panel, 0, wx.CENTRE)
        
        self.mid_hbox.Add(self.mid_vbox1, 0, wx.CENTRE)
        self.mid_hbox.Add(self.mid_vbox2, 0, wx.CENTRE)
        
        self.vbox.Add(self.mid_hbox, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP, border=10)
        self.vbox.Add((-1, 25))
        
        
        # -------------------------------- 下部区域 ------------------------------------
        
        self.sb2 = wx.StaticBox(self.panel, label=u"控件属性", size=(-1, -1))
        self.bsizer = wx.StaticBoxSizer(self.sb2, orient=wx.VERTICAL)
        
        self.hsizer = wx.BoxSizer()
        
        self.vsizer1 = wx.BoxSizer(wx.VERTICAL)
        
        self.label6 = wx.StaticText(self.panel, label=u"ID", size=wx.DefaultSize)
        self.vsizer1.Add(self.label6, flag=wx.LEFT|wx.TOP, border=10)
        
        self.label7 = wx.StaticText(self.panel, label=u"Type", size=wx.DefaultSize)
        self.vsizer1.Add(self.label7, flag=wx.LEFT|wx.TOP, border=10)
        
        self.label8 = wx.StaticText(self.panel, label=u"Visible", size=wx.DefaultSize)
        self.vsizer1.Add(self.label8, flag=wx.LEFT|wx.TOP, border=10)
        
        self.label9 = wx.StaticText(self.panel, label=u"Text", size=wx.DefaultSize)  
        self.vsizer1.Add(self.label9, flag=wx.LEFT|wx.TOP, border=10)
        
        self.hsizer.Add(self.vsizer1)
        self.hsizer.AddSpacer(20)
        
        self.vsizer2 = wx.BoxSizer(wx.VERTICAL)
        
        self.tc_id = wx.TextCtrl(self.panel, size=wx.DefaultSize)
        self.vsizer2.Add(self.tc_id, flag=wx.LEFT|wx.TOP, border=5)
        
        self.tc_type = wx.TextCtrl(self.panel, size=wx.DefaultSize)
        self.vsizer2.Add(self.tc_type, flag=wx.LEFT|wx.TOP, border=5)
        
        self.tc_visible = wx.TextCtrl(self.panel, size=wx.DefaultSize)
        self.vsizer2.Add(self.tc_visible, flag=wx.LEFT|wx.TOP, border=5)
        
        self.tc_text = wx.TextCtrl(self.panel, size=wx.DefaultSize)
        self.tc_text.Enable(False)
        self.tc_text.Bind(wx.EVT_TEXT, self.on_node_text_changed)
        self.vsizer2.Add(self.tc_text, flag=wx.LEFT|wx.TOP, border=5)
        
        self.hsizer.Add(self.vsizer2)
        self.hsizer.AddSpacer(50)
        
        self.vsizer3 = wx.BoxSizer(wx.VERTICAL)
        
        self.label10 = wx.StaticText(self.panel, label=u"HashCode", size=wx.DefaultSize)
        self.vsizer3.Add(self.label10, flag=wx.LEFT|wx.TOP, border=10)
        
        self.label11 = wx.StaticText(self.panel, label=u"Rect", size=wx.DefaultSize)
        self.vsizer3.Add(self.label11, flag=wx.LEFT|wx.TOP, border=10)
        
        self.label12 = wx.StaticText(self.panel, label=u"Enabled", size=wx.DefaultSize)
        self.vsizer3.Add(self.label12, flag=wx.LEFT|wx.TOP, border=10)
        
        self.btn_set_text = wx.Button(self.panel, label=u"修改文本", size=wx.DefaultSize)
        self.btn_set_text.Enable(False)
        self.btn_set_text.Bind(wx.EVT_BUTTON, self.on_set_text_btn_click)
        self.vsizer3.Add(self.btn_set_text, flag=wx.LEFT|wx.TOP, border=10)
        
        self.hsizer.Add(self.vsizer3)
        self.hsizer.AddSpacer(20)
        
        
        self.vsizer4 = wx.BoxSizer(wx.VERTICAL)
        
        self.tc_hashcode = wx.TextCtrl(self.panel, size=wx.DefaultSize)
        self.vsizer4.Add(self.tc_hashcode, flag=wx.LEFT|wx.TOP, border=5)
        
        self.tc_rect = wx.TextCtrl(self.panel, size=wx.DefaultSize)
        self.vsizer4.Add(self.tc_rect, flag=wx.LEFT|wx.TOP, border=5)
        
        self.tc_enable = wx.TextCtrl(self.panel, size=wx.DefaultSize)
        self.vsizer4.Add(self.tc_enable, flag=wx.LEFT|wx.TOP, border=5)
        
        self.cb_show_hex = wx.CheckBox(self.panel, label=u"显示16进制", size=wx.DefaultSize)
        self.vsizer4.Add(self.cb_show_hex, flag=wx.LEFT|wx.TOP, border=5)
        
        self.hsizer.Add(self.vsizer4)
        self.hsizer.AddSpacer(50)
        
        
        self.vsizer5 = wx.BoxSizer(wx.VERTICAL)
        
        self.label13 = wx.StaticText(self.panel, label=u"ProcessName", size=wx.DefaultSize)
        self.vsizer5.Add(self.label13, flag=wx.LEFT|wx.TOP, border=10)
        
        self.label14 = wx.StaticText(self.panel, label=u"Descriptions", size=wx.DefaultSize)
        self.vsizer5.Add(self.label14, flag=wx.LEFT|wx.TOP, border=10)
        
        self.hsizer.Add(self.vsizer5)
        self.hsizer.AddSpacer(20)
        
        
        self.vsizer6 = wx.BoxSizer(wx.VERTICAL)
        
        self.tc_process_name = wx.TextCtrl(self.panel, size=(200, -1))
        self.vsizer6.Add(self.tc_process_name, flag=wx.LEFT|wx.TOP, border=5)
        
        self.tc_desc = wx.TextCtrl(self.panel, size=(200, -1))
        self.vsizer6.Add(self.tc_desc, flag=wx.LEFT|wx.TOP, border=5)
        
        self.hsizer.Add(self.vsizer6)
        self.hsizer.AddSpacer(50)
        
        self.bsizer.Add(self.hsizer, 0, wx.CENTER)
        self.vbox.Add(self.bsizer, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP, border=10)
        self.vbox.Add((-1, 25))
        
        self.panel.SetSizer(self.vbox)
        
        
        self._device_manager = DeviceManager()
        self._device_manager.register_callback(
            self.on_device_inserted, self.on_device_removed
        )
        # self._viewserver_manager = None
        self._window_manager = None
        self._control_manager = None
        self._device_host = None
        self._device_list = []
        self._select_device = None
        self._device = None
        self._screen_size = None
        self._scale_rate = None  # 截图缩放比例
        self._mouse_move_enabled = False
        self._enable_inspect = False
        self._chrome = None

    def on_device_inserted(self, device_name):
        """新设备插入回调"""
        self.statusbar.SetStatusText(u"设备：%s 已插入" % device_name, 0)
        self.cb_device.Append(device_name)
        if self.cb_device.GetSelection() < 0:
            self.cb_device.SetSelection(0)
            self.on_select_device(None)

    def on_device_removed(self, device_name):
        """设备移除回调"""
        self.statusbar.SetStatusText(u"设备：%s 已断开" % device_name, 0)
        for index, it in enumerate(self.cb_device.Items):
            if it == device_name:
                self.cb_device.Delete(index)
                break

    def on_close(self, event):
        """ """
        import atexit

        atexit._exithandlers = []  # 禁止退出时弹出错误框
        event.Skip()

    @property
    def tree(self):
        """当前操作的控件树"""
        return self._tree_list[self._tree_idx]["tree"]

    @property
    def root(self):
        """当前操作的控件树的根"""
        return self._tree_list[self._tree_idx]["root"]

    def on_auto_fresh_checked(self, event):
        """选择了自动刷新"""
        if self.cb_auto_refresh.IsChecked():
            if not self._device:
                dlg = wx.MessageDialog(
                    self, u"尚未选择设备", u"错误", style=wx.OK | wx.ICON_ERROR
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
        self.statusbar.SetStatusText(u"设置控件文本成功", 0)
        time.sleep(0.5)
        t = threading.Thread(target=self._refresh_device_screenshot, args=(True,))
        t.setDaemon(True)
        t.start()

    def _set_image(self, image_path):
        try:
            return self.__set_image(image_path)
        except:
            Log.ex("Set image failed")

    def __set_image(self, image_path):
        """设置图片"""
        from PIL import Image

        main_height = self._main_height - 20
        if not os.path.exists(image_path):
            return
        if self.cb_auto_refresh.IsChecked():
            tmp_path = "%d.png" % int(time.time())
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            os.rename(image_path, tmp_path)
            image_path = tmp_path
        try:
            img = Image.open(image_path)
            img.verify()  # 验证完之后需要重新打开
            img = Image.open(image_path)
        except Exception as e:
            Log.ex("ImageError", image_path, e)
            return
        w, h = img.size

        if w > h:
            # 横屏情况
            target_width = self.image.GetSize()[0]
            min_width = 500
            if target_width < min_width:
                target_width = min_width  # 避免横屏时显示的图像过小
            target_height = int((1.0 * target_width / w) * h)
        else:
            target_height = int(main_height)
            target_width = int((1.0 * target_height / h) * w)

        self._screen_size = img.size
        width, height = self._screen_size  # image.GetSize()
        self._scale_rate = float(target_height) / height
        temp_path = tempfile.mkstemp(".png")[1]

        try:
            out = img.resize((target_width, target_height), Image.ANTIALIAS)
            out.save(temp_path)
        except:
            Log.ex("ImageError", "resize error")
            return

        image = wx.Image(temp_path, wx.BITMAP_TYPE_PNG)

        self.image.SetSize((target_width, target_height))
        self.mask_panel.SetSize((target_width, target_height))

        tree_width = default_size[0] - target_width - 60
        tree_height = main_height

        x = default_size[0] - target_width - 40
        y = 0
        if w > h:
            x = tree_width + 20
            y = int(target_height / 2)  # 居中

        self.image.SetPosition((x, y))
        self.mask_panel.SetPosition((x, y))

        for i in range(len(self._tree_list)):
            # 所有控件树都要修改
            self._tree_list[i]["tree"].SetSize((tree_width, tree_height))

        try:
            image = image.ConvertToBitmap()
        except:
            # 文件损坏
            return

        self.image.SetBitmap(image)
        self.image.Refresh()
        self.image.Show()
        self.mask_panel.Show()

        if self.cb_auto_refresh.IsChecked():
            os.remove(temp_path)
            os.remove(image_path)

    def on_inspect_btn_click(self, event):
        """探测按钮点击回调"""
        self.btn_inspect.Enable(False)
        self._enable_inspect = True

    @run_in_main_thread
    def on_select_device(self, event):
        """选中的某个设备"""
        from qt4a.androiddriver.adb import ADB
        from qt4a.androiddriver.devicedriver import DeviceDriver

        new_dev = self.cb_device.GetValue()
        if new_dev != self._select_device:
            self._select_device = new_dev
            device_id = self._select_device
            if self._device_host:
                device_id = self._device_host + ":" + device_id
            self._device = DeviceDriver(ADB.open_device(device_id))
            self.statusbar.SetStatusText(u"当前设备：%s" % self._select_device, 0)
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
            wx.CallLater(1000, lambda: self.on_getcontrol_btn_click(None))  # 自动获取控件树

        self.btn_refresh.Enable(True)
        self.btn_getcontrol.Enable(True)

    def on_set_device_host_btn_click(self, event):
        """设置设备主机按钮点击回调"""
        hostname = self.tc_dev_host.GetValue()
        if hostname != self._device_host:
            self.statusbar.SetStatusText(u"正在检查设备主机: %s……" % hostname, 0)
            if not self._check_device_host(hostname):
                dlg = wx.MessageDialog(
                    self,
                    u"设备主机无法访问！\n请确认设备主机名是否正确，以及网络是否连通",
                    u"设备主机名错误",
                    style=wx.OK | wx.ICON_ERROR,
                )
                result = dlg.ShowModal()
                dlg.Destroy()
            else:
                self._device_host = hostname
                self.statusbar.SetStatusText(u"检查设备主机: %s 完成" % hostname, 0)

    def on_refresh_btn_click(self, event):
        """刷新按钮点击回调"""
        self.statusbar.SetStatusText(u"正在获取窗口列表……", 0)
        time0 = time.time()
        self.show_windows()
        used_time = time.time() - time0
        self.statusbar.SetStatusText(u"获取窗口列表完成，耗时：%s S" % used_time, 0)

    def _take_screen_shot(self, tmp_path, path, use_cmd=True):
        """屏幕截图"""
        if use_cmd:
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

        run_in_main_thread(self._set_image)(path)

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
                    self.main_panel,
                    id=wx.ID_ANY,
                    pos=(5, 0),
                    size=(600, self._main_height - 20),
                )
                tree_root = controls_dict[key][i]
                root = tree.AddRoot(
                    self._handle_control_id(tree_root["Id"]), data=tree_root
                )
                for child in tree_root["Children"]:
                    self._add_child(process_name, tree, root, child)
                tree.Bind(wx.EVT_TREE_SEL_CHANGED, self.on_tree_node_click)
                tree.Bind(wx.EVT_MOUSE_EVENTS, self.on_tree_mouse_event)

                tree.Bind(wx.EVT_TREE_ITEM_RIGHT_CLICK, self.on_tree_node_right_click)

                item = {
                    "process_name": process_name,
                    "window_title": key,
                    "tree": tree,
                    "root": root,
                }
                self._tree_list.append(item)
        self.switch_control_tree(index)

    @run_in_thread
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
                u"设备：%s 处于锁屏状态，是否需要解锁？" % self.cb_device.GetValue(),
                u"提示",
                style=wx.YES_NO | wx.YES_DEFAULT | wx.ICON_QUESTION,
            )
            result = dlg.ShowModal()
            if result == wx.ID_YES:
                self._device.unlock_keyguard()
                self.on_refresh_btn_click(None)
            dlg.Destroy()

        self.statusbar.SetStatusText(u"正在获取控件树……", 0)
        time0 = time.time()
        try:
            controls_dict = (
                self._control_manager.get_control_tree()
            )  # self.cb_activity.GetValue().strip(), index
            if not controls_dict:
                return
        except RuntimeError as e:
            msg = e.args[0]
            if not isinstance(msg, str):
                msg = msg.decode("utf8")
            dlg = wx.MessageDialog(self, msg, u"查找控件失败", style=wx.OK | wx.ICON_ERROR)
            result = dlg.ShowModal()
            dlg.Destroy()
            return

        t = threading.Thread(target=self._refresh_device_screenshot)
        t.setDaemon(True)
        t.start()

        used_time = time.time() - time0
        self.statusbar.SetStatusText(u"获取控件树完成，耗时：%s S" % used_time, 0)
        msg = ""
        for key in controls_dict:
            msg += "\n%s: %d" % (key, len(controls_dict[key]) - 1)
        Log.i("MainFrame", "get control tree cost %s S%s" % (used_time, msg))
        self._show_control_tree(controls_dict)

    @run_in_main_thread
    def _show_control_tree(self, controls_dict):
        """显示控件树"""
        self.show_controls(controls_dict)

        self._mouse_move_enabled = True
        self.btn_inspect.Enable(True)
        self.tree.SelectItem(self.root)
        self.tree.SetFocus()
        self.btn_getcontrol.Enable(True)

    def on_local_device_selected(self, event):
        """选择本地设备"""
        self._device_host = "127.0.0.1"
        self.tc_dev_host.Enable(False)
        self.btn_set_device_host.Enable(False)

    def on_remote_device_selected(self, event):
        """选择远程设备"""
        self.tc_dev_host.Enable(True)
        self.btn_set_device_host.Enable(True)

    def _check_device_host(self, hostname):
        """检查设备主机是否能正常访问"""
        import socket

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        try:
            sock.connect((hostname, 5037))
            return True
        except socket.error:
            pass

    def _get_current_control(self, tree, parent, x, y):
        """获取坐标（x，y）所在的控件"""
        item_data = tree.GetItemData(parent)
        if item_data == None:
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

    def _close_remote_web_debug(self):
        """关闭web远程调试"""
        if self._chrome:
            self._chrome.close()
            self._chrome = None
            self._current_webview = None
            self.refresh_timer.Stop()

    def on_mouse_move(self, event):
        """mouse move in screen area"""
        if not self._scale_rate:
            return
        x = int(event.x / self._scale_rate)
        y = int(event.y / self._scale_rate)

        self.statusbar.SetStatusText(u"(%d, %d)" % (x, y), 2)

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
            hasattr(self, "_current_webview") and self._current_webview != None
        )
        web_inspect_enabled &= (
            hasattr(self, "_chrome")
            and self._chrome != None
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
                from qt4a.androiddriver.util import ControlExpiredError

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

    def show_windows(self):
        """显示Window列表"""
        self.cb_activity.Clear()
        self._control_manager.update()
        current_window = self._window_manager.get_current_window()

        if current_window == None:
            dlg = wx.MessageDialog(
                self, u"请确认手机是否出现黑屏或ANR", u"无法获取当前窗口", style=wx.OK | wx.ICON_ERROR
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
            idx = self.cb_activity.Append(window.title + " " * index)  # 避免始终选择到第一项
            data = window.title + (("::%d" % index) if index > 0 else "")

            self.cb_activity.SetClientData(idx, data)
            if window.hashcode == current_window.hashcode:
                self.cb_activity.SetSelection(idx)
                run_in_main_thread(self.cb_activity.SetLabelText)(window.title)

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

    def show_controls(self, controls_dict):
        """显示控件树"""
        self._build_control_trees(controls_dict)

    def on_tree_node_click(self, event):
        """点击控件树节点"""
        from manager.controlmanager import WebView

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
        self.tc_desc.SetValue(item_data["Desc"])

    def on_tree_mouse_event(self, event):
        """树型控件鼠标事件"""
        evt_type = event.GetEventType()
        if evt_type != 10034 and evt_type != 10035:
            event.Skip()
            return  # 只处理鼠标右击事件

        _, flags = self.tree.HitTest(event.GetPosition())
        if flags & wx.TREE_HITTEST_ONITEMLABEL == 0:
            # 在节点上右击
            self.tree.PopupMenu(TreeNodePopupMenu(self, None), event.GetPosition())
        event.Skip()

    def on_tree_node_right_click(self, event):
        """ """
        self.tree.PopupMenu(TreeNodePopupMenu(self, event.GetItem()), event.Point)

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
            raise RuntimeError(u"查找控件失败：%s" % hashcode)
        self._draw_mask(control)
        self._expand_tree(control)
        self.tree.SelectItem(control)
        self.tree.SetFocus()

    def locate_by_qpath(self, qpath):
        """使用QPath定位控件"""
        window_title = self.cb_activity.GetValue()
        hashcode = self._control_manager.get_control(window_title, None, qpath)
        if hashcode == 0:
            pos = self._control_manager.get_control(window_title, None, qpath, True)
            split_char = qpath[0]
            qpath_list = qpath[1:].split(split_char)
            err_qpath = split_char.join(qpath_list[pos:])
            if err_qpath:
                err_qpath = split_char + err_qpath  # 补上前面的分隔符
            err_msg = u"控件：%s 未找到\n未找到部分路径为：【%s】" % (qpath, err_qpath)
            raise ControlNotFoundError(err_msg)
        if isinstance(hashcode, list):
            # 找到重复控件
            dlg = SwitchNodeDialog(
                hashcode,
                self,
                u"共找到%d个重复控件" % len(hashcode),
                u"点击“下一个”按钮切换到下一个重复控件",
                u"上一个",
                u"下一个",
            )
            dlg.Show()
            return

        self._focus_control_by_hashcode(hashcode)

    def on_show_hex_string_checked(self, event):
        """ """
        val = self.tc_text.GetValue()
        if self.cb_show_hex.IsChecked():
            val = val.encode("utf8")
            self.tc_text.SetValue(repr(val)[1:-1])
        else:
            try:
                self.tc_text.SetValue(eval("'" + val + "'"))
            except:
                Log.ex("eval error")


class CanvasPanel(wx.Panel):
    """绘图面板"""

    def __init__(self, *args, **kwargs):
        wx.Panel.__init__(self, *args, **kwargs)
        self.Bind(wx.EVT_PAINT, self.on_paint)
        self._draw_points = None
        self._last_draw_points = None

    def draw_rectangle(self, p1, p2):
        """画长方形"""
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
        from manager.controlmanager import EnumWebViewType, WebView

        super(TreeNodePopupMenu, self).__init__(*args, **kwargs)
        self._parent = parent
        self._select_node = select_node

        item1 = wx.MenuItem(self, wx.NewId(), u"生成控件QPath")
        self.Append(item1)
        self.Bind(wx.EVT_MENU, self.on_gen_qpath_menu_click, item1)
        if not select_node:
            item1.Enable(False)

        item2 = wx.MenuItem(self, wx.NewId(), u"输入QPath定位")
        self.Append(item2)
        self.Bind(wx.EVT_MENU, self.on_locate_by_qpath_menu_click, item2)

        #         item3 = wx.MenuItem(self, wx.NewId(), u'查找控件')
        #         self.AppendItem(item3)

        item4 = wx.MenuItem(self, wx.NewId(), u"查找WebView控件")
        self.Append(item4)
        self.Bind(wx.EVT_MENU, self.on_find_webview_control_menu_click, item4)

        item5 = wx.MenuItem(self, wx.NewId(), u"启动WebView调试")
        self.Append(item5)
        self.Bind(wx.EVT_MENU, self.on_open_webview_debug_menu_click, item5)

        item6 = wx.MenuItem(self, wx.NewId(), u"打开WebView命令行")
        self.Append(item6)
        self.Bind(wx.EVT_MENU, self.on_open_webview_console_menu_click, item6)

        menu_title = u"切换控件树[%d/%d]" % (
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
            from qt4a.androiddriver.util import ControlExpiredError

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
                    u"请重新刷新控件树",
                    u"WebView控件已失效",
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
                print(hashcode)
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
                    # print 'xx', qpath
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
            # print item
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
                u"此控件过于复杂，请人工处理",
                u"QPath生成失败",
                style=wx.OK | wx.ICON_ERROR,
            )
            result = dlg.ShowModal()
            dlg.Destroy()
        elif not isinstance(result, tuple):
            dlg = wx.MessageDialog(
                self._parent,
                u"%s\n\n警告：自动生成的QPath仅供参考，不保证一定正确或最优！\n点击“OK”将QPath拷贝到剪切板中" % result,
                u"QPath生成成功",
                style=wx.OK | wx.ICON_INFORMATION,
            )
            dlg.ShowModal()
            self._copy_to_clipboard(result)
            dlg.Destroy()
        else:
            control_type, root_qpath, child_qpath = result
            msg = ""
            if control_type == EnumControlType.ListView:
                msg = u"发现该控件在ListView中，需要先定义ListView控件，然后将该控件设置为ListView控件的子控件\n\nListView控件QPath: %s"
            elif control_type == EnumControlType.GridView:
                msg = u"发现该控件在GridView中，需要先定义GridView控件，然后将该控件设置为GridView控件的子控件\n\nGridView控件QPath: %s"
            elif control_type == EnumControlType.PossiableListView:
                msg = u"该控件可能在自定义ListView中，需要先定义ListView控件，然后将该控件设置为ListView控件的子控件\n\nListView控件QPath: %s"

            msg = msg % root_qpath
            msg += u"\n当前节点QPath: %s" % child_qpath
            dlg = wx.MessageDialog(
                self._parent,
                u"%s\n\n警告：自动生成的QPath仅供参考，不保证一定正确或最优！\n点击“OK”将QPath拷贝到剪切板中" % msg,
                u"QPath生成成功",
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
            u"输入要定位的QPath，将返回该QPath能否正确定位到您期望的控件",
            u"输入要定位的QPath",
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
                    self._parent, err_msg, u"查找控件失败", style=wx.OK | wx.ICON_ERROR
                )
                dlg.ShowModal()
                dlg.Destroy()
            except:
                Log.ex("Mainframe", "QPath error")
                dlg = wx.MessageDialog(
                    self._parent, response, u"QPath语法错误", style=wx.OK | wx.ICON_ERROR
                )
                dlg.ShowModal()
                dlg.Destroy()

    def on_find_webview_control_menu_click(self, event):
        """查找并定位到WebView控件"""
        webview_list = self._parent.find_webview_control(self._parent.root)

        if len(webview_list) == 0:
            dlg = wx.MessageDialog(
                self._parent,
                u"当前界面未找到WebView控件",
                u"查找WebView控件失败",
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
                u"使用WebView调试必须要安装Chrome浏览器",
                u"无法使用WebView调试",
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
                    u"可能是Web内核状态导致，请重启应用后再次尝试！",
                    u"未找到可调试页面",
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
            parent, -1, u"WebView Console - 初始化中……", pos, size, style
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
        font = wx.Font(11, wx.MODERN, wx.NORMAL, wx.NORMAL, False, u"Consolas")
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
                u"执行JavaScript失败",
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
        self.SetTitle(u"WebView Console - %s" % title)

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
        # print key
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
            parent, -1, u"选择调试页面", wx.DefaultPosition, size, style
        )
        self._parent = parent
        wx.StaticText(
            self,
            -1,
            u"检测到%d个页面，请选择希望调试的页面" % len(page_list),
            pos=(20, 10),
            size=(400, 20),
        )
        self._cb_pages = wx.ComboBox(self, wx.ID_ANY, pos=(20, 40), size=(500, 24))
        self._items = []
        for i, page in enumerate(page_list):
            value = u"%d. %s" % (
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
            label=u"开始探测",
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
