# dabai

> 一个使用 JavaScript, Python, HTML, CSS 开发的项目。

![JavaScript](https://img.shields.io/badge/JavaScript-blue) ![Python](https://img.shields.io/badge/Python-blue) ![HTML](https://img.shields.io/badge/HTML-blue)

## ✨ 项目简介

该项目使用 **JavaScript, Python, HTML, CSS** 编写，包含 159 个文件，62,354 行代码。

## 🧠 Harness 扩展框架（技能 / 插件）

「大白」内置稳定的 harness 运行时，通过**技能（Skill）**与**插件（Plugin）**
持续扩展能力，无需改动核心代码：

- 📖 完整文档见 [HARNESS.md](HARNESS.md)
- 🖥 管理台：浏览器打开 http://<大白地址>/harness
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

### 安装

```bash
npm install
```

### 运行

```bash
npm start
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

### 纯净环境下已知为红的 4 个用例（不是代码缺陷）

| 用例 | 原因 |
| --- | --- |
| `tests/test_turn_handoff.py`（2 个） | 直读 `settings.json`，缺文件即 `FileNotFoundError` |
| `tests/test_autoload_skill.py::test_real_harness_loads_code_ops` | 缺 `settings.json` → `harness.progressive_disclosure` 取默认 `False`（`harness/core.py:349`），技能工具全部常驻，`shell_run` 落在基础工具里，与该用例的假设相反 |
| `tests/test_longrun_view.py::test_snapshot_has_fields_frontend_needs` | 长跑任务从未运行过，运行状态文件不存在，快照 `created_at=0` |

### 实例路径

不硬编码实例路径：`PHOENIX_HOME` 环境变量优先，回退按文件自身位置解析仓库根（`deploy/release/update.py:55`、`deploy/release/watch_release.py:122`）。

## 📁 项目结构

```text
dabai/
    ├── audio_cache/
        ├── 14206bf6641d466d9f4b7adc9cae2b0a.mp3
        ├── f38b3bf2a13949e49fddcd43bd96c409.mp3
    ├── backgrounds/
        ├── 太空飞船走廊.glb
        ├── 失落藏宝地.glb
        ├── 测试空间.glb
        ├── 迷宫.glb
    ├── bgm/
        ├── 6695671_光年之外-G.E.M.邓紫棋.余赛亚_eyW8s.mp3
        ├── 6703711_娃娃脸.mp3
    ├── cyber-corp-scoring/
        ├── _shared/
            ├── fonts/
            ├── js/
        ├── assets/
            ├── charts.js
        ├── cyber-corp-scoring.html
    ├── models/
        ├── models/
            ├── 可莉.vrm
            ├── 女仆.vrm
            ├── 女精灵.vrm
            ├── 小蛋糕.vrm
            ├── 水仙儿.vrm
            ├── 米尤.vrm
            ├── avatar.vrm
        ├── Ani_Grok.vrm
        ├── 可莉.vrm
        ├── 呆萌高中生.vrm
        ├── 夜乃樱.vrm
        ├── 女仆.vrm
        ├── 女精灵.vrm
        ├── 小蛋糕.vrm
        ├── 棕发学长.vrm
        ├── 水仙儿.vrm
        ├── 泳装普拉娜.vrm
        ├── 潮流穿搭女.vrm
        ├── 热可可.vrm
        ├── 白女.vrm
        ├── 知性女.vrm
        ├── 米尤.vrm
        ├── avatar.vrm
        ├── 黑裙清冷高中生.vrm
    ├── swarm-game-engine/
        ├── _shared/
            ├── fonts/
            ├── js/
        ├── assets/
            ├── charts.js
        ├── swarm-game-engine.html
    ├── tools/
        ├── gpt_sovits/
            ├── gpt_sovit_v2.py
            ├── gpt_sovits.json
    ├── web/
        ├── assets/
            ├── sounds/
        ├── js/
            ├── audio/
            ├── character/
            ├── core/
            ├── game/
            ├── input/
            ├── network/
            ├── ui/
            ├── vr/
        ├── app.ts
        ├── humanBaseline.json
        ├── index.html
        ├── style.css
    ├── xq3d/
        ├── assets/
            ├── three.module.min.js
        ├── css/
            ├── style.css
        ├── js/
            ├── ai.js
            ├── analysis.js
            ├── engine.js
            ├── main.js
            ├── notation.js
            ├── scene.js
            ├── ui.js
        ├── index.html
        ├── package.json
    ├── _gen_cert.py
    ├── agent.py
    ├── ai_behavior_engine.py
    ├── ai_game_strategies.py
    ├── ai_perception_engine.py
    ├── cards.json
    ├── cert.pem
    ├── cert.pem.bak
    ├── character_cards.json
    ├── dabai.bat
    ├── dabai.py
    ├── dabai4.0.zip
    ├── game_engine.py
    ├── key.pem
    ├── key.pem.bak
    ├── memory.py
    ├── package-lock.json
    ├── package.json
    ├── perception_dispatcher.py
    ├── reward_memory.json
    ├── reward_memory.py
    ├── rl_bandit.json
    ├── rl_coordinator.py
    ├── rl_dating_system_analysis.html
    ├── rl_interval.json
    ├── rl_mode_stats.json
    ├── rl_pushpull.json
    ├── rlhf_calibrator.py
    ├── rlhf_model.json
    ├── screen_shot.py
    ├── server.py
    ├── settings.json
    ├── test.py
    ├── tools.json
    ├── tts_config.json
    ├── world_model.json
    ├── world_model_trainer.py
```

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
