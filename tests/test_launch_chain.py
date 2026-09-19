"""启动链路的守卫测试：一键脚本引用的文件必须真实存在，依赖清单不能漂。

为什么需要：requirements.txt 曾经和 requirements-linux.txt 各写一份、靠人肉同步，
结果 requirements.txt 里 11 个名字在 PyPI 上根本不存在（bpy / imp / TodoService…），
Windows 用户 pip install 直接失败；server.py 又硬编码 loop="uvloop"，而 uvloop 没有
Windows wheel，装上就崩。这些都不是逻辑错误，是「没人盯着就会漂」的清单和路径，
所以用测试钉住。
"""
from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# PyPI 上不存在的名字：Blender 内嵌模块、Python 3.12 已移除的标准库、本机私有包。
NON_PYPI = [
    "bpy", "bmesh", "mathutils", "addon_utils", "rna_prop_ui", "imp",
    "TodoService", "amazing_agent_dingding", "dabai_ears", "dabai_voice",
    "fuctions_all_you_need_base",
]


def _req_lines(name: str) -> list[str]:
    out: list[str] = []
    for raw in (ROOT / name).read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if line:
            out.append(line)
    return out


def _load_check_deps():
    spec = importlib.util.spec_from_file_location("check_deps", ROOT / "tools" / "check_deps.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_requirements_has_no_non_pypi_names():
    lines = _req_lines("requirements.txt")
    bad = [n for n in NON_PYPI if any(re.match(rf"^{re.escape(n)}\b", ln) for ln in lines)]
    assert not bad, f"requirements.txt 里仍有 PyPI 上不存在的名字：{bad}"


def test_requirements_markers_parse():
    """环境标记必须能被解析——写错一个引号，pip 就报 InvalidRequirement。"""
    packaging_req = pytest.importorskip("packaging.requirements")
    for line in _req_lines("requirements.txt"):
        packaging_req.Requirement(line)


def test_check_deps_covers_requirements():
    """check_deps 的清单必须都在 requirements.txt 里，否则「自检说齐全、pip 装不上」。"""
    mod = _load_check_deps()
    haystack = " ".join(_req_lines("requirements.txt")).lower()
    missing = [pkg for _, pkg, _ in mod.REQUIRED if pkg.lower() not in haystack]
    assert not missing, f"check_deps 里这些包没写进 requirements.txt：{missing}"


def test_uvloop_httptools_are_windows_exempt():
    mod = _load_check_deps()
    exempt = {pkg for _, pkg, e in mod.REQUIRED if e}
    assert exempt == {"uvloop", "httptools"}
    for pkg in exempt:
        hit = [ln for ln in _req_lines("requirements.txt") if ln.lower().startswith(pkg)]
        assert hit and "sys_platform" in hit[0], f"{pkg} 缺 sys_platform 标记，Windows 上会尝试安装"


def test_launch_scripts_reference_existing_files():
    """脚本里写死的 tools/* 路径必须真实存在——改名漏一处就是启动即崩。"""
    for script in ("phoenix.sh", "phoenix.bat", "tools/linux_setup.sh"):
        text = (ROOT / script).read_text(encoding="utf-8")
        for ref in sorted(set(re.findall(r"tools[/\\]([A-Za-z0-9_]+\.(?:py|sh))", text))):
            assert (ROOT / "tools" / ref).is_file(), f"{script} 引用了不存在的 tools/{ref}"


def test_bat_and_sh_options_aligned():
    """Windows 与 Linux 的入口脚本必须支持同一组开关，否则「一键启动」只在一边成立。"""
    sh = (ROOT / "phoenix.sh").read_text(encoding="utf-8")
    bat = (ROOT / "phoenix.bat").read_text(encoding="utf-8")
    for opt in ("--setup", "--check"):
        assert opt in sh, f"phoenix.sh 缺 {opt}"
        assert opt in bat, f"phoenix.bat 缺 {opt}"


def test_bat_goto_labels_exist():
    """bat 的 goto 目标必须存在——标签写错，cmd 会一路走到文件末尾静默退出。"""
    bat = (ROOT / "phoenix.bat").read_text(encoding="utf-8")
    labels = {m.group(1).lower() for m in re.finditer(r"^\s*:([A-Za-z0-9_]+)\s*$", bat, re.M)}
    targets = {m.group(1).lower() for m in re.finditer(r"\bgoto\s+([A-Za-z0-9_]+)", bat, re.I)}
    assert targets <= labels, f"phoenix.bat 的 goto 指向不存在的标签：{sorted(targets - labels)}"


def test_server_does_not_hardcode_uvloop():
    """server.py 不许再硬编码 loop="uvloop"：Windows 上 uvloop 没有 wheel，启动即崩。"""
    src = (ROOT / "server.py").read_text(encoding="utf-8")
    code = "\n".join(ln for ln in src.splitlines() if not ln.strip().startswith("#"))
    assert not re.search(r"""loop\s*=\s*["']uvloop["']""", code), "server.py 仍有硬编码 uvloop"
    assert not re.search(r"""http\s*=\s*["']httptools["']""", code), "server.py 仍有硬编码 httptools"


def test_requirements_linux_is_compat_shell():
    assert _req_lines("requirements-linux.txt") == ["-r requirements.txt"], \
        "requirements-linux.txt 应只剩指向 requirements.txt 的兼容壳"


def test_legacy_dead_cli_removed():
    """dabai.py 引用不存在的 amazing_agent_dingding/dabai_voice/dabai_ears，是不可运行的死代码。"""
    assert not (ROOT / "dabai.py").exists()


def _load_env_compat():
    spec = importlib.util.spec_from_file_location("env_compat", ROOT / "env_compat.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_new_entry_points_exist():
    """新入口一个都不能少：文档里写的就是这四个名字。"""
    for name in ("phoenix.sh", "phoenix.bat", "phoenix", "phoenix_cli.py"):
        assert (ROOT / name).is_file(), f"新入口缺失：{name}"


def test_legacy_aliases_forward_to_new_names():
    """旧名必须留转发壳：已部署实例的 systemd / crontab / 旧文档里写死了 dabai.*，
    升级后删掉就是断链。壳里必须出现新名——否则转发到自己会无限递归。"""
    for legacy, target in (("dabai.sh", "phoenix.sh"), ("dabai.bat", "phoenix.bat"),
                           ("dabai", "phoenix"), ("dabai_cli.py", "phoenix_cli.py")):
        path = ROOT / legacy
        assert path.is_file(), f"旧名转发壳缺失：{legacy}（已部署实例会断链）"
        assert target in path.read_text(encoding="utf-8"), f"{legacy} 没有转发到 {target}"


def test_launch_scripts_do_not_reference_old_names():
    """新入口里不许再出现旧名——脚本自己引用自己，用户按提示敲的就是不存在的文件。"""
    for script in ("phoenix.sh", "phoenix.bat"):
        text = (ROOT / script).read_text(encoding="utf-8")
        body = "\n".join(ln for ln in text.splitlines()
                         if not ln.strip().startswith(("#", "rem")))
        assert "dabai.sh" not in body and "dabai.bat" not in body, \
            f"{script} 仍在引用旧脚本名"


def test_env_compat_bridges_both_prefixes(monkeypatch):
    """改名不能断环境变量：只设旧名要能读到新名、只设新名要能读到旧名、冲突时新名优先。"""
    import os

    mod = _load_env_compat()

    def clear():
        for k in [k for k in os.environ if k.startswith(("DABAI_", "PHOENIX_"))]:
            os.environ.pop(k, None)

    for k in [k for k in os.environ if k.startswith(("DABAI_", "PHOENIX_"))]:
        monkeypatch.delenv(k, raising=False)
    try:
        clear()
        os.environ["DABAI_PORT"] = "9001"
        mod.promote_legacy_env()
        assert os.environ.get("PHOENIX_PORT") == "9001", "旧名没有提升为新名"

        clear()
        os.environ["PHOENIX_WORKSPACE"] = "/tmp/ws"
        mod.promote_legacy_env()
        assert os.environ.get("DABAI_WORKSPACE") == "/tmp/ws", "新名没有回填旧名"

        clear()
        os.environ["DABAI_PORT"], os.environ["PHOENIX_PORT"] = "1", "2"
        mod.promote_legacy_env()
        assert os.environ["DABAI_PORT"] == "2", "两个都设且不同值时，应新名优先"
    finally:
        clear()
        monkeypatch.undo()


@pytest.mark.skipif(sys.platform == "win32", reason="Windows 没有 POSIX 可执行位")
def test_shell_entry_points_are_executable():
    """入口脚本丢了 +x 就是 Permission denied —— 用户照文档敲的第一条命令就失败。

    踩过：新建的转发壳默认 644，把 git mv 保住的 755 覆盖掉，而测试只查内容不查权限，
    一路绿灯到用户手上才炸。
    """
    for name in ("phoenix.sh", "phoenix", "dabai.sh", "dabai"):
        mode = (ROOT / name).stat().st_mode
        assert mode & 0o111, f"{name} 没有可执行位（chmod +x）"
