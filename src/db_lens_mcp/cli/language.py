"""Thin CLI language helpers for config guidance."""

from __future__ import annotations

from typing import Final, Literal, cast

import typer

Language = Literal["en", "zh"]

_SUPPORTED_LANGUAGES: Final[set[str]] = {"en", "zh"}
_LANGUAGE_PROMPT: Final[str] = "Choose language / 选择语言 (zh/en)"
_LANGUAGE_RETRY: Final[str] = "Please enter zh or en. / 请输入 zh 或 en。"

_MESSAGES: Final[dict[Language, dict[str, str]]] = {
    "en": {
        "profile_prompt": "Profile name",
        "host_prompt": "Host",
        "port_prompt": "Port",
        "database_prompt": "Database",
        "username_prompt": "Username",
        "password_prompt": "Password",
        "driver_prompt": "Database driver",
        "password_keep_prompt": "Password (leave empty to keep current)",
        "saved_profile": "Saved profile {profile!r} to {path}",
        "updated_profile": "Updated profile {profile!r} in {path}",
        "deleted_profile_summary": (
            "Delete profile {profile!r}: "
            "{driver}://{username}@{host}:{port}/{database}"
        ),
        "delete_confirm": "Delete profile {profile!r}?",
        "delete_cancelled": "Delete cancelled.",
        "deleted_profile": "Deleted profile {profile!r} from {path}",
        "default_profile_set": "default_profile: {profile}",
        "default_profile_cleared": "default_profile: cleared",
        "database_not_checked": "database: not checked",
        "database_failed": "database: failed: {error}",
        "database_ok": "database: ok",
        "next_step": "Next: {command}",
        "profile_saved_rerun": (
            "Profile was saved. Fix the connection information and rerun: {command}"
        ),
        "profile_updated_rerun": (
            "Profile was updated. Fix the connection information and rerun: {command}"
        ),
        "config_update_failed": "config_update: failed: {error}",
        "config_delete_failed": "config_delete: failed: {error}",
        "empty_value": "{name} must not be empty.",
        "unsupported_driver": "Only mysql and mariadb are supported in the first phase.",
    },
    "zh": {
        "profile_prompt": "请输入 profile 名称",
        "host_prompt": "请输入 host",
        "port_prompt": "请输入 port",
        "database_prompt": "请输入 database",
        "username_prompt": "请输入 username",
        "password_prompt": "请输入 password",
        "driver_prompt": "请输入 driver",
        "password_keep_prompt": "请输入 password（留空表示保持当前值）",
        "saved_profile": "已保存 profile {profile!r} 到 {path}",
        "updated_profile": "已在 {path} 中更新 profile {profile!r}",
        "deleted_profile_summary": (
            "将删除 profile {profile!r}: "
            "{driver}://{username}@{host}:{port}/{database}"
        ),
        "delete_confirm": "确认删除 profile {profile!r} 吗？",
        "delete_cancelled": "已取消删除。",
        "deleted_profile": "已从 {path} 删除 profile {profile!r}",
        "default_profile_set": "default_profile: {profile}",
        "default_profile_cleared": "default_profile: 已清空",
        "database_not_checked": "database: 未检查",
        "database_failed": "database: 失败: {error}",
        "database_ok": "database: 连接成功",
        "next_step": "下一步：{command}",
        "profile_saved_rerun": (
            "profile 已保存。请修正连接信息后重新运行：{command}"
        ),
        "profile_updated_rerun": (
            "profile 已更新。请修正连接信息后重新运行：{command}"
        ),
        "config_update_failed": "config_update: 失败: {error}",
        "config_delete_failed": "config_delete: 失败: {error}",
        "empty_value": "{name} 不能为空。",
        "unsupported_driver": "第一期只支持 mysql 和 mariadb。",
    },
}


def parse_language(language: str | None) -> Language | None:
    """Parse an explicit CLI language flag."""

    if language is None:
        return None
    normalized = language.strip().lower()
    if normalized not in _SUPPORTED_LANGUAGES:
        raise typer.BadParameter("language must be zh or en.")
    return cast(Language, normalized)


def prompt_for_language() -> Language:
    """Ask the user to choose a CLI language."""

    while True:
        choice = typer.prompt(_LANGUAGE_PROMPT).strip().lower()
        if choice in _SUPPORTED_LANGUAGES:
            return cast(Language, choice)
        typer.echo(_LANGUAGE_RETRY)


def resolve_language(language: str | None, *, prompt_if_missing: bool) -> Language:
    """Return the selected language, prompting only for interactive flows."""

    parsed = parse_language(language)
    if parsed is not None:
        return parsed
    if prompt_if_missing:
        return prompt_for_language()
    return "en"


def message(language: Language, key: str, **kwargs: object) -> str:
    """Render a localized CLI message."""

    return _MESSAGES[language][key].format(**kwargs)
