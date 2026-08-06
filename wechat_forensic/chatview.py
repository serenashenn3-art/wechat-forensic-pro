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

    def list_contacts(self) -> List[Dict]:
        """查询联系人列表, 返回 [{wxid, nickname, remark, alias}]

        过滤掉公众号 (gh_* 开头) 和空 username。优先按"有备注"排序,
        便于取证人员快速定位已备注的对象。
        """
        rows: List[Dict] = []
        if self.schema == SCHEMA_ANDROID:
            cur = self._conn.execute(
                "SELECT username, nickname, remark, alias FROM rcontact "
                "WHERE username NOT LIKE 'gh_%' AND username != '' "
                "ORDER BY CASE WHEN remark != '' THEN 0 ELSE 1 END, nickname"
            )
            for r in cur.fetchall():
                rows.append({
                    "wxid": r["username"],
                    "nickname": r["nickname"] or "",
                    "remark": r["remark"] or "",
                    "alias": r["alias"] or "",
                })
        elif self.schema == SCHEMA_PC:
            cur = self._conn.execute(
                "SELECT username, nickname, remark FROM contact "
                "WHERE username NOT LIKE 'gh_%' AND username != '' "
                "ORDER BY CASE WHEN remark != '' THEN 0 ELSE 1 END, nickname"
            )
            for r in cur.fetchall():
                rows.append({
                    "wxid": r["username"],
                    "nickname": r["nickname"] or "",
                    "remark": r["remark"] or "",
                    "alias": "",
                })
        else:  # SCHEMA_IOS
            cur = self._conn.execute(
                "SELECT userName, dbContactNickName, dbContactRemark FROM Friend "
                "WHERE userName NOT LIKE 'gh_%' AND userName IS NOT NULL "
                "ORDER BY CASE WHEN dbContactRemark IS NOT NULL THEN 0 ELSE 1 END"
            )
            for r in cur.fetchall():
                rows.append({
                    "wxid": r["userName"],
                    "nickname": r["dbContactNickName"] or "",
                    "remark": r["dbContactRemark"] or "",
                    "alias": "",
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
    ) -> Tuple[str, List[Dict]]:
        """按勾选的 wxid 列表导出消息, 每个联系人一个文件 + SHA-256

        返回 (manifest_path, files_report)。manifest 含授权依据留痕。
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
        """
        if self.schema == SCHEMA_ANDROID:
            cur = self._conn.execute(
                "SELECT isSend, createTime, content, type FROM message "
                "WHERE talker = ? ORDER BY createTime ASC",
                (wxid,),
            )
            return [{
                "isSend": r["isSend"],
                "time": r["createTime"],
                "content": r["content"] or "",
                "type": r["type"],
            } for r in cur.fetchall()]
        self.log.warning(
            f"schema={self.schema} 的消息不在当前 db 内"
            f" (PC 在 msg_*.db / iOS 在 Chat_* 表), 跳过 {wxid} 的消息导出"
        )
        return []

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
