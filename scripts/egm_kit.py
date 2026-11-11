#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""egm_kit.py — EGM（大象-金鱼）设计评审工作流的脚手架与守门工具。

无第三方依赖，离线可跑。三个子命令：

  new     在建档目录下生成一轮设计目录（概念简报、草案、裁决台账、交接边界）
  packet  把设计文档变成金鱼评审包：解析文档内部引用，生成只读清单与 manifest
  check   校验某轮评审报告的结构与记账，或校验整个设计目录是否真的收敛

退出码：0 通过；1 未通过。未通过时逐条打印原因，不输出“大致没问题”的结论。

用法示例：
  python egm_kit.py new webhook-retry --root docs/designs --title "Webhook 投递重试" --object technical
  python egm_kit.py packet docs/designs/2026-11-11-webhook-retry/design_draft.md --base .
  python egm_kit.py check docs/designs/2026-11-11-webhook-retry/reviews/round-01
  python egm_kit.py check docs/designs/2026-11-11-webhook-retry
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------- 常量

STEP_REPORTS = [
    (5, "step5_zoom_out_report.md", "zoom_out + inventive_catalyst"),
    (6, "step6_comprehension_report.md", "comprehension"),
    (7, "step7_critic_report.md", "design + structural + style"),
    (8, "step8_intermediate_zoom_out_report.md", "zoom_out"),
    (9, "step9_readiness_report.md", "readiness + codebase_details + style"),
]

SEVERITIES = ("Blocker", "Major", "Minor", "Nit")
ADJUDICATIONS = ("PROPOSE FIX", "CONTEST", "ESCALATE", "DECLINE")
FINDING_STATUSES = ("settled", "open", "reopened")

META_KEYS = ("评审者", "步骤", "范围", "对象类型", "只读", "隔离模式", "状态")

FINDING_ID = re.compile(r"^F(\d+)-(\d{1,3})$")
LINK_INLINE = re.compile(r"\[[^\]]*\]\(\s*([^)\s]+?)(?:\s+\"[^\"]*\")?\s*\)")
LINK_HTML = re.compile(r"href\s*=\s*[\"']([^\"']+)[\"']", re.IGNORECASE)
LINK_ANGLE = re.compile(r"<(https?://[^>\s]+)>", re.IGNORECASE)
BACKTICK = re.compile(r"`([^`\n]+)`")

SKIP_SCHEMES = ("http://", "https://", "mailto:", "tel:", "data:", "ftp://")

CODE_EXT = (
    ".py", ".pyi", ".java", ".kt", ".ts", ".tsx", ".js", ".jsx", ".vue", ".go",
    ".rs", ".c", ".h", ".cpp", ".cs", ".rb", ".php", ".sql", ".proto", ".yaml",
    ".yml", ".json", ".toml", ".ini", ".xml", ".gradle", ".sh", ".ps1", ".md",
)

CLOSING_NOTE = "未通过不代表方案有问题，只代表还不到能交给实现的程度。"


# ---------------------------------------------------------------- 基础工具

def fail(msg: str) -> int:
    print(f"[错误] {msg}")
    return 1


def read_text(path: Path) -> str:
    """只接受 UTF-8（含 BOM）。读不出来就报错，不猜测编码。"""
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        raise SystemExit(
            f"[错误] 无法以 UTF-8 读取：{path}\n"
            "        请先另存为 UTF-8（无 BOM 也可），再重新运行。"
        )


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def split_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def is_separator(cells: list[str]) -> bool:
    return bool(cells) and all(set(c) <= set("-: ") and c for c in cells)


def posix(path: Path, base: Path) -> str:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return path.as_posix()


def sanitize_slug(raw: str) -> str:
    slug = re.sub(r"[^\w\-]+", "-", raw.strip(), flags=re.UNICODE)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug or "design"


# ---------------------------------------------------------------- new

