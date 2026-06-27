# env-guardian

![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![CI](https://img.shields.io/github/actions/workflow/status/Yannnn22/env-guardian/python-test.yml?label=CI)

> 轻量级 CLI 工具，用于校验 `.env` 文件的环境变量声明是否完整。  
> 将实际使用的 `.env` 与参照文件 `.env.example` 进行比对，快速定位缺失、多余或空值的键。

---

## 安装

```bash
# 从本地源码安装
pip install .

# 或开发模式安装（推荐，修改代码后即时生效）
pip install -e .
```

## 使用示例

### 1. 基本校验

当前目录下存在 `.env` 与 `.env.example`，直接运行：

```text
$ env-guardian
✅ All good! 所有键值对完整，无异常。
```

### 2. 发现缺失与空值（严格模式）

如果 `.env` 中缺少 `DB_PORT`、`DEBUG` 的值为空：

```text
$ env-guardian --strict
❌ ERROR 发现以下问题：
  缺少键：DB_PORT
  空值键：DEBUG
```

`--strict` 模式下退出码为 **1**，非严格模式仅给出提示文字，退出码仍为 **0**。

### 3. 自定义文件路径

```text
$ env-guardian --env .env.production --example .env.example --strict
❌ ERROR 发现以下问题：
  缺少键：SECRET_KEY
```

### 4. 类型标记校验

当 `.env.example` 中包含类型声明时，可额外检查实际值类型是否匹配：

```text
$ env-guardian --check-types
❌ ERROR 类型标记校验失败：
  PORT: 类型不匹配：声明为 int，实际值为 'abc'，推断类型为 str
```

## 核心 API

| 函数 | 说明 |
| --- | --- |
| `parse_env_file(file_path)` | 读取 .env / .env.example，忽略注释和空行，返回 `dict[str, str]` |
| `validate(env, example)` | 比对两个字典，返回 `{missing, extra, empty_value}` 三个列表 |
| `check_type_hint(env, example)` | 识别 `<int>`、`<bool>` 等类型标记并校验实际值类型 |

## 开发

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest -v
```

## 项目结构

```
env-guardian/
├── pyproject.toml
├── requirements.txt
├── README.md
├── .gitignore
├── .github/workflows/
│   └── python-test.yml
├── src/
│   └── validator/
│       ├── __init__.py
│       ├── cli.py
│       └── core.py
└── tests/
    ├── __init__.py
    ├── test_core.py
    └── fixtures/
        ├── normal/
        ├── missing/
        ├── empty_value/
        └── extra/
```
