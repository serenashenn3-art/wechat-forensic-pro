"""chatview.py 测试: 已解密 db 联系人查询 + 选择性导出

所有测试用 tmp_path 构造 mock 明文 sqlite, 不接触任何真实微信数据,
不包含任何密钥推导代码。"""

import json
import sqlite3
from pathlib import Path

import pytest

from wechat_forensic.chatview import (
    ChatViewer,
    EncryptedDatabaseError,
    UnsupportedSchemaError,
    SCHEMA_ANDROID,
    SCHEMA_PC,
)
from wechat_forensic.hashing import Hasher


def _make_android_db(path: Path):
    """构造 mock Android EnMicroMsg.db (已解密明文)"""
    conn = sqlite3.connect(str(path))
    conn.executescript(
        """
        CREATE TABLE rcontact (
            username TEXT, nickname TEXT, remark TEXT, alias TEXT
        );
        CREATE TABLE message (
            talker TEXT, isSend INTEGER, createTime INTEGER,
            content TEXT, type INTEGER
        );
        """
    )
    conn.executemany(
        "INSERT INTO rcontact VALUES (?,?,?,?)",
        [
            ("wxid_alice", "Alice", "爱丽丝", "alice_wx"),
            ("wxid_bob", "Bob", "", "bob_wx"),
            ("gh_pubaccount", "公众号", "", ""),
            ("", "空", "", ""),
        ],
    )
    conn.executemany(
        "INSERT INTO message VALUES (?,?,?,?,?)",
        [
            ("wxid_alice", 0, 1700000000000, "你好", 1),
            ("wxid_alice", 1, 1700000001000, "嗨", 1),
            ("wxid_bob", 0, 1700000002000, "在吗", 1),
        ],
    )
    conn.commit()
    conn.close()


def _make_pc_db(path: Path):
    """构造 mock PC MicroMsg.db (仅联系人, 无消息表)"""
    conn = sqlite3.connect(str(path))
    conn.executescript("CREATE TABLE contact (username TEXT, nickname TEXT, remark TEXT);")
    conn.executemany(
        "INSERT INTO contact VALUES (?,?,?)",
        [("wxid_carol", "Carol", "卡罗尔"), ("gh_x", "公众号", "")],
    )
    conn.commit()
    conn.close()


def test_open_and_list_android(stub_logger, tmp_path):
    """Android db: 识别 schema, 列出联系人, 过滤公众号/空"""
    db = tmp_path / "android.db"
    _make_android_db(db)

    with ChatViewer(stub_logger, str(db)) as v:
        assert v.schema == SCHEMA_ANDROID
        contacts = v.list_contacts()
        wxids = [c["wxid"] for c in contacts]
        assert "wxid_alice" in wxids
        assert "wxid_bob" in wxids
        assert "gh_pubaccount" not in wxids
        assert "" not in wxids
        # 有备注的 alice 应排在前
        assert contacts[0]["wxid"] == "wxid_alice"
        assert contacts[0]["remark"] == "爱丽丝"
        assert contacts[0]["alias"] == "alice_wx"


def test_open_pc_schema(stub_logger, tmp_path):
    """PC db: 识别 schema, alias 字段为空"""
    db = tmp_path / "pc.db"
    _make_pc_db(db)

    with ChatViewer(stub_logger, str(db)) as v:
        assert v.schema == SCHEMA_PC
        contacts = v.list_contacts()
        assert len(contacts) == 1  # 过滤掉 gh_x
        assert contacts[0]["wxid"] == "wxid_carol"
        assert contacts[0]["remark"] == "卡罗尔"
        assert contacts[0]["alias"] == ""


