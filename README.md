# pasm-domain-advisor

> 泛例 PASM 领域顾问引擎 · **引擎不写死任何业务词**，把任意领域写成一份
> `DomainProfile` 数据，就能产出结合「现行规则 + 用户真实前提 + 多维剖析 + 自检闸门」
> 的专业清单。抖音宠物店 / 跨境电商 / 食品许可只是示例实例。

[English](#english) · 中文

## 中文

### 为什么需要它

小U 当年「差」的根因不是模型弱，而是被部署成「单轮对话壳」——缺前提抽取、缺实时数据、
缺多维剖析、缺自检闸门。`pasm-domain-advisor` 把这套能力固化成可复用的引擎，**把小U
从单轮壳升级成多轮智能体**的参谋内核。

### 安装

```bash
pip install pasm-domain-advisor            # 核心零依赖，装完即可跑
pip install "pasm-domain-advisor[pasm]"     # 接真 PASM 认知（资料库/记忆/情绪）
pip install "pasm-domain-advisor[xlsx]"     # 生成 xlsx 定价表
```

### 30 秒上手

```python
from pasm_da import DomainAdvisorAgent

agent = DomainAdvisorAgent("xiaou", profile_id="douyin_pet_store")
print(agent.render("我已有寰霖汇商贸的个体工商户营业执照，想开个宠物店卖猫砂和冻干"))
```

命令行：

```bash
pasm-da list                                              # 已注册领域
pasm-da run --profile cross_border_ecom --text "我有海关注册，想做跨境电商出口"
pasm-da demo                                              # 预置剧本
```

### 小U 真注入（三件套 + DeepSeek）

见 [`examples/wire_xiaou.py`](examples/wire_xiaou.py) —— 可运行落地版：

```bash
DEEPSEEK_API_KEY=sk-xxx PASM_DA_LIVE_WEB=1 python examples/wire_xiaou.py
```

- `web_search`：联网核验领域最新政策（`PASM_DA_LIVE_WEB=1` 才真联网，默认离线安全）。
- `code_run`：在子进程跑 Python，**真实生成定价 Excel**（不是只描述）。
- `file_write`：把清单写盘，交给工作流。
- LLM：DeepSeek（OpenAI 兼容），缺 key 自动回落模板 + 固化知识，绝不报错。

### 怎么加一个全新领域（泛例的核心价值）

只需新增一个 `DomainProfile` 实例，引擎一行不用改：

```python
from pasm_da.domain_profile import DomainProfile, PremiseSignal, PremiseConstraint

PROFILE = DomainProfile(
    id="my_domain",
    name_zh="我的领域",
    domain="my_domain",
    premise_signals=[PremiseSignal(key="has_x", label_zh="已具备 X", patterns=["X"])],
    premise_constraints=[PremiseConstraint(if_premise="has_x",
        forbid_reco_contains=["不要做 Y"], warn_zh="你已有 X，应直接做 Z")],
    rule_queries=["领域最新政策 2025"],
    compliance_matrix={"维度": ["要点"]},
    analysis_dimensions=["维度"],
    risk_dimensions=["风险"],
    knowledge=[{"title": "已核验要点"}],
)
```

然后 `from pasm_da.profiles import register; register(PROFILE)` 即可。

### MCP 服务（可被 WorkBuddy / ClawHub / Claude Desktop 调用）

```bash
pasm-da-mcp                 # 起 stdio 服务（平台大模型通过 da_advise 调你的实例）
pasm-da-mcp --selftest      # 本地自检
```

### 自检闸门（防「自相矛盾 / 无依据断言」）

- **前提一致性**：已有执照却让开个人店、有海关注册却让不报关直发、仅预包装却让办食品经营许可证
  —— 这类硬伤被显式拦截。
- **事实接地**：建议关键词必须落在「已核验规则 / 合规矩阵 / 前提」上，否则标「无依据」。

### 许可

MIT · © arronzheng

---

## English

### Why

The root cause of "小U" underperforming was not a weak model, but being deployed as a
single-turn shell — missing premise extraction, live data, multi-dimensional analysis,
and a self-check gate. `pasm-domain-advisor` turns that into a reusable engine and serves
as the "advisor core" to upgrade 小U from a single-turn shell into a multi-turn agent.

### Install

```bash
pip install pasm-domain-advisor
pip install "pasm-domain-advisor[pasm]"     # real PASM cognition
pip install "pasm-domain-advisor[xlsx]"     # xlsx pricing sheet
```

### Quick start

```python
from pasm_da import DomainAdvisorAgent
agent = DomainAdvisorAgent("xiaou", profile_id="douyin_pet_store")
print(agent.render("I hold an individual-business license and want to open a pet store"))
```

### What makes it "generic"

Add a new domain by dropping a `DomainProfile` instance — the engine code never changes.
Three sample profiles (Douyin pet store / cross-border e-commerce / food license) prove
the point. The self-check gate blocks self-contradictory and ungrounded advice.

### License

MIT · © arronzheng
