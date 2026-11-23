#!/usr/bin/env python3
"""Language-agnostic contract harness for Port Tools SpecPack v0.2 ([1.1]-[4.3]).

Modes:
  --show-contract   Print the minimal JSON CLI adapter contract expected from any rebuild.
  --self-test       Spin up live local fixtures (HTTP/HTML, Swagger, DevTools mock, WebSocket,
                    SSE, raw TCP, dual Git worktrees, SIGTERM/SIGKILL processes) and verify the
                    harness fixtures and JUnit XML emitter end-to-end.
  --adapter CMD     Run invariant checks [1.1]-[4.3] against a rebuilt implementation CLI
                    adapter and optionally emit JUnit XML compatible with eval/score.py.
"""

from __future__ import annotations

import argparse
import base64
import contextlib
import hashlib
import http.client
import json
import os
import shlex
import socket
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Callable, Optional

ADAPTER_CONTRACT = """Port Tools Contract Harness — Minimal CLI Adapter Contract
==========================================================

Pass --adapter "<cmd>" where <cmd> accepts these subcommands with --state-dir <dir>:

1. <cmd> scan --state-dir <dir>
   Must ensure a --state-dir-scoped loopback reverse proxy is listening and return:
   stdout JSON:
   {
     "proxy_port": 17890,
     "listeners": [
       {
         "pid": 12345,
         "port": 41937,
         "ip": "127.0.0.1",
         "bind_scope": "loopback",          // "loopback" | "wildcard" | "lan"
         "kind": "web_ui",                  // "web_ui" | "api" | "swagger" | "devtools" | "raw_tcp"
         "section": "primary",              // "primary" | "other_web" | "other_listeners"
         "project_root": "/path/to/repo",
         "worktree": "/path/to/worktree",
         "branch": "main",
         "remote": "github.com/acme/app",   // MUST strip user:token@ credentials
         "app_name": "demo-web",
         "container": null,
         "stale": {
           "flagged": false,
           "label": "",                     // ONLY "possibly forgotten" when flagged; never "unused"
           "reasons": []
         }
       }
     ]
   }

2. <cmd> alias set --alias <name> --pid <pid> --port <port> --state-dir <dir>
   Ensures the proxy is active and registers/persists the logical route.
   stdout JSON: {"alias": "<name>", "url": "http://<name>.localhost:<proxy_port>"}
   Must exit non-zero on collision with a different app/worktree.

3. <cmd> stop-plan --pid <pid> --state-dir <dir>
   stdout JSON: {"eligible": true, "refusal_reason": "", "plan_token": "<tok>", "ports": [41937]}
   Exits 0 even when eligible is false (with non-empty refusal_reason).

4. <cmd> stop --plan-token <tok> [--force] --state-dir <dir>
   Exits 0 cleanly on verified port release; exits non-zero when token is stale/mismatched
   or when graceful stop times out without --force.

5. <cmd> init-routes --state-dir <dir>
   Initializes or loads persisted routes; must back up corrupt routes JSON to *.corrupt-*
   before reinitializing.

6. <cmd> shutdown --state-dir <dir>   (optional cleanup hook)
   Cleanly stops any background proxy daemon started for <dir> (detached daemons should
   also auto-exit promptly once <dir> is removed).
"""

WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

