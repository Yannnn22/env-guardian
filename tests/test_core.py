"""
env-guardian 核心函数测试。

所有测试均读取 ``tests/fixtures/`` 下的真实 .env / .env.example 文件，
确保 ``parse_env_file`` 和 ``validate`` 在实际文件 I/O 下行为正确。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from validator.core import parse_env_file, validate

FIXTURES = Path(__file__).resolve().parent / "fixtures"


# ── 辅助 ──────────────────────────────────────────────────────

def _read(fixture_dir: str) -> tuple[dict, dict]:
    """读取指定场景下的一对 .env 和 .env.example，返回 (env_dict, example_dict)。"""
    d = FIXTURES / fixture_dir
    return parse_env_file(str(d / ".env")), parse_env_file(str(d / ".env.example"))


# ── 测试用例 ──────────────────────────────────────────────────

def test_normal_match() -> None:
    """正常场景：env 和 example 完全匹配，三个列表均应为空。"""
    env, example = _read("normal")
    result = validate(env, example)

    assert result["missing"] == [], f"预期无缺失，得到 {result['missing']}"
    assert result["extra"] == [], f"预期无多余，得到 {result['extra']}"
    assert result["empty_value"] == [], f"预期无空值，得到 {result['empty_value']}"


def test_missing_key() -> None:
    """缺失场景：env 缺少 example 中的 DB_PORT，验证 missing 捕获到该键。"""
    env, example = _read("missing")
    result = validate(env, example)

    assert "DB_PORT" in result["missing"], (
        f"DB_PORT 应在 missing 列表中，得到 {result['missing']}"
    )
    assert result["extra"] == [], f"预期无多余键，得到 {result['extra']}"
    assert result["empty_value"] == [], f"预期无空值，得到 {result['empty_value']}"


def test_empty_value() -> None:
    """空值场景：env 中 DB_HOST 的值为空，验证 empty_value 捕获到它。"""
    env, example = _read("empty_value")
    result = validate(env, example)

    assert "DB_HOST" in result["empty_value"], (
        f"DB_HOST 应在 empty_value 列表中，得到 {result['empty_value']}"
    )
    assert result["missing"] == [], f"预期无缺失，得到 {result['missing']}"
    assert result["extra"] == [], f"预期无多余，得到 {result['extra']}"


def test_extra_key() -> None:
    """多余场景：env 比 example 多出 EXTRA_KEY，验证 extra 捕获到它。"""
    env, example = _read("extra")
    result = validate(env, example)

    assert "EXTRA_KEY" in result["extra"], (
        f"EXTRA_KEY 应在 extra 列表中，得到 {result['extra']}"
    )
    assert result["missing"] == [], f"预期无缺失，得到 {result['missing']}"
    assert result["empty_value"] == [], f"预期无空值，得到 {result['empty_value']}"


# ── parse_env_file 专项 ──────────────────────────────────────

def test_parse_env_file_comment_blank_ignored() -> None:
    """确认注释行与空白行被正确忽略，同时正常键值对依然被解析。"""
    d = FIXTURES / "normal"
    env = parse_env_file(str(d / ".env"))

    assert "DB_HOST" in env
    assert env["DB_PORT"] == "5432"
    assert len(env) == 4


def test_parse_env_file_not_found() -> None:
    """传入不存在的路径应抛出 FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        parse_env_file("/tmp/__nonexistent_env_file__")


def test_parse_env_file_invalid_line() -> None:
    """包含不含 ``=`` 的有效行应抛出 ValueError。"""
    bad_file = FIXTURES / "normal" / ".env"
    # 造一个临时坏文件
    tmp = FIXTURES / "___bad_env_tmp"
    try:
        tmp.write_text("KEY1=value1\nINVALID_LINE_NO_EQUALS\nKEY2=value2\n")
        with pytest.raises(ValueError):
            parse_env_file(str(tmp))
    finally:
        tmp.unlink(missing_ok=True)
