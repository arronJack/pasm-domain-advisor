# PASM 泛例领域顾问智能体（pasm-domain-advisor）

给任意一个"需要结合**现行规则 + 用户真实资源 + 多维剖析 + 自检纠错**"的顾问场景，
提供一个专业、不过时、不自相矛盾的清单引擎。**抖音宠物店开店只是其中一个示例实例**，
要复用它，写一个 `DomainProfile` 即可，引擎一行不改。

```python
from pasm_da import DomainAdvisorAgent

agent = DomainAdvisorAgent("xiaou", profile_id="douyin_pet_store")
print(agent.render("我已有寰霖汇商贸的个体工商户营业执照，想开个宠物店"))
# -> 专业执行清单：前提确认 / 已核验现行规则(0元入驻·GMV档保证金·0粉开播) /
#    决策(直接开个体店，不要降级个人店) / 合规矩阵 / 风险 / 自检结论
```

## 它解决的根本问题

很多"AI 参谋"出错，不是模型弱，而是**少了三样东西**（小U 当年的硬伤）：

1. **前提感知缺失**——用户说"已有执照"，模型却按默认套路让"小白先个人店试水"。
2. **实时数据缺失**——依赖训练截止前的旧规则（"交保证金几百到几千"），而 2025–2026 新规早已变（0元入驻 / 保证金按 GMV 档 / 0粉开播）。
3. **自检缺失**——给出自相矛盾、或无依据的断言，没人拦。

本技能用一套**泛例引擎 + 声明式领域 profile** 同时补上这三样。

## 这个技能给你什么

| 能力 | 说明 |
|---|---|
| **泛例引擎** | 引擎固定，领域由 `DomainProfile` 注入；新增领域只需 drop 一个 profile 文件 |
| **前提抽取** | 从用户原话抽取"已有什么"（执照/资质…），**决定一切**的推荐基调 |
| **现行规则核验** | 用固化知识兜底 + 可选联网实时核验最新政策（2025–2026） |
| **多维剖析** | 按 profile 的维度与合规矩阵产出清单 |
| **自检闸门** | 复用 `touches_surface` 技术：**反自相矛盾**（已有执照却推个人店会被拦下）+ **反无依据断言** |
| **结构化交付** | Markdown 清单 + 可选定价 Excel（TOP5 SKU 测算，调用 `code_run` 生成） |
| **LLM 可选** | 配了 `llm` 走大模型组织语言；没配走模板，**永远有专业回答** |
| **工具可选** | 注入 `web_search` / `code_run` / `file_io` 即获得联网/算账/读写能力（对照 WorkBuddy） |

**你主要就用这几个**：`DomainAdvisorAgent(...).render(text)` · `engine.advise(text)` · 新增领域写 profile。

## 它跑在什么之上：pasm-skills + pasm-framework

| | 是什么 | 装它 |
|---|---|---|
| **pasm-skills**（基座） | 认知层 / 记忆 / 学习 / 情绪 | `pip install pasm-skills` |
| **pasm-framework**（应用框架） | 应用级表面：资料库 / HTTP 网关 / 流式输出 | `pip install pasm-framework` |
| **pasm-domain-advisor**（本技能） | 泛例顾问引擎 + 示例 profile | `pip install pasm-domain-advisor` |

> 引擎本体**纯标准库**即可运行；框架用于资料库持久化与 MCP/Web 接入。

## 泛例怎么用：新增一个领域只要写一个 profile