def test_export_messages_android(stub_logger, tmp_path):
    """Android: 按勾选导出消息, 每联系人一个文件 + SHA-256 + manifest"""
    db = tmp_path / "android.db"
    _make_android_db(db)
    out = tmp_path / "out"

    with ChatViewer(stub_logger, str(db)) as v:
        mp, files = v.export_messages(
            ["wxid_alice", "wxid_bob"],
            str(out),
            authorization="本人设备/wxid_self",
        )

    manifest = json.loads(Path(mp).read_text(encoding="utf-8"))
    assert manifest["authorization"] == "本人设备/wxid_self"
    assert manifest["schema"] == SCHEMA_ANDROID
    assert len(manifest["files"]) == 2

    by_wxid = {f["wxid"]: f for f in manifest["files"]}
    assert by_wxid["wxid_alice"]["message_count"] == 2
    assert by_wxid["wxid_bob"]["message_count"] == 1
    assert Path(by_wxid["wxid_alice"]["path"]).exists()
    assert len(by_wxid["wxid_alice"]["sha256"]) == 64

    # 导出文件内容: 真实换行 (非 "\\n"), 含消息文本
    content = Path(by_wxid["wxid_alice"]["path"]).read_text(encoding="utf-8")
    assert "wxid_alice" in content
    assert "你好" in content
    assert "嗨" in content
    assert "\n" in content


def test_export_pc_no_messages(stub_logger, tmp_path):
    """PC db 无消息表: 导出时消息数为 0, 但仍生成文件 + 哈希"""
    db = tmp_path / "pc.db"
    _make_pc_db(db)
    out = tmp_path / "out"

    with ChatViewer(stub_logger, str(db)) as v:
        mp, files = v.export_messages(["wxid_carol"], str(out))

    assert len(files) == 1
    assert files[0]["message_count"] == 0
    assert len(files[0]["sha256"]) == 64


def test_parse_selection():
    """'1,3,5-8' 语法: 越界忽略, 去重保序, 反向范围, 空格容忍"""
    assert ChatViewer.parse_selection("1", 10) == [0]
    assert ChatViewer.parse_selection("1,3", 10) == [0, 2]
    assert ChatViewer.parse_selection("1,3,5-8", 10) == [0, 2, 4, 5, 6, 7]
    assert ChatViewer.parse_selection("1,100", 5) == [0]  # 越界忽略
    assert ChatViewer.parse_selection("1,1,2", 10) == [0, 1]  # 去重
    assert ChatViewer.parse_selection("5-3", 10) == [2, 3, 4]  # 反向范围
    assert ChatViewer.parse_selection(" 1 , 2 ", 10) == [0, 1]  # 空格容忍
    assert ChatViewer.parse_selection("", 10) == []


def test_encrypted_db_rejected(stub_logger, tmp_path):
    """加密 db (非 sqlite 二进制) 应抛 EncryptedDatabaseError, 不解密"""
    db = tmp_path / "fake_encrypted.db"
    db.write_bytes(b"this is not a sqlite database, looks like encrypted payload")

    with pytest.raises(EncryptedDatabaseError):
        ChatViewer(stub_logger, str(db)).open()


def test_unsupported_schema(stub_logger, tmp_path):
    """无微信联系人表的 db 应抛 UnsupportedSchemaError"""
    db = tmp_path / "other.db"
    conn = sqlite3.connect(str(db))
    conn.execute("CREATE TABLE foo (x INTEGER)")
    conn.commit()
    conn.close()

    with pytest.raises(UnsupportedSchemaError):
        ChatViewer(stub_logger, str(db)).open()


def test_missing_db(stub_logger, tmp_path):
    """不存在的 db 应抛 FileNotFoundError"""
    with pytest.raises(FileNotFoundError):
        ChatViewer(stub_logger, str(tmp_path / "nope.db")).open()


def test_readonly_does_not_modify_source(stub_logger, tmp_path):
    """只读打开: 源 db 在 list/export 前后 SHA-256 不变 (取证铁律)"""
    db = tmp_path / "android.db"
    _make_android_db(db)
    before = Hasher.sha256_file(str(db))

    out = tmp_path / "out"
    with ChatViewer(stub_logger, str(db)) as v:
        v.list_contacts()
        v.export_messages(["wxid_alice"], str(out))

    after = Hasher.sha256_file(str(db))
    assert before == after, "只读模式下源 db 不应被修改"


