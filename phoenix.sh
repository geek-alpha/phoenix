#!/usr/bin/env bash
# Phoenix Linux / macOS 启动脚本（与 phoenix.bat 等价）
#
# 用法：
#   ./phoenix.sh              # 启动 server.py
#   ./phoenix.sh --setup      # 一键：建 venv + 装依赖 + 自检 + 启动（首次用这条）
#   ./phoenix.sh --check      # 只做环境自检，不启动
#
# 环境变量：
#   PHOENIX_PYTHON  指定解释器（默认：venv/bin/python → python3）
#   PHOENIX_PORT    覆盖端口（默认沿用 settings.json 配置）
#
# 旧名 DABAI_PYTHON / DABAI_PORT 继续可用（已部署实例的 systemd 与脚本里写死了）。
set -euo pipefail

cd "$(dirname "$(readlink -f "$0" 2>/dev/null || echo "$0")")"
ROOT="$(pwd)"

# ---- 参数分流：--setup / --help 自己处理，其余原样透传给 server.py ----
SETUP=0
PASS_ARGS=()
for a in "$@"; do
  case "$a" in
    --setup) SETUP=1 ;;
    -h|--help) sed -n '2,13p' "$0"; exit 0 ;;
    *) PASS_ARGS+=("$a") ;;
  esac
done
if [ ${#PASS_ARGS[@]} -gt 0 ]; then set -- "${PASS_ARGS[@]}"; else set --; fi

# ---- 一键引导：venv 不在、或启动必需依赖不全，都补装（幂等）----
# 只看 venv/bin/python 存在与否是不够的：上次装到一半（磁盘满 / 网络断）会留下一个
# 半成品 venv，再跑 --setup 会直接跳过，问题拖到启动时才炸。
if [ "$SETUP" = "1" ]; then
  # 依赖清单只有 tools/check_deps.py 一处（与 requirements.txt 同源），这里不内联抄。
  if [ ! -x "$ROOT/venv/bin/python" ] || \
     ! "$ROOT/venv/bin/python" "$ROOT/tools/check_deps.py" --gate >/dev/null 2>&1; then
    echo "== 环境缺失或依赖不全：创建虚拟环境并安装依赖 =="
    "$ROOT/tools/linux_setup.sh" --venv || {
      echo "✗ 环境创建失败。若缺系统包，先跑：$ROOT/tools/linux_setup.sh --install-system" >&2
      exit 1
    }
  fi
fi

# ---- 选解释器：优先项目内 venv，其次 PATH ----
PY="${PHOENIX_PYTHON:-${DABAI_PYTHON:-}}"
if [ -z "$PY" ]; then
  if [ -x "$ROOT/venv/bin/python" ]; then
    PY="$ROOT/venv/bin/python"
  elif [ -x "$ROOT/.venv/bin/python" ]; then
    PY="$ROOT/.venv/bin/python"
  elif command -v python3 >/dev/null 2>&1; then
    PY="$(command -v python3)"
  else
    echo "✗ 找不到 python3，请先安装 Python 3.10+ 或设置 PHOENIX_PYTHON" >&2
    exit 1
  fi
fi

# ---- 依赖自检（缺关键包时给出可执行命令，而不是让 server 崩在 import）----
if [ "${1:-}" = "--check" ]; then
  exec "$PY" "$ROOT/tools/selfcheck.py"
fi

# 依赖清单只在 tools/check_deps.py 里一份（与 requirements.txt 同源，Windows 上自动
# 豁免 uvloop/httptools）。以前这里内联抄了一遍，于是 uvloop/httptools/python-multipart
# 三个「一 import 就崩」的包全在盲区，问题留到启动才暴露。
if ! "$PY" "$ROOT/tools/check_deps.py"; then
  echo "  或一键补齐：$ROOT/phoenix.sh --setup" >&2
  exit 1
fi

export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8
exec "$PY" server.py "$@"
