# AndroidUISpy使用文档

## 概述

AndroidUISpy可以辅助探测Android端原生控件树和Web Dom树，帮助使用 [QT4A](https://github.com/Tencent/QT4A) 进行控件QPath和XPath的封装。请从github下载 [AndroidUISpy工具](https://github.com/qtacore/AndroidUISpy/releases)。

接下来以Windows版本(AndroidUISpy.exe)为例，说明如何探测Android原生控件树和Web Dom树。

## 探测Android控件树

先上图，节点（左侧树型控件）与控件（右侧屏幕截图）可以双向定位，显示控件控件ID、类型、坐标等信息:

![inspect_native_control_tree](https://raw.githubusercontent.com/qtacore/AndroidUISpy/master/res/inspect_native_control_tree.gif)

如上，使用左上角+号在屏幕内探测目标控件，左侧会显示对应控件树节点。当然，在左侧控件树点击节点，也会自动探测到右侧的目标区域。如果打开AndroidUiSpy时没有自动抓取控件树并显示正确的Activity名，请先手动用左上角+号在屏幕内探测任何一个控件，此时会获取Activity等信息。

## 探测Web Dom树

请确保你PC上已安装chrome浏览器。然后来到目标webview网页视图，在AndroidUiSpy左侧区域-鼠标右键-查找WebView控件，此时会找到控件树中对应WebView控件（命名为节点A），如下：

![inspect_dom_tree](https://raw.githubusercontent.com/qtacore/AndroidUISpy/master/res/inspect_dom_tree.gif)

接着对着节点A-右键-启动WebView调试，过会会自动调起chrome浏览器显示Dom树，点击Dom树各节点，可以看到AndroidUISpy内app屏幕对应区域被选中。接下来你就可以开始Web控件的XPath封装了。


