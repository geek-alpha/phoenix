# Phoenix

> 一个使用 JavaScript, Python, HTML, CSS 开发的项目。

![JavaScript](https://img.shields.io/badge/JavaScript-blue) ![Python](https://img.shields.io/badge/Python-blue) ![HTML](https://img.shields.io/badge/HTML-blue)

## ✨ 项目简介

该项目使用 **JavaScript, Python, HTML, CSS** 编写：316 个源文件、约 13.7 万行自有代码（不含 `web/vendor/` 里的第三方库），仓库共 477 个跟踪文件。

## 🔑 第一步：注册账号、申请 API Key（必需）

Phoenix 的**对话模型、语音识别、AI 画图**都走 OpenAI 兼容接口，默认供应商是
[硅基流动 SiliconFlow](https://cloud.siliconflow.cn/i/ByXrxmTh)。
没有这把 Key，服务照样能启动、网页也能打开，但**听不见、画不出**（语音合成默认用免费的 `edge-tts`，不需要 Key）。
第一次用，先花 3 分钟把 Key 办了：

| 注册地址（点链接或扫码） | 二维码 |
| --- | --- |
| **https://cloud.siliconflow.cn/i/ByXrxmTh** | <img src="docs/images/siliconflow-invite-qr.jpg" width="150" alt="扫码注册硅基流动"> |

**三步拿到 Key：**

1. **注册登录** —— 打开上面的链接，用手机号或邮箱注册（新用户有官方赠送额度，以官方页面为准）。
2. **实名认证（必须做）** —— 登录后进 [用户中心 → 实名认证](https://cloud.siliconflow.cn/account/authentication)，
   选「个人实名认证」→ 填身份信息 → **用支付宝 App 扫码完成人脸识别**。
   按《网络安全法》与平台规则，未实名认证的账号**不能充值、不能开票**，付费模型用不了；
   免费模型也有调用频次限制。企业用户请走「企业实名认证」（法人人脸识别 / 对公打款）。
3. **创建 API Key** —— 进 [API 密钥](https://cloud.siliconflow.cn/account/ak) 页面 → 点「**新建 API 密钥**」→
   复制 `sk-` 开头那串（只完整显示一次，丢了就再建一个）。

**Key 拿到后填哪儿：**

| 能力 | 在哪里填 | 备注 |
| --- | --- | --- |
| 对话模型 | 网页工具栏 → **模型供应商** → 选中「硅基流动」→ 填 API Key → 激活 | 也可直接改 `settings.json` 的 `api_key` + `base_url`（**两者必须成对改**，只换 Key 不换地址会 401） |
| 语音识别（说话 → 文字） | 网页工具栏 → **角色卡片** → 编辑卡片 → 「识别 API Key」 | 留空则沿用对话那把 Key（`server.py:1691`）；识别端点默认就是硅基流动 |
| AI 画图 | 记事本打开 `settings.json`，填 `images_api_key` | `images_base_url` 默认已是硅基流动；这一项**没有网页入口**，只能改文件 |
| 语音合成（文字 → 说话） | 不用管 | 默认 `edge_tts` 免费引擎；想换硅基流动 CosyVoice 再填 TTS 那组字段 |

网页里改的即时生效；改 `settings.json` 需要重启服务（重新跑一次 `phoenix.bat` / `./phoenix.sh`）。

## 🧠 Harness 扩展框架（技能 / 插件）

Phoenix 内置稳定的 harness 运行时，通过**技能（Skill）**与**插件（Plugin）**
持续扩展能力，无需改动核心代码：

- 📖 完整文档见 [HARNESS.md](HARNESS.md)
- 🖥 管理台：浏览器打开 http://<Phoenix 地址>/harness
- 🧩 技能目录 skills/（内置：文件助手、天气、AI 画图）
- 🔌 插件目录 plugins/（内置：hello_plugin 示例）
- 🪶 渐进式披露：settings.json 开启 harness.progressive_disclosure 后，on_demand 技能按需注入
  （一句话摘要 + 内置 skill_help 工具拉取完整说明书），技能再多也不撑爆上下文
- ⚙️ 管理 API：/api/harness/status 、/api/harness/skills 、/api/harness/plugins 、/api/harness/reload

```bash
# 新增一个技能：建目录 → 写 skill.json（可加 skill.py 实现）→ 管理台热重载
mkdir skills/my_skill
```

## 🚀 快速开始

### 0. 环境要求

| 依赖 | 版本 | 必需？ | 不装的后果 |
| --- | --- | --- | --- |
| **Python** | 3.10+ | **必需** | 服务起不来（`--check` 直接判 FAIL） |
| **Node.js** | **22.6+** | **必需** | 服务照常启动、网页也能打开，但会**永远停在「连接中…」**：前端是 TypeScript 源码直服，靠 Node 自带的类型剥离实时转译（`server.py:345`），Node 缺失时 `.ts` 原样下发，浏览器直接语法报错，且服务端不报错 |
| Git | 任意 | 可选 | 只是不能 `git clone`，下压缩包一样用 |
| ffmpeg | 任意 | 可选 | 音视频处理能力降级 |
| Chrome / Chromium | 任意 | 可选 | 网页深挖技能降级为 requests |

分平台手把手教程：**Windows → [WINDOWS.md](WINDOWS.md)**，**Linux → [LINUX.md](LINUX.md)**。

### 1. 拿到代码

```bash
# 方式 A：下载发行包（不需要 Git）—— Releases 页下 phoenix-<版本>.tar.gz 后解压
tar -xzf phoenix-1.0.0.tar.gz && cd phoenix-1.0.0

# 方式 B：克隆仓库
git clone https://github.com/geek-alpha/phoenix.git
```

⚠️ **不要放在受保护目录**：Windows 的 `Program Files`、需要 sudo 的 `/usr/local`，都会让非管理员 / 非 root 卡在建 venv 或写证书那一步（`phoenix.bat` 已会提前拦下并提示）。Windows 建议放 `C:\Users\<你的名字>\Phoenix`。

### 2. 一键启动

```bash
./phoenix.sh --setup      # Linux / macOS
phoenix.bat --setup       # Windows（双击也行）
```

一条命令做四件事，幂等、可重复跑：**建 venv → 装依赖 → 环境自检 → 启动服务**。
只想体检不启动：`./phoenix.sh --check` / `phoenix.bat --check`；
起不来先跑 `phoenix.bat --diag`（打印解释器、依赖、端口占用、Windows 保留端口段、是否管理员）。

首次启动会自动从 `settings.example.json` 生成 `settings.json`（该文件不入仓，因为要存你的 API Key），并现场签一张本机 TLS 证书。**API Key 要自己填**——见上面「第一步」。

⚠️ **venv 不要建在 tmpfs 上**：不少系统 `/tmp` 是内存盘（`df -h /tmp` 看容量），依赖装到一半会 `No space left on device`，留下一个「能 import 一部分」的半成品环境——这种环境最坑，`--setup` 现在会检测并补齐，但不如一开始就别踩。

默认直接跑 HTTPS（自签证书，首次启动生成）。如果你在前面挂了 nginx 做 TLS 终结，把 `settings.json` 的 `harness.http_only` 改成 `true`，服务就只监听 8001 回源端口。

依赖清单两边共用一份 `requirements.txt`，平台差异用 PEP 508 环境标记表达：`uvloop`/`httptools` 标了 `sys_platform != "win32"`，在 Windows 上自动跳过——它们没有 Windows wheel，装了也 import 不了；服务启动时逐个探测，缺了自动退回 asyncio + h11。`bpy`/`bmesh`/`mathutils` 这类 Blender 内嵌模块不在 pip 面内，要用模型转换技能时装系统 Blender 并设 `PHOENIX_BLENDER` 指向它（旧名 `DABAI_BLENDER` 仍可用）。

### 3. 打开网页

浏览器访问 **https://127.0.0.1:8000**。首次是自签证书，浏览器提示「不安全」→ 高级 → 继续访问即可。首页要加载 3D 模型和几十个前端模块，**10~30 秒属正常**，状态点变绿即就绪。

### 4. 前端开发（可选，运行期不需要）

跑 Phoenix 只需要 Python + Node.js，**不需要 `npm install`**：three.js / three-vrm 等库已随包放在 `web/vendor/`，由 `web/index.html` 的 importmap 引用。

```bash
npm install          # 只有改前端才需要：装 vite / tsc / three 这些构建期依赖
npm run dev          # vite 开发服务器（后端需已在 8000 跑着）
npm run typecheck    # tsc 类型检查
```

### 服务托管与重启（本机实际部署方式）

本机 server.py 由**系统级 systemd 单元** `myservice.service` 托管（`/etc/systemd/system/myservice.service`，`Restart=always` / 3s，enabled，另有 `10-recovery.conf`、`20-linux-native.conf`、`30-secrets.conf` 三个 drop-in 注入环境变量）。

```bash
tools/restart_server.sh              # 重启（委托 systemctl，再自检 + 落报告）
tools/restart_server.sh --delay 20   # 延迟 20 秒动手（给发起方留收尾时间）
tools/restart_server.sh --check      # 只体检不重启（rc=0 表示健康）
journalctl -u myservice.service -f   # 日志在这里，不在文件里
```

重启结果落在 `data/restart_report.txt`：新 PID / 状态 / 监听端口 / `tools/reload_check.py` 的核心文件生效检查 / journal 末尾。

两条经验（2026-09-13 实测）：① 不要自己 kill + spawn —— systemd 会在 3 秒后自己拉起，脚本再起的第二个实例只会 bind 失败；② 进程的 stdout 接的是 journald socket，所以「日志文件为空」不代表没日志，先看 `journalctl -u <unit>`。判断谁在托管只需一条命令：`cat /proc/<pid>/cgroup`。

## 📦 发布包里有什么、缺什么

发行包**不含私有模块与私有数据**，代码对它们一律做了可选依赖处理：缺了服务照常启动，只少对应功能。

### 私有模块（不随包发布，缺失时自动降级）

| 模块 | 缺失后的行为 |
| --- | --- |
| `email_verify.py` | 邮箱验证码注册与找回密码关闭：`/api/auth/status` 返回 `email_ready=false`（`server.py:822`），登录页自行隐藏邮箱入口；发码 / 换票据接口返回 400 `email_verify_disabled`（`server.py:840`、`server.py:869`），`auth_core.py:253`、`auth_core.py:424` 同样拒绝。**不会放行未验证的邮箱。** |
| `peer_watch.py` | 联邦节点观测关闭（`peer_mesh.py:400`），其余功能不受影响。 |

打包器把 `try/except ImportError` 直接包住的 import 判为可选依赖，单列提醒、不拦打包；裸 import 仍会拒绝出包（`deploy/release/build_release.py`）。

### 私有数据文件（不随包发布，首次运行自动生成）

读它们的代码自己兜默认值——`agent.py:1013` 的 `_read_json_or(path, default)`、`memory.py:2049` 读 `settings.json` 失败即用内置默认参数——所以缺文件不会让服务起不来；`tools/`、`tests/` 里的探针会直接 `FileNotFoundError`。

```text
character_cards.json   role_card_users.json   chat_memory.db   conviction.json
gene_stats.json   harness_task_memory.json   long_horizon.json   settings.json
skills/tasks/data/tasks.json   tts_config.json   video_favorites.json
```

清单不用手抄，按 AST 从代码里现算：

```bash
python3 deploy/release/build_release.py --list
# ! 11 个数据文件被 tools/tests 直接引用、但包里没有（跑探针会 FileNotFoundError）：
#     character_cards.json ← agent.py, server.py, tools/role_card_isolation_probe.py（3 处引用…）
```

### TLS 证书（不随包发布，首次启动现场自签）

包里**不带任何证书**——带一张固定的 CA，等于让每个装它的用户去信任发布方的根 CA（那张 CA 的私钥能签任意域名）。改成每台机器自己签：首次启动时 `tls_cert.py` 生成 `phoenix-ca.crt`（供手机下载安装，走 `/phoenix-ca.crt`）和服务器证书 `cert.pem` / `key.pem`。四个文件都留在本机，不入仓、不进包，私钥权限 600。

证书里写的是 IP，换网段时只重签服务器证书、CA 不动，手机已装好的根证书继续有效：

```bash
python3 tls_cert.py              # 缺什么补什么，IP 变了自动重签服务器证书
python3 tls_cert.py --print-san  # 只看这次会覆盖哪些地址
python3 tls_cert.py --force      # 整套重签（手机要重装一次根证书）
```

优先用 `cryptography` 模块，没装则退回 `openssl` 命令行。


### 纯净环境下已知为红的 4 个用例（不是代码缺陷）

| 用例 | 原因 |
| --- | --- |
| `tests/test_turn_handoff.py`（2 个） | 直读 `settings.json`，缺文件即 `FileNotFoundError` |
| `tests/test_autoload_skill.py::test_real_harness_loads_code_ops` | 缺 `settings.json` → `harness.progressive_disclosure` 取默认 `False`（`harness/core.py:349`），技能工具全部常驻，`shell_run` 落在基础工具里，与该用例的假设相反 |
| `tests/test_longrun_view.py::test_snapshot_has_fields_frontend_needs` | 长跑任务从未运行过，运行状态文件不存在，快照 `created_at=0` |

### 实例路径

不硬编码实例路径：`PHOENIX_HOME` 环境变量优先，回退按文件自身位置解析仓库根（`deploy/release/update.py:55`、`deploy/release/watch_release.py:122`）。

## 🖼️ 截图

> 在此处添加项目截图或演示动图。

## 🧠 上下文机制优化

### 1. 分层记忆（省 token）
- 短期窗口（最近轮次，按 `short_term_max_tokens` 预算、单轮超长截断）；
- 长期摘要（只带最新摘要，`summary_max_tokens` 预算）；
- 常驻长期记忆（按 importance 取 top-k，`long_term_max_tokens` 预算）；
- 按需召回（关键词检索，`recall_max_tokens` 强制封顶）。
- 每轮对话把 raw/packed 估算与真实 prompt 用量写入 `context_stats` 表，
  可直接按表内实际用量核算节省（实测约 70%+）。
- 详细设计见 [MEMORY_HIERARCHY.md](MEMORY_HIERARCHY.md)。

### 2. 工具参数严格校验
- 工具执行前按定义（`function.parameters`，与技能工具 inputSchema 同构）校验
  required、类型、enum、嵌套 object/array、数值/长度边界；
- 安全类型自动转换（"30"→30、"true"→True），无法转换或缺参时
  不执行工具，而是把中文错误回填给模型自行修正（`tool_validation.py`）。

### 3. 工具执行反馈 / 心跳
- 工具执行期间每 `tool_heartbeat_interval_sec`（默认 5s）向前端推送
  `tool_call_progress` 心跳事件，工具链卡片实时显示“已运行 N 秒”，
  长任务不再“静默无输出”；
- 超时以结构化错误回填给模型，不抛异常中断对话；并行工具调用同样带心跳。

## 🤝 参与贡献

欢迎提交 Issue 和 Pull Request。

## 📄 许可证

[MIT](LICENSE)
