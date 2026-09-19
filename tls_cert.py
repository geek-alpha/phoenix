#!/usr/bin/env python3
"""本机 TLS 证书：自签一张 CA + 一张服务器证书，首次启动时生成。

为什么包里不带现成的 CA：CA 私钥只要留在发布方手里，装过这张 CA 的手机就等于
把「签发任意域名证书」的能力交了出去 —— 而手机装根证书正是手机端离线缓存
（Service Worker 必须 HTTPS）的前提。改成每台机器自己签，谁都不用信别人。

生成物（都在本机，不入仓、不进包；私钥一律不放 web/，那个目录挂在 /static 下）：

  phoenix-ca.crt   根证书，供手机下载安装（/phoenix-ca.crt）
  phoenix-ca.key   CA 私钥，续签服务器证书用
  cert.pem         服务器证书（server.py 直接读）
  key.pem          服务器私钥

换网段时只重签服务器证书、CA 不动，手机已装的根证书继续有效 —— 证书里写的是
IP，IP 变了不重签，手机上只会看到一句含糊的「不安全」。

用法：
    python tls_cert.py                # 缺什么补什么，IP 变了自动重签服务器证书
    python tls_cert.py --force        # 整套重签（手机要重装根证书）
    python tls_cert.py --print-san    # 只看这次会覆盖哪些地址
"""

from __future__ import annotations

import argparse
import ipaddress
import shutil
import socket
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

CA_FILE = "phoenix-ca.crt"
CA_KEY_FILE = "phoenix-ca.key"
LEAF_FILE = "cert.pem"
LEAF_KEY_FILE = "key.pem"

CA_COMMON_NAME = "Phoenix Local CA"
CA_ORG = "Phoenix"
CA_DAYS = 3650
LEAF_DAYS = 397          # 苹果对 TLS 证书的上限是 398 天，留一天余量
RSA_BITS = 2048


# ── 地址探测 ─────────────────────────────────────────────────────────────
def detect_ips(extra: Iterable[str] = ()) -> List[str]:
    """本机能被访问到的地址：回环 + 默认出口网卡 + 主机名解析结果。

    SAN 必须写死地址，写漏了手机连上就是「证书无效」，而这一层错在浏览器里
    只会显示成一句含糊的「不安全」，根本看不出是证书里少了个 IP。
    """
    ips: List[str] = ["127.0.0.1", "::1"]

    def _add(ip: str) -> None:
        ip = str(ip).split("%", 1)[0]      # 去掉 IPv6 的 scope id（fe80::1%eth0）
        if not ip or ip in ips:
            return
        try:
            addr = ipaddress.ip_address(ip)
        except ValueError:
            return
        # 链路本地地址（169.254/16、fe80::/10）只在本段链路可用，写进 SAN
        # 是纯噪音；组播/未指定地址同理。
        if addr.is_link_local or addr.is_multicast or addr.is_unspecified:
            return
        ips.append(ip)

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))     # 不发包，只让内核选出出口网卡
            _add(s.getsockname()[0])
        finally:
            s.close()
    except OSError:
        pass

    for family in (socket.AF_INET, socket.AF_INET6):
        try:
            infos = socket.getaddrinfo(socket.gethostname(), None, family)
        except OSError:
            continue
        for info in infos:
            _add(info[4][0])

    for ip in extra:
        _add(ip)
    return ips


def detect_names(extra: Iterable[str] = ()) -> List[str]:
    names = ["localhost"]

    def _add(name: str) -> None:
        name = (name or "").strip()
        if not name or name in names:
            return
        try:
            name.encode("ascii")           # 中文主机名不能进 SAN
        except UnicodeEncodeError:
            return
        names.append(name)

    host = socket.gethostname()
    _add(host)
    _add(host.split(".", 1)[0] + ".local")
    for n in extra:
        _add(n)
    return names


def _san_text(ips: Sequence[str], names: Sequence[str]) -> str:
    return ", ".join(list(names) + list(ips))


# ── 后端：cryptography 优先，退回 openssl 命令行 ──────────────────────────
def _pick_backend() -> str:
    try:
        import cryptography  # noqa: F401
        return "cryptography"
    except Exception:
        pass
    if shutil.which("openssl"):
        return "openssl"
    raise RuntimeError(
        "既没有 cryptography 模块、也没有 openssl 命令，无法生成 TLS 证书。"
        "装一个即可：pip install cryptography"
    )


def _crypto():
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    return x509, hashes, serialization, rsa


