# MCP Handoff Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `db-lens mcp handoff` so users can copy one command's output and send it to another agent for generic MCP installation.

**Architecture:** Reuse the existing MCP server config helpers so `install-*`, `mcp config`, and `mcp handoff` share the same command/args/env payload. Add one new CLI command plus one text-rendering helper that wraps the generic JSON config in a Chinese installation prompt for other agents.

**Tech Stack:** Python 3.11+, Typer CLI, existing `tests/test_cli.py` CLI coverage, markdown docs under `README.md` and `.harness/`.

---

### Task 1: Add CLI tests for the handoff command

**Files:**
- Modify: `tests/test_cli.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_mcp_handoff_prints_generic_agent_prompt() -> None:
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "mcp",
            "handoff",
            "--command",
            "/usr/local/bin/db-lens",
            "--config-file",
            "/tmp/db-lens.toml",
        ],
    )

    assert result.exit_code == 0
    assert "请把下面这个 MCP server 配置到你当前使用的 MCP 客户端中，并完成安装。" in result.stdout
    assert '"mcpServers"' in result.stdout
    assert '"command": "/usr/local/bin/db-lens"' in result.stdout
    assert '"args": [' in result.stdout
    assert 'DB_LENS_CONFIG_FILE' in result.stdout


def test_mcp_handoff_omits_empty_env_block() -> None:
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "mcp",
            "handoff",
            "--command",
            "/usr/local/bin/db-lens",
        ],
    )

    assert result.exit_code == 0
    assert 'DB_LENS_CONFIG_FILE' not in result.stdout
    assert '"env": {}' not in result.stdout
```

- [ ] **Step 2: Run the targeted test to verify it fails**

Run: `env PYTHONPATH=src pytest tests/test_cli.py -k handoff`
Expected: FAIL because `mcp handoff` does not exist yet.

- [ ] **Step 3: Keep existing no-secrets coverage aligned**

```python
def test_mcp_handoff_does_not_print_secrets() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["mcp", "handoff"])

    assert result.exit_code == 0
    lowered = result.stdout.lower()
    assert "password" not in lowered
    assert "master_key" not in lowered
    assert "mysql://" not in lowered
```

- [ ] **Step 4: Re-run the targeted test set**

Run: `env PYTHONPATH=src pytest tests/test_cli.py -k handoff`
Expected: still FAIL until implementation is added, but now all handoff expectations are encoded.

- [ ] **Step 5: Do not commit**

Run: `git diff -- tests/test_cli.py`
Expected: diff only shows the new handoff-related tests. Do not create a commit because project rules forbid git commits.

### Task 2: Implement the handoff command and shared rendering helper

**Files:**
- Modify: `src/db_lens_mcp/cli/main.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Add the command to the help output**

```python
                "   db-lens mcp config --client trae",
                "   db-lens mcp handoff",
```

- [ ] **Step 2: Add the new Typer command**

```python
@mcp_app.command("handoff")
def mcp_handoff(
    server_name: str = typer.Option("db-lens", help="MCP server name in the handoff message."),
    command: str = typer.Option("", help="Command used by the MCP client. Defaults to db-lens."),
    config_file: str = typer.Option(
        "",
        help="Optional DB_LENS_CONFIG_FILE value for clients that need an explicit path.",
    ),
) -> None:
    """Print a generic MCP installation message for other agents."""

    command_value = command.strip() or _resolve_db_lens_command()
    typer.echo(_handoff_message(server_name, command_value, config_file.strip()))
```

- [ ] **Step 3: Add the text-rendering helper using the shared config payload**

```python
def _handoff_message(server_name: str, command: str, config_file: str = "") -> str:
    payload = {
        "mcpServers": {
            server_name: _base_server_config(command, config_file),
        }
    }
    config_json = json.dumps(payload, indent=2, ensure_ascii=False)
    return "\n".join(
        [
            "请把下面这个 MCP server 配置到你当前使用的 MCP 客户端中，并完成安装。",
            "",
            "要求：",
            f"- server 名称保持为 {server_name}",
            "- 使用下面的 command、args 和 env",
            "- 不要修改配置中的字段名",
            "- 如果你的客户端不支持自动安装，请把下面的 JSON 配置粘贴到对应的 MCP 配置位置",
            "- 安装完成后，确认你已经能看到 db-lens 提供的 MCP tools",
            "",
            "配置：",
            config_json,
        ]
    )
