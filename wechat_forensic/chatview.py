"""已解密微信 db 的联系人查询 + 选择性消息导出

法律边界 (AGENTS.md § 法律红线, 优先级最高):
    本模块**只读取已解密的明文 sqlite**, 不包含任何密钥推导 / SQLCipher
    解密代码。若传入的 db 仍处于加密状态, 本模块会拒绝处理并提示用户
    先用合规鉴定工具解密。合法授权场景: 个人取证 / 企业合规审计 (经员工
    书面同意) / 警方司法取证 / 司法鉴定 / 学术研究。

    本模块刻意不解密、不接触密钥, 仅对"已解密的明文 sqlite"做查询与
    选择性导出, 用于减小全量提取的体积 (只导出勾选联系人的消息)。

引入此模块即表示使用者承诺在合法授权场景下使用, 并对所处理的数据来源
合法性负责。
"""

import datetime
import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .hashing import Hasher


class EncryptedDatabaseError(Exception):
    """db 仍是 SQLCipher 加密状态, 本工具拒绝处理 (不解密)"""


class UnsupportedSchemaError(Exception):
    """无法识别的 db schema (非微信联系人 db)"""


# schema 探测结果常量
SCHEMA_ANDROID = "android"   # EnMicroMsg.db 解密后: rcontact + message
SCHEMA_PC = "pc"             # MicroMsg.db: contact (消息在 msg_*.db, 不在此 db)
SCHEMA_IOS = "ios"           # MM.sqlite: Friend


# 老版/不同导出工具产生的列名变体。键为标准化后的逻辑名。
CONTACT_COLUMNS = {
    "wxid": ["username", "userName", "UserName", "alias", "Alias"],
    "nickname": ["nickname", "nickName", "NickName", "m_nsNickName", "dbContactNickName", "con_displayname", "conNickname"],
    "remark": ["remark", "Remark", "m_nsRemark", "dbContactRemark", "conRemark", "con_remark"],
    "alias": ["alias", "Alias", "m_nsAliasName", "con_username", "weixinhao", "wxid"],
}

MESSAGE_COLUMNS = {
    "talker": ["talker", "strTalker", "username", "UserName"],
    "isSend": ["isSend", "is_send", "IzSend", "type"],
    "time": ["createTime", "create_time", "msgTime", "msgtime", "MsgTime", "CreateTime"],
    "content": ["content", "msgContent", "msg_content", "message", "msg"],
    "type": ["type", "msgType", "msg_type", "Type"],
}