def _crypto_ca() -> Dict[str, object]:
    x509, hashes, serialization, rsa = _crypto()
    from cryptography.x509.oid import NameOID

    now = datetime.now(timezone.utc)
    key = rsa.generate_private_key(public_exponent=65537, key_size=RSA_BITS)
    name = x509.Name([
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, CA_ORG),
        x509.NameAttribute(NameOID.COMMON_NAME, CA_COMMON_NAME),
    ])
    cert = (
        x509.CertificateBuilder()
        .subject_name(name).issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))   # 容忍客户端时钟略慢
        .not_valid_after(now + timedelta(days=CA_DAYS))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=False, content_commitment=False, key_encipherment=False,
                data_encipherment=False, key_agreement=False, key_cert_sign=True,
                crl_sign=True, encipher_only=False, decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()),
                       critical=False)
        .sign(key, hashes.SHA256())
    )
    return {
        "cert_pem": cert.public_bytes(serialization.Encoding.PEM),
        "key_pem": key.private_bytes(serialization.Encoding.PEM,
                                     serialization.PrivateFormat.PKCS8,
                                     serialization.NoEncryption()),
        "cert_obj": cert, "key_obj": key,
    }


def _crypto_leaf(ips: Sequence[str], names: Sequence[str],
                 ca_cert: object, ca_key: object) -> Dict[str, bytes]:
    x509, hashes, serialization, rsa = _crypto()
    from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

    now = datetime.now(timezone.utc)
    key = rsa.generate_private_key(public_exponent=65537, key_size=RSA_BITS)
    alt: List[object] = [x509.DNSName(n) for n in names]
    alt += [x509.IPAddress(ipaddress.ip_address(ip)) for ip in ips]
    cert = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, CA_ORG),
            x509.NameAttribute(NameOID.COMMON_NAME, ips[0] if ips else "localhost"),
        ]))
        .issuer_name(ca_cert.subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=LEAF_DAYS))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True, content_commitment=False, key_encipherment=True,
                data_encipherment=False, key_agreement=False, key_cert_sign=False,
                crl_sign=False, encipher_only=False, decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]),
                       critical=False)
        .add_extension(x509.SubjectAlternativeName(alt), critical=False)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()),
                       critical=False)
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()),
            critical=False,
        )
        .sign(ca_key, hashes.SHA256())
    )
    return {
        "cert_pem": cert.public_bytes(serialization.Encoding.PEM),
        "key_pem": key.private_bytes(serialization.Encoding.PEM,
                                     serialization.PrivateFormat.PKCS8,
                                     serialization.NoEncryption()),
    }


def _crypto_load_ca(cert_pem: bytes, key_pem: bytes) -> Tuple[object, object]:
    x509, _hashes, serialization, _rsa = _crypto()
    return (x509.load_pem_x509_certificate(cert_pem),
            serialization.load_pem_private_key(key_pem, password=None))


def _crypto_missing_address(cert_path: Path, ips: Sequence[str],
                            names: Sequence[str]) -> List[str]:
    """已有服务器证书里缺哪些当前地址（空列表 = 够用）。"""
    try:
        x509, _h, _s, _r = _crypto()
        cert = x509.load_pem_x509_certificate(cert_path.read_bytes())
        ext = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
        have = set(ext.get_values_for_type(x509.DNSName))
        have |= {str(v) for v in ext.get_values_for_type(x509.IPAddress)}
    except Exception:
        return []
    return [x for x in list(names) + list(ips) if x not in have]


def _openssl(*args: str) -> None:
    p = subprocess.run(["openssl", *args], capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"openssl {args[0]} 失败：{p.stderr.strip()}")


def _openssl_ca() -> Dict[str, bytes]:
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        key, crt = t / "ca.key", t / "ca.crt"
        _openssl("req", "-x509", "-newkey", f"rsa:{RSA_BITS}", "-nodes",
                 "-keyout", str(key), "-out", str(crt), "-days", str(CA_DAYS),
                 "-subj", f"/O={CA_ORG}/CN={CA_COMMON_NAME}",
                 "-addext", "basicConstraints=critical,CA:TRUE,pathlen:0",
                 "-addext", "keyUsage=critical,keyCertSign,cRLSign")
        return {"cert_pem": crt.read_bytes(), "key_pem": key.read_bytes()}


def _openssl_leaf(ips: Sequence[str], names: Sequence[str],
                  ca_cert_pem: bytes, ca_key_pem: bytes) -> Dict[str, bytes]:
    san = ",".join([f"DNS:{n}" for n in names] + [f"IP:{ip}" for ip in ips])
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        ca_key, ca_crt = t / "ca.key", t / "ca.crt"
        ca_key.write_bytes(ca_key_pem)
        ca_crt.write_bytes(ca_cert_pem)
        leaf_key, leaf_csr, leaf_crt = t / "leaf.key", t / "leaf.csr", t / "leaf.crt"
        _openssl("req", "-newkey", f"rsa:{RSA_BITS}", "-nodes",
                 "-keyout", str(leaf_key), "-out", str(leaf_csr),
                 "-subj", f"/O={CA_ORG}/CN={ips[0] if ips else 'localhost'}")
        ext = t / "leaf.ext"
        ext.write_text(
            "basicConstraints=critical,CA:FALSE\n"
            "keyUsage=critical,digitalSignature,keyEncipherment\n"
            "extendedKeyUsage=serverAuth\n"
            f"subjectAltName={san}\n"
            "subjectKeyIdentifier=hash\n"
            "authorityKeyIdentifier=keyid,issuer\n",
            encoding="utf-8",
        )
        _openssl("x509", "-req", "-in", str(leaf_csr), "-CA", str(ca_crt),
                 "-CAkey", str(ca_key), "-CAcreateserial", "-out", str(leaf_crt),
                 "-days", str(LEAF_DAYS), "-extfile", str(ext))
        return {"cert_pem": leaf_crt.read_bytes(), "key_pem": leaf_key.read_bytes()}