CONCEPTS_TEMPLATE = """# {title} · 概念简报

| 项 | 内容 |
| --- | --- |
| 设计标识 | {design_id} |
| 对象类型 | {object_type} |
| 建档时间 | {stamp} |
| 状态 | brainstorm |

## 1. 要解决的问题

（一句话写清问题本身，不写方案。谁在什么场景下遇到什么代价。）

## 2. 目标

-

## 3. 非目标

- （明确划出去的东西，比目标更能防漂移）

## 4. 约束

- 时间：
- 人力：
- 技术栈 / 平台：
- 合规 / 数据：

## 5. 成功判据

- （可被第三人检验的判据，不写“体验更好”这类说法）

## 6. 七镜头速记

| 镜头 | 追问 | 结论 |
| --- | --- | --- |
| 对立面 / YAGNI | 不做会怎样？有没有更小的做法？ | |
| 成本与配额 | 钱、额度、算力、人力谁付？ | |
| UX 与开发者体验 | 谁要多学一步？谁要多等一秒？ | |
| 迁移与向后兼容 | 旧数据、旧调用方、旧配置怎么办？ | |
| 可观测性与 SRE | 坏了怎么知道？怎么定位？怎么回滚？ | |
| 长期技术债 | 半年后谁会为它付利息？ | |
| 创造性催化剂 | 有没有被否得太早的第三种做法？ | |

## 7. 已否决方案

| 方案 | 否决理由 | 什么条件下可能重新考虑 |
| --- | --- | --- |

## 8. 显式假设

| # | 假设 | 若不成立的影响 | 待验证方式 |
| --- | --- | --- | --- |
| A1 | | | |

## 9. 待澄清

| # | 问题 | 为什么必须问人 | 状态 |
| --- | --- | --- | --- |
"""

DRAFT_TECH = [
    ("1. 背景与目标", "问题、目标、成功判据（与概念简报一致，不一致要写明为什么改了）"),
    ("2. 范围与非目标", "这次改什么、不改什么、边界在哪里"),
    ("3. 现状与约束", "当前实现、数据量级、调用方、不能动的东西"),
    ("4. 方案与备选", "主方案 + 至少一个备选；对比维度写明"),
    ("5. 契约：接口与数据", "请求/响应字段、错误码、存储结构、幂等语义"),
    ("6. 失败与一致性", "超时、重试、重复投递、部分成功、补偿与对账"),
    ("7. 可观测性", "日志、指标、告警、追踪字段、排查路径"),
    ("8. 安全与权限", "鉴权、越权、密钥、数据最小化"),
    ("9. 迁移、回滚与兼容", "灰度步骤、旧数据、回滚触发条件"),
    ("10. 测试计划", "单测/集成/回归分别覆盖哪个风险点"),
    ("11. 风险与未决项", "已知风险、依赖、仍需人决定的事"),
    ("12. 决策记录", "决策 / 理由 / 代价 / 依据"),
]

DRAFT_PRODUCT = [
    ("1. 背景与目标", "问题、目标、成功判据（与概念简报一致，不一致要写明为什么改了）"),
    ("2. 范围与非目标", "这次覆盖什么、不覆盖什么"),
    ("3. 现状与约束", "现有流程、人群、系统、资源约束"),
    ("4. 方案与备选", "主方案 + 至少一个备选；对比维度写明"),
    ("5. 规则与流程", "主流程、分支、状态流转、口径定义"),
    ("6. 角色与权限", "谁发起、谁审批、谁可见、谁承担后果"),
    ("7. 边界与例外", "异常人群、极端场景、争议处理、兜底"),
    ("8. 指标与验收", "衡量口径、取数方式、验收条件"),
    ("9. 依赖与风险", "依赖方、时间窗、外部条件、风险"),
    ("10. 落地节奏", "分批、灰度、宣导、复盘节点"),
    ("11. 决策记录", "决策 / 理由 / 代价 / 依据"),
]


def draft_template(title: str, design_id: str, object_type: str, stamp: str) -> str:
    sections = DRAFT_TECH if object_type == "technical" else DRAFT_PRODUCT
    lines = [
        f"# {title} · 设计草案",
        "",
        "| 项 | 内容 |",
        "| --- | --- |",
        f"| 设计标识 | {design_id} |",
        f"| 对象类型 | {object_type} |",
        f"| 版本 | v1 |",
        f"| 建档时间 | {stamp} |",
        "| 状态 | draft |",
        "",
        "> 逐节写，每写完一节停下等人反馈；不要一次性甩出全文。",
        "> 每个判断要么给依据，要么标成显式假设（A1、A2……）。",
        "",
    ]
    for idx, (heading, hint) in enumerate(sections):
        lines.append(f"## {heading}")
        lines.append("")
        if heading.startswith("12.") or heading.startswith("11."):
            if "决策记录" in heading:
                lines += [
                    "| 决策 | 理由 | 代价 | 依据 / 假设 |",
                    "| --- | --- | --- | --- |",
                    "| | | | |",
                ]
            else:
                lines += ["- （风险 / 未决项 / 需要人拍板的事）"]
        else:
            lines.append(f"<!-- {hint} -->")
            lines.append("")
        if idx != len(sections) - 1:
            lines.append("")
    return "\n".join(lines) + "\n"


