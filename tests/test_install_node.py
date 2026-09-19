#!/usr/bin/env python3
"""install_node.py 回归 —— 盯住两处最容易变成「装是装上了、网页还是打不开」的判定。

1) 版本下限。module.stripTypeScriptTypes 的 Added in 是 v23.2.0 / v22.13.0（Node
   官方 module.json 的 meta.added）。判低了会放过 22.6~22.12 这批「装了 Node 但没有
   这个 API」的版本 —— 自动安装报告成功，用户看到的还是永远「连接中…」。
   元组比较 `(major, minor) >= (22, 13)` 在这里是错的：它会把 23.0/23.1 当成
   「比 22.13 新」而放行。
2) 解压剥层。zip 顶层是 node-v22.23.2-win-x64/，不剥掉的话 node.exe 埋在子目录里，
   private_exe() 永远找不到，等于白装。
"""
import importlib.util
import zipfile
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("install_node_under_test", BASE / "tools" / "install_node.py")
inode = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(inode)


@pytest.mark.parametrize("raw,want", [
    ("v22.23.2", (22, 23, 2)),
    ("22.13.0\n", (22, 13, 0)),
    ("V23.2.0", (23, 2, 0)),
    ("v22.13", (22, 13, 0)),
    ("", None),
    ("garbage", None),
    ("v22.x.0", None),
    ("v24.0.0-rc.1", (24, 0, 0)),
])
def test_parse_version(raw, want):
    assert inode.parse_version(raw) == want


def test_min_version_is_the_documented_added_in():
    """下限必须是 Node 文档里的 Added in 版本，不能凭感觉放宽。"""
    assert inode.MIN_VERSION == (22, 13)


@pytest.mark.parametrize("ver,want", [
    ((22, 12, 9), False),   # 22.12 还没有 stripTypeScriptTypes
    ((22, 13, 0), True),
    ((22, 23, 2), True),
    ((23, 0, 0), False),    # 元组比较陷阱：23.0 不比 22.13「新」，它根本没这个 API
    ((23, 1, 0), False),
    ((23, 2, 0), True),
    ((24, 0, 0), True),
    ((20, 19, 2), False),   # Debian 13 apt 自带的就是这个版本
    (None, False),
])
def test_is_supported(ver, want):
    assert inode.is_supported(ver) is want


def _make_zip(path: Path, entries: dict) -> None:
    with zipfile.ZipFile(path, "w") as zf:
        for name, data in entries.items():
            zf.writestr(name, data)


def test_extract_strips_top_level(tmp_path):
    zip_path = tmp_path / "node.zip"
    _make_zip(zip_path, {
        "node-v22.23.2-win-x64/": b"",
        "node-v22.23.2-win-x64/node.exe": b"binary",
        "node-v22.23.2-win-x64/npm/bin/x.js": b"js",
    })
    dest = tmp_path / "out"
    dest.mkdir()
    assert inode.extract_strip_top(zip_path, dest) == 0
    assert (dest / "node.exe").read_bytes() == b"binary"
    assert (dest / "npm" / "bin" / "x.js").read_bytes() == b"js"
    assert not (dest / "node-v22.23.2-win-x64").exists()


def test_extract_rejects_path_escape(tmp_path):
    zip_path = tmp_path / "bad.zip"
    _make_zip(zip_path, {"top/../../evil.txt": b"x"})
    dest = tmp_path / "out"
    dest.mkdir()
    with pytest.raises(RuntimeError, match="越界"):
        inode.extract_strip_top(zip_path, dest)


def _fake_node(path: Path, version: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"#!/bin/sh\necho {version}\n")
    path.chmod(0o755)
    return path


def test_find_usable_prefers_private_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setenv("PATH", "")
    exe = _fake_node(inode.private_exe(), "v22.23.2")
    found, ver = inode.find_usable()
    assert found == exe
    assert ver == (22, 23, 2)


def test_find_usable_rejects_too_old(tmp_path, monkeypatch):
    """装了 20.x 的机器必须判定为「不可用」——否则不会触发自动安装。"""
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setenv("PATH", "")
    _fake_node(inode.private_exe(), "v20.19.2")
    assert inode.find_usable() == (None, None)


def test_ensure_refuses_on_non_windows(monkeypatch, capsys):
    monkeypatch.setattr(inode, "is_windows", lambda: False)
    assert inode.do_ensure() == 1
    assert "FAIL" in capsys.readouterr().out


def test_ensure_reports_ok_without_downloading(monkeypatch, capsys):
    """已就绪时必须直接回路径，不能再去下 35 MB。"""
    monkeypatch.setattr(inode, "is_windows", lambda: True)
    monkeypatch.setattr(inode, "find_usable", lambda: (Path("/x/node"), (22, 23, 2)))

    def _boom(*a, **k):
        raise AssertionError("已就绪却仍然发起了下载")

    monkeypatch.setattr(inode, "download", _boom)
    assert inode.do_ensure() == 0
    assert capsys.readouterr().out.strip() == "OK /x/node"