```

- [ ] **Step 4: Run the targeted handoff tests**

Run: `env PYTHONPATH=src pytest tests/test_cli.py -k handoff`
Expected: PASS for the new handoff tests.

- [ ] **Step 5: Smoke-check syntax**

Run: `/Users/zhenghao/.pyenv/versions/3.10.13/bin/python3 -m py_compile src/db_lens_mcp/cli/main.py tests/test_cli.py`
Expected: command exits 0.

### Task 3: Update user-facing docs and change tracking

**Files:**
- Modify: `README.md`
- Modify: `scripts/install.sh`
- Modify: `.harness/docs/modules/configuration.md`
- Modify: `.harness/docs/modules/deployment.md`
- Modify: `.harness/changes/2026-06-28-mcp-client-installers.md`

- [ ] **Step 1: Add the new command to README command lists**

```markdown
db-lens mcp handoff
```

- [ ] **Step 2: Add a short README explanation for unknown agents**

```markdown
For other agents or MCP clients that are not directly supported yet, run:

```bash
db-lens mcp handoff
```

Then copy the output and send it to the agent so it can install the MCP server into its own client configuration.
```

- [ ] **Step 3: Update install-script next steps to mention handoff**

```sh
     $DB_LENS_COMMAND mcp handoff
```

- [ ] **Step 4: Update `.harness` docs and change record**

```markdown
- 对其他未直接支持的 Agent，使用 `db-lens mcp handoff` 输出通用安装提示词。
```

- [ ] **Step 5: Review the final diff instead of committing**

Run: `git diff -- README.md scripts/install.sh .harness/docs/modules/configuration.md .harness/docs/modules/deployment.md .harness/changes/2026-06-28-mcp-client-installers.md`
Expected: docs only mention the new handoff path and do not change unrelated behavior. Do not create a commit because project rules forbid git commits.

### Task 4: Run final verification in the available local environment

**Files:**
- Modify: `none`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Run the available CLI-focused verification**

Run: `env PYTHONPATH=src /Users/zhenghao/opt/anaconda3/bin/python - <<'PY'`
```python
from db_lens_mcp.cli.main import _handoff_message

message = _handoff_message("db-lens", "/usr/local/bin/db-lens", "/tmp/db-lens.toml")
assert "请把下面这个 MCP server 配置到你当前使用的 MCP 客户端中，并完成安装。" in message
assert '"mcpServers"' in message
assert 'DB_LENS_CONFIG_FILE' in message
print("handoff validation ok")
```
`PY`
Expected: prints `handoff validation ok`.

- [ ] **Step 2: Re-run syntax validation**

Run: `/Users/zhenghao/.pyenv/versions/3.10.13/bin/python3 -m py_compile src/db_lens_mcp/cli/main.py tests/test_cli.py`
Expected: exits 0.

- [ ] **Step 3: Record the environment limitation**

```text
Full pytest execution is not available here because the machine lacks the project-required Python 3.11 / uv runtime, so final reporting must call out that limitation explicitly.
```

- [ ] **Step 4: Capture the final workspace diff summary**

Run: `git diff --stat -- src/db_lens_mcp/cli/main.py tests/test_cli.py README.md scripts/install.sh .harness/docs/modules/configuration.md .harness/docs/modules/deployment.md .harness/changes/2026-06-28-mcp-client-installers.md docs/superpowers/plans/2026-06-28-mcp-handoff.md`
Expected: only the handoff implementation, docs, and plan files are listed.

- [ ] **Step 5: Do not commit**

Run: `git status --short`
Expected: modified files remain unstaged or staged per local preference, with no commit created because project rules forbid git commits.
