"""音乐默认音量：初始 50%，且只在调用方明确指定时才改。

回归的坑：旧实现 `Number(JSON.parse(getItem(KEY) || 'null'))` 对全新用户得到
Number(null) === 0，而 0 能通过 0<=v<=1 的范围校验 —— 默认音量实际是「静音」，
那条 `return 0.5` 的兜底几乎永远走不到。
"""
import json
import os
import pathlib
import shutil
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
BGM_TS = ROOT / "web" / "js" / "audio" / "20_bgm_player.ts"
WS_TS = ROOT / "web" / "js" / "network" / "09_websocket.ts"
VOLUME_KEY = "dabai.musicVolume.v1"
DEFAULT_VOLUME = 0.5

# 转译走和服务端同一条路径（node 内置 stripTypeScriptTypes），不用装 npm 依赖
_TRANSPILE_JS = (
    "const fs=require('node:fs');"
    "const {stripTypeScriptTypes}=require('node:module');"
    "process.stdout.write(stripTypeScriptTypes(fs.readFileSync(process.env.BGM_TS_PATH,'utf8')));"
)

_STUB_JS = """
const store = new Map();
globalThis.localStorage = {
  getItem: (k) => (store.has(k) ? store.get(k) : null),
  setItem: (k, v) => store.set(k, String(v)),
};
globalThis.document = { addEventListener() {} };
globalThis.WebSocket = { OPEN: 1 };
const mod = await import(process.argv[2]);
const KEY = process.argv[3];
const mk = () => { const A = { ws: null, sendAIAction: null }; mod.default(A); return A; };
const cases = [
  ['fresh', null, 0.5],
  ['empty-string', '', 0.5],
  ['literal-null', 'null', 0.5],
  ['saved-0.35', '0.35', 0.35],
  ['user-muted-0', '0', 0],
  ['garbage', 'not-a-number', 0.5],
  ['out-of-range-5', '5', 0.5],
];
const out = [];
for (const [label, raw, want] of cases) {
  if (raw === null) store.delete(KEY); else store.set(KEY, raw);
  out.push([label, mk().getBGMState().volume, want]);
}
process.stdout.write(JSON.stringify(out));
"""


@pytest.mark.skipif(shutil.which("node") is None, reason="需要 node 转译前端 .ts")
def test_music_default_volume(tmp_path):
    node = shutil.which("node")
    env = dict(os.environ, BGM_TS_PATH=str(BGM_TS))
    tr = subprocess.run([node, "-e", _TRANSPILE_JS], capture_output=True,
                        text=True, env=env, timeout=60)
    assert tr.returncode == 0, f"转译失败：{tr.stderr}"
    assert "DEFAULT_MUSIC_VOLUME" in tr.stdout, "转译产物里没有默认音量常量"

    mjs = tmp_path / "bgm.mjs"
    mjs.write_text(tr.stdout, encoding="utf-8")
    stub = tmp_path / "stub.mjs"
    stub.write_text(_STUB_JS, encoding="utf-8")

    run = subprocess.run([node, str(stub), str(mjs), VOLUME_KEY],
                         capture_output=True, text=True, timeout=60)
    assert run.returncode == 0, f"桩脚本失败：{run.stderr}"
    got = json.loads(run.stdout)
    bad = [(label, val, want) for label, val, want in got if val != want]
    assert not bad, f"音量解析不符（场景, 实际, 期望）：{bad}"


def test_play_music_does_not_override_volume():
    """点歌指令不带 volume 时必须沿用用户音量，不能有 0.8 兜底把它顶掉。"""
    src = WS_TS.read_text(encoding="utf-8")
    assert "args.volume !== undefined ? args.volume : 0.8" not in src
    assert "args.value !== undefined ? Number(args.value) : 0.8" not in src


def test_default_volume_is_50_percent():
    src = BGM_TS.read_text(encoding="utf-8")
    assert f"DEFAULT_MUSIC_VOLUME = {DEFAULT_VOLUME}" in src
