#!/usr/bin/env python3
"""启动前依赖自检 —— 缺「启动必需」包就打印清单并以 1 退出。

单一来源：清单与 requirements.txt 的「启动必需」段同源（uvloop/httptools 在 Windows
上豁免，跟那份文件里的 sys_platform 标记一致）。dabai.sh / dabai.bat / selfcheck.py
都调这里，避免三处各写一份清单、各自漂。

用法：
    python3 tools/check_deps.py          # 人类可读；缺包 → 退出 1
    python3 tools/check_deps.py --json   # 机器可读
"""
from __future__ import annotations

import importlib.util
import json
import sys

# (import 名, requirements 里的包名, 是否 Windows 豁免)
REQUIRED: list[tuple[str, str, bool]] = [
    ("fastapi", "fastapi", False),
    ("uvicorn", "uvicorn", False),
    ("multipart", "python-multipart", False),
    ("websockets", "websockets", False),
    ("uvloop", "uvloop", True),
    ("httptools", "httptools", True),
    ("aiohttp", "aiohttp", False),
    ("requests", "requests", False),
    ("starlette", "starlette", False),
    ("numpy", "numpy", False),
    ("edge_tts", "edge-tts", False),
    ("openai", "openai", False),
]


def _exempt(win_exempt: bool) -> bool:
    return win_exempt and sys.platform == "win32"


def missing() -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for mod, pkg, win_exempt in REQUIRED:
        if _exempt(win_exempt):
            continue
        try:
            found = importlib.util.find_spec(mod) is not None
        except (ImportError, ValueError):
            found = False
        if not found:
            out.append((mod, pkg))
    return out


def main() -> int:
    miss = missing()
    if "--json" in sys.argv:
        print(json.dumps({"missing": [{"module": m, "package": p} for m, p in miss]},
                         ensure_ascii=False))
        return 1 if miss else 0
    if miss:
        print("[X] 缺少启动必需依赖：" + ", ".join(p for _, p in miss))
        print("    安装：python -m pip install -r requirements.txt")
        print("    或一键补齐：dabai.sh --setup  /  dabai.bat --setup")
        return 1
    checked = len([1 for _, _, e in REQUIRED if not _exempt(e)])
    print(f"[ OK ] 启动必需依赖齐全（{checked} 项，平台 {sys.platform}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
