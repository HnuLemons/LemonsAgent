import re
from pathlib import Path

import yaml

from .config import SKILLS_DIR


class SkillLoader:
    def __init__(self, skills_dir: Path):
        self.skills_dir = skills_dir
        self.skills = {}
        self._load_all()

    def _load_all(self):
        if not self.skills_dir.exists():
            return
        for f in sorted(self.skills_dir.rglob("SKILL.md")):  # 遍历所有 Skills，写入 skills 字典
            # 单个技能文件损坏（乱码、权限、读取失败）只跳过该文件并告警，
            # 不影响其他技能加载，更不能让启动崩溃
            try:
                text = f.read_text(encoding="utf-8")
                meta, body = self._parse_frontmatter(text)
            except (OSError, UnicodeDecodeError) as exc:
                print(f"[技能文件读取失败，已跳过]: {f}（{exc}）")
                continue
            name = meta.get("name", f.parent.name)
            self.skills[name] = {"meta": meta, "body": body, "path": str(f)}

    # 解析 Markdown 文件顶部的 Front Matter
    # 把 SKILL.md 拆成两部分：
    # 1.meta：技能配置（YAML）
    # 2.body：技能正文（Markdown 内容）
    def _parse_frontmatter(self, text: str) -> tuple:
        match = re.match(r"^---\n(.*?)\n---\n(.*)", text, re.DOTALL)
        if not match:
            return {}, text
        try:
            meta = yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError:
            meta = {}
        return meta, match.group(2).strip()

    # 方法调用返回结果示例
    # - python: Python代码分析 [coding,debug]
    # - search: 网络搜索 [web]
    def get_descriptions(self) -> str:
        if not self.skills:
            return "(no skills available)"
        lines = []
        for name, skill in self.skills.items():
            desc = skill["meta"].get("description", "No description")
            tags = skill["meta"].get("tags", "")
            line = f"  - {name}: {desc}"
            if tags:
                line += f" [{tags}]"
            lines.append(line)
        return "\n".join(lines)

    # 根据技能名称获取对应 skill 的正文内容，并按照 XML 标签格式封装返回，供 Agent / LLM 使用。
    def get_content(self, name: str) -> str:
        skill = self.skills.get(name)
        if not skill:
            return f"Error: Unknown skill '{name}'. Available: {', '.join(self.skills.keys())}"
        return f'<skill name="{name}">\n{skill["body"]}\n</skill>'


# 全局技能加载器单例（与原始代码中的 SKILL_LOADER 对应）
SKILL_LOADER = SkillLoader(SKILLS_DIR)
