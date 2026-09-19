#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""环境变量新旧名兼容：DABAI_* ↔ PHOENIX_* 双向同步。

改名把 dabai 换成 phoenix 时，环境变量不能直接换名：已部署实例的 systemd 单元、
crontab、启动脚本里写死的都是 DABAI_*（81 处引用），换了就是启动即失联。

做法：进程启动最早期跑一次双向同步 ——
  · 只设了 DABAI_X  → 补出 PHOENIX_X
  · 只设了 PHOENIX_X → 补出 DABAI_X
  · 两个都设且不同值 → 新名优先（把旧名覆盖成新名的值）
之后新代码读 PHOENIX_*、老代码读 DABAI_*，两边拿到同一个值。
"""
from __future__ import annotations

import os

LEGACY_PREFIX = "DABAI_"
PREFIX = "PHOENIX_"


def promote_legacy_env() -> dict[str, str]:
    """同步两个前缀的环境变量，返回 {被写入的变量名: 来源}。幂等，可重复调用。"""
    synced: dict[str, str] = {}
    for key in list(os.environ):  # 快照：本轮新写入的键不参与本轮遍历，避免自激
        if key.startswith(LEGACY_PREFIX):
            new_key = PREFIX + key[len(LEGACY_PREFIX):]
            if new_key not in os.environ:
                os.environ[new_key] = os.environ[key]
                synced[new_key] = key
            elif os.environ[new_key] != os.environ[key]:
                os.environ[key] = os.environ[new_key]  # 新名优先，回写旧名
                synced[key] = new_key
        elif key.startswith(PREFIX):
            old_key = LEGACY_PREFIX + key[len(PREFIX):]
            if old_key not in os.environ:
                os.environ[old_key] = os.environ[key]
                synced[old_key] = key
    return synced