DECISION_TEMPLATE = """# {title} · 裁决台账

| 项 | 内容 |
| --- | --- |
| 设计标识 | {design_id} |
| 状态 | reviewing |

## 裁决口径

- PROPOSE FIX：接受，按建议改。
- CONTEST：驳回，必须引用评审者能读到的证据（文档章节、代码行、清单内文件）。
- ESCALATE：转给人决定，写清需要哪个层级的判断。
- DECLINE：本轮不改，写明接受的风险与复查时机。

## 裁决台账

| Finding | 轮次 | 裁决 | 理由 / 证据 | 处置 | 状态 |
| --- | --- | --- | --- | --- | --- |

## 收敛记录

| 轮次 | Blocker | Major | Minor | Nit | 本轮 clean | 备注 |
| --- | --- | --- | --- | --- | --- | --- |

## 未决问题（等用户拍板）

| # | 问题 | 需要谁决定 | 状态 |
| --- | --- | --- | --- |
"""

HANDOFF_TEMPLATE = """# {title} · 交接边界

| 项 | 内容 |
| --- | --- |
| 设计标识 | {design_id} |
| 依据版本 | 设计草案 v（填最终版本） |
| 评审轮次 | 共 __ 轮，最后连续 clean __ 轮 |
| 人已批准 | 否 |

## Target Scope & File Boundary（实现 agent 只准在这里写）

| # | 允许修改的路径 | 允许的操作 | 说明 |
| --- | --- | --- | --- |
| 1 | | 新增 / 修改 | |

## 禁止触碰

| # | 路径或范围 | 原因 |
| --- | --- | --- |

## 完成判据

- （可执行的验收条件，含要跑的命令或要看的指标）

## 越界处理

- 一旦需要改清单外的文件：停下来，把需要和理由报回大象，由人扩清单，不自行扩大范围。
"""

INDEX_TEMPLATE = """# {title}

| 项 | 内容 |
| --- | --- |
| 设计标识 | {design_id} |
| 对象类型 | {object_type} |
| 当前状态 | brainstorm |
| 唯一实现依据 | design_draft.md（评审收敛后） |

## 产物

| 文件 | 作用 |
| --- | --- |
| concepts_brief.md | 概念简报：问题、目标、约束、否决方案、假设 |
| design_draft.md | 设计草案：唯一实现依据 |
| review_packet.md | 金鱼评审包：只读清单与评审规则（每轮重新生成） |
| manifest.json | 评审清单与隔离方式记录 |
| reviews/round-01/ | 第 1 轮五步评审报告 |
| decision_record.md | 裁决台账与收敛记录 |
| handoff_boundary.md | 交接边界：实现阶段允许写入的范围 |
"""


def cmd_new(args) -> int:
    root = Path(args.root).resolve()
    slug = sanitize_slug(args.slug)
    stamp = _dt.date.today().isoformat()
    design_id = f"{stamp}-{slug}"
    target = root / design_id
    if target.exists():
        return fail(f"目录已存在，不覆盖：{target}")
    title = args.title or slug

    write_text(target / "index.md", INDEX_TEMPLATE.format(
        title=title, design_id=design_id, object_type=args.object))
    write_text(target / "concepts_brief.md", CONCEPTS_TEMPLATE.format(
        title=title, design_id=design_id, object_type=args.object, stamp=stamp))
    write_text(target / "design_draft.md", draft_template(
        title, design_id, args.object, stamp))
    write_text(target / "decision_record.md", DECISION_TEMPLATE.format(
        title=title, design_id=design_id))
    write_text(target / "handoff_boundary.md", HANDOFF_TEMPLATE.format(
        title=title, design_id=design_id))
    (target / "reviews" / "round-01").mkdir(parents=True, exist_ok=True)

    print(f"[OK] 已建档：{target}")
    for name in ("index.md", "concepts_brief.md", "design_draft.md",
                 "decision_record.md", "handoff_boundary.md"):
        print(f"     - {name}")
    print("     - reviews/round-01/（空目录，五份报告写这里）")
    print("")
    print("下一步：先填 concepts_brief.md，七镜头逐个走完再进 draft。")
    print(f"生成评审包：python egm_kit.py packet \"{target / 'design_draft.md'}\" --base .")
    return 0


