"""check_all.py：批量体检指定目录下的所有技能并输出报告（沙箱内运行，仅用标准库）。

（命名避开标准库 inspect，防止同名遮蔽导致 argparse 等崩溃。）

扫描 <root> 的每个一级子目录，凡含 SKILL.md 的视为一个技能，逐个校验并汇总。

用法:
    python3 check_all.py [root] [--json] [--output index.json]

选项:
    root      待扫描目录（默认 /workspace/dist）
    --json    以 JSON 输出报告
    --output  同时把索引写入指定文件（技能名/版本/状态/问题清单）
"""

import argparse
import json
import os
import sys

# 复用同目录 validate.py 的校验逻辑（脚本目录自动在 sys.path）
from validate import validate_skill


def inspect_root(root: str):
    """扫描并校验 root 下所有技能，返回结果列表。"""
    results = []
    if not os.path.isdir(root):
        return results
    for entry in sorted(os.listdir(root)):
        sub = os.path.join(root, entry)
        if not os.path.isdir(sub):
            continue
        if not os.path.isfile(os.path.join(sub, "SKILL.md")):
            continue  # 无 SKILL.md 的目录不视为技能，跳过
        errors, warnings, meta = validate_skill(sub)
        status = "error" if errors else ("warn" if warnings else "ok")
        results.append({
            "name": meta.get("name", entry),
            "dir": entry,
            "version": meta.get("version", ""),
            "status": status,
            "errors": errors,
            "warnings": warnings,
        })
    return results


def main():
    parser = argparse.ArgumentParser(description="批量体检技能目录")
    parser.add_argument("root", nargs="?", default="/workspace/dist", help="待扫描目录")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出")
    parser.add_argument("--output", default=None, help="把索引写入指定文件")
    args = parser.parse_args()

    results = inspect_root(args.root)
    summary = {
        "root": args.root,
        "total": len(results),
        "ok": sum(1 for r in results if r["status"] == "ok"),
        "warn": sum(1 for r in results if r["status"] == "warn"),
        "error": sum(1 for r in results if r["status"] == "error"),
        "skills": results,
    }

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"体检目录：{args.root}（共 {summary['total']} 个技能）")
        for r in results:
            print(f"  [{r['status']:5}] {r['dir']} (v{r['version'] or '-'})")
            for e in r["errors"]:
                print(f"         报错: {e}")
            for w in r["warnings"]:
                print(f"         告警: {w}")
        print(f"汇总：ok={summary['ok']} warn={summary['warn']} error={summary['error']}")

    # 可选：输出索引文件
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        print(f"索引已写入：{args.output}")

    sys.exit(1 if summary["error"] else 0)


if __name__ == "__main__":
    main()
