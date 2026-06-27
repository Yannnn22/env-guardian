"""
env-guardian 核心校验模块。

提供 .env 文件解析、键值对完整性比对、以及可选的类型标记校验能力。
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


# ── 类型标记解析 ──────────────────────────────────────────────

_TYPE_HINT_PATTERN = re.compile(
    r"^<(?P<type>int|float|bool|str|list|dict)>$"
)


def _infer_type(value: str) -> type | None:
    """将字符串值解析为 Python 内置类型，解析失败返回 None。"""
    # bool 必须优先于 int 检查，因为 bool 是 int 的子类
    if value.lower() in ("true", "false", "1", "0"):
        return bool
    try:
        int(value)
        return int
    except ValueError:
        pass
    try:
        float(value)
        return float
    except ValueError:
        pass
    # 判断是否为 list/dict 的简单表示（仅作演示用途，非完整解析）
    if value.startswith("[") and value.endswith("]"):
        return list
    if value.startswith("{") and value.endswith("}"):
        return dict
    return str


# ── 核心 API ──────────────────────────────────────────────────

def parse_env_file(file_path: str) -> dict[str, str]:
    """读取 .env 文件并返回键值对字典。

    处理规则：
      - 忽略以 ``#`` 开头的注释行。
      - 忽略空行。
      - 按第一个 ``=`` 拆分键与值。
      - 移除键和值两端的空白字符。
      - 如果值被单引号或双引号包裹，剥去引号。

    Parameters
    ----------
    file_path : str
        .env 或 .env.example 文件的路径。

    Returns
    -------
    dict[str, str]
        解析后的键值对字典。

    Raises
    ------
    FileNotFoundError
        文件不存在。
    ValueError
        文件中存在无法解析的行（不含 ``=`` 的非空非注释行）。
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在：{file_path}")

    env_dict: dict[str, str] = {}

    for lineno, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()

        # 忽略空行和注释行
        if not line or line.startswith("#"):
            continue

        # 内联注释处理：截取 # 前的内容
        if "#" in line:
            line = line.split("#", 1)[0].strip()
            if not line:
                continue

        if "=" not in line:
            raise ValueError(
                f"第 {lineno} 行缺少 ``=``，无法解析为键值对：{raw_line!r}"
            )

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        # 剥去外层引号
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]

        if key:
            env_dict[key] = value

    return env_dict


def validate(
    env_dict: dict[str, str],
    example_dict: dict[str, str],
) -> dict[str, list[str]]:
    """比对两个字典，返回缺失 / 多余 / 空值三种异常列表。

    以 ``example_dict`` 为基准，检查 ``env_dict``：
      - **missing**       — example 中有但 env 中没有的键。
      - **extra**         — env 中有但 example 中没有的键。
      - **empty_value**   — 值在 env 中为空字符串或 None 的键。

    Parameters
    ----------
    env_dict : dict[str, str]
        实际使用的环境变量字典（通常来自 ``.env``）。
    example_dict : dict[str, str]
        参照字典（通常来自 ``.env.example``）。

    Returns
    -------
    dict[str, list[str]]
        包含 ``missing``、``extra``、``empty_value`` 三个键的字典，
        每个键对应一个字符串列表。
    """
    missing: list[str] = []
    extra: list[str] = []
    empty_value: list[str] = []

    env_keys = set(env_dict.keys())
    example_keys = set(example_dict.keys())

    missing = sorted(example_keys - env_keys)
    extra = sorted(env_keys - example_keys)

    common_keys = env_keys & example_keys
    for key in common_keys:
        val = env_dict[key]
        if val is None or val == "":
            empty_value.append(key)
    empty_value.sort()

    return {
        "missing": missing,
        "extra": extra,
        "empty_value": empty_value,
    }


def check_type_hint(
    env_dict: dict[str, str],
    example_dict: dict[str, str],
) -> dict[str, str]:
    """校验 .env.example 中的类型标记与实际值类型是否匹配。

    当 example 中的值形如 ``<int>``、``<float>``、``<bool>``、
    ``<str>``、``<list>``、``<dict>`` 时，认为该键带有类型声明，
    函数会尝试将 env 中对应的实际值推断为 Python 内置类型并比较。

    如果实际值无法转换成声明类型，结果字典中会记录一条错误信息。

    Parameters
    ----------
    env_dict : dict[str, str]
        实际使用的环境变量字典。
    example_dict : dict[str, str]
        参照字典，值中可包含类型标记如 ``<int>``。

    Returns
    -------
    dict[str, str]
        键为环境变量名，值为人类可读的错误描述。
        如果全部通过，返回空字典。
    """
    errors: dict[str, str] = {}

    type_map: dict[str, type] = {
        "int": int,
        "float": float,
        "bool": bool,
        "str": str,
        "list": list,
        "dict": dict,
    }

    for key, example_value in example_dict.items():
        example_value = example_value.strip()

        match = _TYPE_HINT_PATTERN.match(example_value)
        if not match:
            continue

        declared_type_str = match.group("type")
        expected_type = type_map.get(declared_type_str, type(None))

        if key not in env_dict:
            errors[key] = f"缺少该键，无法校验类型（期望 {declared_type_str}）"
            continue

        actual_value = env_dict[key]
        if actual_value is None or actual_value == "":
            continue

        inferred = _infer_type(actual_value)

        if expected_type is str:
            continue

        if inferred is not expected_type:
            errors[key] = (
                f"类型不匹配：声明为 {declared_type_str}，"
                f"实际值为 {actual_value!r}，推断类型为 {inferred.__name__ if inferred else 'unknown'}"
            )

    return errors
