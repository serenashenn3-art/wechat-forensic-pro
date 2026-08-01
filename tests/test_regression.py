"""v2.0.6 跨平台 bug 回归测试 + HMAC 密钥指纹测试

每个测试对应 CHANGELOG.md v2.0.1 修复记录中提到的一个具体 bug。
目的:防止修复被无意中再次破坏 (regression)。

v2.0.1 修复的 7 个跨平台 bug (见 CHANGELOG):
  1. _hash_directory 错误地把路径字符串当文件内容传入 sha256_file
  2. 取证报告 _forensic_report.txt 中所有 \n 被错误转义为字面 \\n
  3. os.geteuid() 在 Windows 抛 AttributeError
  4. macOS 物理磁盘扫描逻辑不通
  5. Windows 磁盘信息优先 PowerShell, wmic 仅作回退
  6. --no-interactive 模式下仍会因 input() 阻塞
  7. v2.0.6 新增: HMAC 签名不存储 key fingerprint (本次新增的回归保护)
"""

import hashlib
import json
import os
import platform
import subprocess
import sys

import pytest


# =============================================================================
# Bug 1: _hash_directory 不能把路径当内容
# =============================================================================
def test_regression_bug1_hash_directory_uses_file_content_not_path(tmp_path):
    """_hash_directory 必须用文件内容 + 相对路径,而不是把路径字符串当内容"""
    from wechat_forensic.extractor import Extractor
    from wechat_forensic.logger import ForensicLogger

    (tmp_path / "a.txt").write_bytes(b"alpha")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.txt").write_bytes(b"bravo")

    log = ForensicLogger(str(tmp_path / "log.txt"))
    ext = Extractor(log, tmp_path)

    h1 = ext._hash_directory(tmp_path)
    h2 = ext._hash_directory(tmp_path)
    assert h1 == h2, "Hash 必须是确定性的"
    assert len(h1) == 64
    assert all(c in "0123456789abcdef" for c in h1)


def test_regression_bug1_hash_directory_detects_content_change(tmp_path):
    """修改文件内容后, hash 必须变化 (证明确实是内容哈希,不是路径哈希)"""
    from wechat_forensic.extractor import Extractor
    from wechat_forensic.logger import ForensicLogger

    f = tmp_path / "a.txt"
    f.write_bytes(b"original")
    log = ForensicLogger(str(tmp_path / "log.txt"))
    ext = Extractor(log, tmp_path)
    h_before = ext._hash_directory(tmp_path)

    f.write_bytes(b"modified")
    h_after = ext._hash_directory(tmp_path)
    assert h_before != h_after, "内容变化应改变 hash"


# =============================================================================
# Bug 2: _forensic_report.txt 中 \n 不能被转义
# =============================================================================
def test_regression_bug2_report_txt_uses_real_newlines(tmp_path):
    """TXT 报告中的换行必须是真实 \\n,不能是字面 '\\\\n'"""
    from wechat_forensic.report import ReportGenerator

    txt_path = ReportGenerator.generate(
        str(tmp_path),
        [{"step": "测试步骤", "timestamp": "2026-08-02", "description": "这是描述"}],
        case_id="CASE-REG-001",
        evidence_id="E-REG-001",
    )
    raw = open(txt_path, "rb").read()  # 用二进制读,直接看字节

    # 不能出现字面 "\n" (即 \ + n),必须是真实 0x0a
    assert b"\\n" not in raw, (
        f"报告里出现了字面 \\n 字节 (bug v2.0.1 复发): "
        f"前 200 字节: {raw[:200]!r}"
    )
    # 必须有真实的换行符
    assert b"\n" in raw, "报告应该有真实换行符"


def test_regression_bug2_report_json_also_safe(tmp_path):
    """JSON 报告里 _summary_text 字段也是真实换行 (双格式一致)"""
    from wechat_forensic.report import ReportGenerator

    ReportGenerator.generate(
        str(tmp_path),
        [{"step": "test", "timestamp": "t", "description": "d"}],
        case_id="CASE-REG-002",
        evidence_id="E-REG-002",
    )
    json_path = tmp_path / "_forensic_report.json"
    data = json.loads(json_path.read_text(encoding="utf-8"))

    summary = data.get("summary_text") or data.get("_summary_text", "")
    if summary:
        # 不能有字面 \n
        assert "\\n" not in summary, "JSON 里 summary_text 也不能有字面 \\n"
        assert "\n" in summary, "JSON 里 summary_text 必须有真实换行"


