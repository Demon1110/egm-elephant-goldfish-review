---
name: egm-elephant-goldfish-review
description: EGM（Elephant-Goldfish Model，大象金鱼）设计评审工作流：动手实现之前先把设计审清楚。大象（持有上下文的当前会话）写概念简报与设计草案，金鱼（零上下文的只读子代理）按五步多角色评审，人按 PROPOSE FIX / CONTEST / ESCALATE / DECLINE 裁决，连续两轮 clean 收敛，产物落进 docs/designs 作为唯一实现依据，最后产出交接边界。这些场景触发：系统设计、架构设计、技术方案设计要落成可评审的文档；需求梳理、需求澄清要收敛成带约束与假设的简报；技术方案评审、产品业务方案评审；写 spec、写设计规格后再挑毛病；开发落地前的风险检查与实现就绪度检查；需要没参与讨论的第三方视角；或提到 EGM、大象金鱼、Elephant-Goldfish、egm-brainstorm、egm-draft、egm-review、egm-resolve 时。支持软件技术设计（接口、数据模型、架构、可靠性、迁移）与产品业务方案两类对象。不用于小 bug 修复、需求已完全明确的一次性改动，也不替代代码评审与测试。
---

# EGM 大象金鱼设计评审工作流

## 这套流程在做什么

| 角色 | 是谁 | 负责 |
| --- | --- | --- |
| 大象 | 当前会话，持有项目上下文与讨论历史 | 澄清需求、写概念简报与设计草案、派发评审、执行裁决 |
| 金鱼 | 宿主新建的、零上下文的只读子代理 | 只读评审包与白名单文件，按角色找问题，不做裁决 |
| 人 | 用户 | 架构取舍、批准、承担结果 |

同一个人写完设计再自己审，会拿脑子里的隐含假设去补文档的空白。换一双没参与讨论的眼睛读文档，空白才会显形。所以**金鱼必须在文件之外看不到任何背景**——这是整套流程唯一不可替代的部分。

> 本文所有 `scripts/…`、`references/…` 路径都相对**本技能目录**；`docs/designs/…` 相对**当前项目根**。

## 六条铁律（违反任一条，本次流程作废）

1. **产物落盘，不进聊天窗**。草案、报告、台账只写文件；对话里只给路径 + 一句结论（不超过 120 字）。禁止把草案全文、报告全文贴进回复。
2. **相 1–4 不碰生产代码**。只写 `docs/designs/<设计>/` 下的产物。这条没有强制机制，所以每轮结束用 `git status` 自查一次。
3. **金鱼只读白名单**。只读 `review_packet.md` 与 `manifest.json` 的 `read_list`；不读父对话、不读清单外文件、不改任何文件。
4. **一次只问一个问题，且独占该轮**。需要用户决策时，一条消息只问一件事；能给选项就给 2–4 个选项。
5. **没有可隔离的子代理就停下**。同一上下文里换个角色自评，不算金鱼评审。要降级必须用户明确同意并记录，`check` 会拦未批准的降级。
6. **裁决权在人**。AI 只给建议，不改严重度、不删 finding、不替用户接受风险。

另有一条工程约定：**评审期间草案冻结**。某轮评审开始后到裁决应用前，`design_draft.md` 不许改动；要改就作废本轮、重新 `packet`、重新派发。否则报告的章节号对不上版本，收敛记录是假的。

## 从哪一相进入

| 手上的东西 | 入口 |
| --- | --- |
| 只有一句需求 | 相 1 |
| 有 `concepts_brief.md` | 相 2 |
| 有 `design_draft.md`，只要求评审 | 相 3 |
| 有评审报告 | 相 4 |
| 台账收敛、等交接 | 相 5 |

用户只丢来一份文档说“帮我看看有没有问题”时，仍要走相 3→4→5，不要直接口头点评——口头点评没有台账，也就没有收敛。

## 相 1：Brainstorm（产出概念简报）

