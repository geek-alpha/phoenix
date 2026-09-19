#!/usr/bin/env python3
"""启动前依赖自检 —— 缺「启动必需」包就打印清单并以 1 退出。

单一来源：清单与 requirements.txt 的「启动必需」段同源（uvloop/httptools 在 Windows
上豁免，跟那份文件里的 sys_platform 标记一致）。phoenix.sh / phoenix.bat / selfcheck.py
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
# 启动必需：缺任意一项 server.py 都起不来。
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

# 能力依赖：缺了服务照常启动，但对应功能会整块失效。
# 为什么不并进 REQUIRED：并进去会让「只想聊天」的用户被一条视频依赖挡在门外；
# 为什么不干脆不查：yt_dlp 曾经就是这样漏的——它在 requirements.txt 的「启动必需」段里，
# 却不在这个清单里，于是 phoenix.bat --setup 判定「依赖齐全」直接跳过安装，
# yt_dlp 永远装不上、也永远查不出来，用户只看到视频功能全废。
# (import 名, requirements 里的包名, 缺了会失去什么)
CAPABILITY: list[tuple[str, str, str]] = [
    ("yt_dlp", "yt-dlp", "视频搜索 / 热门 / 点播（YouTube、自定义源与 B 站 yt-dlp 兜底路径）"),
    ("PIL", "Pillow", "图片缩略图与图像处理"),
    ("tree_sitter", "tree-sitter", "代码结构感知检索（symbols / code_map）"),
    ("mss", "mss", "截屏"),
    ("netifaces", "netifaces", "网卡枚举兜底（全局 IPv6 探测）"),
    ("gradio_client", "gradio_client", "Gradio 客户端能力"),
    ("cryptography", "cryptography", "自签 TLS 证书首选后端（缺了退 openssl 命令行）"),
    ("pypdf", "pypdf", "PDF 附件正文提取"),
    ("qrcode", "qrcode", "手机配对二维码"),
]


def _exempt(win_exempt: bool) -> bool:
    return win_exempt and sys.platform == "win32"


def _found(mod: str) -> bool:
    try:
        return importlib.util.find_spec(mod) is not None
    except (ImportError, ValueError):
        return False


def missing() -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for mod, pkg, win_exempt in REQUIRED:
        if _exempt(win_exempt):
            continue
        if not _found(mod):
            out.append((mod, pkg))
    return out


def missing_capability() -> list[tuple[str, str, str]]:
    """返回缺失的能力依赖：(import 名, 包名, 会失去什么)。"""
    return [(mod, pkg, what) for mod, pkg, what in CAPABILITY if not _found(mod)]


def main() -> int:
    miss = missing()
    miss_cap = missing_capability()
    # --gate：只要「启动必需」或「能力依赖」有缺就退出 1。
    # 供 phoenix.sh/bat 的 --setup 判定用——用默认模式（缺能力依赖退出 0）会让
    # --setup 看到「齐全」直接跳过 pip install，缺的包永远补不上。
    gate = "--gate" in sys.argv
    if "--json" in sys.argv:
        print(json.dumps({
            "missing": [{"module": m, "package": p} for m, p in miss],
            "missing_capability": [{"module": m, "package": p, "loses": w}
                                   for m, p, w in miss_cap],
        }, ensure_ascii=False))
        return 1 if (miss or (gate and miss_cap)) else 0
    if miss:
        print("[X] 缺少启动必需依赖：" + ", ".join(p for _, p in miss))
        print("    安装：python -m pip install -r requirements.txt")
        print("    或一键补齐：phoenix.sh --setup  /  phoenix.bat --setup")
        return 1
    if miss_cap:
        print("[!] 缺少能力依赖（服务能启动，以下功能不可用）：")
        for _, pkg, what in miss_cap:
            print(f"      - {pkg}：{what}")
        print("    补齐：phoenix.sh --setup  /  phoenix.bat --setup")
        if gate:
            return 1
    checked = len([1 for _, _, e in REQUIRED if not _exempt(e)])
    if not miss_cap:
        print(f"[ OK ] 依赖齐全（启动必需 {checked} 项 + 能力依赖 {len(CAPABILITY)} 项，"
              f"平台 {sys.platform}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