# =============================================================================
# Bug 3: os.geteuid() 在 Windows 抛 AttributeError
# =============================================================================
def test_regression_bug3_is_admin_works_on_all_platforms(monkeypatch):
    """is_admin() 必须在 Windows / macOS / Linux 上都不抛异常

    v2.0.1 之前直接用 os.geteuid(),在 Windows 上 AttributeError。
    修复后改用 os.name 分流 (Windows 用 ctypes, 其他用 os.geteuid)。
    """
    from wechat_forensic.utils import is_admin

    # 模拟 Windows
    monkeypatch.setattr(os, "name", "nt")
    # 不应抛异常
    try:
        result = is_admin()
        assert isinstance(result, bool)
    except AttributeError as e:
        pytest.fail(f"is_admin() 在 Windows 模拟下抛 AttributeError: {e}")

    # 模拟 Linux/macOS
    monkeypatch.setattr(os, "name", "posix")
    try:
        result = is_admin()
        assert isinstance(result, bool)
    except AttributeError as e:
        pytest.fail(f"is_admin() 在 POSIX 模拟下抛 AttributeError: {e}")


def test_regression_bug3_is_admin_handles_missing_ctypes(monkeypatch):
    """Windows 上 ctypes 不可用时,应优雅返回 False 而非崩溃"""
    from wechat_forensic import utils

    monkeypatch.setattr(os, "name", "nt")

    # 删除 ctypes (模拟不可用)
    import sys
    saved_ctypes = sys.modules.get("ctypes")
    sys.modules["ctypes"] = None  # type: ignore

    try:
        result = utils.is_admin()
        assert result is False, "ctypes 不可用时, is_admin 应返回 False"
    finally:
        if saved_ctypes is not None:
            sys.modules["ctypes"] = saved_ctypes
        else:
            sys.modules.pop("ctypes", None)


# =============================================================================
# Bug 4: macOS 物理磁盘扫描必须过滤分区,只留整盘
# =============================================================================
def test_regression_bug4_macos_physical_disks_filters_partitions(monkeypatch, tmp_path):
    """diskutil list 输出如 /dev/disk0 /dev/disk0s1 /dev/disk0s2,
    必须过滤掉带 s 数字后缀的,只保留 /dev/disk0 这种整盘"""
    from wechat_forensic.scanner import Scanner

    # 准备假 diskutil 输出
    fake_list_output = """
/dev/disk0 (internal, physical):
   #:                       TYPE NAME                    SIZE       IDENTIFIER
   0:      GUID_partition_scheme                        *500.1 GB   disk0
   1:             Apple_APFS_ISC                         524.3 MB   disk0s1
   2:                 Apple_APFS Container disk4         300.0 GB   disk0s2

/dev/disk1 (external, physical):
   #:                       TYPE NAME                    SIZE       IDENTIFIER
   0:     FDisk_partition_scheme                        *1.0 TB     disk1
   1:                  Apple_HFS Backup                  1.0 TB     disk1s1
"""

    def fake_run(cmd, *args, **kwargs):
        r = subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")
        if cmd == ["diskutil", "list"]:
            r.stdout = fake_list_output
        elif len(cmd) >= 3 and cmd[0] == "diskutil" and cmd[1] == "info":
            r.stdout = "Total Size:    500.1 GB (500107862016 Bytes)\nDevice / Media Name: APPLE SSD\n"
        return r

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(platform, "system", lambda: "Darwin")

    class FakeLogger:
        def error(self, *a, **k): pass
        def warning(self, *a, **k): pass

    s = Scanner(FakeLogger())
    disks = s.physical_disks()
    paths = [d["path"] for d in disks]
    # 整盘应在
    assert "/dev/disk0" in paths
    assert "/dev/disk1" in paths
    # 分区必须被过滤掉
    assert "/dev/disk0s1" not in paths
    assert "/dev/disk0s2" not in paths
    assert "/dev/disk1s1" not in paths


# =============================================================================
# Bug 5: Windows 磁盘信息必须优先 PowerShell, wmic 仅作回退
# =============================================================================
def test_regression_bug5_windows_drives_prefers_powershell(monkeypatch):
    """Windows 扫描必须先尝试 PowerShell (CIM),失败后才回退 wmic"""
    from wechat_forensic.scanner import Scanner

    ps_call_count = {"n": 0}
    wmic_call_count = {"n": 0}

    def fake_run(cmd, *args, **kwargs):
        r = subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")
        if cmd and cmd[0] == "powershell":
            ps_call_count["n"] += 1
            # PowerShell ConvertTo-Csv -NoTypeInformation 输出格式
            r.stdout = (
                '"DeviceID","Size","FreeSpace","FileSystem","VolumeName"\n'
                '"C:","500000000000","100000000000","NTFS","System"\n'
                '"D:","1000000000000","500000000000","NTFS","Data"\n'
            )
        elif cmd and cmd[0] == "wmic":
            wmic_call_count["n"] += 1
            r.stdout = ""
        return r

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(platform, "system", lambda: "Windows")

    class FakeLogger:
        def error(self, *a, **k): pass
        def warning(self, *a, **k): pass

    s = Scanner(FakeLogger())
    drives = s.drives()
    assert ps_call_count["n"] >= 1, "Windows 应至少调用一次 PowerShell"
    assert wmic_call_count["n"] == 0, "PowerShell 成功时不应回退 wmic"
    assert len(drives) == 2, f"应解析出 2 个盘, 实际: {drives}"