class ChatViewer:
    """读取已解密微信 db, 列出联系人, 按勾选导出消息。

    本类不接触任何加密 db / 密钥。调用方必须保证传入的是已解密明文 sqlite。
    打开方式为只读 (sqlite uri mode=ro), 不会修改源 db。
    """

    def __init__(self, logger, db_path: str):
        self.log = logger
        self.db_path = Path(db_path)
        self.schema: Optional[str] = None
        self._conn: Optional[sqlite3.Connection] = None

    def open(self) -> "ChatViewer":
        """打开 db (只读), 检测加密, 探测 schema"""
        if not self.db_path.exists():
            raise FileNotFoundError(f"db 不存在: {self.db_path}")
        # 只读打开: 取证场景严禁修改源 db (AGENTS.md § 关键安全约束)
        uri = f"file:{self.db_path.as_posix()}?mode=ro"
        try:
            self._conn = sqlite3.connect(uri, uri=True)
            self._conn.row_factory = sqlite3.Row
            # 加密 db 在首次查询时会抛 DatabaseError
            cur = self._conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            tables = {row[0] for row in cur.fetchall()}
        except sqlite3.DatabaseError as e:
            if self._conn:
                self._conn.close()
                self._conn = None
            msg = str(e).lower()
            if "encrypted" in msg or "not a database" in msg or "file is not" in msg:
                raise EncryptedDatabaseError(
                    f"db 仍是加密状态 ({self.db_path})。本工具不包含解密能力,"
                    f" 请先用合规鉴定工具将其解密为明文 sqlite 后再传入。"
                ) from e
            raise
        self.schema = self._detect_schema(tables)
        self.log.info(
            f"已打开 db: {self.db_path} (schema={self.schema}, 表 {len(tables)} 个)"
        )
        return self

    @staticmethod
    def _detect_schema(tables: set) -> str:
        """根据表名集合判断微信 db 类型"""
        if "rcontact" in tables and "message" in tables:
            return SCHEMA_ANDROID
        if "contact" in tables:
            return SCHEMA_PC
        if "Friend" in tables:
            return SCHEMA_IOS
        raise UnsupportedSchemaError(
            f"无法识别的 schema, 现有表 (前 10): {sorted(tables)[:10]}。"
            f" 支持: Android(rcontact+message) / PC(contact) / iOS(Friend)"
        )

    def _columns(self, table: str) -> set:
        """获取指定表的实际列名集合"""
        cur = self._conn.execute(f"PRAGMA table_info({table})")
        return {row["name"] for row in cur.fetchall()}

    @staticmethod
    def _pick_col(cols: set, *candidates) -> Optional[str]:
        """从候选列名中挑选第一个存在的列名"""
        for c in candidates:
            if c in cols:
                return c
        return None

    def _resolve_contact_cols(self, table: str) -> Dict[str, Optional[str]]:
        """根据实际表列名, 解析出 wxid/nickname/remark/alias 对应的真实列"""
        cols = self._columns(table)
        return {
            key: self._pick_col(cols, *candidates)
            for key, candidates in CONTACT_COLUMNS.items()
        }

    def list_contacts(self) -> List[Dict]:
        """查询联系人列表, 返回 [{wxid, nickname, remark, alias}]

        过滤掉公众号 (gh_* 开头) 和空 username。优先按"有备注"排序,
        便于取证人员快速定位已备注的对象。

        对老版微信/不同导出工具产生的列名变体做动态适配。
        """
        rows: List[Dict] = []
        table_map = {
            SCHEMA_ANDROID: "rcontact",
            SCHEMA_PC: "contact",
            SCHEMA_IOS: "Friend",
        }
        table = table_map.get(self.schema)
        if not table:
            return rows

        mapping = self._resolve_contact_cols(table)
        wxid_col = mapping.get("wxid") or "username"
        nick_col = mapping.get("nickname") or "nickname"
        remark_col = mapping.get("remark") or "remark"
        alias_col = mapping.get("alias")

        # 构造 SELECT / WHERE / ORDER BY, 只使用实际存在的列
        select_cols = [wxid_col, nick_col, remark_col]
        if alias_col:
            select_cols.append(alias_col)
        order_col = remark_col if mapping.get("remark") else nick_col

        where_parts = [f"{wxid_col} NOT LIKE 'gh_%'", f"{wxid_col} != ''"]
        sql = (
            f"SELECT {', '.join(select_cols)} FROM {table} "
            f"WHERE {' AND '.join(where_parts)} "
            f"ORDER BY CASE WHEN {order_col} != '' THEN 0 ELSE 1 END, {nick_col}"
        )
        cur = self._conn.execute(sql)
        for r in cur.fetchall():
            rows.append({
                "wxid": r[wxid_col] or "",
                "nickname": r[nick_col] or "",
                "remark": r[remark_col] or "",
                "alias": r[alias_col] if alias_col else "",
            })
        self.log.info(f"查询到 {len(rows)} 个联系人 (已过滤公众号)")
        return rows

    @staticmethod
    def parse_selection(spec: str, total: int) -> List[int]:
        """解析 '1,3,5-8' 语法为 0-based 索引列表 (去重保序, 越界忽略)

        total: 联系人总数, 用于校验编号范围。返回 0-based 索引。
        """
        result: List[int] = []
        seen = set()
        for part in spec.replace(" ", "").split(","):
            if not part:
                continue
            if "-" in part:
                lo, hi = part.split("-", 1)
                lo_i, hi_i = int(lo), int(hi)
                if lo_i > hi_i:
                    lo_i, hi_i = hi_i, lo_i
                for i in range(lo_i, hi_i + 1):
                    if 1 <= i <= total and i not in seen:
                        seen.add(i)
                        result.append(i - 1)
            else:
                i = int(part)
                if 1 <= i <= total and i not in seen:
                    seen.add(i)
                    result.append(i - 1)
        return result

    def export_messages(
        self,
        wxids: List[str],
        out_dir: str,
        authorization: str = "",
        authorization_type: str = "",
    ) -> Tuple[str, List[Dict]]:
        """按勾选的 wxid 列表导出消息, 每个联系人一个文件 + SHA-256

        返回 (manifest_path, files_report)。manifest 含授权依据与类型留痕。
        """
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        files_report: List[Dict] = []
        for wxid in wxids:
            msgs = self._fetch_messages(wxid)
            safe = wxid.replace("/", "_").replace("\\", "_")
            fpath = out / f"chat_{safe}.txt"
            self._write_messages(fpath, wxid, msgs)
            sha = Hasher.sha256_file(str(fpath))
            files_report.append({
                "wxid": wxid,
                "path": str(fpath),
                "sha256": sha,
                "message_count": len(msgs),
                "size": fpath.stat().st_size,
            })
            self.log.evidence(
                f"导出 {wxid}: {len(msgs)} 条 -> {fpath} (sha256={sha[:12]}...)"
            )
        manifest = {
            "tool": "WeChat Forensic Extractor Pro - ChatViewer",
            "time": datetime.datetime.now().isoformat(),
            "source_db": str(self.db_path),
            "schema": self.schema,
            "authorization_type": authorization_type or "(未填写)",
            "authorization": authorization or "(未填写)",
            "selected_wxids": wxids,
            "files": files_report,
        }
        mp = out / "_chatview_manifest.json"
        # AGENTS.md 约束: 换行必须用真实 \n, 不能用 "\\n"
        with open(mp, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
        self.log.success(f"清单: {mp}")
        return str(mp), files_report

    def _fetch_messages(self, wxid: str) -> List[Dict]:
        """取该联系人的消息 (按时间升序)

        Android: message 表 talker=wxid, createTime 为毫秒。
        PC/iOS: 消息不在联系人 db 内 (PC 在 msg_*.db, iOS 在 Chat_* 表),
        当前 db 仅含联系人, 此处返回空并给出 warning。

        对老版/不同导出工具的列名变体做动态适配。
        """
        if self.schema != SCHEMA_ANDROID:
            self.log.warning(
                f"schema={self.schema} 的消息不在当前 db 内"
                f" (PC 在 msg_*.db / iOS 在 Chat_* 表), 跳过 {wxid} 的消息导出"
            )
            return []

        tables = {row[0] for row in self._conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "message" not in tables:
            return []

        cols = self._columns("message")
        talker_col = self._pick_col(cols, *MESSAGE_COLUMNS["talker"]) or "talker"
        is_send_col = self._pick_col(cols, *MESSAGE_COLUMNS["isSend"]) or "isSend"
        time_col = self._pick_col(cols, *MESSAGE_COLUMNS["time"]) or "createTime"
        content_col = self._pick_col(cols, *MESSAGE_COLUMNS["content"]) or "content"
        type_col = self._pick_col(cols, *MESSAGE_COLUMNS["type"])

        select_cols = [is_send_col, time_col, content_col]
        if type_col:
            select_cols.append(type_col)
        sql = (
            f"SELECT {', '.join(select_cols)} "
            f"FROM message WHERE {talker_col} = ? ORDER BY {time_col} ASC"
        )
        cur = self._conn.execute(sql, (wxid,))
        return [{
            "isSend": r[is_send_col],
            "time": r[time_col],
            "content": r[content_col] or "",
            "type": r[type_col] if type_col else None,
        } for r in cur.fetchall()]

    @staticmethod
    def _format_time(ts) -> str:
        """格式化时间戳: Android 毫秒 / PC 秒 / 其他原样"""
        if isinstance(ts, (int, float)):
            if ts > 1e12:  # 毫秒
                return datetime.datetime.fromtimestamp(ts / 1000).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            if ts > 0:     # 秒
                return datetime.datetime.fromtimestamp(ts).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
        return str(ts)

    def _write_messages(self, fpath: Path, wxid: str, msgs: List[Dict]):
        """把消息写成人类可读文本 (换行必须真实 \\n, AGENTS.md 约束)"""
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(f"# 联系人: {wxid}\n")
            f.write(f"# 消息数: {len(msgs)}\n")
            f.write("=" * 60 + "\n")
            for m in msgs:
                dt = self._format_time(m["time"])
                sender = "我" if m["isSend"] else "对方"
                f.write(f"[{dt}] {sender}: {m['content']}\n")

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self):
        return self.open()

    def __exit__(self, *exc):
        self.close()
