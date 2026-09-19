#!/usr/bin/env bash
# 旧名兼容：dabai.sh 已改名为 phoenix.sh，这里只做转发。
# 保留的原因：已部署实例的 crontab / systemd / 旧文档里写死了 ./dabai.sh。
exec "$(dirname "$(readlink -f "$0" 2>/dev/null || echo "$0")")/phoenix.sh" "$@"
