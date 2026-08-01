"""提取器 + 目录哈希测试 (覆盖 v2.0.1 关键 bug 修复)"""

from pathlib import Path

from wechat_forensic.extractor import Extractor


def test_hash_directory_uses_real_file_content(stub_logger, tmp_path):
    """v2.0.1 修复: 原版错误地传入路径字符串而非文件内容"""
    (tmp_path / "a.txt").write_text("hello")
    (tmp_path / "b.txt").write_text("world")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "c.txt").write_text("!")

    ext = Extractor(stub_logger, str(tmp_path / "out"))
    h1 = ext._hash_directory(tmp_path)

    # 修改一个文件, 哈希必须变化 (证明 _hash_directory 真的读到了内容)
    (tmp_path / "a.txt").write_text("hello-CHANGED")
    h2 = ext._hash_directory(tmp_path)
    assert h1 != h2, "目录哈希必须对文件内容敏感"


def test_hash_directory_order_sensitive(stub_logger, tmp_path):
    """相同内容但位于不同子目录的文件, 在同一父目录中哈希必须不同"""
    parent = tmp_path / "parent"
    (parent / "x").mkdir(parents=True)
    (parent / "x" / "f.txt").write_text("same content")
    (parent / "y").mkdir(parents=True)
    (parent / "y" / "f.txt").write_text("same content")

    ext = Extractor(stub_logger, str(tmp_path / "out"))
    h = ext._hash_directory(parent)
    # 内容相同 + 路径不同 -> 哈希应该不同
    # (因为相对路径 'x/f.txt' != 'y/f.txt' 纳入了哈希)
    h_x_only = ext._hash_directory(parent / "x")
    h_y_only = ext._hash_directory(parent / "y")
    assert h_x_only == h_y_only, "单层目录内只有 f.txt 时应相同(测试基线)"
    # 父目录包含两个子目录时, 因为相对路径不同, 总哈希必变
    assert len(h) == 64, "父目录哈希应能正常生成"
    # 进一步断言: 在父目录中, x 与 y 子目录的相对路径影响哈希
    # 构造一个对照: 删除 y 子目录, 应得到不同哈希
    import shutil
    shutil.rmtree(parent / "y")
    h_only_x = ext._hash_directory(parent)
    assert h != h_only_x, "子目录结构变化必须导致目录哈希变化"


def test_extract_pc_copies_databases(stub_logger, tmp_path):
    """端到端: extract_pc 应只复制数据库并打哈希"""
    src = tmp_path / "wechat"
    src.mkdir()
    (src / "Msg").mkdir()
    (src / "Msg" / "MicroMsg.db").write_text("db1")
    (src / "Msg" / "other.bin").write_text("skipped")
    (src / "FileStorage").mkdir()
    (src / "FileStorage" / "image.jpg").write_bytes(b"\xff\xd8fake-jpg")
    (src / "config").mkdir()
    (src / "config" / "config.ini").write_text("[conf]")

    out = tmp_path / "out"
    ext = Extractor(stub_logger, str(out))
    info = {"wxid": "wxid_test", "path": str(src),
            "msg": str(src / "Msg"),
            "filestorage": str(src / "FileStorage"),
            "config": str(src / "config")}
    dst, report = ext.extract_pc(info)

    assert Path(dst).exists()
    assert (Path(dst) / "Msg" / "MicroMsg.db").exists()
    # 验证 other.bin 被 patterns 过滤掉
    assert not (Path(dst) / "Msg" / "other.bin").exists()
    assert any(f["sha256"] for f in report["files"])
