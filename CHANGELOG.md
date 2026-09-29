# 更新日志 · CHANGELOG

> 装它：`pip install pasm-domain-advisor`

## v0.1.0 —— 泛例领域顾问引擎首发（开店仅为示例）

> 这是第一个正式版本。核心是一个**不写死任何业务词**的顾问引擎：
> 把任意领域写成一份 `DomainProfile` 数据，引擎就能产出结合「现行规则 +
> 用户真实前提 + 多维剖析 + 自检闸门」的专业清单。抖音宠物店只是第一个示例实例。

### 新增

- **泛例引擎** `pasm_da.engine.DomainAdvisor`：五步（前提抽取 → 现行规则核验 →
  多维剖析 → 自检闸门 → 结构化交付），纯标准库即可运行，LLM 与工具可选注入。
- **自检闸门** `pasm_da.gate`：复用 `pasm-customer-service` 的 `touches_surface`
  反幻觉技术，并扩展「前提一致性（自相矛盾）」与「事实接地（无依据断言）」两道闸门；
  信息陈列类建议不参与前提一致性判错，避免误伤正确科普。
- **声明式规格** `DomainProfile`：前提信号 / 前提约束 / 规则检索 / 合规矩阵 /
  剖析维度 / 风险维度 / 交付物 / 已核验知识，全部数据化。
- **三个示例 profile**（证明泛例可复制，引擎零改动）：
  - `douyin_pet_store` 抖音电商·宠物店开店（个体店 vs 个人店、0元入驻、保证金 GMV 档、
    宠物饲料资质、广告法红线、运费模型、定价 Excel）。
  - `cross_border_ecom` 跨境电商·合规开店（海关注册、9610/1210/9710/9810、综合税与限额、
    三单比对、知识产权、数据合规）。
  - `food_business_license` 食品经营许可·办理合规（预包装备案 vs 许可、小餐饮备案、
    流程、场地设施、健康证、网络亮证）。
- **真实工具三层注入** `pasm_da.tools_impl`：`web_search`（联网核验，可开关）/
  `code_run`（子进程跑 Python 生成定价表）/ `file_write`（写盘），默认注入、优雅降级。
- **DeepSeek 接线**：`llm_client` 走 OpenAI 兼容协议（DeepSeek 默认），缺 key 自动回落模板。
- **MCP 适配器** `pasm_da.adapters.mcp`：stdio 上零依赖 JSON-RPC 2.0，暴露
  `da_list_profiles` / `da_advise`，可被 WorkBuddy / ClawHub / Claude Desktop 直接调用。
- **CLI**：`pasm-da run/list/demo`、`pasm-da-mcp --selftest/serve`。
- **完整文档**：`README.md`（中英）、`docs/XIAOU_AGENT_CONFIG.md`（小U 升级接线方案）、
  示例 `examples/wire_xiaou.py`（真注入三件套 + DeepSeek 的可运行落地版）。

### 设计要点

- 引擎不依赖 `pasm-framework`；核心运行时**零第三方依赖**，装完即可 `pasm-da demo` 跑通。
  接真 PASM 认知 / 生成 xlsx 走可选 extra（`pasm` / `xlsx`）。
- 所有工具方法与 LLM 调用**永不抛异常**：失败回落到模板 + 固化知识，保证永远有专业回答。

### 验证

- `tools/selfcheck.py` 全绿：三个 profile 正确流均「矛盾 0 / 无依据 0」；
  三个领域各自的错误流（有执照却让开个人店 / 有海关注册却让不报关直发 /
  仅预包装却让办食品经营许可证）均被闸门精准拦截。
- `pasm-da-mcp --selftest` 全绿（协议 + 离线降级 + 参数校验）。
- 纯引擎无 LLM 也能产出完整清单，且定价表由 `code_run` 真实生成。

### 附件说明

`.whl` / `.tar.gz` 为离线装机用发行产物，从 `git archive HEAD` 解包构建，保证「产物 == 已提交 tag」。
在线安装请走 PyPI：`pip install pasm-domain-advisor`。