# ── 对外接口 ─────────────────────────────────────────────────────────────
def cert_paths(base_dir: str | Path) -> Tuple[Path, Path, Path, Path]:
    b = Path(base_dir)
    return b / CA_FILE, b / CA_KEY_FILE, b / LEAF_FILE, b / LEAF_KEY_FILE


def _write(path: Path, data: bytes, *, secret: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data)
    if secret:
        try:
            tmp.chmod(0o600)
        except OSError:
            pass
    tmp.replace(path)


def ensure_certs(base_dir: str | Path, *, extra_ips: Iterable[str] = (),
                 extra_names: Iterable[str] = (), force: bool = False,
                 quiet: bool = False) -> dict:
    """缺什么补什么。已有的 CA 尽量留着 —— 换掉它，手机就得重装根证书。"""
    ca_crt, ca_key, leaf_crt, leaf_key = cert_paths(base_dir)
    had_ca = ca_crt.is_file() or ca_key.is_file()
    if force:
        for p in (ca_crt, ca_key, leaf_crt, leaf_key):
            p.unlink(missing_ok=True)

    have_ca = ca_crt.is_file() and ca_key.is_file()
    have_leaf = leaf_crt.is_file() and leaf_key.is_file()

    ips = detect_ips(extra_ips)
    names = detect_names(extra_names)

    # 服务器证书里写的是 IP，换网段后旧证书就不匹配了：只重签它，CA 不动
    stale = have_leaf and bool(_crypto_missing_address(leaf_crt, ips, names))
    if have_ca and have_leaf and not stale:
        return {"created": False, "renewed": "", "ca_cert": ca_crt,
                "leaf_cert": leaf_crt, "leaf_key": leaf_key, "ca_key": ca_key}

    backend = _pick_backend()
    if have_ca and (stale or not have_leaf):
        ca_pem, ca_key_pem = ca_crt.read_bytes(), ca_key.read_bytes()
        if backend == "cryptography":
            leaf = _crypto_leaf(ips, names, *_crypto_load_ca(ca_pem, ca_key_pem))
        else:
            leaf = _openssl_leaf(ips, names, ca_pem, ca_key_pem)
        _write(leaf_crt, leaf["cert_pem"])
        _write(leaf_key, leaf["key_pem"], secret=True)
        renewed = "leaf"
    else:
        # CA 缺了或残缺：整套重签，手机需要重新安装根证书
        if backend == "cryptography":
            ca = _crypto_ca()
            leaf = _crypto_leaf(ips, names, ca["cert_obj"], ca["key_obj"])
        else:
            ca = _openssl_ca()
            leaf = _openssl_leaf(ips, names, ca["cert_pem"], ca["key_pem"])
        _write(ca_crt, ca["cert_pem"])
        _write(ca_key, ca["key_pem"], secret=True)
        _write(leaf_crt, leaf["cert_pem"])
        _write(leaf_key, leaf["key_pem"], secret=True)
        renewed = "ca+leaf"

    if not quiet:
        print(f"  根证书    : {ca_crt}")
        print(f"  服务器证书: {leaf_crt} / {leaf_key.name}")
        print(f"  SAN       : {_san_text(ips, names)}")
        if renewed == "ca+leaf" and had_ca:
            print("  ⚠ 根证书也换了：手机需要重新安装一次")
    return {"created": True, "renewed": renewed, "ca_cert": ca_crt,
            "leaf_cert": leaf_crt, "leaf_key": leaf_key, "ca_key": ca_key,
            "ips": ips, "names": names, "stale": stale}


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="生成/检查本机自签 TLS 证书")
    ap.add_argument("--base", default=str(Path(__file__).resolve().parent),
                    help="证书落地目录（默认本文件所在目录）")
    ap.add_argument("--force", action="store_true", help="整套重签（手机要重装根证书）")
    ap.add_argument("--print-san", action="store_true", help="只打印会写进 SAN 的地址")
    args = ap.parse_args(argv)

    if args.print_san:
        print("DNS:", ", ".join(detect_names()))
        print("IP :", ", ".join(detect_ips()))
        return 0

    try:
        res = ensure_certs(args.base, force=args.force)
    except Exception as e:
        print(f"生成失败：{e}", file=sys.stderr)
        return 1
    if not res["created"]:
        print("已存在且地址覆盖齐全，未改动")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    raise SystemExit(main())