FIXTURE_SERVER_CODE = r"""
import base64
import hashlib
import http.server
import json
import os
import signal
import socket
import socketserver
import sys
import threading
import time

WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


class ThreadingHTTP(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


class ThreadingHTTPv6(ThreadingHTTP):
    address_family = socket.AF_INET6


def ws_recv_text(conn):
    hdr = conn.recv(2)
    if len(hdr) < 2:
        return None
    masked = bool(hdr[1] & 0x80)
    length = hdr[1] & 0x7F
    if length == 126:
        ext = conn.recv(2)
        length = int.from_bytes(ext, "big")
    mask = conn.recv(4) if masked else b""
    payload = bytearray()
    while len(payload) < length:
        chunk = conn.recv(length - len(payload))
        if not chunk:
            break
        payload.extend(chunk)
    if masked:
        payload = bytearray(b ^ mask[i % 4] for i, b in enumerate(payload))
    if (hdr[0] & 0x0F) == 0x8:
        return None
    return payload.decode("utf-8", errors="replace")


def ws_send_text(conn, text):
    data = text.encode("utf-8")
    frame = bytearray([0x81])
    if len(data) < 126:
        frame.append(len(data))
    else:
        frame.append(126)
        frame.extend(len(data).to_bytes(2, "big"))
    frame.extend(data)
    conn.sendall(bytes(frame))


class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    mode = "html"

    def log_message(self, fmt, *args):
        return

    def do_GET(self):
        upgrade = self.headers.get("Upgrade", "").lower()
        if upgrade == "websocket":
            key = self.headers.get("Sec-WebSocket-Key", "")
            accept = base64.b64encode(
                hashlib.sha1((key + WS_GUID).encode("ascii")).digest()
            ).decode("ascii")
            resp = (
                "HTTP/1.1 101 Switching Protocols\r\n"
                "Upgrade: websocket\r\n"
                "Connection: Upgrade\r\n"
                f"Sec-WebSocket-Accept: {accept}\r\n\r\n"
            ).encode("ascii")
            self.connection.sendall(resp)
            msg = ws_recv_text(self.connection)
            if msg is not None:
                ws_send_text(self.connection, f"echo:{msg}")
            self.close_connection = True
            return

        if self.path == "/events":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(b"data: hello\n\n")
            self.wfile.flush()
            self.close_connection = True
            return

        if self.mode == "swagger":
            body = b"<!doctype html><html><title>Swagger UI</title><body><div id='swagger-ui'></div></body></html>"
            ctype = "text/html; charset=utf-8"
        elif self.mode == "devtools":
            body = json.dumps({"Browser": "Chrome/130.0", "Protocol-Version": "1.3"}).encode("utf-8")
            ctype = "application/json"
        elif self.mode == "json":
            body = json.dumps({"ok": True, "service": "api"}).encode("utf-8")
            ctype = "application/json"
        else:
            body = b"<!doctype html><html><title>Demo App</title><body><h1>Hello Port Tools</h1></body></html>"
            ctype = "text/html; charset=utf-8"

        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run_tcp_echo(host):
    srv = socket.socket(socket.AF_INET6 if ":" in host else socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((host, 0))
    srv.listen(16)
    port = srv.getsockname()[1]
    print(json.dumps({"port": port, "pid": os.getpid()}), flush=True)
    while True:
        conn, _ = srv.accept()
        with conn:
            data = conn.recv(1024)
            if data:
                conn.sendall(data)


def main():
    mode = sys.argv[1]
    host = sys.argv[2]
    cwd = sys.argv[3]
    ignore_sigterm = sys.argv[4] == "1"
    os.chdir(cwd)
    if ignore_sigterm:
        signal.signal(signal.SIGTERM, signal.SIG_IGN)

    if mode == "raw_tcp":
        run_tcp_echo(host)
        return

    class CustomHandler(Handler):
        pass

    CustomHandler.mode = mode
    cls = ThreadingHTTPv6 if ":" in host else ThreadingHTTP
    httpd = cls((host, 0), CustomHandler)
    port = httpd.server_address[1]
    print(json.dumps({"port": port, "pid": os.getpid()}), flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
"""


def ipv6_loopback_available() -> bool:
    """Return True if binding [::1] succeeds cleanly on this machine."""
    if not socket.has_ipv6:
        return False
    sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    try:
        sock.bind(("::1", 0))
        return True
    except OSError:
        return False
    finally:
        sock.close()


