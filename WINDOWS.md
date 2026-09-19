# Phoenix 在 Windows 上运行（从零开始）

> 面向第一次用的人：从「一台什么都没装的 Windows 电脑」到「网页里能跟角色说话」。
> 每一步都写了**怎么验证这一步成功了**。全程不需要管理员权限。

## 0. 开始之前

| 项目 | 要求 | 说明 |
| --- | --- | --- |
| 系统 | Windows 10 / 11（64 位） | |
| 网络 | 能正常上网 | 首次要下几百 MB 的 Python 依赖 |
| 磁盘 | 留 2 GB | `venv\` 实测约 450 MB，3D 模型另算 |
| 时间 | 15 分钟左右 | 其中 3~5 分钟在等 pip 下载，没有任何输出是正常的 |
| 管理员权限 | **不需要** | 唯一例外见 §10 的 WinError 10013 |

需要装两样东西：**Python**（跑服务）和 **Node.js**（网页界面必需）。Git、ffmpeg、Chrome 都是可选的。

## 1. 装 Python（必需）

1. 打开 <https://www.python.org/downloads/windows/> ，下载 **Python 3.12** 的
   「Windows installer (64-bit)」。
2. 双击安装包。**第一屏底部务必勾上 `Add python.exe to PATH`** —— 漏了这一步，
   后面 `phoenix.bat` 会找不到 Python。然后点 `Install Now`。
3. 验证：按 `Win + R` → 输入 `cmd` → 回车，在黑窗里敲：

   ```bat
   python --version
   ```

   看到 `Python 3.12.x` 就成功了。

   看不到怎么办：
   - 提示「不是内部或外部命令」：第 2 步的 PATH 没勾上。重跑安装包 → `Modify` → 勾
     「Add Python to environment variables」。
   - 敲 `python` 却弹出微软应用商店：那是 Windows 的「应用别名」在拦路。去
     `设置 → 应用 → 高级应用设置 → 应用执行别名`，把 `python.exe` / `python3.exe` 两项关掉。

## 2. 装 Node.js（必需，最容易漏）

**为什么必需**：Phoenix 的前端是 TypeScript 源码直服，靠 Node 自带的类型剥离能力实时转译成 JS
（`server.py:345`）。没有 Node，服务照样能启动、网页也能打开，但会**永远停在「连接中…」**，
而且服务端不报任何错 —— 所以这一步别省。

1. 打开 <https://nodejs.org/> ，下载 **LTS 版（要 22.6 或更高）** 的 Windows 安装包（`.msi`）。
   官网在国内可能只有几十 KB/s，慢的话用国内镜像（实测可用）：

   ```text
   https://registry.npmmirror.com/-/binary/node/v22.23.2/node-v22.23.2-x64.msi
   ```

   要装别的版本：打开 <https://registry.npmmirror.com/-/binary/node/> 挑版本目录，
   Windows 包名是 `node-v<版本>-x64.msi`（32 位是 `-x86.msi`）。
2. 一路「Next」装完，不用改任何选项。
3. 验证（**新开**一个 cmd）：

   ```bat
   node --version
   ```

   要输出 `v22.6.0` 或更高。低于 22.6 的版本没有 `module.stripTypeScriptTypes`，
   网页一样打不开 —— 去官网下新版覆盖安装。

## 3. 拿到 Phoenix

**方式 A：下载发行包（推荐，不需要 Git）**

1. 打开 <https://github.com/geek-alpha/phoenix/releases> ，下载 `phoenix-1.0.0.tar.gz`。
2. 解压到 `C:\Users\<你的用户名>\Phoenix`。

   > 别放 `Program Files`（非管理员没有写权限，会卡在建 venv 那一步），
   > 也别放桌面 —— 如果开了 OneDrive 同步，几千个文件会被反复上传。

   右键「全部解压缩」对付 `.tar.gz` 经常出错，用 Windows 自带的 tar 更稳：

   ```bat
   mkdir "%USERPROFILE%\Phoenix"
   tar -xzf "%USERPROFILE%\Downloads\phoenix-1.0.0.tar.gz" -C "%USERPROFILE%\Phoenix" --strip-components=1
   ```

**方式 B：装了 Git 的话**

```bat
cd %USERPROFILE%
git clone https://github.com/geek-alpha/phoenix.git
```

**验证**：`dir "%USERPROFILE%\Phoenix\phoenix.bat"` 能看到文件就对了。

## 4. 申请 API Key（必需）

对话模型、语音识别、AI 画图都要它，默认供应商是**硅基流动（SiliconFlow）**：

| 注册地址（点链接或扫码） | 二维码 |
| --- | --- |
| **<https://cloud.siliconflow.cn/i/ByXrxmTh>** | <img src="docs/images/siliconflow-invite-qr.jpg" width="140" alt="扫码注册硅基流动"> |

1. **注册登录**：打开链接，用手机号或邮箱注册（新用户有官方赠送额度，以官方页面为准）。
2. **实名认证（必须做）**：登录后进 [用户中心 → 实名认证](https://cloud.siliconflow.cn/account/authentication)，
   选「个人实名认证」→ 填身份信息 → **用支付宝 App 扫码完成人脸识别**。
   按《网络安全法》要求，未实名认证的账号不能充值、不能开票，付费模型用不了；免费模型也有频次限制。
3. **创建 API Key**：进 [API 密钥](https://cloud.siliconflow.cn/account/ak) → 点「**新建 API 密钥**」→
   复制 `sk-` 开头那串（只完整显示一次，丢了就再建一个）。

先把 Key 存到记事本，§7 要用。

## 5. 一键启动

第一次**必须带 `--setup`**——直接双击 `phoenix.bat` 只会启动、不会装依赖，缺依赖时它会停下来提示你补跑。开 cmd 跑：

```bat
cd %USERPROFILE%\Phoenix
phoenix.bat --setup
```

第一次会发生这些事（都正常，**别关窗口**）：

| 阶段 | 大概耗时 | 你会看到 |
| --- | --- | --- |
| 建虚拟环境 | 10~30 秒 | `== 环境缺失或依赖不全：创建虚拟环境并安装依赖 ==` |
| 装 Python 依赖 | **3~5 分钟** | `正在安装依赖（首次下载量较大，可能几分钟无输出，属正常）`，前几行会列出探测到的 pip 源 |
| 环境自检 | 几秒 | 一行行 `[OK]` / `[WARN]` |
| 生成配置与证书 | 几秒 | 从 `settings.example.json` 生成 `settings.json`；现场签 TLS 证书 |
| 启动服务 | 10~30 秒 | 打印启动横幅：`3D 虚拟 AI 角色陪聊 服务器已启动` + `本机访问` / `局域网` 两行地址 |

看到那段启动横幅、并且列出了 `本机访问 : https://127.0.0.1:8000` 就是成功了。**这个黑窗口要保持开着**，关掉服务就停了。