```python
from pasm_da import DomainProfile, PremiseSignal, PremiseConstraint

my_profile = DomainProfile(
    id="cross_border_compliance",
    name_zh="跨境电商合规参谋",
    domain="cross_border",
    premise_signals=[PremiseSignal(key="has_import_license", label_zh="已持有进出口权",
                                  patterns=["进出口权","进口资质"], default=False)],
    premise_constraints=[PremiseConstraint(if_premise="has_import_license",
                         forbid_reco_contains=["先别做进口"], warn_zh="你已有进出口权，可直接做一般贸易进口")],
    rule_queries=["跨境电商 2025 税收政策", "跨境电商 保税备货 新规"],
    compliance_matrix={"主体资质": ["营业执照+进出口权", "海关报关单位注册"],
                       "税务": ["跨境电商综合税", "免税额度"]},
    analysis_dimensions=["主体与资质", "税务与成本", "物流与清关"],
    risk_dimensions=["走私/灰清关风险", "知识产权侵权"],
    deliverables=["checklist"],
    knowledge=[{"title": "跨境电商零售进口单次交易限值5000元、年度26000元，超限按一般贸易征税"}],
)
# 注册后即可用：DomainAdvisorAgent("a", profile=my_profile).render(text)
```

`pasm_da/profiles/douyin_pet_store.py` 是同样写法的**完整示例**，照抄即可。

## 铁律（与客服产品同源）

1. **不许编造**。`knowledge` 里带 `source` 的才是事实基准；联网结果也按来源标注。
2. **前提优先于默认**。已有某资质就必须给"直接用该资质拿满权益"的路径，禁止降级建议——并由 `premise_constraints` 闸门兜底拦截。
3. **每条建议必须落地在事实面上**（标题/标签/已核验规则/合规要点），否则 `touches_surface` 判为"无依据"。
4. **政策会变动**。每次规则更新需重新生成清单（联网核验）；固化知识也要随政策刷新。
5. **反幻觉闸门是保守取向**：宁可标"需联网核验"也不瞎给——代价是边界偏保守，可调 `rule_queries` 与知识库缓解。

## 什么时候用

- 需要一个**基于现行规则 + 用户真实前提**作答的参谋，而不是"张嘴按训练默认套路编"；
- 需要**自动拦下自相矛盾**（已有执照却让开个人店）与**无依据断言**；
- 需要把同一套顾问能力**复用到多个领域**（开店 / 合规 / 财税 / 留学 …）而不重写引擎；
- 需要产出**可机读清单 + 可选定价表**，接进工作流或后台。

## 0. 30 秒上手

```bash
pip install pasm-domain-advisor
python -m pasm_da.quickstart        # 预置剧本：抖音宠物店（含前提抽取+自检）
```

## 6. 接 LLM 与工具（可选，对照小U 升级）

```python
from pasm_da import DomainAdvisorAgent

agent = DomainAdvisorAgent(
    "xiaou", profile_id="douyin_pet_store",
    llm={"provider": "openai-compatible", "model": "deepseek-chat",
         "base_url": "https://api.deepseek.com/v1", "api_key": "你的key"},
    tools={"web_search": my_web_fn, "code_run": my_code_fn, "file_write": my_file_fn},
)
print(agent.render("我已有寰霖汇商贸的个体工商户营业执照，想开个宠物店"))
```

- **`llm` 不绑定厂商**：OpenAI 兼容即可（DeepSeek / 通义 / 你自建网关）。
- **`tools` 三件套**正是小U 缺的能力：联网核验、算账（定价 Excel）、读写文件。
- LLM 或工具不可用时会**自动回落**到模板 + 固化知识，保证永远有专业回答。

## 7. 已知短板（如实说明）

- 无 LLM / 无联网时，剖析是"基于合规矩阵的模板展开"，深度不如大模型；但**纪律（前提感知 + 事实接地 + 自检）不变**。
- 检索是词面/规则匹配，不是语义理解：口语说法尽量写进 `compliance_matrix` 的要点或 `rule_queries`。
- 闸门是保守取向（宁可标"需核验"也不瞎给）。

## 8. 相关技能

- `pasm-cs-agent` —— 智能客服（同一套"就事实作答 + 反答非所问"内核）
- `pasm-npc` / `pasm-companion` / `pasm-tutor` —— 其他 PASM 成品智能体
- `pasm-longterm-verify` —— 验证层：回答"跑久了还是好的吗"