1. 先判断该不该走这套流程：小 bug 修复、需求已完全明确、一次性改动 → 告诉用户直接做更快，退出。
2. 七镜头先各写一句独立初判，再逐个展开（顺序展开会让后一个镜头被前一个结论锚定）：对立面/YAGNI、成本与配额、UX 与开发者体验、迁移与向后兼容、可观测性与 SRE、长期技术债、创造性催化剂。七格都要有结论，写“不适用”也要给理由。
3. 能自己查的（代码、文档、仓库结构）不要问用户；只把真正卡住、必须人拍板的问题留下，**一次问一个**。
4. 用户的每一句临时补充，都要落进“约束”或“显式假设”，并编号 A1、A2……否则它只会活在对话里，金鱼看不到。
5. 建档：`python scripts/egm_kit.py new <slug> --root docs/designs --title "<标题>" --object technical|product`

退出条件：目标、非目标、约束、成功判据、已否决方案五项齐备，且每条假设都有编号。填写标准见 `references/templates.md`。

## 相 2：Draft（产出设计草案）

1. 逐节写：写一节 → 存盘 → 一句“§X 已写入，这节我按 Y 处理，有异议请指出” → 等回复。禁止一次生成全文。
2. 每个判断要么有依据（数据、代码、规范、前序结论），要么标成 `A#` 假设。两者都没有的句子，删掉。
3. 每个取舍进决策记录表：决策 / 理由 / 代价 / 依据。代价写不出来的取舍，说明还没想清楚。
4. 禁词：适当、合理、尽快、尽量、必要时、视情况。出现即视为缺陷，自己是第一个该抓的人。
5. technical 与 product 的必填章节不同，由 `new --object` 决定骨架；合格线见 `references/rubrics.md`。

## 相 3：Review（金鱼五步）

### 3.1 建包（每轮一次）

```
python scripts/egm_kit.py packet "docs/designs/<设计>/design_draft.md" --base . --object technical --round round-01
```

脚本解析文档内部链接与反引号路径，生成白名单 `read_list`，并把越界文件、URL、缺失引用单列。**越界项必须由人逐条批准**才可加进白名单，AI 不得自行扩大范围。

### 3.2 先填隔离记录

在 `manifest.json` 的 `isolation` 里写清 `mode`、`host`、`zero_context`、`approved_by_human`。等级判定、各宿主字段、派发口令、泄漏探针见 `references/hosts.md`。拿不准就记 `fresh-subagent-query-leak`，别写成 `fresh-subagent`。

### 3.3 五步派发

| 步骤 | 角色 | 范围 | 报告 |
| --- | --- | --- | --- |
| Step 5 初始拉远 | zoom_out + inventive_catalyst（可并发） | 全文件 | `step5_zoom_out_report.md` |
| Step 6 理解性 | comprehension（直接提问，不带前序结论） | 按范围内 | `step6_comprehension_report.md` |
| Step 7 批评者 | design + structural + style | FeatureRange | `step7_critic_report.md` |
| Step 8 中段拉远 | zoom_out（专盯新长出的防御性设计，按 YAGNI 剪） | 全文件 | `step8_intermediate_zoom_out_report.md` |
| Step 9 就绪度 | readiness + codebase_details + style | DetailedRange | `step9_readiness_report.md` |

派发口令只允许包含角色、可读文件、输出位置、禁令四类内容；**不带设计背景、不带前几轮结论、不带用户原话**。派发后逐轮等报告落地，不要一边派一边改草案。

各角色只回答自己的问题，混答视为无效评审，边界见 `references/personas.md`；严重度与质量门槛见 `references/rubrics.md`。

### 3.4 派发示例（豆包环境）

```
create_agent(
  agent_type="OrganizerAgent",
  title="金鱼评审 Step5 zoom_out",
  hint="你是 EGM 评审者 egm-zoom_out，步骤 5，范围全文件。只读 docs/designs/<设计>/review_packet.md 及其白名单文件；只写 docs/designs/<设计>/reviews/round-01/step5_zoom_out_report.md；按评审包第 5、6 节执行；不读清单外文件、不改其他文件；找不到必需文件报 incomplete，不给结论。完成后只回一句：报告已写入，共 N 条 finding。"
)
```