> **关于下载源**：装依赖走的是 `tools/pip_mirror.py`，它会先并发探测阿里云 / 中科大 / 腾讯云 /
> 华为云 / 清华 / 官方 PyPI，挑一个当下**真能下载**的源，装失败还会自动换下一个。
> 为什么要探测而不是写死一个：清华 PyPI 对云服务器 IP 段会返回 403（能连上、但不给包），
> 家宽却正常 —— 写死哪个源都会坑掉一部分人。
> 想看各源在你网络下的实测状态：`venv\Scripts\python.exe tools\pip_mirror.py --probe`；
> 想强制指定：`set PHOENIX_PIP_INDEX=https://mirrors.aliyun.com/pypi/simple`。
>
> 另外：**3D 动作下载**（Mixamo）用的浏览器内核要单独装，约 150MB 且走国外 CDN，
> 慢的话先设镜像再装：
>
> ```bat
> set PLAYWRIGHT_DOWNLOAD_HOST=https://registry.npmmirror.com/-/binary/playwright
> venv\Scripts\playwright install chromium
> ```

> 别拿 `Uvicorn running on ...` 当成功标志——服务的日志级别是 `warning`，这行 INFO 根本不会打印（实测 `journalctl` 里匹配数为 0）。

- 只想体检、不启动：`phoenix.bat --check`
- 起不来 / 卡住：`phoenix.bat --diag`，把输出整段贴出来即可定位

