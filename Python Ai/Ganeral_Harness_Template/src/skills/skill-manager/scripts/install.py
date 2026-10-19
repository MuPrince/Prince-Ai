"""install.py：从 GitHub（zip）或本地 zip/目录安装技能到交付目录（沙箱内运行，仅用标准库）。

用法:
    python3 install.py --github <owner>/<repo>[@branch] [--subdir 子目录] [--output-dir /workspace/dist]
    python3 install.py --local <zip路径|目录> [--output-dir /workspace/dist]

安装后自动执行一次规范校验（复用 validate.py），并打印结果。
市场安装为预留能力：配置环境变量 MARKET_REGISTRY_URL 后可用（当前未实现）。
"""

import argparse
import io
import os
import shutil
import sys
import urllib.request
import zipfile

from validate import validate_skill  # 复用同目录校验逻辑

# 技能市场地址（预留配置项，暂未实现安装逻辑）
MARKET_REGISTRY_URL = os.getenv("MARKET_REGISTRY_URL", "")


def download_github_zip(repo: str, branch: str) -> bytes:
    """通过 codeload 下载 GitHub 仓库 zip（无需 git）。"""
    url = f"https://codeload.github.com/{repo}/zip/refs/heads/{branch}"
    req = urllib.request.Request(url, headers={"User-Agent": "skill-manager"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def extract_zip(data: bytes, dest: str) -> str:
    """解压 zip 到 dest，返回解压出的顶层目录路径。"""
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        zf.extractall(dest)
        names = zf.namelist()
    # GitHub zip 会带一层 <repo>-<branch>/ 顶层目录
    top = names[0].split("/")[0] if names else ""
    return os.path.join(dest, top)


def find_skill_dir(base: str, subdir: str = ""):
    """在 base 下定位技能目录：优先 subdir；否则要求 base 本身含 SKILL.md。"""
    candidate = os.path.join(base, subdir) if subdir else base
    if os.path.isfile(os.path.join(candidate, "SKILL.md")):
        return candidate
    return None


def install_to(src_dir: str, output_dir: str) -> str:
    """把技能目录拷贝到交付目录，返回最终路径。"""
    name = os.path.basename(os.path.normpath(src_dir))
    dest = os.path.join(output_dir, name)
    if os.path.exists(dest):
        shutil.rmtree(dest)  # 交付目录内覆盖（沙箱临时区，安全）
    shutil.copytree(src_dir, dest)
    return dest


def main():
    parser = argparse.ArgumentParser(description="安装技能到交付目录")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--github", help="GitHub 仓库，格式 owner/repo[@branch]（默认 main）")
    src.add_argument("--local", help="本地 zip 文件或目录路径")
    parser.add_argument("--subdir", default="", help="仓库/包内技能所在子目录")
    parser.add_argument("--output-dir", default="/workspace/dist", help="交付根目录")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    tmp = os.path.join(args.output_dir, ".install_tmp")

    try:
        if args.github:
            # 解析 owner/repo[@branch]
            repo, _, branch = args.github.partition("@")
            branch = branch or "main"
            print(f"下载 GitHub 仓库：{repo} (分支 {branch})")
            try:
                data = download_github_zip(repo, branch)
            except Exception as e:
                print(f"错误：下载失败（{e}）。可尝试其他分支（如 master）或改用本地 zip", file=sys.stderr)
                sys.exit(1)
            shutil.rmtree(tmp, ignore_errors=True)
            os.makedirs(tmp)
            base = extract_zip(data, tmp)
        else:
            if not os.path.exists(args.local):
                print(f"错误：本地路径不存在：{args.local}", file=sys.stderr)
                sys.exit(1)
            if zipfile.is_zipfile(args.local):
                shutil.rmtree(tmp, ignore_errors=True)
                os.makedirs(tmp)
                with open(args.local, "rb") as f:
                    base = extract_zip(f.read(), tmp)
            else:
                base = args.local  # 本地目录直接用

        # 定位技能目录（支持 --subdir 指定仓库内子目录）
        skill_dir = find_skill_dir(base, args.subdir)
        if skill_dir is None:
            print("错误：未找到 SKILL.md（可用 --subdir 指定技能所在子目录）", file=sys.stderr)
            sys.exit(1)

        dest = install_to(skill_dir, args.output_dir)
        print(f"已安装到交付目录：{dest}")

        # 安装后自动校验
        errors, warnings, meta = validate_skill(dest)
        for e in errors:
            print(f"  [报错] {e}")
        for w in warnings:
            print(f"  [告警] {w}")
        if errors:
            print("安装完成但校验未通过，请修复后再分配", file=sys.stderr)
            sys.exit(1)
        print(f"校验通过：{meta.get('name')} v{meta.get('version', '-')}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)  # 清理解压临时目录


if __name__ == "__main__":
    main()