框架会把用户本轮原始请求一并带给子代理——这是已知的 L2 泄漏。所以派发前把一切背景写进文件，对话里只说“请评审这份文档”。验证隔离的办法见 `hosts.md` 的泄漏探针，结果记进台账备注。

## 相 4：Resolve（裁决与收敛）

1. 把报告里的 findings **原样**搬进 `decision_record.md`，不改严重度、不合并条目、不删。完成后对话里只报：轮次、各级数量、需要人拍板的项——不贴报告正文。
2. 每条给一个裁决：`PROPOSE FIX` / `CONTEST` / `ESCALATE` / `DECLINE`。理解性缺口不许 CONTEST；CONTEST 必须引用金鱼读得到的证据；DECLINE 必须写复查时机。
3. 收敛判定：`clean = 本轮没有 Blocker 或 Major`。判定发生在应用本轮修复之前，所以本轮新提的 B/M 一律算未 settled，不能靠“当场改掉”洗成 clean。连续两轮 clean 才算收敛；上限 5 轮；出现 churn 交人。
4. 每轮结束跑结构校验：

```
python scripts/egm_kit.py check "docs/designs/<设计>/reviews/round-01"
python scripts/egm_kit.py check "docs/designs/<设计>"   # 收敛与否
```

reopen、churn、假收敛六种样子见 `references/convergence.md`。到第 5 轮仍有分歧，停止自动化，把两轮报告与台账交人。

## 相 5：Handoff（交接边界）

1. 填 `handoff_boundary.md`：依据版本、总轮次与末尾连续 clean 轮数、**人已批准=是（写批准人与日期）**、允许修改的路径清单、禁止触碰、完成判据、已知小问题。
2. 实现阶段只能在 Target Scope & File Boundary 内写；要改清单外文件，停下报回大象，由人扩清单。
3. 只有人批准后才开始实现。AI 不得自行宣布“设计通过、可以写代码”。

## 对象类型

| | technical | product |
| --- | --- | --- |
| 建档 | `--object technical` | `--object product` |
| 代码核对 | `code_check` 默认 on，Step 9 读白名单内源码核对路径与签名 | 恒为 off，不读代码 |
| Step 9 口径 | 实现就绪度：字段、失败路径、迁移、测试是否可编码 | 执行就绪度：角色、口径、例外、争议是否可落地 |
| rubric | 12 维（`rubrics.md` 第三节） | 10 维（`rubrics.md` 第四节） |

代码问题和设计问题不要混着评：代码问题进代码评审，设计问题进这里。

## 交接前自检（缺一项就不算完成）

- [ ] 每轮 5 份报告齐全，元信息表 `状态=complete`，隔离模式已填
- [ ] `manifest.json` 存在，`read_list` 与报告引用一致，越界与缺失引用都已处理
- [ ] 所有 Blocker / Major 在台账里是 `settled`，没有 `open` 或 `reopened`
- [ ] 连续两轮 clean，总轮次 ≤ 5，`check` 全目录通过
- [ ] 没有出现假收敛六种样子中的任何一种
- [ ] `handoff_boundary.md` 有版本号、批准人、路径清单、完成判据
- [ ] `git status` 里没有相 1–4 意外改动的生产代码

## 参考文件

| 文件 | 什么时候读 |
| --- | --- |
| `references/personas.md` | 派发前确认每个角色只答什么、禁止什么 |
| `references/rubrics.md` | 写 findings、定严重度、切 FeatureRange / DetailedRange |
| `references/convergence.md` | 做裁决、判 clean、处理 reopen 与 churn |
| `references/hosts.md` | 填隔离记录、写派发口令、验泄漏、走降级 |
| `references/templates.md` | 填概念简报、草案、台账、交接边界 |
| `scripts/egm_kit.py` | 建档、生成评审包、校验轮次与收敛 |