# ---------------------------------------------------------------- packet

PACKET_RULES = """# 金鱼评审包（EGM）

## 1. 你在做什么

你是本次评审的金鱼：一个没有参与过任何前置讨论的评审者。你只能依据本包和下面
“允许阅读清单”里的文件形成判断。你没有看过设计者的对话，这是刻意的——请把文档
读不懂的地方当成文档的问题报出来，而不是替它补全。

## 2. 事实

| 项 | 值 |
| --- | --- |
| 设计标识 | {design_id} |
| 设计文档 | {design_path} |
| 对象类型 | {object_type} |
| 是否核对代码 | {code_check_text} |
| 允许阅读文件数 | {read_count} |
| 生成时间 | {stamp} |

## 3. 允许阅读清单（白名单，只有这些）

{read_list}

清单外文件、父对话、项目里其他文档一律不得读取。需要清单外的文件才能判断时，
在报告里写“需要额外文件：<路径>，理由：……”，并标记本次评审为 incomplete。

## 4. 找不到文件时

必需文件缺失或读不出来，报告里写 incomplete 并列出缺什么，不要凭印象给结论。

## 5. 输出契约

- 只读：不修改任何文件。
- 报告写到 {report_path}。
- 报告开头必须有元信息表：评审者 / 步骤 / 范围 / 对象类型 / 只读 / 隔离模式 / 状态。
- 问题写在 `## Findings` 下，逐行一行一条，六列：Finding / 严重度 / 位置 / 问题 / 依据 / 建议。
- Finding 编号格式 `F{{step}}-NN`（NN 从 01 递增），本轮内不得重号。
- 严重度只用 Blocker / Major / Minor / Nit。

## 6. 硬约束

1. 不确定就标注“不确定 + 需要什么才能确定”，不要编。
2. 每条问题必须能被第三人按“位置 + 依据”复现，写不出位置或依据的不要写。
3. 不要提“建议补充文档/建议加强测试”这类无法验收的意见。
4. 不要复述文档内容充当评审结论。
5. 不评价文档作者，只评价设计。

## 7. 清单外引用（需人批准后才可读）

{out_of_scope}

## 8. 缺失引用（文档提到但当前不存在）

{missing}
"""


def collect_refs(text: str) -> list[str]:
    refs: list[str] = []
    for rx in (LINK_INLINE, LINK_HTML, LINK_ANGLE):
        refs += [m.group(1).strip() for m in rx.finditer(text)]
    for m in BACKTICK.finditer(text):
        token = m.group(1).strip()
        if not token or any(ch.isspace() for ch in token):
            continue
        if token.startswith(SKIP_SCHEMES) or token.startswith("#"):
            continue
        looks_like_path = (
            token.endswith(CODE_EXT)
            or token.startswith(("./", "../", "/", "~/"))
        )
        if looks_like_path:
            refs.append(token)
    return refs


