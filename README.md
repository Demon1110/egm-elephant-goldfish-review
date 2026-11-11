# EGM 大象金鱼设计评审工作流

动手实现之前，先把设计审清楚。

这套流程把“写设计”和“审设计”拆给两个互不相见的角色：**大象**持有项目上下文，负责澄清需求、写概念简报与设计草案；**金鱼**是一个零上下文的只读子代理，只读评审包和白名单文件，按角色挑毛病。人保留裁决权。

---

## 解决什么问题

同一个会话里写完设计再自己审，草稿里的假设、被否掉的方案、随口补的约束都还在窗口里，模型会拿这些隐含信息去补文档的空白——看起来完整，实际全是没写下来的东西。

换一个没参与讨论的读者，文档的空白才会显形。所以这套流程唯一不可替代的部分是：**金鱼在文件之外看不到任何背景**。

---

## 适用与不适用

| 适用 | 不适用 |
| --- | --- |
| 系统设计、架构设计要落成可评审的文档 | 小 bug 修复 |
| 需求梳理、需求澄清要收敛成带约束与假设的简报 | 需求已完全明确的一次性改动 |
| 技术方案 / 产品业务方案评审 | 代码评审与测试（这里不替代） |
| 写 spec、设计规格后再挑毛病 | 只要一张草图或口头建议 |
| 开发落地前的风险检查与实现就绪度检查 | |

两类评审对象：`technical`（接口、数据模型、架构、可靠性、迁移，允许核对源码）与 `product`（产品/业务方案，不读代码，评审口径换成可执行性）。

---

## 快速开始

技能安装在：

```
C:\Users\admin\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills\egm-elephant-goldfish-review
```

在任意项目根目录下：

```bash
# 1. 建档：生成概念简报、设计草案、台账、交接边界
python <skill>/scripts/egm_kit.py new webhook-retry \
  --root docs/designs --title "Webhook 投递重试" --object technical

# 2. 先填 concepts_brief.md（七镜头），再逐节写 design_draft.md

# 3. 生成评审包：解析文档内部引用，产出只读白名单与 manifest
python <skill>/scripts/egm_kit.py packet "docs/designs/<设计>/design_draft.md" --base . --object technical

# 4. 派金鱼按 step5→step9 各写一份报告，然后做裁决

# 5. 校验：单轮结构 / 整个设计目录是否收敛
python <skill>/scripts/egm_kit.py check "docs/designs/<设计>/reviews/round-01"
python <skill>/scripts/egm_kit.py check "docs/designs/<设计>"
```

也可以直接对助手说“用 EGM 评审一下这个方案”，或提到 EGM、大象金鱼、零上下文评审、egm-review 等。

---

## 五相流程

| 相 | 干什么 | 产物 |
| --- | --- | --- |
| 1 Brainstorm | 七镜头（对立面/YAGNI、成本与配额、UX、迁移兼容、可观测性、技术债、创造性催化剂）收敛需求 | `concepts_brief.md` |
| 2 Draft | 逐节写，每节停下等反馈；判断要么有依据，要么标 `A#` 假设 | `design_draft.md` |
| 3 Review | 金鱼五步：初始拉远 → 理解性 → 批评者 → 中段拉远（YAGNI 剪枝）→ 就绪度 | `reviews/round-XX/` 五份报告 |
| 4 Resolve | 四类裁决，按轮次收敛 | `decision_record.md` |
| 5 Handoff | 给出实现阶段允许写入的边界 | `handoff_boundary.md` |

评审角色共 8 个：zoom_out、inventive_catalyst、comprehension、design、structural、style、readiness、codebase_details。每个只答自己那类问题，混答视为无效评审。

---

## 三条硬机制

### 1. 零上下文分级

| 级别 | 形态 | 能否叫金鱼评审 |
| --- | --- | --- |
| L1 | 全新子代理，只读，无父对话、无项目指令注入 | 可以 |
| L2 | 全新子代理，但宿主会带上用户本轮原始请求 | 可以，须标注 |
| L3 | 同会话换角色自评 | **不可以**，需人批准且只能当自查 |

当前豆包环境属于 L2：子代理不继承父对话，但框架会传用户原始请求。所以要求“背景全写进文件，对话里只说请评审这份文档”，并用泄漏探针验证。

### 2. 白名单与越界

评审包从文档自身的链接和路径生成 `read_list`；越界文件、URL、缺失引用单列。**越界项必须由人逐条批准**才能进白名单。金鱼不改任何文件。

### 3. 收敛判定

```
clean = 本轮没有 Blocker 或 Major（在应用本轮修复之前判定）
```

连续两轮 clean 才算收敛，上限 5 轮；出现 churn（撤销旧修复才能消新问题）交人。`check` 会拦下：缺报告、状态不是 complete、finding 未进台账、CONTEST 无证据、未批准的降级隔离。

---

## 产物目录

```
docs/designs/<日期>-<设计>/
├── index.md                 总览
├── concepts_brief.md        概念简报
├── design_draft.md          设计草案（收敛后成为唯一实现依据）
├── review_packet.md         金鱼评审包（每轮重建）
├── manifest.json            白名单、越界项、隔离方式
├── reviews/
│   └── round-01/
│       ├── step5_zoom_out_report.md
│       ├── step6_comprehension_report.md
│       ├── step7_critic_report.md
│       ├── step8_intermediate_zoom_out_report.md
│       └── step9_readiness_report.md
├── decision_record.md       裁决台账 + 收敛记录 + 未决问题
└── handoff_boundary.md      实现阶段允许写入的范围
```

---

## 技能目录

| 文件 | 作用 |
| --- | --- |
| `SKILL.md` | 六条铁律、五相流程、进入点、交接自检 |
| `references/personas.md` | 8 个角色的职责边界与禁止项 |
| `references/rubrics.md` | 四道发现门槛、严重度、technical 12 维 / product 10 维 |
| `references/convergence.md` | 四类裁决、clean 定义、reopen/churn、假收敛六种样子 |
| `references/hosts.md` | 隔离分级、各宿主字段、派发口令、泄漏探针、降级流程 |
| `references/templates.md` | 简报、草案、台账、交接边界的填写标准 |
| `scripts/egm_kit.py` | `new` / `packet` / `check`，无第三方依赖 |

---

## 验证情况

脚本用临时样例工程跑通了完整链路：建档 → 生成评审包（白名单、越界、缺失、URL 均正确归档）→ 单轮结构校验 → 两轮 clean 收敛 → 反例拦截（单轮不许判收敛、缺报告、未批准降级全部报错）。`product` 骨架与两种报告元信息写法也已验证。

未验证：真实宿主上的子代理派发与模型评审质量——这部分只有实际跑一轮评审才能确认。

---

## 已知限制

- 相 1–4 不碰生产代码是约定，没有强制机制，靠每轮 `git status` 自查。
- 无法证明宿主“没有偷偷注入项目指令文件”，只能按各宿主已记录的字段判断，并写进隔离记录。
- 评审意见不能替代测试和人工判断；草案通过不等于实现没问题。
