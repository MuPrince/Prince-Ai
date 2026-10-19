"""scaffold.py：生成标准技能骨架（沙箱内运行，仅用标准库）。

用法:
    python3 scaffold.py --name my-skill --description "做什么" \
        [--version 0.1.0] [--author xxx] [--tags "a,b"] \
        [--output-dir /workspace/dist]

产物:
    <output-dir>/<name>/SKILL.md      （由模板渲染 frontmatter）
    <output-dir>/<name>/scripts/      （空目录，附 example.py 占位）
"""

import argparse
import os
import re
import sys

# 模板内容兜底（优先读取 ../templates/SKILL_TEMPLATE.md）
FALLBACK_TEMPLATE = """---
name: {{name}}
description: {{description}}
version: {{version}}
author: {{author}}
tags:
{{tags_yaml}}
---

# {{name}}

<!-- 一句话说明这个技能做什么、什么时候该用它 -->

## 何时使用

<!-- 明确触发场景：用户在什么意图下应该启用本技能 -->

## 使用方法

<!-- 分步骤写清 Agent 的操作流程：读哪些文件、运行哪些命令、输出什么 -->

## 注意事项

<!-- 硬性约束、限制条件、常见错误与处理方式 -->
"""

# 占位示例脚本
EXAMPLE_SCRIPT = '''"""示例脚本：按需替换为实际逻辑。"""


def main():
    print("hello from {{name}}")


if __name__ == "__main__":
    main()
'''

NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")  # kebab-case 技能名


def load_template() -> str:
    """优先读取技能自带模板文件，失败则用内置兜底模板。"""
    tpl = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "templates", "SKILL_TEMPLATE.md")
    try:
        with open(tpl, "r", encoding="utf-8") as f:
            return f.read()
    except OSError:
        return FALLBACK_TEMPLATE


def main():
    parser = argparse.ArgumentParser(description="生成标准技能骨架")
    parser.add_argument("--name", required=True, help="技能名（小写字母/数字/中划线）")
    parser.add_argument("--description", required=True, help="一句话描述")
    parser.add_argument("--version", default="0.1.0", help="版本号（默认 0.1.0）")
    parser.add_argument("--author", default="unknown", help="作者（默认 unknown）")
    parser.add_argument("--tags", default="", help="逗号分隔标签")
    parser.add_argument("--output-dir", default="/workspace/dist", help="输出根目录")
    args = parser.parse_args()

    # 名称合法性校验
    if not NAME_RE.match(args.name):
        print(f"错误：技能名 '{args.name}' 非法，需为小写字母/数字/中划线（kebab-case）", file=sys.stderr)
        sys.exit(1)

    skill_dir = os.path.join(args.output_dir, args.name)
    if os.path.exists(skill_dir):
        print(f"错误：目标目录已存在：{skill_dir}", file=sys.stderr)
        sys.exit(1)

    # 渲染模板变量
    tags = [t.strip() for t in args.tags.split(",") if t.strip()]
    tags_yaml = "\n".join(f"  - {t}" for t in tags) if tags else "  - general"
    content = load_template()
    for key, val in {
        "name": args.name,
        "description": args.description,
        "version": args.version,
        "author": args.author,
        "tags_yaml": tags_yaml,
    }.items():
        content = content.replace("{{" + key + "}}", val)

    # 写入骨架：SKILL.md + scripts/example.py
    os.makedirs(os.path.join(skill_dir, "scripts"))
    with open(os.path.join(skill_dir, "SKILL.md"), "w", encoding="utf-8") as f:
        f.write(content)
    with open(os.path.join(skill_dir, "scripts", "example.py"), "w", encoding="utf-8") as f:
        f.write(EXAMPLE_SCRIPT.replace("{{name}}", args.name))

    print(f"骨架已生成：{skill_dir}")
    print(f"下一步：补充 SKILL.md 正文与 scripts/ 脚本后，运行 validate.py 校验")


if __name__ == "__main__":
    main()
