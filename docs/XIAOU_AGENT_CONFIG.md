# 小U 升级接线方案（Phase A）

> 目标：把小U 从「单轮对话壳」升级为「带工具权限 + 前提抽取 + 自检循环」的
> 多轮智能体，对齐 WorkBuddy 式能力。本方案直接复用刚做好的
> **pasm-domain-advisor** 泛例引擎作为小U 的"参谋内核"。
> 抖音宠物店清单里每一条错，都对应本方案要补的一项能力。

---

## 一、诊断：小U 当年为什么差

| 小U 旧形态 | 缺的能力 | 后果（宠物店清单里的硬伤） |
|---|---|---|
| 单轮：`提示词 → 一次 LLM → 回答` | **前提抽取** | 用户说"已有执照"，仍让"小白先个人店试水" |
| 同上 | **实时数据** | 用训练截止前的旧规则："交保证金几百到几千" |
| 同上 | **多维剖析** | 没把"冻干=宠物饲料=需供应商生产许可证"串起来 |
| 同上 | **自检闸门** | 给出自相矛盾/无依据断言，没人拦 |

**归因**：不是 DeepSeek 弱，也不是 PASM 内核差，而是小U 被部署成"单轮壳"，
PASM 的认知层（前提/规划/世界模型/自检）与工具路由（MCP）根本没被触发。

---

## 二、接线总览：小U = 泛例引擎 + 工具 + LLM + 记忆

```
用户消息
  │
  ▼
小U 编排层（多轮循环，复用 PASM 规划器/世界模型做前提抽取与重规划）
  │  ① 抽取前提  → domain_advisor.gate.extract_premises()
  │  ② 核验现行规则 → 注入 web_search 工具（实时）or profile.knowledge（兜底）
  │  ③ 多维剖析  → engine.analyze()（LLM 或模板）
  │  ④ 自检闸门  → engine.selfcheck()（反自相矛盾 + 反无依据）
  │  ⑤ 结构化交付 → Markdown 清单 + 可选定价 Excel（code_run）
  ▼
专业、不过时、不自相矛盾的回答
```

小U 不需要重写一个引擎——**直接把 pasm-domain-advisor 当作它的"参谋内核"**，
小U 负责上层编排、人格、记忆衔接与工具注入。

---

## 三、具体改动（落到配置与代码）

### 1) 启用工具权限（小U 缺的那层）

在 `agent_spec.toml`（或等效配置）里给小U 开三件套，并挂 domain_advisor 技能：

```toml
[agent]
id = "xiaou"

[agent.persona]
name = "小U"
role = "泛例领域顾问 + 全能助手"
temper = 0.6
energy = 0.5
play = 0.3

# 把领域顾问作为小U 的内核技能挂载
[agent.skills.domain_advisor]
enabled = true
default_profile = "douyin_pet_store"     # 默认领域；用户谈别的领域时切换 profile

# 三件套工具（对照 WorkBuddy：联网 / 算账 / 读写）
[[agent.capabilities]]
name = "web_search"
description = "联网检索领域最新政策与规则"
[[agent.capabilities]]
name = "code_run"
description = "运行代码，生成定价 Excel 等计算型交付物"
[[agent.capabilities]]
name = "file_write"
description = "把清单/表格写入文件，交给工作流"

[agent.platforms]
mcp = true
web = true
web_port = 8082
```

部署层把真实工具实现注入引擎：

```python
from pasm_da import build_advisor_agent

# 真实工具实现（接你自己的搜索/沙箱/文件系统）
def my_web(q): ...          # 返回该领域最新政策摘要
def my_code(code, run_in): ...  # 沙箱执行，返回 stdout
def my_file(path, content): ...  # 写盘

a = build_advisor_agent(
    "xiaou", profile_id="douyin_pet_store",
    llm={"provider": "openai-compatible", "model": "deepseek-chat",
         "base_url": "https://api.deepseek.com/v1", "api_key": "你的KEY"},
    tools={"web_search": my_web, "code_run": my_code, "file_write": my_file},
)
```

### 2) 前提抽取接入 PASM 认知层（不再漏掉"已有执照"）

让小U 的**规划器/世界模型**在每轮把用户原话过一遍 `extract_premises()`，
把抽到的前提写进记忆（`observe(salience=5, tags=["前提"])`），后续所有回答都以
这些前提为约束基线——这正是把"单轮"变"多轮闭环"的关键一步。

```python
premises = a.engine.extract_premises(user_text, a.profile)
for k, v in premises.items():
    a.observe(title="前提:%s=%s" % (k, v), salience=5, tags=["前提"], category="前提")
```

### 3) 自检闸门作为"发言前最后一道关"

无论 LLM 还是模板产出的草稿，发布前必须过 `engine.selfcheck()`。
若 `report.flags` 非空（自相矛盾 / 无依据），小U **不得原样输出**，要先修正或标"需核验"。
这把"答非所问 / 自相矛盾"在出口处拦死——客服产品里同款闸门已实测有效。

### 4) LLM 不绑定厂商、且要能回落

`llm` 是普通字典（DeepSeek / 通义 / 自建网关皆可）。LLM 或工具不可用时，
引擎自动回落到"模板 + 固化知识"，保证**永远有专业回答，而非报错**。

---

## 四、自检清单（改完逐项验证）

- [ ] 小U 不再"个人店试水"：喂"我有个体户执照"→ 输出"直接开个体店"，且自检无 contradiction。
- [ ] 小U 给的保证金/0元入驻口径是 2025–2026 新规（联网核验 or 固化知识覆盖）。
- [ ] 每轮回答前经过 `extract_premises` + `selfcheck` 两道关（日志可查）。
- [ ] 用户谈"冻干"时，回答明确区分"供应商持证 vs 你只需索取归档"。
- [ ] 用户要算账时，`code_run` 真能生成定价 Excel（而不是只描述）。
- [ ] LLM 挂掉时仍能产出模板版清单（不报错、不空白）。

---

## 五、为什么这是"泛例"而不是"只解决开店"

`pasm-domain_advisor` 的引擎**不含任何开店业务词**；开店只是 `profiles/douyin_pet_store.py`
这一个数据实例。小U 以后要答"跨境合规 / 医美 / 财税 / 留学"，
只要再写一个 `DomainProfile` 注册进 `profiles/registry.py`，小U 立刻具备同款专业能力——
无需为每类问题重写逻辑。这正是把"小U 差"从个案修成"体系修"的核心。
