"""命令行入口"""

import argparse
import datetime
import getpass
import platform
import sys
from pathlib import Path

from . import __version__
from .chatview import ChatViewer, EncryptedDatabaseError, UnsupportedSchemaError
from .config import Config
from .extractor import Extractor
from .hashing import Hasher
from .locator import Locator
from .logger import ForensicLogger
from .mirror import MirrorGenerator
from .packer import Packer
from .report import ReportGenerator, ReportValidationError
from .scanner import Scanner
from .uploader import Uploader, UploaderRegistry, get_config_for, load_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wechat-forensic",
        description=f"WeChat Forensic Extractor Pro v{__version__}",
    )
    parser.add_argument(
        "--mode",
        choices=["quick", "forensic"],
        default="forensic",
        help="quick=直接提取文件 | forensic=生成镜像+哈希+报告",
    )
    parser.add_argument("--source", help="手动指定源路径")
    parser.add_argument(
        "--mirror-disk",
        help="指定物理磁盘进行位对位镜像 (如 /dev/sdb 或 \\\\PhysicalDrive0)",
    )
    parser.add_argument("--output", default="./wechat_forensic_output", help="输出目录")
    parser.add_argument("--zip-password", help="压缩密码")
    parser.add_argument(
        "--upload",
        default="none",
        help=(
            "云端上传目标。内置: baidu / aliyun / s3 / webdav / sftp / local / none。"
            " 任意第三方插件名也接受 (见 --upload-list)。"
        ),
    )
    parser.add_argument(
        "--upload-config",
        default=None,
        help=(
            "上传配置文件路径 (YAML 或 JSON)。"
            " 留空则按 $WECHAT_FORENSIC_UPLOAD_CONFIG / ~/.config/wechat-forensic/upload.yaml 查找,"
            " 或用 $WECHAT_FORENSIC_UPLOAD_<NAME>_* 环境变量。"
        ),
    )
    parser.add_argument(
        "--upload-list",
        action="store_true",
        help="列出所有可用上传器 (内置 + 插件) 后退出",
    )
    parser.add_argument("--no-interactive", action="store_true", help="非交互模式")
    parser.add_argument("--case-id", help="案件编号 / 司法鉴定委托函号 (写入报告)")
    parser.add_argument("--evidence-id", help="证据编号, 如 E001 (写入报告)")
    parser.add_argument(
        "--sign",
        action="store_true",
        help="对最终报告做数字签名 (生成 _signature.json, 密钥来自 WECHAT_FORENSIC_HMAC_KEY)",
    )
    parser.add_argument(
        "--chatview",
        help=(
            "已解密微信 db 路径 (明文 sqlite)。启用此模式可列出联系人"
            " (昵称/备注) 并按勾选导出消息。本工具不解密 db,"
            " 请先用合规鉴定工具解密为明文 sqlite。"
        ),
    )
    parser.add_argument(
        "--authorization",
        help="授权依据 (chatview 模式必填, 写入 manifest 留痕)",
    )
    parser.add_argument(
        "--select",
        help=(
            "非交互模式: 指定联系人。支持编号 '1,3,5-8' 或 wxid"
            " 'wxid_a,wxid_b'。留空则交互式勾选 (配合 --no-interactive 跳过)。"
        ),
    )
    parser.add_argument(
        "--version", action="version", version=f"wechat-forensic {__version__}"
    )
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    # 单独处理 --chatview: 选择性消息导出模式 (独立于全量提取流程)
    if args.chatview:
        return _run_chatview(args)

    # 单独处理 --upload-list: 打印后即退出
    if args.upload_list:
        reg = UploaderRegistry()
        print("Available uploaders:")
        print()
        for u in reg.list():
            star = "*" if u["is_builtin"] else "+"
            print(
                f"  [{star}] {u['name']:14s}  {u['display_name']}\n"
                f"        deps: {u['required_deps']}"
            )
            if u["config_schema_hint"]:
                print(f"        config: {u['config_schema_hint']}")
        print()
        print("(*) builtin   (+) plugin from ~/.config/wechat-forensic/plugins/uploaders/")
        return 0

    log = ForensicLogger(Config().LOG_FILE)
    operations: list = []

    print("=" * 70)
    print(f"  WeChat Forensic Extractor Pro v{__version__}")
    print("  跨平台微信聊天记录取证提取工具链")
    print("=" * 70)
    log.info(f"启动模式: {args.mode}")
    log.info(f"操作系统: {platform.platform()}")
    log.info(f"操作人员: {getpass.getuser()}")

    # 1. 扫描
    print("\n" + "-" * 70)
    print("[步骤 1/6] 扫描设备与存储介质")
    print("-" * 70)
    scanner = Scanner(log)
    drives = scanner.drives()
    log.info(f"发现 {len(drives)} 个逻辑磁盘:")
    for d in drives:
        log.info(f"  {d['device']} -> {d['mount']} | 可用 {d['free']} / 总 {d['total']}")

    physical = []
    if args.mode == "forensic":
        physical = scanner.physical_disks()
        log.info(f"发现 {len(physical)} 个物理磁盘:")
        for p in physical:
            log.info(f"  {p.get('path', '-')} | {p.get('model', '-')} | {p.get('size', '-')}")

    # 2. 镜像
    mirror_info = None
    if args.mode == "forensic" and (args.mirror_disk or not args.no_interactive):
        print("\n" + "-" * 70)
        print("[步骤 2/6] 位对位镜像生成")
        print("-" * 70)
        mirror_gen = MirrorGenerator(log)
        if args.mirror_disk:
            target = args.mirror_disk
        elif physical and not args.no_interactive:
            print("\n可镜像的物理磁盘:")
            for i, p in enumerate(physical, 1):
                print(f"  {i}. {p.get('path')} | {p.get('model')} | {p.get('size')}")
            print("  0. 跳过镜像,直接提取文件")
            choice = input("\n选择要镜像的磁盘编号: ").strip()
            if choice == "0" or not choice:
                target = None
            else:
                try:
                    target = physical[int(choice) - 1]["path"]
                except (IndexError, ValueError):
                    target = None
        else:
            target = None

        if target:
            mirror_dir = Path(args.output) / "mirrors"
            mirror_dir.mkdir(parents=True, exist_ok=True)
            mirror_path = str(
                mirror_dir / f"disk_mirror_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.img"
            )
            log.evidence(f"开始镜像磁盘: {target}")
            mirror_info = mirror_gen.mirror_disk_dd(target, mirror_path)
            if mirror_info.get("success"):
                operations.append(
                    {
                        "step": "磁盘镜像生成",
                        "timestamp": datetime.datetime.now().isoformat(),
                        "description": f"位对位镜像 {target}",
                        "source": target,
                        "output": mirror_path,
                        "sha256": mirror_info["sha256"],
                        "tool": "dd",
                    }
                )
            else:
                log.error("镜像生成失败,将尝试直接文件提取")

    # 3. 定位
    print("\n" + "-" * 70)
    print("[步骤 3/6] 定位微信数据")
    print("-" * 70)
    locator = Locator(log)
    pc = locator.find_pc([args.source]) if args.source else locator.find_pc()
    mobile = locator.find_mobile()
    targets = []
    if pc:
        log.info(f"发现 {len(pc)} 个PC微信数据:")
        for i, x in enumerate(pc, 1):
            log.info(f"  {i}. {x['wxid']} @ {x['path']}")
            targets.append(("pc", x))
    if mobile:
        log.info(f"发现 {len(mobile)} 个手机备份:")
        for i, x in enumerate(mobile, 1):
            log.info(f"  {i}. {x['type']} @ {x['path'][:60]}...")
            targets.append(("mobile", x))

    if not targets:
        if not args.no_interactive:
            custom = input("\n未自动发现,手动输入路径(逗号分隔)或回车退出: ").strip()
            if custom:
                pc = locator.find_pc([p.strip() for p in custom.split(",")])
                targets = [("pc", x) for x in pc]
        if not targets:
            log.error("未找到微信数据,退出")
            return 1

    # 4. 提取
    print("\n" + "-" * 70)
    print("[步骤 4/6] 提取与哈希校验")
    print("-" * 70)
    extractor = Extractor(log, args.output)
    extracted_dirs = []
    for t, info in targets:
        if t == "pc":
            dst, hash_report = extractor.extract_pc(info)
        else:
            dst, hash_report = extractor.extract_mobile(info)
        extracted_dirs.append(dst)
        operations.append(
            {
                "step": "数据提取",
                "timestamp": datetime.datetime.now().isoformat(),
                "description": f"提取 {info.get('wxid', info.get('type'))}",
                "source": info.get("path", info.get("src")),
                "output": dst,
                "file_hashes": hash_report,
            }
        )
    extractor.save_manifest()

    # 5. 压缩
    print("\n" + "-" * 70)
    print("[步骤 5/6] 压缩打包")
    print("-" * 70)
    arc_path = Packer.zip_dir(args.output, pwd=args.zip_password, logger=log)
    arc_hash = Hasher.sha256_file(arc_path)
    operations.append(
        {
            "step": "压缩打包",
            "timestamp": datetime.datetime.now().isoformat(),
            "description": "打包所有提取数据",
            "output": arc_path,
            "sha256": arc_hash,
            "encrypted": args.zip_password is not None,
        }
    )
    log.evidence(f"压缩包 SHA-256: {arc_hash}")

    # 6. 上传
    if args.upload != "none":
        print("\n" + "-" * 70)
        print("[步骤 6/6] 云端上传")
        print("-" * 70)
        upload_ok = False
        upload_message = ""
        upload_remote = ""
        upload_alg = args.upload

        registry = UploaderRegistry()
        uploader_obj = registry.get(args.upload)
        if uploader_obj is not None:
            # 新路径: 注册表 + 可插拔
            full_cfg = load_config(args.upload_config)
            cfg = get_config_for(args.upload, full_cfg)
            result = uploader_obj.upload(arc_path, logger=log, config=cfg)
            upload_ok = bool(result.get("success"))
            upload_message = result.get("message", "")
            upload_remote = result.get("remote", "")
            upload_alg = result.get("algorithm", args.upload)
        else:
            # 兜底: 旧静态方法(向后兼容)
            if args.upload == "baidu":
                upload_ok = Uploader.baidu(arc_path, log)
            elif args.upload == "aliyun":
                upload_ok = Uploader.aliyun(arc_path, log)
            else:
                log.error(
                    f"未知上传器: {args.upload!r}。"
                    f" 用 --upload-list 查看所有可用上传器。"
                )
                upload_message = f"未找到名为 '{args.upload}' 的上传器"
                upload_alg = "unknown"

        operations.append(
            {
                "step": "云端上传",
                "timestamp": datetime.datetime.now().isoformat(),
                "description": f"上传至 {args.upload}",
                "source": arc_path,
                "sha256": arc_hash,
                "success": upload_ok,
                "message": upload_message,
                "remote": upload_remote,
                "algorithm": upload_alg,
            }
        )

    # 报告
    print("\n" + "-" * 70)
    print("[最终] 生成取证报告")
    print("-" * 70)
    try:
        report_path = ReportGenerator.generate(
            args.output,
            operations,
            log,
            case_id=args.case_id,
            evidence_id=args.evidence_id,
        )
    except ReportValidationError as e:
        log.error(f"报告生成失败: {e}")
        print(f"\n[错误] {e}")
        print("提示: 司法取证场景请提供 --case-id 和 --evidence-id")
        return 1

    # 可选: 数字签名
    if args.sign:
        from .security import sign_report

        sig = sign_report(report_path)
        log.success(f"数字签名: {sig.get('signature_algorithm')} -> _signature.json")

    # 汇总
    print("\n" + "=" * 70)
    print("  取证完成")
    print("=" * 70)
    print(f"  输出目录: {args.output}")
    print(f"  压缩包:   {arc_path}")
    print(f"  包哈希:   {arc_hash}")
    print(f"  报告:     {report_path}")
    if mirror_info and mirror_info.get("success"):
        print(f"  镜像:     {mirror_info['output']}")
        print(f"  镜像哈希: {mirror_info['sha256']}")
    print("=" * 70)
    print("\n  ⚠️  提示: 如需司法程序使用,建议委托有资质的电子数据")
    print("     司法鉴定机构出具正式鉴定报告。")
    print("=" * 70)
    return 0


