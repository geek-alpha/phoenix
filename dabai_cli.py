#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""旧名兼容：dabai_cli.py 已改名为 phoenix_cli.py，这里只做转发。

保留的原因：已部署实例的 tools/longrun/runner.py 与 watchdog 的 pgrep 模式
里写死了 dabai_cli.py，删掉会让长跑任务直接断链。
"""
from __future__ import annotations

import os
import runpy
import sys

_TARGET = os.path.join(os.path.dirname(os.path.abspath(__file__)), "phoenix_cli.py")

if __name__ == "__main__":
    # 让 argparse 的帮助信息显示新名，而不是这个转发壳的名字
    sys.argv[0] = _TARGET
    runpy.run_path(_TARGET, run_name="__main__")