def cmd_packet(args) -> int:
    design = Path(args.design).resolve()
    if not design.is_file():
        return fail(f"设计文档不存在：{design}")
    base = Path(args.base).resolve()
    text = read_text(design)

    found, urls, outside, missing = [], [], [], []
    for ref in collect_refs(text):
        clean = ref.split("#")[0].strip().strip("<>")
        if not clean:
            continue
        if clean.lower().startswith(SKIP_SCHEMES):
            if clean not in urls:
                urls.append(clean)
            continue
        path = Path(clean)
        if not path.is_absolute():
            path = design.parent / clean
        try:
            resolved = path.resolve()
        except OSError:
            resolved = path
        if not resolved.is_file():
            if clean not in missing:
                missing.append(clean)
            continue
        if not resolved.is_relative_to(base):
            try:
                rel = Path(os.path.relpath(resolved, base)).as_posix()
            except ValueError:
                rel = resolved.as_posix()
            if rel not in outside:
                outside.append(rel)
            continue
        rel = posix(resolved, base)
        if rel not in found:
            found.append(rel)

    design_rel = posix(design, base) if design.is_relative_to(base) else design.as_posix()
    read_list = [design_rel] + [f for f in found if f != design_rel]
    design_id = design.parent.name
    code_check = (args.code_check == "on") if args.object == "technical" else False
    stamp = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")

    def bullet(items: list[str], empty: str) -> str:
        return "\n".join(f"- `{i}`" for i in items) if items else empty

    packet = PACKET_RULES.format(
        design_id=design_id,
        design_path=design_rel,
        object_type=args.object,
        code_check_text="是（可读清单内源码核对签名与路径）" if code_check else "否（只评文档自身完整性）",
        read_count=len(read_list),
        stamp=stamp,
        read_list=bullet(read_list, "- （只有设计文档本身）"),
        report_path=f"reviews/{args.round}/",
        out_of_scope=bullet(outside + urls, "- 无"),
        missing=bullet(missing, "- 无"),
    )

    manifest_path = design.parent / "manifest.json"
    isolation = {"mode": "", "host": "", "zero_context": None, "approved_by_human": False, "notes": ""}
    human_approved: list[str] = []
    if manifest_path.is_file():
        try:
            old = json.loads(read_text(manifest_path))
            if isinstance(old.get("isolation"), dict):
                isolation = {**isolation, **old["isolation"]}
            if isinstance(old.get("human_approved"), list):
                human_approved = old["human_approved"]
        except (json.JSONDecodeError, SystemExit):
            print("[警告] 旧 manifest.json 无法解析，将重新生成（原有隔离记录丢失）")

    manifest = {
        "design_id": design_id,
        "design": design_rel,
        "object_type": args.object,
        "code_check": code_check,
        "generated_at": stamp,
        "base": base.as_posix(),
        "packet": posix(design.parent / "review_packet.md", base),
        "read_list": read_list,
        "out_of_scope": outside,
        "urls": urls,
        "missing": missing,
        "human_approved": human_approved,
        "isolation": isolation,
    }
    write_text(design.parent / "review_packet.md", packet)
    write_text(manifest_path, json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")

    print(f"[OK] 评审包已生成：{design.parent / 'review_packet.md'}")
    print(f"     可读文件 {len(read_list)} 个；清单外 {len(outside)} 个；缺失引用 {len(missing)} 个；URL {len(urls)} 个")
    if outside or urls:
        print("[警告] 存在清单外引用，需人逐条批准后才可加入白名单：")
        for item in outside + urls:
            print(f"       - {item}")
    if missing:
        print("[警告] 文档引用了不存在的文件，Step 9 会把它们当作缺陷：")
        for item in missing:
            print(f"       - {item}")
    print("")
    print("下一步：派 5 个金鱼按 step5→step9 各写一份报告；派之前把隔离方式填进 manifest.json。")
    return 0


# ---------------------------------------------------------------- check

def parse_meta(text: str) -> dict[str, str]:
    """元信息既支持表格行 `| 状态 | complete |`，也支持 `状态：complete`。"""
    meta: dict[str, str] = {}
    line_pattern = re.compile(r"^[-*]?\s*(评审者|步骤|范围|对象类型|只读|隔离模式|状态)\s*[：:]\s*(.+)$")
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("|"):
            cells = split_row(stripped)
            if len(cells) < 2 or is_separator(cells):
                continue
            if cells[0] in META_KEYS and cells[0] not in meta:
                meta[cells[0]] = cells[1]
            continue
        match = line_pattern.match(stripped)
        if match and match.group(1) not in meta:
            meta[match.group(1)] = match.group(2).strip()
    return meta


def parse_findings(text: str) -> list[list[str]]:
    rows: list[list[str]] = []
    in_section = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("##"):
            head = stripped.lstrip("#").strip().lower()
            in_section = head.startswith("findings") or "问题清单" in head
            continue
        if not in_section or not stripped.startswith("|"):
            continue
        cells = split_row(stripped)
        if not cells or is_separator(cells):
            continue
        if FINDING_ID.match(cells[0]):
            rows.append(cells)
    return rows


def check_round(round_dir: Path, ledger: dict[str, dict], require_ledger: bool,
                errors: list[str], warnings: list[str]) -> dict:
    summary = {"round": round_dir.name, "Blocker": 0, "Major": 0, "Minor": 0, "Nit": 0,
               "findings": 0, "clean": None}
    seen: dict[str, str] = {}

    for step, filename, personas in STEP_REPORTS:
        report = round_dir / filename
        if not report.is_file():
            errors.append(f"{round_dir.name} 缺报告：{filename}")
            continue
        text = read_text(report)
        meta = parse_meta(text)
        status = meta.get("状态", "")
        if status.lower() != "complete":
            errors.append(f"{filename} 状态不是 complete（当前：{status or '未填'}）")
        if not meta.get("隔离模式"):
            warnings.append(f"{filename} 未记录隔离模式，无法确认是零上下文评审")
        if "TODO" in text or "TBD" in text or "待填" in text:
            warnings.append(f"{filename} 仍留占位标记（TODO/TBD/待填）")

        rows = parse_findings(text)
        if not rows and "未发现问题" not in text:
            warnings.append(f"{filename} 既没有问题也没有“未发现问题”结论")
        for cells in rows:
            fid = cells[0]
            idx = int(FINDING_ID.match(fid).group(1))
            if idx != step:
                warnings.append(f"{filename} 中 {fid} 的编号与步骤 {step} 不一致")
            if len(cells) < 6:
                errors.append(f"{filename} 中 {fid} 列数不足 6（当前 {len(cells)}）")
                continue
            severity = cells[1]
            if severity not in SEVERITIES:
                errors.append(f"{filename} 中 {fid} 严重度非法：{severity}")
                continue
            if not cells[2] or not cells[4]:
                errors.append(f"{filename} 中 {fid} 缺“位置”或“依据”，无法复核")
            if fid in seen:
                errors.append(f"{fid} 重复：{seen[fid]} 与 {filename}")
            seen[fid] = filename
            summary[severity] += 1
            summary["findings"] += 1

            if require_ledger:
                if fid not in ledger:
                    errors.append(f"{fid} 未进裁决台账")
                elif ledger[fid]["状态"] not in FINDING_STATUSES:
                    errors.append(f"{fid} 台账状态非法：{ledger[fid]['状态']}")
                elif severity in ("Blocker", "Major") and ledger[fid]["状态"] != "settled":
                    warnings.append(f"{fid}（{severity}）尚未 settled，本轮不能算 clean")

    summary["clean"] = summary["Blocker"] == 0 and summary["Major"] == 0
    return summary


def parse_ledger(path: Path, errors: list[str]) -> dict[str, dict]:
    ledger: dict[str, dict] = {}
    if not path.is_file():
        return ledger
    in_section = False
    for line in read_text(path).splitlines():
        stripped = line.strip()
        if stripped.startswith("##"):
            in_section = "裁决台账" in stripped
            continue
        if not in_section or not stripped.startswith("|"):
            continue
        cells = split_row(stripped)
        if not cells or is_separator(cells) or not FINDING_ID.match(cells[0]):
            continue
        if len(cells) < 6:
            errors.append(f"台账行 {cells[0]} 列数不足 6")
            continue
        fid, rnd, adjudication, evidence, action, status = cells[:6]
        if adjudication not in ADJUDICATIONS:
            errors.append(f"台账 {fid} 裁决非法：{adjudication}")
        if status not in FINDING_STATUSES:
            errors.append(f"台账 {fid} 状态非法：{status}")
        if adjudication == "CONTEST" and not evidence:
            errors.append(f"台账 {fid} CONTEST 未给证据")
        if fid in ledger:
            errors.append(f"台账 {fid} 重复登记")
        ledger[fid] = {"轮次": rnd, "裁决": adjudication, "状态": status}
    return ledger


def cmd_check(args) -> int:
    target = Path(args.target).resolve()
    if not target.is_dir():
        return fail(f"目录不存在：{target}")

    design_mode = (target / "reviews").is_dir() and not target.name.startswith("round-")
    if design_mode:
        design_dir = target
        rounds = sorted(p for p in (target / "reviews").iterdir()
                        if p.is_dir() and p.name.startswith("round-"))
    else:
        design_dir = target.parent.parent
        rounds = [target]
    ledger_path = Path(args.ledger) if args.ledger else design_dir / "decision_record.md"

    if not rounds:
        return fail(f"{target} 下没有 round-* 评审轮次")

    errors: list[str] = []
    warnings: list[str] = []
    ledger = parse_ledger(ledger_path, errors) if ledger_path.is_file() else {}
    if not ledger_path.is_file():
        (errors if design_mode else warnings).append(f"未找到裁决台账：{ledger_path}")

    summaries = [check_round(r, ledger, bool(ledger), errors, warnings) for r in rounds]

    manifest = design_dir / "manifest.json"
    if manifest.is_file():
        try:
            data = json.loads(read_text(manifest))
            iso = data.get("isolation") or {}
            mode = iso.get("mode") or ""
            if not mode:
                (errors if design_mode else warnings).append("manifest.json 未填写 isolation.mode")
            elif "same" in mode or "degrad" in mode:
                if not iso.get("approved_by_human"):
                    errors.append("隔离方式为降级同上下文评审，但没有人批准记录，按 EGM 规则这不算金鱼评审")
                else:
                    warnings.append("隔离方式为降级同上下文评审：报告结论只能当自查，不能当第三方评审")
            elif "leak" in mode:
                warnings.append("隔离方式记录了原始请求透传：评审者可能被用户当时的表述锚定，报告需据此降权")
            if data.get("out_of_scope") and not data.get("human_approved"):
                warnings.append("存在清单外引用但无 human_approved 记录，金鱼不得读取这些文件")
        except json.JSONDecodeError:
            errors.append("manifest.json 不是合法 JSON")
    else:
        (errors if design_mode else warnings).append("未找到 manifest.json：无法核对白名单与隔离方式")

    for s in summaries:
        print(f"[轮次] {s['round']}：共 {s['findings']} 条；"
              f"Blocker {s['Blocker']} / Major {s['Major']} / Minor {s['Minor']} / Nit {s['Nit']}；"
              f"clean={'是' if s['clean'] else '否'}")

    if design_mode:
        tail = []
        for s in reversed(summaries):
            if not s["clean"]:
                break
            tail.append(s["round"])
        print(f"[收敛] 末尾连续 clean 轮次：{len(tail)}（要求 >= 2）")
        if len(tail) < 2:
            errors.append("收敛条件未达成：需要连续两轮无 Blocker 且无 Major")
        if len(summaries) > 5:
            errors.append("轮次超过 5 轮上限，剩余分歧必须交人决定")

    for w in warnings:
        print(f"[警告] {w}")
    for e in errors:
        print(f"[错误] {e}")
    if errors:
        print("")
        print(f"结论：未通过。{CLOSING_NOTE}")
        return 1
    print("")
    print("结论：通过本轮结构校验。")
    return 0


# ---------------------------------------------------------------- CLI

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="egm_kit.py", description="EGM 大象-金鱼设计评审工作流的脚手架与守门工具")
    sub = parser.add_subparsers(dest="command", required=True)

    p_new = sub.add_parser("new", help="生成一轮设计目录")
    p_new.add_argument("slug", help="设计标识（会转成 kebab-case）")
    p_new.add_argument("--root", default="docs/designs", help="建档根目录，默认 docs/designs")
    p_new.add_argument("--title", default="", help="中文标题，默认用 slug")
    p_new.add_argument("--object", default="technical", choices=("technical", "product"),
                       help="对象类型：technical 软件技术设计 / product 产品业务方案")
    p_new.set_defaults(func=cmd_new)

    p_packet = sub.add_parser("packet", help="生成金鱼评审包与 manifest")
    p_packet.add_argument("design", help="设计草案路径")
    p_packet.add_argument("--base", default=".", help="项目根，白名单不得越出此目录，默认当前目录")
    p_packet.add_argument("--object", default="technical", choices=("technical", "product"))
    p_packet.add_argument("--code-check", default="on", choices=("on", "off"),
                          help="是否允许核对源码，technical 默认 on，product 恒为 off")
    p_packet.add_argument("--round", default="round-01", help="本轮目录名，默认 round-01")
    p_packet.set_defaults(func=cmd_packet)

    p_check = sub.add_parser("check", help="校验某轮报告或整个设计目录是否收敛")
    p_check.add_argument("target", help="轮次目录（reviews/round-01）或设计目录")
    p_check.add_argument("--ledger", default="", help="裁决台账路径，默认设计目录下 decision_record.md")
    p_check.set_defaults(func=cmd_check)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
