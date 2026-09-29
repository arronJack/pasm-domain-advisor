"""技能包构建（复用 pasm-agent-authoring 的 build API）。

用法：
    python tools/build_skill.py --zip --clean
产出：
    dist/zip-root/<name>/SKILL.md            # ZIP 根目录直接是 SKILL.md
    dist/slug-dir/<name>/SKILL.md
    <name>-<ver>.zip
"""
from __future__ import annotations

from pasm_skills.build import ProjectMeta, SkillSpec, run_cli

META = ProjectMeta(author="arronzheng", homepage="https://gitee.com/arronzheng/pasm-domain-advisor")

SKILLS = [
    SkillSpec(
        name="pasm-domain-advisor",
        body_file="skill/SKILL.domain-advisor.body.md",
        display_name_zh="泛例领域顾问智能体",
        display_name_en="Generic Domain Advisor Agent",
        desc_zh=("一个通用顾问引擎：把任意领域写成 DomainProfile，即可产出结合现行规则、"
                 "用户真实前提、多维剖析与自检纠错的清单。抖音宠物店开店仅为示例实例。"),
        desc_en=("A generic advisory engine: write any domain as a DomainProfile and get a "
                 "checklist grounded in current rules, the user's real premises, multi-angle "
                 "analysis and a self-check gate. The Douyin pet store is just a sample."),
        plain_desc=("Generic PASM domain advisor: declarative DomainProfile + premise extraction "
                    "+ current-rule verification + self-check gate. Reusable across domains."),
        plain_category="agents",
        plain_tags=["pasm", "advisor", "compliance", "llm"],
    ),
]

if __name__ == "__main__":
    raise SystemExit(run_cli(SKILLS, META))