## 6. 打开网页

用 Chrome 或 Edge 访问 **https://127.0.0.1:8000**：

1. 首次会弹「你的连接不是私密连接」→ 点「高级」→「继续前往 127.0.0.1（不安全）」。
   这是本机现场签的自签证书导致的，属正常（证书和私钥都只在这台机器上）。
2. 如果弹出「Windows 安全中心警报」（防火墙）→ **勾选「专用网络」→ 允许访问**。
   不勾的话，同一 WiFi 下的手机连不上。
3. 页面要加载 3D 模型和几十个前端模块，**10~30 秒属正常**。状态点从「连接中…」变绿即就绪。

> 启动日志里会打印三行访问地址（本机 / 局域网 / IPv6），**以日志里的端口为准**：
> 8000 被占用时服务会自动往后找一个可用端口，并打印「→ 本次自动改用端口 N」。

## 7. 填 API Key（三个地方）

拿到 §4 的 Key 之后：

| 能力 | 在哪里填 | 备注 |
| --- | --- | --- |
| 对话模型 | 网页工具栏 → **模型供应商** → 选中「硅基流动」→ 填 API Key → 激活 | 首次使用默认就是管理员，这个按钮可见 |
| 语音识别（你说话 → 文字） | 网页工具栏 → **角色卡片** → 编辑卡片 → 「识别 API Key」 | 留空则沿用对话那把 Key（`server.py:1691`） |
| AI 画图 | 网页工具栏 → **模型供应商** → 面板下方「AI 画图 API Key」→ 填 Key → 保存 | `images_base_url` / `images_model` 留空即用默认（硅基流动 / `Kwai-Kolors/Kolors`） |
| 语音合成（文字 → 说话） | 不用管 | 默认 `edge_tts` 免费引擎，不需要 Key |

网页里改的即时生效；改过 `settings.json` 要重启服务（关掉黑窗口，重新双击 `phoenix.bat`）。

> 想用 DeepSeek 之类别的模型也完全可以，但 `settings.json` 里的 `api_key` 和 `base_url` 是**成对**的，
> 只换 Key 不换地址会 401。

## 8. 手机 / 平板接入（可选）

手机和电脑连**同一个 WiFi**，然后用手机浏览器打开：

```text
https://<电脑的局域网IP>:8000/setup
```

电脑 IP 在启动日志的「局域网」那一行里；`/setup` 是手机接入向导页（下载根证书 `phoenix-ca.crt`、
扫配对二维码）。手机第一次要装这个根证书，否则 HTTPS 会被拦、离线缓存也起不来。

## 9. 日常：启动、停止、换端口、更新