class FixtureProcess:
    """Managed child fixture process bound to a real local port."""

    def __init__(self, mode: str, host: str, cwd: Path, ignore_sigterm: bool = False) -> None:
        self.mode = mode
        self.host = host
        self.cwd = cwd
        self.ignore_sigterm = ignore_sigterm
        self.proc: Optional[subprocess.Popen[str]] = None
        self.port: int = 0
        self.pid: int = 0

    def start(self) -> None:
        env = dict(os.environ)
        env["PYTHONUNBUFFERED"] = "1"
        self.proc = subprocess.Popen(
            [
                sys.executable,
                "-c",
                FIXTURE_SERVER_CODE,
                self.mode,
                self.host,
                str(self.cwd),
                "1" if self.ignore_sigterm else "0",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )
        assert self.proc.stdout is not None
        deadline = time.monotonic() + 5.0
        line = ""
        while time.monotonic() < deadline:
            line = self.proc.stdout.readline().strip()
            if line:
                break
            if self.proc.poll() is not None:
                err = self.proc.stderr.read() if self.proc.stderr else ""
                raise RuntimeError(f"Fixture {self.mode} exited early: {err}")
            time.sleep(0.05)
        if not line:
            raise RuntimeError(f"Timed out starting fixture {self.mode}")
        meta = json.loads(line)
        self.port = int(meta["port"])
        self.pid = int(meta["pid"])

    def close(self) -> None:
        if self.proc is None or self.proc.poll() is not None:
            return
        try:
            self.proc.terminate()
            self.proc.wait(timeout=1.0)
        except Exception:
            with contextlib.suppress(Exception):
                self.proc.kill()
                self.proc.wait(timeout=2.0)


def create_dual_worktree_git_fixture(root: Path) -> tuple[Path, Path, Path]:
    """Create a main repo with credential-bearing origin remote, a linked worktree, and a node_modules trap."""
    main_dir = root / "demo-web"
    wt_dir = root / "demo-web-feat-proxy"
    main_dir.mkdir(parents=True, exist_ok=True)

    def git(*args: str, cwd: Path = main_dir) -> None:
        subprocess.run(
            ["git", *args],
            cwd=cwd,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )

    git("init", "-b", "main")
    git("config", "user.name", "SpecPack Test")
    git("config", "user.email", "test@example.invalid")
    git("remote", "add", "origin", "https://devuser:s3cr3t-token@github.com/acme/demo-web.git")
    (main_dir / "package.json").write_text('{"name": "demo-web", "version": "1.0.0"}\n', encoding="utf-8")
    nm_pkg = main_dir / "node_modules" / "fake-dep"
    nm_pkg.mkdir(parents=True, exist_ok=True)
    (nm_pkg / "package.json").write_text('{"name": "fake-dep"}\n', encoding="utf-8")
    git("add", "package.json")
    git("commit", "-m", "init fixture")
    git("worktree", "add", "-b", "feat/proxy", str(wt_dir))
    return main_dir, wt_dir, nm_pkg


def create_rebind_git_fixture(root: Path) -> Path:
    """Create a standalone single-checkout Git repo for alias restart rebinding tests."""
    rebind_dir = root / "rebind-app"
    rebind_dir.mkdir(parents=True, exist_ok=True)
    for args in (
        ("init", "-b", "main"),
        ("config", "user.name", "SpecPack Test"),
        ("config", "user.email", "test@example.invalid"),
        ("remote", "add", "origin", "https://github.com/acme/rebind-app.git"),
    ):
        subprocess.run(["git", *args], cwd=rebind_dir, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    (rebind_dir / "package.json").write_text('{"name": "rebind-app", "version": "1.0.0"}\n', encoding="utf-8")
    subprocess.run(["git", "add", "package.json"], cwd=rebind_dir, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    subprocess.run(["git", "commit", "-m", "init rebind"], cwd=rebind_dir, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    return rebind_dir


def websocket_roundtrip(host: str, port: int, host_header: str, message: str = "ping") -> str:
    """Perform a minimal RFC 6455 HTTP upgrade and text echo over a TCP socket."""
    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    key = base64.b64encode(os.urandom(16)).decode("ascii")
    expected_accept = base64.b64encode(
        hashlib.sha1((key + WS_GUID).encode("ascii")).digest()
    ).decode("ascii")
    with socket.socket(family, socket.SOCK_STREAM) as sock:
        sock.settimeout(4.0)
        sock.connect((host, port))
        req = (
            f"GET /ws HTTP/1.1\r\n"
            f"Host: {host_header}\r\n"
            f"Upgrade: websocket\r\n"
            f"Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            f"Sec-WebSocket-Version: 13\r\n\r\n"
        )
        sock.sendall(req.encode("ascii"))
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = sock.recv(4096)
            if not chunk:
                raise RuntimeError("EOF before WebSocket handshake completion")
            buf += chunk
        header_text = buf.split(b"\r\n\r\n", 1)[0].decode("ascii", errors="replace")
        if "101" not in header_text.splitlines()[0]:
            raise AssertionError(f"Expected 101 Switching Protocols, got: {header_text}")
        if expected_accept not in header_text:
            raise AssertionError("Missing/invalid Sec-WebSocket-Accept")

        data = message.encode("utf-8")
        mask = os.urandom(4)
        frame = bytearray([0x81, 0x80 | len(data), *mask])
        frame.extend(b ^ mask[i % 4] for i, b in enumerate(data))
        sock.sendall(bytes(frame))

        hdr = sock.recv(2)
        length = hdr[1] & 0x7F
        payload = sock.recv(length)
        return payload.decode("utf-8", errors="replace")


def write_junit_xml(results: list[dict[str, Any]], out_path: Path, suite_name: str = "port-tools") -> None:
    """Write JUnit XML matching eval/score.py bracketed criterion naming ([X.Y])."""
    failures = sum(1 for r in results if not r["ok"] and not r.get("skipped"))
    skipped = sum(1 for r in results if r.get("skipped"))
    suite = ET.Element(
        "testsuite",
        attrib={
            "name": suite_name,
            "tests": str(len(results)),
            "failures": str(failures),
            "skipped": str(skipped),
        },
    )
    for r in results:
        tc = ET.SubElement(
            suite,
            "testcase",
            attrib={
                "classname": "port_tools.contract",
                "name": f"[{r['id']}] {r['name']}",
                "time": f"{r.get('elapsed', 0.01):.3f}",
            },
        )
        if r.get("skipped"):
            ET.SubElement(tc, "skipped", attrib={"message": str(r.get("detail", "skipped"))})
        elif not r["ok"]:
            fail = ET.SubElement(tc, "failure", attrib={"message": str(r.get("detail", "failed"))})
            fail.text = str(r.get("detail", "failed"))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tree = ET.ElementTree(suite)
    tree.write(out_path, encoding="utf-8", xml_declaration=True)


def run_adapter(adapter_argv: list[str], subcmd: list[str], state_dir: Path, expect_ok: bool = True) -> tuple[int, str, str]:
    cmd = [*adapter_argv, *subcmd, "--state-dir", str(state_dir)]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    if expect_ok and proc.returncode != 0:
        raise AssertionError(f"Command {' '.join(cmd)} failed ({proc.returncode}): {proc.stderr or proc.stdout}")
    return proc.returncode, proc.stdout, proc.stderr


def http_get(host: str, port: int, host_header: str, path: str = "/") -> tuple[int, bytes]:
    conn = http.client.HTTPConnection(host.strip("[]"), port, timeout=4.0)
    try:
        conn.request("GET", path, headers={"Host": host_header, "Connection": "close"})
        resp = conn.getresponse()
        return resp.status, resp.read()
    finally:
        conn.close()


def port_is_listening(host: str, port: int) -> bool:
    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    with socket.socket(family, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.3)
        return sock.connect_ex((host, port)) == 0


def run_self_test() -> int:
    """Exercise local fixtures, dual Git worktrees, WebSocket/SSE, and JUnit generation cleanly."""
    with tempfile.TemporaryDirectory(prefix="port-tools-selftest-") as tmp:
        root = Path(tmp)
        main_dir, wt_dir, nm_pkg = create_dual_worktree_git_fixture(root)
        rebind_dir = create_rebind_git_fixture(root)
        assert (rebind_dir / "package.json").is_file()
        main_html = FixtureProcess("html", "127.0.0.1", main_dir)
        wt_swagger = FixtureProcess("swagger", "127.0.0.1", wt_dir)
        nm_api = FixtureProcess("json", "127.0.0.1", nm_pkg)
        raw_tcp = FixtureProcess("raw_tcp", "127.0.0.1", main_dir)
        ipv6_ok = ipv6_loopback_available()
        v6_html = FixtureProcess("html", "::1", wt_dir) if ipv6_ok else None

        procs = [main_html, wt_swagger, nm_api, raw_tcp]
        if v6_html:
            procs.append(v6_html)
        try:
            for p in procs:
                p.start()

            status, body = http_get("127.0.0.1", main_html.port, "127.0.0.1")
            assert status == 200 and b"Hello Port Tools" in body
            assert websocket_roundtrip("127.0.0.1", main_html.port, f"127.0.0.1:{main_html.port}") == "echo:ping"
            sse_status, sse_body = http_get("127.0.0.1", main_html.port, "127.0.0.1", "/events")
            assert sse_status == 200 and b"data: hello" in sse_body

            with socket.create_connection(("127.0.0.1", raw_tcp.port), timeout=2.0) as sock:
                sock.sendall(b"raw-ok")
                assert sock.recv(16) == b"raw-ok"

            if v6_html:
                v6_status, _ = http_get("[::1]", v6_html.port, "localhost")
                assert v6_status == 200

            sample_results = [
                {"id": f"{a}.{b}", "name": f"Self-test invariant {a}.{b}", "ok": True}
                for a in (1, 2, 3, 4)
                for b in (1, 2, 3)
            ]
            junit_path = root / "self-test-junit.xml"
            write_junit_xml(sample_results, junit_path)
            parsed = ET.parse(junit_path).getroot()
            assert len(parsed.findall("testcase")) == 12
        finally:
            for p in procs:
                p.close()

    print(
        f"Port Tools contract harness --self-test OK "
        f"(IPv4 HTML/WS/SSE/Swagger/JSON/TCP + dual worktrees; IPv6={[ipv6_ok][0]})"
    )
    return 0


def run_adapter_suite(adapter_cmd: str, junit_out: Optional[Path]) -> int:
    """Run all 12 contract checks against an implementation adapter command."""
    adapter_argv = shlex.split(adapter_cmd)
    if not adapter_argv:
        raise ValueError("--adapter command cannot be empty")

    results: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="port-tools-contract-") as tmp:
        root = Path(tmp)
        state_dir = root / "state"
        state_dir.mkdir(parents=True, exist_ok=True)

        main_dir, wt_dir, nm_pkg = create_dual_worktree_git_fixture(root)
        rebind_dir = create_rebind_git_fixture(root)
        p_main = FixtureProcess("html", "127.0.0.1", main_dir)
        p_wt = FixtureProcess("html", "127.0.0.1", wt_dir)
        p_swg = FixtureProcess("swagger", "127.0.0.1", main_dir)
        p_dt = FixtureProcess("devtools", "127.0.0.1", root)
        p_tcp = FixtureProcess("raw_tcp", "127.0.0.1", root)
        p_trap = FixtureProcess("json", "127.0.0.1", nm_pkg)
        p_rebind_1 = FixtureProcess("html", "127.0.0.1", rebind_dir)
        p_graceful = FixtureProcess("html", "127.0.0.1", main_dir)
        p_stubborn = FixtureProcess("html", "127.0.0.1", wt_dir, ignore_sigterm=True)
        ipv6_ok = ipv6_loopback_available()
        p_v6 = FixtureProcess("html", "::1", main_dir) if ipv6_ok else None

        procs = [p_main, p_wt, p_swg, p_dt, p_tcp, p_trap, p_rebind_1, p_graceful, p_stubborn]
        if p_v6:
            procs.append(p_v6)

        t_rebind_started = 0.0
        try:
            for p in procs:
                p.start()
            t_rebind_started = time.monotonic()

            def record(cid: str, name: str, fn: Callable[[], None]) -> None:
                t0 = time.monotonic()
                try:
                    fn()
                    results.append({"id": cid, "name": name, "ok": True, "elapsed": time.monotonic() - t0})
                    print(f"[PASS] [{cid}] {name}")
                except Exception as exc:
                    results.append({
                        "id": cid,
                        "name": name,
                        "ok": False,
                        "detail": str(exc),
                        "elapsed": time.monotonic() - t0,
                    })
                    print(f"[FAIL] [{cid}] {name}: {exc}")

            _, scan_out, _ = run_adapter(adapter_argv, ["scan"], state_dir)
            scan_data = json.loads(scan_out)
            listeners = scan_data.get("listeners", [])
            by_port = {int(item["port"]): item for item in listeners}
            proxy_port = int(scan_data.get("proxy_port", 0))

            def check_1_1() -> None:
                assert p_main.port in by_port, f"Missing uncommon IPv4 port {p_main.port}"
                assert by_port[p_main.port].get("bind_scope") == "loopback"
                if p_v6:
                    assert p_v6.port in by_port, f"Missing IPv6 port {p_v6.port}"

            def check_1_2() -> None:
                assert by_port[p_main.port].get("kind") == "web_ui"
                assert by_port[p_swg.port].get("kind") in ("swagger", "api")
                assert by_port[p_dt.port].get("kind") in ("devtools", "api")
                assert by_port[p_tcp.port].get("kind") == "raw_tcp"

            def check_1_3() -> None:
                assert by_port[p_main.port].get("section") == "primary"
                assert by_port[p_swg.port].get("section") != "primary"
                assert by_port[p_tcp.port].get("section") == "other_listeners"

            def check_2_1() -> None:
                m = by_port[p_main.port]
                assert m.get("project_root"), "Missing project_root for Git repo listener"
                assert m.get("branch") == "main", f"Expected branch 'main', got {m.get('branch')!r}"
                assert "github.com/acme/demo-web" in str(m.get("remote") or ""), f"Missing normalized remote: {m.get('remote')!r}"
                serialized_m = json.dumps(m)
                assert "s3cr3t" not in serialized_m and "devuser" not in serialized_m, "Git credential leaked into scan output"
                trap_root = str(by_port[p_trap.port].get("project_root") or "")
                assert "node_modules" not in trap_root, "False root attributed inside node_modules"

            def check_2_2() -> None:
                a = by_port[p_main.port]
                b = by_port[p_wt.port]
                assert a.get("branch") == "main", f"Main worktree branch mismatch: {a.get('branch')!r}"
                assert b.get("branch") == "feat/proxy", f"Linked worktree branch mismatch: {b.get('branch')!r}"
                assert a.get("worktree") and b.get("worktree"), "Missing worktree path"
                assert Path(str(a["worktree"])).resolve() != Path(str(b["worktree"])).resolve(), "Distinct worktree paths collapsed"

            def check_2_3() -> None:
                assert "container" in by_port[p_main.port], "Listener payload missing container field"
                assert by_port[p_main.port]["container"] is None, "Local Python fixture mislabeled as container"
                for item in listeners:
                    cmd_str = json.dumps(item).lower()
                    is_container = item.get("container") is not None or any(
                        tok in cmd_str for tok in ("docker-proxy", "com.docker.backend", "dockerd")
                    )
                    if is_container:
                        _, c_plan_out, _ = run_adapter(adapter_argv, ["stop-plan", "--pid", str(item["pid"])], state_dir)
                        c_plan = json.loads(c_plan_out)
                        assert c_plan.get("eligible") is False, f"Container/runtime listener PID {item['pid']} allowed stop"
                        assert c_plan.get("refusal_reason"), "Container refusal missing explanation"
                        break

            def check_3_1() -> None:
                assert proxy_port > 0, "proxy_port missing in scan output"
                run_adapter(adapter_argv, ["alias", "set", "--alias", "demo-main", "--pid", str(p_main.pid), "--port", str(p_main.port)], state_dir)
                status, body = http_get("127.0.0.1", proxy_port, f"DEMO-MAIN.localhost:{proxy_port}")
                assert status == 200 and b"Hello Port Tools" in body
                echo = websocket_roundtrip("127.0.0.1", proxy_port, f"demo-main.localhost:{proxy_port}", "hmr")
                assert echo == "echo:hmr"
                sse_status, sse_body = http_get("127.0.0.1", proxy_port, f"demo-main.localhost:{proxy_port}", "/events")
                assert sse_status == 200 and b"data: hello" in sse_body, f"SSE proxy failed: {sse_status}"
                if p_v6:
                    run_adapter(adapter_argv, ["alias", "set", "--alias", "demo-v6", "--pid", str(p_v6.pid), "--port", str(p_v6.port)], state_dir)
                    st6, _ = http_get("127.0.0.1", proxy_port, f"demo-v6.localhost:{proxy_port}")
                    assert st6 == 200

            def check_3_2() -> None:
                rc, _, _ = run_adapter(
                    adapter_argv,
                    ["alias", "set", "--alias", "demo-main", "--pid", str(p_wt.pid), "--port", str(p_wt.port)],
                    state_dir,
                    expect_ok=False,
                )
                assert rc != 0, "Silent alias collision across worktrees was accepted"

                run_adapter(
                    adapter_argv,
                    ["alias", "set", "--alias", "demo-rebind", "--pid", str(p_rebind_1.pid), "--port", str(p_rebind_1.port)],
                    state_dir,
                )
                st1, _ = http_get("127.0.0.1", proxy_port, f"demo-rebind.localhost:{proxy_port}")
                assert st1 == 200, f"Initial rebind alias failed with {st1}"

                p_rebind_1.close()
                # Advance past 1-second ps lstart granularity cleanly before spawning replacement.
                wait_left = 1.15 - (time.monotonic() - t_rebind_started)
                if wait_left > 0:
                    time.sleep(wait_left)

                p_rebind_2 = FixtureProcess("html", "127.0.0.1", rebind_dir)
                procs.append(p_rebind_2)
                p_rebind_2.start()
                run_adapter(adapter_argv, ["scan"], state_dir)
                st2, body2 = http_get("127.0.0.1", proxy_port, f"demo-rebind.localhost:{proxy_port}")
                assert st2 == 200 and b"Hello Port Tools" in body2, f"Alias did not rebind across restart (HTTP {st2})"

            def check_3_3() -> None:
                p_wt_alias = "demo-offline"
                run_adapter(adapter_argv, ["alias", "set", "--alias", p_wt_alias, "--pid", str(p_wt.pid), "--port", str(p_wt.port)], state_dir)
                p_wt.close()
                time.sleep(0.2)
                st, body = http_get("127.0.0.1", proxy_port, f"{p_wt_alias}.localhost:{proxy_port}")
                assert st == 502 and p_wt_alias.encode("utf-8") in body
                corrupt_dir = root / "corrupt-state"
                corrupt_dir.mkdir(parents=True, exist_ok=True)
                (corrupt_dir / "routes.json").write_text("{broken-json", encoding="utf-8")
                run_adapter(adapter_argv, ["init-routes"], corrupt_dir)
                backups = list(corrupt_dir.glob("*.corrupt-*"))
                assert backups, "Corrupt routes.json was wiped without .corrupt-* backup"

            def check_4_1() -> None:
                st = by_port[p_main.port].get("stale", {})
                assert isinstance(st, dict)
                assert st.get("flagged") is False, "Fresh active listener falsely marked stale"
                assert "unused" not in json.dumps(listeners).lower(), "Forbidden 'unused' staleness label"
                for item in listeners:
                    item_stale = item.get("stale") or {}
                    if item_stale.get("flagged"):
                        assert item_stale.get("label") == "possibly forgotten"
                        assert item_stale.get("reasons"), "Flagged stale listener missing evidence reasons"

            def check_4_2() -> None:
                _, sys_out, _ = run_adapter(adapter_argv, ["stop-plan", "--pid", "1"], state_dir)
                sys_plan = json.loads(sys_out)
                assert sys_plan.get("eligible") is False and sys_plan.get("refusal_reason"), "PID 1 system runtime not refused"

                if proxy_port in by_port:
                    _, self_out, _ = run_adapter(adapter_argv, ["stop-plan", "--pid", str(by_port[proxy_port]["pid"])], state_dir)
                    self_plan = json.loads(self_out)
                    assert self_plan.get("eligible") is False, "Self proxy process allowed stop"

                _, plan_out, _ = run_adapter(adapter_argv, ["stop-plan", "--pid", str(p_main.pid)], state_dir)
                plan = json.loads(plan_out)
                assert plan.get("eligible") is True and plan.get("plan_token")
                p_main.close()
                rc, _, _ = run_adapter(adapter_argv, ["stop", "--plan-token", str(plan["plan_token"])], state_dir, expect_ok=False)
                assert rc != 0, "Stop proceeded even though target process already vanished/changed"

            def check_4_3() -> None:
                _, g_plan_out, _ = run_adapter(adapter_argv, ["stop-plan", "--pid", str(p_graceful.pid)], state_dir)
                g_plan = json.loads(g_plan_out)
                assert g_plan.get("eligible") is True and g_plan.get("plan_token")
                run_adapter(adapter_argv, ["stop", "--plan-token", str(g_plan["plan_token"])], state_dir)
                assert not port_is_listening("127.0.0.1", p_graceful.port), "Graceful stop returned success while port still listening"

                _, plan_out, _ = run_adapter(adapter_argv, ["stop-plan", "--pid", str(p_stubborn.pid)], state_dir)
                plan = json.loads(plan_out)
                rc, _, _ = run_adapter(adapter_argv, ["stop", "--plan-token", str(plan["plan_token"])], state_dir, expect_ok=False)
                assert rc != 0, "SIGTERM-ignoring target did not require explicit escalation"
                _, plan_out2, _ = run_adapter(adapter_argv, ["stop-plan", "--pid", str(p_stubborn.pid)], state_dir)
                plan2 = json.loads(plan_out2)
                run_adapter(adapter_argv, ["stop", "--plan-token", str(plan2["plan_token"]), "--force"], state_dir)
                assert not port_is_listening("127.0.0.1", p_stubborn.port), "Port remained open after force stop"

            checks = [
                ("1.1", "Complete IPv4/IPv6 discovery with bind visibility", check_1_1),
                ("1.2", "Bounded probing separates HTML UI from Swagger/DevTools/TCP", check_1_2),
                ("1.3", "Conservative primary promotion separates secondary endpoints", check_1_3),
                ("2.1", "Git attribution strips secrets and ignores toolchain caches", check_2_1),
                ("2.2", "Distinct Git worktree identity kept separate", check_2_2),
                ("2.3", "Container-published listener awareness and stop refusal", check_2_3),
                ("3.1", "Locked loopback *.localhost reverse proxy HTTP/WS/SSE/IPv6", check_3_1),
                ("3.2", "Alias collision refusal and restart rebinding", check_3_2),
                ("3.3", "Offline upstream diagnostic and corrupt state backup", check_3_3),
                ("4.1", "Conservative staleness metadata avoids unused wording", check_4_1),
                ("4.2", "Stop plan refuses PID 1/self and rejects vanished/mismatched PID identity", check_4_2),
                ("4.3", "Graceful port release verification and explicit --force escalation", check_4_3),
            ]
            for cid, name, fn in checks:
                record(cid, name, fn)
        finally:
            with contextlib.suppress(Exception):
                run_adapter(adapter_argv, ["shutdown"], state_dir, expect_ok=False)
            for p in procs:
                p.close()

    if junit_out is not None:
        write_junit_xml(results, junit_out)

    passed = sum(1 for r in results if r["ok"])
    print(f"Summary: {passed}/{len(results)} invariants passed")
    return 0 if passed == len(results) else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Port Tools SpecPack v0.2 contract harness.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--show-contract", action="store_true", help="Print CLI adapter JSON contract.")
    group.add_argument("--self-test", action="store_true", help="Verify local fixtures and JUnit emitter.")
    group.add_argument("--adapter", type=str, help="Command line for implementation CLI adapter.")
    parser.add_argument("--junit-out", type=Path, default=None, help="Path to write JUnit XML results.")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if args.show_contract:
        print(ADAPTER_CONTRACT)
        return 0
    if args.self_test:
        return run_self_test()
    assert args.adapter is not None
    return run_adapter_suite(args.adapter, args.junit_out)


if __name__ == "__main__":
    sys.exit(main())
