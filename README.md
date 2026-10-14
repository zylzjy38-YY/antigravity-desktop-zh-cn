# Antigravity Desktop 简体中文汉化

从日常使用的运行时汉化中提取的独立 Windows 汉化包。下载、解压，双击 **一键安装.bat**，以后使用桌面上的 **Antigravity 中文** 入口。

**[下载 Windows 一键汉化包](https://github.com/zylzjy38-YY/antigravity-desktop-zh-cn/releases/latest/download/antigravity-desktop-zh-cn-v1.0.0.zip)** · [查看版本说明与 SHA256](https://github.com/zylzjy38-YY/antigravity-desktop-zh-cn/releases/latest)

**当前适配 Antigravity Desktop 2.23.0，已在 Windows 11 x64 测试。** 面向 Windows 10/11，Windows 10 尚未实机验收。这是独立桌面客户端，不是基于 VS Code 的 Antigravity IDE；安装工具会检查版本，其他版本会停止安装。没有验证 macOS、Linux 和其他版本。

## 使用

1. 下载 Release 中的 `antigravity-desktop-zh-cn-v1.0.0.zip`，将整个压缩包解压到普通文件夹。Code → Download ZIP 是源码，需 Python 3.12 或更高版本及 `requirements.txt` 中的依赖；免安装 Python 的版本请从 Releases 下载。
2. 保存工作并完全退出 Antigravity Desktop，再双击 `一键安装.bat`。一般无需管理员权限；Release 中的 Python 工具已打包，用户无需安装 Python 或额外依赖。
3. 安装后会启动程序并创建桌面入口 `Antigravity 中文`。以后从这个入口打开，助手会自动连接本机页面并汉化。
4. 卸载时先完全退出 Antigravity，等待约 35 秒让助手退出，然后双击 `一键卸载.bat`。

默认检测当前用户的 `AppData\Local\Programs\antigravity\Antigravity.exe` 和 `Program Files\Antigravity\Antigravity.exe`。找不到时会弹出文件选择框。安装文件保存到 `%LOCALAPPDATA%\AntigravityDesktopZhCn`，不覆盖已有的同名安装或桌面入口。

Windows 可能因新发布的未签名程序显示 SmartScreen 提示；核对来源、SHA256 与源码后再决定是否运行。本包使用 Python 编写，不调用 PowerShell，也不改变系统执行策略。Release 目前仅提供 Windows x64。

## 汉化范围

包含 3,136 条界面词典项和少量动态文案规则，覆盖词典匹配的导航、设置、菜单、按钮、提示和界面属性。页面更新、刷新和窗口失焦时继续处理界面。

翻译逻辑排除聊天正文、代码、终端、Markdown、编辑器、输入值、工具输出及识别到的项目名、对话名等用户内容。此保护依赖客户端 DOM 结构；版本更新后应重新检查。词典条目数量不等于逐项验证过的界面数量，也不代表所有页面都完成汉化。

本包通过本机 Chromium 调试协议在页面运行翻译脚本，不修改 `app.asar` 或软件安装文件，不更改网络代理，不包含皮肤、壁纸、其他应用、账户配置或登录资料。原生系统托盘和 Electron 主进程菜单不在本包的汉化范围。

## 工作方式与使用限制

中文入口启用随机端口的本机调试接口，助手仅连接所选 `Antigravity.exe` 进程拥有的 IPv4 回环监听端口，检查页面和 WebSocket 地址后注入汉化。助手不上传数据、不读取浏览器凭据，也不发送聊天消息。调试接口允许本机其他进程操作页面，因此应在可信的本机环境中使用。

助手只在使用中文入口后启动，程序退出约 30 秒后退出；不添加开机启动项。通过官方入口启动通常不会启动本汉化。安装时如果程序已经打开且没有调试接口，会提示先保存工作并退出，不强制结束程序。

官方升级后，入口仍能找到相同路径，但界面结构可能变化。请重新核实兼容性；本版本不承诺未来版本自动兼容。已有其他运行时汉化或皮肤助手时可能重复翻译，建议仅保留一种汉化来源。

安装成功表示文件和入口已安装；运行状态可在安装目录 `status.json` 中检查，`healthyPages > 0` 表示助手已在至少一个页面验证脚本运行。它不等同于所有文案翻译正确。未显示中文时，确认完全退出后使用中文入口，核对客户端版本；需要排查时可检查安装目录的 `status.json`；源码用户可用 `python -X utf8 tool.py --check` 核对版本。

## 来源与许可

界面词典部分来自 [ATopos-svg/antigravity-chinese-community-pack](https://github.com/ATopos-svg/antigravity-chinese-community-pack)，沿用 MIT 许可，原版权声明见 `THIRD-PARTY-LICENSE.txt`。本仓库是提取、整理和独立打包版本，不把社区词典宣称为全部原创。本仓库代码采用 MIT 许可，见 `LICENSE`。Release 所包含的 Python 与依赖许可证保存在 `runtime-licenses/`，也会随安装保存。

本包只包含汉化资源、安装/启动/卸载脚本、说明和验证代码。Antigravity 是其权利方的产品，本项目是非官方社区汉化包。

## 验证

测试脚本位于 `tests/`。页面行为测试使用开发环境中的 Playwright 与 Edge，安装和协议测试使用 Python；用户运行 Release 不需要这些测试依赖。详细结果见 `VALIDATION.md`。

构建免安装 Python 的版本可运行 `python build.py`，先安装 `requirements-build.txt` 中的依赖。构建工具不会上传仓库或发布 Release。

源码使用示例（先安装 Python 3.12 或更高版本）：

```text
python -m pip install -r requirements.txt
python -X utf8 tool.py --install
python -X utf8 tool.py --uninstall
```