def _resolve_selection(args, contacts) -> list:
    """从 --select 或交互式 input 解析选中的 0-based 索引"""
    if args.select:
        spec = args.select.strip()
        cleaned = spec.replace(",", "").replace("-", "").replace(" ", "")
        if cleaned.isdigit() and cleaned:
            # 编号语法: 1,3,5-8
            return ChatViewer.parse_selection(spec, len(contacts))
        # wxid 语法: wxid_a,wxid_b
        wxid_set = {w.strip() for w in spec.split(",") if w.strip()}
        return [i for i, c in enumerate(contacts) if c["wxid"] in wxid_set]
    if not args.no_interactive:
        print("\n输入要导出的联系人编号 (如 1,3,5-8), 回车跳过:")
        spec = input("选择> ").strip()
        if not spec:
            return []
        return ChatViewer.parse_selection(spec, len(contacts))
    return []


def _run_chatview(args) -> int:
    """选择性消息导出模式: 已解密 db -> 列联系人 -> 勾选 -> 导出

    本模式只读取已解密明文 sqlite, 不含任何解密/密钥推导代码。
    """
    if not args.authorization:
        print("[错误] chatview 模式必须提供 --authorization (授权依据留痕)")
        print("  合法场景: 个人取证 / 企业合规 / 司法鉴定 / 警方 / 学术研究")
        return 1

    log = ForensicLogger(Config().LOG_FILE)

    print("=" * 70)
    print(f"  WeChat Forensic Extractor Pro v{__version__} - ChatViewer")
    print("  选择性消息导出 (仅读取已解密明文 sqlite, 不含解密能力)")
    print("=" * 70)
    log.info(f"授权依据: {args.authorization}")
    log.info(f"源 db: {args.chatview}")

    try:
        with ChatViewer(log, args.chatview) as viewer:
            contacts = viewer.list_contacts()
            if not contacts:
                print("\n未查询到联系人, 退出。")
                return 0

            print("\n" + "-" * 70)
            print(f"联系人列表 (共 {len(contacts)} 个, 已过滤公众号)")
            print("-" * 70)
            for i, c in enumerate(contacts, 1):
                label = c["remark"] or c["nickname"] or c["wxid"]
                extra = []
                if c["remark"] and c["nickname"]:
                    extra.append(f"昵称={c['nickname']}")
                if c["alias"]:
                    extra.append(f"微信号={c['alias']}")
                tail = f"  [{', '.join(extra)}]" if extra else ""
                print(f"  {i:>4}. {label}  (wxid={c['wxid']}){tail}")

            selected_idx = _resolve_selection(args, contacts)
            if not selected_idx:
                print("\n未选择任何联系人, 退出。")
                return 0

            selected_wxids = [contacts[i]["wxid"] for i in selected_idx]
            print(f"\n已选择 {len(selected_wxids)} 个联系人, 开始导出...")
            for i in selected_idx:
                c = contacts[i]
                label = c["remark"] or c["nickname"] or c["wxid"]
                print(f"  - {label} ({c['wxid']})")

            out_dir = str(Path(args.output) / "chatview")
            mp, files = viewer.export_messages(
                selected_wxids, out_dir, authorization=args.authorization
            )

            print("\n" + "=" * 70)
            print("  ChatViewer 导出完成")
            print("=" * 70)
            print(f"  输出目录: {out_dir}")
            print(f"  清单:     {mp}")
            print(f"  文件数:   {len(files)}")
            total_msgs = sum(f["message_count"] for f in files)
            print(f"  消息总数: {total_msgs}")
            print("=" * 70)
            return 0
    except (EncryptedDatabaseError, UnsupportedSchemaError, FileNotFoundError) as e:
        log.error(str(e))
        print(f"\n[错误] {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
