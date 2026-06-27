"""
env-guardian CLI 入口。

提供命令行参数解析及校验流程编排，用户可通过 ``env-guardian --help`` 查看用法。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .core import check_type_hint, parse_env_file, validate


# ANSI 颜色与符号
_RED = "\033[91m"
_GREEN = "\033[92m"
_RESET = "\033[0m"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="env-guardian",
        description="校验 .env 文件是否完整，并与 .env.example 比对。",
    )
    parser.add_argument(
        "--env",
        default=".env",
        help="待校验的环境变量文件路径（默认：当前目录下的 .env）",
    )
    parser.add_argument(
        "--example",
        default=".env.example",
        help="参照文件路径（默认：当前目录下的 .env.example）",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="开启严格模式：存在缺失或空值时退出码为 1，并输出红色错误提示",
    )
    parser.add_argument(
        "--check-types",
        action="store_true",
        help="额外校验 .env.example 中的类型标记（如 PORT=<int>）是否与实际值类型一致",
    )
    return parser


def _print_error(message: str) -> None:
    """以红色 ``❌ ERROR`` 前缀打印到 stderr。"""
    print(f"{_RED}❌ ERROR{_RESET} {message}", file=sys.stderr)


def _print_success(message: str) -> None:
    """以绿色 ``✅ All good!`` 前缀打印到 stdout。"""
    print(f"{_GREEN}✅ All good!{_RESET} {message}")


def main(argv: list[str] | None = None) -> int:
    """CLI 入口函数。

    Parameters
    ----------
    argv : list[str] | None
        命令行参数列表，默认为 ``sys.argv[1:]``。

    Returns
    -------
    int
        退出码 — 0 表示通过，1 表示校验未通过（strict 模式）或文件不存在。
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    env_path = Path(args.env)
    example_path = Path(args.example)

    # ── 文件存在性检查 ─────────────────────────────────────
    if not env_path.exists() and not example_path.exists():
        _print_error(
            f"文件均不存在：{env_path} 与 {example_path}\n"
            f"请确认当前工作目录正确，或通过 --env / --example 指定文件路径。"
        )
        return 1

    if not env_path.exists():
        _print_error(
            f"文件不存在：{env_path}\n"
            f"请确认路径正确，或通过 --env 指定。"
        )
        return 1

    if not example_path.exists():
        _print_error(
            f"文件不存在：{example_path}\n"
            f"请确认路径正确，或通过 --example 指定。"
        )
        return 1

    # ── 解析与校验 ─────────────────────────────────────────
    try:
        env_dict = parse_env_file(str(env_path))
        example_dict = parse_env_file(str(example_path))
    except (FileNotFoundError, ValueError) as exc:
        _print_error(str(exc))
        return 1

    result = validate(env_dict, example_dict)

    has_issues = bool(result["missing"] or result["empty_value"])

    if args.strict and has_issues:
        _print_error("发现以下问题：")
        if result["missing"]:
            print(f"  缺少键：{', '.join(result['missing'])}", file=sys.stderr)
        if result["empty_value"]:
            print(f"  空值键：{', '.join(result['empty_value'])}", file=sys.stderr)
        return 1

    # ── 类型标记校验（可选） ────────────────────────────────
    if args.check_types:
        type_errors = check_type_hint(env_dict, example_dict)
        if type_errors:
            _print_error("类型标记校验失败：")
            for key, msg in type_errors.items():
                print(f"  {key}: {msg}", file=sys.stderr)
            return 1

    # ── 非严格模式下的提示 ────────────────────────────────
    if has_issues:
        details: list[str] = []
        if result["missing"]:
            details.append(f"缺少 {len(result['missing'])} 个键")
        if result["extra"]:
            details.append(f"多余 {len(result['extra'])} 个键")
        if result["empty_value"]:
            details.append(f"{len(result['empty_value'])} 个空值")
        _print_success(f"（存在潜在问题：{'；'.join(details)}）")
        return 0

    _print_success("所有键值对完整，无异常。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
