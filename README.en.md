# db-lens-mcp

Default documentation: [README.md](README.md) in Chinese.

## Introduction

`db-lens-mcp` is a database-context MCP tool for backend developers and AI coding tools. It lets AI tools such as Codex, Claude Code, and Trae safely inspect MySQL / MariaDB schema, indexes, table size estimates, and SELECT execution plans while you write code, review SQL, or investigate slow-query risk.

It is not a general SQL client. It does not expose arbitrary SQL execution, change tables, create indexes, or modify data.

## Use Cases

Think of `db-lens-mcp` as a read-only database lens for AI tools: the AI does not need a database console or a full connection string, but it can still inspect database context through MCP.

It is mainly used to:

- Inspect table schema: columns, types, primary keys, and comments.
- Inspect indexes: indexed columns, uniqueness, order, type, and cardinality estimates.
- Estimate table size: row count, data size, and index size.
- Analyze `SELECT` queries: read execution plans and flag risks such as full table scans, missing index usage, or high estimated rows.
- Help AI write backend code: let it understand the real database structure before changing DAO, Mapper, Repository, Service, or SQL code.

It is not used to:

- Use it as a database administration tool or SQL console.
- Ask an AI to run `INSERT`, `UPDATE`, `DELETE`, DDL, or operational commands.
- Replace full DBA slow-query analysis, capacity planning, or index review.
- Run it as a full team HTTP/SSE service in the first version. Server deployment is only reserved at a basic level for now.

## Install

Run one command:

```bash
curl -fsSL https://raw.githubusercontent.com/MagicPelican/db-lens-mcp/master/scripts/install.sh | sh
```

After installation, follow the next-step commands printed in the terminal. Normally, check the installation first:

```bash
db-lens doctor
```

View available commands:

```bash
db-lens help
```

## Configuration Flow

Use three steps.

### 1. Add a Database

```bash
db-lens config add
```

Follow the prompts:

- profile name, for example `local-dev`
- database host and port
- database names, separated by commas
- username and password

Use a read-only database account when possible.

### 2. Test the Connection

```bash
db-lens config test local-dev
```

### 3. Connect an AI Client

Codex:

```bash
db-lens mcp install-codex
```

Claude Code:

```bash
db-lens mcp install-claude-code
```

Trae:

```bash
db-lens mcp install-trae
```

After installing the MCP config, restart the client and ask the AI to use `db-lens`.

For other agents or MCP clients:

```bash
db-lens mcp handoff
```

Send the full output to the agent so it can add `db-lens` to its own MCP configuration.

## MCP Capabilities

The MCP server exposes only fixed allowlisted tools:

| Tool | Purpose |
| --- | --- |
| `list_profiles` | List configured connection profiles without passwords |
| `list_databases` | List visible databases for a profile |
| `refresh_table_cache` | Refresh the local table-to-database mapping cache |
| `find_tables` | Find which database contains a table by name or keyword |
| `list_tables` | List tables in a database |
| `describe_table` | Inspect columns, primary key, and table comments |
| `list_indexes` | Inspect indexes, uniqueness, column order, index type, and cardinality estimates |
| `get_table_stats` | Inspect row-count, data-size, and index-size estimates |
| `explain_select` | Run tool-generated `EXPLAIN` for a safe single `SELECT` |
| `inspect_query` | Return related schema, indexes, stats, execution plan, and basic risk hints for a query |

Example prompts:

```text
Use db lens to inspect the orders table schema and indexes.
```

```text
Use db lens to analyze whether this SQL may be slow:
select * from orders where user_id = ? order by created_at desc limit 20
```

## Safety Boundary

The design is based on "read-only context + allowlisted tools".

- No generic SQL execution tool is exposed.
- Only a single `SELECT` can be analyzed.
- User-written `EXPLAIN` is rejected; `EXPLAIN` is generated internally by the tool.
- Multi-statement SQL is rejected.
- `INSERT`, `UPDATE`, `DELETE`, DDL, `CALL`, `LOAD DATA`, transaction control, and other high-risk statements are rejected.
- SQL validation uses MySQL-dialect AST parsing, not string-prefix checks.
- SQL with placeholders can return schema and index context, but `db-lens-mcp` will not invent parameter values to run `EXPLAIN`.
- MCP errors returned to AI clients are redacted for common password, key, and connection-string patterns.
- `config list` does not show passwords, ciphertext, or the master key.

## Common Commands

```bash
db-lens doctor
db-lens help

db-lens config add
db-lens config update local-dev
db-lens config delete old-profile
db-lens config list
db-lens config test local-dev

db-lens cache refresh local-dev

db-lens mcp install-codex
db-lens mcp install-claude-code
db-lens mcp install-trae
db-lens mcp handoff

db-lens mcp config --client codex
db-lens mcp config --client claude-code
db-lens mcp config --client trae
db-lens mcp config
db-lens mcp run
```

Notes:

- `db-lens mcp run` manually starts the MCP stdio server, mainly for troubleshooting.
- `db-lens mcp config` prints MCP config snippets without modifying client config files.
- `db-lens mcp install-*` attempts to write the corresponding client config automatically.

## Advanced Configuration

Most users do not need to edit config files manually. Use config files and environment variables for scripting, Docker, or reserved server deployment paths.

Config file example:

```toml
[profiles.local-dev]
driver = "mysql"
host = "127.0.0.1"
port = 3306
databases = ["app_db", "audit_db"]
username = "readonly_user"
password = "enc:v1:..."
connect_timeout_seconds = 5
read_timeout_seconds = 10
```

Common environment variables:

```text
DB_LENS_CONFIG_FILE=/path/to/config.toml
DB_LENS_MASTER_KEY=...
```

Configuration precedence:

```text
CLI arguments > environment variables > config.toml > defaults
```

Interactive configuration commands support language selection:

```bash
db-lens config add --language zh
db-lens config add --language en
```

When omitted, `config add`, interactive `config update`, and confirmation-based `config delete` ask the user to choose Chinese or English first.

## Server Deployment Status

The current main path is local MCP stdio usage. Server/team deployment is only reserved at a basic level:

- Config file and master key can be supplied through environment variables.
- Docker-based usage can build on the same configuration model later.
- Full HTTP/SSE MCP server, authentication, multi-tenancy, audit, and web admin are outside the first version.

## Troubleshooting

### db-lens Not Found

Run the installer again and keep the terminal output. The installer should print an executable `db-lens` path; if it does not print one, or if the printed command still does not work, the installer logic needs to be fixed.

### MCP Client Cannot See db-lens

Verify the command first:

```bash
db-lens doctor
db-lens mcp config
```

Then rerun the client-specific installer and restart the client:

```bash
db-lens mcp install-codex
```

### AI Cannot Find a Table

If the table was just created or renamed, refresh the table cache:

```bash
db-lens cache refresh local-dev
```

If multiple databases contain the same table name, specify the database explicitly in your request.

### EXPLAIN Was Skipped

If the SQL uses placeholders such as `?` without parameter values, `db-lens-mcp` will not invent values. It may return schema, index, and risk context while skipping `EXPLAIN`.
