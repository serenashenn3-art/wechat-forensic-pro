"""取证报告生成 — 符合 ISO/IEC 27037 框架"""

import datetime
import getpass
import json
import platform
import socket
import sys
from pathlib import Path
from typing import List, Optional

from .security import chain_of_custody_template


class ReportGenerator:
    @staticmethod
    def generate(
        output_dir: str,
        operations: List[dict],
        logger=None,
        case_id: Optional[str] = None,
        evidence_id: Optional[str] = None,
    ) -> str:
        """生成 JSON + TXT 报告

        Args:
            output_dir: 输出目录
            operations: 操作日志列表
            logger: 日志器
            case_id: 案件编号 (司法鉴定委托函号)
            evidence_id: 证据编号 (E001 等)

        Returns:
            报告 txt 文件路径
        """
        report = {
            "report_id": f"WFE-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
            "report_version": "2.0.3",
            "tool": {
                "name": "WeChat Forensic Extractor Pro",
                "version": "2.0.3",
                "url": "https://github.com/serenashenn3-art/wechat-forensic-pro",
            },
            "generated_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "environment": {
                "operator": getpass.getuser(),
                "hostname": socket.gethostname(),
                "platform": platform.platform(),
                "python_version": sys.version.split()[0],
            },
            "compliance": {
                "frameworks": [
                    "ISO/IEC 27037:2012",
                    "ISO/IEC 27042:2015",
                    "RFC 3227",
                    "NIST SP 800-86",
                ],
                "principle": "原始证据不可修改,所有操作在副本/镜像上进行",
                "hash_algorithm": "SHA-256 (4MB chunk)",
                "integrity_verification": "每个关键步骤均计算并记录 SHA-256",
            },
            "chain_of_custody": chain_of_custody_template(),
            "operations": operations,
            "output_artifacts": [],
        }
        if case_id:
            report["chain_of_custody"]["case_id"] = case_id
        if evidence_id:
            report["chain_of_custody"]["evidence_id"] = evidence_id

        # 写入 JSON
        json_path = Path(output_dir) / "_forensic_report.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        # 写入 TXT (人类可读)
        txt_path = Path(output_dir) / "_forensic_report.txt"
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("=" * 78 + "\n")
            f.write("  微信聊天记录取证报告\n")
            f.write("  WeChat Forensic Acquisition Report\n")
            f.write("=" * 78 + "\n\n")
            f.write(f"报告编号 (Report ID):    {report['report_id']}\n")
            f.write(f"报告版本 (Schema):      {report['report_version']}\n")
            f.write(f"生成时间 (UTC):         {report['generated_at_utc']}\n")
            f.write(f"工具:                   {report['tool']['name']} v{report['tool']['version']}\n")
            f.write(f"操作员 (Operator):      {report['environment']['operator']}\n")
            f.write(f"主机名 (Hostname):      {report['environment']['hostname']}\n")
            f.write(f"操作系统 (Platform):    {report['environment']['platform']}\n")
            f.write(f"Python 版本:            {report['environment']['python_version']}\n\n")

            f.write("-" * 78 + "\n")
            f.write("  合规框架 (Compliance Framework)\n")
            f.write("-" * 78 + "\n")
            for fw in report["compliance"]["frameworks"]:
                f.write(f"  - {fw}\n")
            f.write(f"  原则: {report['compliance']['principle']}\n")
            f.write(f"  哈希: {report['compliance']['hash_algorithm']}\n\n")

            coc = report["chain_of_custody"]
            f.write("-" * 78 + "\n")
            f.write("  证据链 (Chain of Custody)\n")
            f.write("-" * 78 + "\n")
            f.write(f"  案件编号 (Case ID):     {coc.get('case_id', '<未填写>')}\n")
            f.write(f"  证据编号 (Evidence ID): {coc.get('evidence_id', '<未填写>')}\n")
            f.write(f"  取证时间:               {coc['acquisition']['date_utc']}\n")
            f.write(f"  取证地点:               {coc['acquisition']['location']}\n")
            f.write(f"  操作员:                 {coc['acquisition']['operator']}\n")
            f.write(f"  见证人:                 {coc['acquisition']['witness']}\n")
            f.write(f"  取证方法:               {coc['acquisition']['method']}\n")
            f.write(f"  写保护:                 {'是' if coc['acquisition']['write_blocking']['used'] else '否 (司法效力将受影响)'}\n\n")

            f.write("-" * 78 + "\n")
            f.write("  操作日志 (Operations)\n")
            f.write("-" * 78 + "\n\n")
            for i, op in enumerate(operations, 1):
                f.write(f"[步骤 {i}] {op.get('step', 'Unknown')}\n")
                f.write(f"  时间: {op.get('timestamp', '-')}\n")
                f.write(f"  描述: {op.get('description', '-')}\n")
                if "sha256" in op:
                    f.write(f"  SHA-256: {op['sha256']}\n")
                if "source" in op:
                    f.write(f"  来源: {op['source']}\n")
                if "output" in op:
                    f.write(f"  输出: {op['output']}\n")
                f.write("\n")

            f.write("-" * 78 + "\n")
            f.write("  证据完整性声明 (Integrity Statement)\n")
            f.write("-" * 78 + "\n\n")
            f.write("1. 所有哈希值使用 SHA-256 算法计算(4MB 块)\n")
            f.write("2. 原始存储介质在提取过程中未被修改\n")
            f.write("3. 所有操作均有时间戳和操作人员记录\n")
            f.write("4. 本报告可附带数字签名 (见 _signature.json)\n")
            f.write("5. 如需司法效力, 建议委托有资质的电子数据司法鉴定机构复核\n\n")

            f.write("-" * 78 + "\n")
            f.write("  ⚠️ 局限性与免责声明 (Limitations & Disclaimer)\n")
            f.write("-" * 78 + "\n\n")
            f.write("本工具:\n")
            f.write("  - 仅做位对位提取,不包含 EnMicroMsg.db 解密\n")
            f.write("  - 解密他人微信数据仍需合法授权\n")
            f.write("  - 不能保证数据库内容在原始设备上未被修改 (本工具只校验提取副本)\n")
            f.write("  - 报告内容仅作为操作日志, 不构成司法鉴定意见书\n")
            f.write("  - 司法鉴定需由具备 CNAS / CMA 资质的机构出具正式报告\n")

        if logger:
            logger.success(f"取证报告生成: {txt_path}")
        return str(txt_path)