def test_regression_bug5_windows_drives_falls_back_to_wmic(monkeypatch):
    """PowerShell 不可用时,必须回退到 wmic (不能直接放弃)"""
    from wechat_forensic.scanner import Scanner

    def fake_run(cmd, *args, **kwargs):
        r = subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")
        if cmd and cmd[0] == "powershell":
            raise FileNotFoundError("powershell not found")
        elif cmd and cmd[0] == "wmic":
            r.stdout = (
                "DeviceID  Size  FreeSpace  FileSystem  VolumeName\n"
                "C:        500000000000  100000000000  NTFS  System\n"
                "D:        1000000000000  500000000000  NTFS  Data\n"
            )
        return r

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(platform, "system", lambda: "Windows")

    class FakeLogger:
        def error(self, *a, **k): pass
        def warning(self, *a, **k): pass

    s = Scanner(FakeLogger())
    drives = s.drives()
    assert len(drives) == 2, f"PowerShell 不可用时应回退 wmic,实际驱动数: {len(drives)}"


# =============================================================================
# Bug 6: --no-interactive 模式下, 任何 input() 调用都应跳过
# =============================================================================
def test_regression_bug6_no_input_calls_in_main_loop():
    """--no-interactive 模式下代码里不能有 input() 调用 (会阻塞 CI / 无人值守)

    静态检查:每处 input() 必须位于 'if not args.no_interactive' (或类似)
    分支内,否则会在无人值守/自动化场景下阻塞。
    """
    import re
    from pathlib import Path

    src_dir = Path(__file__).resolve().parent.parent / "wechat_forensic"
    bad_calls = []
    for py in src_dir.glob("*.py"):
        text = py.read_text(encoding="utf-8")
        lines = text.splitlines()
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if not re.search(r"\binput\s*\(", line):
                continue
            # 检查前 10 行内是否有 no_interactive / not args.no_interactive 等守卫
            context = "\n".join(lines[max(0, i - 10) : i])
            has_guard = bool(
                re.search(r"no_interactive", context)
                or re.search(r"isinstance\(.+input", context)
            )
            if not has_guard:
                bad_calls.append(f"{py.name}:{i}: {line}")

    assert not bad_calls, (
        f"发现无守卫的 input() 调用,在 --no-interactive 模式下会阻塞:\n"
        + "\n".join(bad_calls)
    )


# =============================================================================
# Bug 7 (v2.0.6 新增): HMAC 签名必须记录 key fingerprint,不存明文
# =============================================================================
def test_regression_bug7_hmac_signature_records_key_fingerprint(tmp_path, monkeypatch):
    """_signature.json 必须包含 key_fingerprint_sha256 字段,
    用于事后核验密钥身份,但绝不暴露明文 key。"""
    from wechat_forensic.security import sign_report

    test_key = "case-2026-001-secret-key-please-rotate"
    monkeypatch.setenv("WECHAT_FORENSIC_HMAC_KEY", test_key)

    report = tmp_path / "_forensic_report.json"
    report.write_text('{"case": "test"}', encoding="utf-8")

    sign_report(str(report))
    sig_path = tmp_path / "_signature.json"
    sig = json.loads(sig_path.read_text(encoding="utf-8"))

    # 1. 必须有 fingerprint 字段
    assert "key_fingerprint_sha256" in sig, "缺少 key_fingerprint_sha256 字段"
    # 2. fingerprint 必须等于 key 的 SHA-256
    expected_fp = hashlib.sha256(test_key.encode("utf-8")).hexdigest()
    assert sig["key_fingerprint_sha256"] == expected_fp
    # 3. 绝不能把明文 key 写入签名文件
    assert test_key not in sig_path.read_text(encoding="utf-8"), (
        "明文 HMAC key 出现在 _signature.json 中,违反密钥管理规范!"
    )
    # 4. fingerprint 也不应等于 key 本身
    assert sig["key_fingerprint_sha256"] != test_key


def test_regression_bug7_different_keys_produce_different_fingerprints(tmp_path, monkeypatch):
    """不同案件的 key 必须产生不同 fingerprint,确保可区分"""
    from wechat_forensic.security import sign_report

    report = tmp_path / "_forensic_report.json"
    report.write_text('{"case": "x"}', encoding="utf-8")

    monkeypatch.setenv("WECHAT_FORENSIC_HMAC_KEY", "key-for-case-A")
    sign_report(str(report))
    sig_a = json.loads((tmp_path / "_signature.json").read_text(encoding="utf-8"))
    fp_a = sig_a["key_fingerprint_sha256"]

    monkeypatch.setenv("WECHAT_FORENSIC_HMAC_KEY", "key-for-case-B")
    sign_report(str(report))
    sig_b = json.loads((tmp_path / "_signature.json").read_text(encoding="utf-8"))
    fp_b = sig_b["key_fingerprint_sha256"]

    assert fp_a != fp_b, "不同 key 必须产生不同 fingerprint"
    # 两个指纹都是合法的 SHA-256 hex (64 字符)
    assert len(fp_a) == 64 and len(fp_b) == 64
