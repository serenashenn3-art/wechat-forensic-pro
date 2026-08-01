"""哈希模块测试"""

from wechat_forensic.hashing import Hasher


def test_sha256_bytes_known_vector():
    # 已知 SHA-256("hello")
    assert Hasher.sha256_bytes(b"hello") == (
        "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
    )


def test_sha256_file_matches_bytes(tmp_path):
    p = tmp_path / "f.txt"
    p.write_bytes(b"hello world")
    assert Hasher.sha256_file(str(p)) == Hasher.sha256_bytes(b"hello world")


def test_verify_roundtrip(tmp_path):
    p = tmp_path / "f.txt"
    p.write_bytes(b"roundtrip")
    expected = Hasher.sha256_file(str(p))
    assert Hasher.verify(str(p), expected) is True
    assert Hasher.verify(str(p), "0" * 64) is False


def test_md5_known_vector(tmp_path):
    p = tmp_path / "f.txt"
    p.write_bytes(b"hello")
    import hashlib
    assert Hasher.md5_file(str(p)) == hashlib.md5(b"hello").hexdigest()