def test_authorization_recorded_in_manifest(stub_logger, tmp_path):
    """授权依据必须写入 manifest 留痕 (AGENTS.md 合规要求)"""
    db = tmp_path / "android.db"
    _make_android_db(db)
    out = tmp_path / "out"

    with ChatViewer(stub_logger, str(db)) as v:
        mp, _ = v.export_messages(
            ["wxid_bob"], str(out),
            authorization="A-个人取证-本人设备",
            authorization_type="A",
        )

    manifest = json.loads(Path(mp).read_text(encoding="utf-8"))
    assert manifest["authorization"] == "A-个人取证-本人设备"
    assert manifest["authorization_type"] == "A"
    assert manifest["selected_wxids"] == ["wxid_bob"]


def test_pc_legacy_columns(stub_logger, tmp_path):
    """PC 老版列名变体: UserName / con_displayname / conRemark"""
    db = tmp_path / "pc_legacy.db"
    conn = sqlite3.connect(str(db))
    conn.executescript(
        "CREATE TABLE contact (UserName TEXT, con_displayname TEXT, conRemark TEXT);"
        "INSERT INTO contact VALUES ('wxid_legacy', 'LegacyNick', 'LegacyRemark');"
    )
    conn.commit()
    conn.close()

    with ChatViewer(stub_logger, str(db)) as v:
        contacts = v.list_contacts()
        assert len(contacts) == 1
        assert contacts[0]["wxid"] == "wxid_legacy"
        assert contacts[0]["nickname"] == "LegacyNick"
        assert contacts[0]["remark"] == "LegacyRemark"


def test_ios_legacy_columns(stub_logger, tmp_path):
    """iOS 老版列名变体: Friend / m_nsNickName / m_nsRemark"""
    db = tmp_path / "ios_legacy.db"
    conn = sqlite3.connect(str(db))
    conn.executescript(
        "CREATE TABLE Friend (userName TEXT, m_nsNickName TEXT, m_nsRemark TEXT);"
        "INSERT INTO Friend VALUES ('wxid_ios', 'iOSNick', 'iOSRemark');"
    )
    conn.commit()
    conn.close()

    with ChatViewer(stub_logger, str(db)) as v:
        contacts = v.list_contacts()
        assert len(contacts) == 1
        assert contacts[0]["wxid"] == "wxid_ios"
        assert contacts[0]["nickname"] == "iOSNick"
        assert contacts[0]["remark"] == "iOSRemark"


def test_android_legacy_message_columns(stub_logger, tmp_path):
    """Android 老版消息列名变体: strTalker / IsSend / msgTime / msgContent + weixinhao"""
    db = tmp_path / "android_legacy_msg.db"
    conn = sqlite3.connect(str(db))
    conn.executescript(
        "CREATE TABLE rcontact (username TEXT, nickname TEXT, remark TEXT, weixinhao TEXT);"
        "CREATE TABLE message (strTalker TEXT, IsSend INTEGER, msgTime INTEGER, msgContent TEXT);"
        "INSERT INTO rcontact VALUES ('wxid_leg1', 'LegacyOne', 'LegacyRemark', 'wx_leg_one');"
        "INSERT INTO message VALUES ('wxid_leg1', 0, 1700000000000, 'msg1');"
        "INSERT INTO message VALUES ('wxid_leg1', 1, 1700000001000, 'msg2');"
    )
    conn.commit()
    conn.close()

    with ChatViewer(stub_logger, str(db)) as v:
        contacts = v.list_contacts()
        assert len(contacts) == 1
        assert contacts[0]["alias"] == "wx_leg_one"
        mp, files = v.export_messages(["wxid_leg1"], str(tmp_path / "out"))
        assert files[0]["message_count"] == 2