| 想做什么 | 怎么做 |
| --- | --- |
| 启动 | 双击 `phoenix.bat`（日常不需要再带 `--setup`） |
| 停止 | 在黑窗口里按 `Ctrl + C`，或直接关掉窗口 |
| 体检 | `phoenix.bat --check` |
| 换端口 | `set PHOENIX_PORT=8100` 后再启动（不设就用 8000；被占用时服务会自动往后找并打印实际端口） |
| 更新 | 下载新版压缩包解压到**新目录**，把旧目录的 `settings.json`、`stt_config.json`、`tts_config.json`、`character_cards.json`、`data\` 拷过去，再用新目录启动 |

> 仓库里的 `deploy/release/update.py` 是给 Linux + systemd 用的自动更新器（重启那一步走 `systemctl`），
> Windows 上别用，手动替换更稳。

## 10. 出问题怎么办

**第一步永远是这条**，把输出整段贴出来：

```bat
phoenix.bat --diag
```

它会打印：解释器路径、依赖缺失清单、8000 端口占用、Windows 保留端口段、yt-dlp / ffmpeg、是否管理员。

| 现象 | 原因 | 怎么办 |
| --- | --- | --- |
| 双击后黑窗一闪就没了 | 依赖缺失或端口占用，脚本 `exit` 时窗口跟着关了 | 开个 cmd 跑 `phoenix.bat`，或在目录里跑 `phoenix.bat --diag` |
| 卡在「正在安装依赖」很久 | pip 在下载（正常），或当前源慢/被限流 | 等满 5 分钟；还不行让脚本自己重新挑源：`venv\Scripts\python.exe tools\pip_mirror.py -r requirements.txt`（探测所有镜像 + 失败自动换源）。看各源实测状态：`venv\Scripts\python.exe tools\pip_mirror.py --probe` |
| 报 `WinError 10013` / 端口被拒 | Hyper-V / WSL2 / Docker 保留了 8000 所在段，非管理员绑不上（管理员能绑，所以看着像「必须管理员运行」） | 服务输出里已经给了命令。管理员 PowerShell 任选其一：`net stop winnat && net start winnat`，或 `netsh int ipv4 add excludedportrange protocol=tcp startport=8000 numberofports=1`。查当前保留段：`netsh interface ipv4 show excludedportrange protocol=tcp` |
| 报端口已被占用 | 另一个程序在 8000 上（常见：上一个 Phoenix 没关干净） | 服务会自动改用其它端口并在日志里写明；想手动清：`netstat -ano \| findstr :8000` 拿 PID → 任务管理器结束 |
| 网页一直「连接中…」 | 没装 Node.js，或版本低于 22.6 | 见 §2；用 `node --version` 确认 ≥ v22.6 |
| 网页能开，一进去就弹「还没填大模型 API Key」 | 首次安装还没配 Key（settings.json 里 api_key 是空串） | 见 §4：设置 → 模型供应商填入并保存。老版本没这条提示，表现是「连上了但发消息没反应」，服务窗口里一个 `Missing credentials` 报错 |
| 网页能开，但说话没反应 / 画不出图 | API Key 没填或填错 | 见 §4、§7；语音识别没 Key 会直接报「未配置 API Key」 |
| 中文变乱码 | 控制台代码页不是 UTF-8 | `phoenix.bat` 已自动 `chcp 65001`；自己手敲命令的话先执行一次 `chcp 65001` |
| 装在 `Program Files` 里起不来 | 目录没有写权限 | 挪到 `%USERPROFILE%\Phoenix` |
| 手机连不上 | 防火墙没放行，或不在同一 WiFi | 见 §6 第 2 步；确认手机和电脑连的是同一个路由器 |

## 11. 目录速查

```text
Phoenix\
├─ phoenix.bat          启动脚本（--setup / --check / --diag）
├─ server.py            主服务（FastAPI + WebSocket）
├─ settings.json        ★ 你的配置：API Key、模型、记忆参数（首次启动生成，不入仓）
├─ stt_config.json      语音识别配置（首次保存时生成）
├─ tts_config.json      语音合成配置（首次保存时生成）
├─ venv\                Python 虚拟环境（--setup 建）
├─ web\                 前端（index.html + TypeScript 源码 + vendor 库）
├─ skills\              技能目录（文件助手、天气、画图、视频…）
├─ data\                运行数据：聊天库、上传、日志
└─ tools\               自检 / 打包 / 发布工具
```

相关文档：[README.md](README.md)（总览）· [LINUX.md](LINUX.md)（Linux 版教程）· [HARNESS.md](HARNESS.md)（技能 / 插件开发）
