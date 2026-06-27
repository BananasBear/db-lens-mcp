# MCP Tools Spec

## 设计目标

一期 MCP 工具服务于后端 AI 开发过程中的数据库上下文补全。工具只暴露固定白名单能力，不提供通用 SQL 执行入口。

AI 使用这些工具了解：

- 表结构和字段含义。
- 索引设计。
- 表数据量和容量估算。
- SELECT 查询执行计划。
- 查询是否可能慢、是否走索引、是否存在明显风险。

## 工具清单

| 工具 | 作用 | 风险级别 | 一期优先级 |
| --- | --- | --- | --- |
| `list_databases` | 获取当前连接可见的数据库列表 | 低 | P1 |
| `list_tables` | 获取指定 database 下的表列表，支持关键词过滤 | 低 | P1 |
| `describe_table` | 获取表字段、类型、是否可空、默认值、主键、注释 | 低 | P0 |
| `list_indexes` | 获取表索引、唯一性、字段顺序、索引类型、基数估算 | 低 | P0 |
| `get_table_stats` | 获取行数估算、数据容量、索引容量、更新时间 | 低 | P1 |
| `explain_select` | 对单条 SELECT 执行 EXPLAIN，返回原始计划和结构化摘要 | 中 | P0 |
| `inspect_query` | 组合分析 SELECT：相关表、表结构、索引、统计信息、执行计划、风险提示 | 中 | P0 |

P0 是一期重点打磨能力，P1 是支撑能力。

## 通用输入字段

所有工具都应支持连接配置别名：

```json
{
  "profile": "local-dev"
}
```

涉及 database 的工具显式传入 database，不依赖隐式当前库：

```json
{
  "profile": "local-dev",
  "database": "app_db"
}
```

## `list_databases`

### 输入

```json
{
  "profile": "local-dev"
}
```

### 输出

```json
{
  "databases": [
    {
      "name": "app_db"
    }
  ]
}
```

## `list_tables`

### 输入

```json
{
  "profile": "local-dev",
  "database": "app_db",
  "keyword": "order"
}
```

`keyword` 可选。

### 输出

```json
{
  "database": "app_db",
  "tables": [
    {
      "name": "orders",
      "comment": "订单表",
      "table_type": "BASE TABLE"
    }
  ]
}
```

## `describe_table`

### 输入

```json
{
  "profile": "local-dev",
  "database": "app_db",
  "table": "orders"
}
```

### 输出

```json
{
  "database": "app_db",
  "table": "orders",
  "columns": [
    {
      "name": "user_id",
      "type": "bigint",
      "nullable": false,
      "default": null,
      "primary_key": false,
      "comment": "用户 ID"
    }
  ],
  "primary_key": ["id"],
  "comment": "订单表"
}
```

## `list_indexes`

### 输入

```json
{
  "profile": "local-dev",
  "database": "app_db",
  "table": "orders"
}
```

### 输出

```json
{
  "database": "app_db",
  "table": "orders",
  "indexes": [
    {
      "name": "idx_user_created",
      "unique": false,
      "type": "BTREE",
      "columns": ["user_id", "created_at"],
      "cardinality": 10240
    }
  ]
}
```

## `get_table_stats`

### 输入

```json
{
  "profile": "local-dev",
  "database": "app_db",
  "table": "orders"
}
```

### 输出

```json
{
  "database": "app_db",
  "table": "orders",
  "row_count_estimate": 1200000,
  "data_length_bytes": 268435456,
  "index_length_bytes": 134217728,
  "updated_at": "2026-06-27T10:00:00Z",
  "source": "information_schema"
}
```

默认使用元数据估算，不执行 `count(*)`。

## `explain_select`

### 输入

```json
{
  "profile": "local-dev",
  "database": "app_db",
  "sql": "select * from orders where user_id = ? order by created_at desc limit 20"
}
```

### 输出

```json
{
  "accepted": true,
  "query_type": "SELECT",
  "explain": {
    "summary": {
      "status": "ok",
      "tables": ["orders"],
      "access_types": ["ref"],
      "used_indexes": ["idx_user_created"],
      "estimated_rows": 20,
      "extra": []
    }
  },
  "risk_hints": []
}
```

## `inspect_query`

`inspect_query` 是一期核心工具。它把 AI 最需要的数据库上下文一次性组合返回。

### 输入

```json
{
  "profile": "local-dev",
  "database": "app_db",
  "sql": "select * from orders where user_id = ? order by created_at desc limit 20"
}
```

### 输出

```json
{
  "accepted": true,
  "query_type": "SELECT",
  "referenced_tables": ["orders"],
  "table_context": [
    {
      "database": "app_db",
      "table": "orders",
      "columns": [],
      "indexes": [],
      "stats": {}
    }
  ],
  "metadata_errors": [],
  "explain": {
    "summary": {
      "status": "ok",
      "tables": ["orders"],
      "access_types": ["ref"],
      "used_indexes": ["idx_user_created"],
      "estimated_rows": 20,
      "extra": []
    }
  },
  "risk_hints": [
    {
      "level": "warning",
      "code": "select_all_columns",
      "message": "查询使用 SELECT *，建议只选择业务需要的字段。"
    }
  ],
  "ai_summary": "该查询访问 orders 表，过滤字段为 user_id，排序字段为 created_at。当前执行计划显示使用 idx_user_created，预计扫描行数较低。"
}
```

如果某个表的元数据读取失败，`inspect_query` 仍会在 SQL 安全校验通过后继续尝试 EXPLAIN，并通过 `metadata_errors` 返回按表聚合的脱敏错误。

## 风险提示

一期只做基础、可解释的风险提示，不做强索引建议。

| code | level | 含义 |
| --- | --- | --- |
| `full_table_scan` | warning | 执行计划显示可能全表扫描 |
| `index_not_used` | warning | 查询未使用索引 |
| `high_rows_examined` | warning | 估算扫描行数较高 |
| `using_filesort` | warning | 执行计划可能使用 filesort |
| `using_temporary` | warning | 执行计划可能使用临时表 |
| `select_all_columns` | info | 使用 `SELECT *` |
| `missing_where` | warning | 大表查询缺少 WHERE |
| `unknown_table_stats` | info | 表统计信息不足 |

## 拒绝输出

SQL 不符合安全要求时，工具必须拒绝执行。

```json
{
  "accepted": false,
  "reason": "Only single SELECT statements are allowed.",
  "risk": "blocked_non_select"
}
```

## 安全要求

- 所有工具必须只执行白名单数据库操作。
- 不提供通用 SQL 执行入口。
- `explain_select` 和 `inspect_query` 只能接受单条 SELECT。
- 用户传入 EXPLAIN 语句必须拒绝；EXPLAIN 由工具内部生成。
- 多语句 SQL 必须拒绝。
- 解析失败必须拒绝。
- 带占位符 SQL 未提供参数时，可以返回表结构和索引上下文，但必须跳过 EXPLAIN。
- 不得自动猜测或编造参数值。
- INSERT、UPDATE、DELETE、DDL、CALL、LOAD DATA、事务控制等语句必须拒绝。
- 返回结果不得包含数据库密码、密钥或完整连接串。

## 待确认

- MCP 工具最终 JSON Schema。
- MySQL `EXPLAIN FORMAT=JSON` 是否作为一期默认格式。
- 风险提示阈值，例如 `high_rows_examined` 的默认行数。
- EXPLAIN 参数绑定方式。
