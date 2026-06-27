# Security Standards

## 核心安全边界

- 推荐用户使用只读数据库账号，但项目安全不能依赖账号权限是否足够小。
- 工具层必须强制能力白名单，不提供通用 SQL 执行入口。
- EXPLAIN 只允许工具内部对单条 SELECT 生成。
- 用户不能直接传入 EXPLAIN 语句。
- 禁止执行 INSERT、UPDATE、DELETE、DDL、CALL、LOAD DATA、事务控制等高风险语句。

## SQL 校验

- 一期使用 `sqlglot` 解析 SQL，方言按 MySQL 处理。
- 用户输入 SQL 必须经过 AST 解析和类型判断，不得只靠字符串前缀或正则判断。
- 解析失败时拒绝执行。
- 多语句输入必须拒绝。
- 只允许单条 `SELECT`。
- 允许 `WITH ... SELECT ...` 这类查询语句。
- 注释、空白、大小写和分号差异交给解析器处理；解析失败或解析出多语句时拒绝。
- 用户传入 `EXPLAIN SELECT ...` 必须拒绝，由工具内部生成 EXPLAIN。

## 校验流程

```text
输入 SQL
  -> 去除首尾空白
  -> sqlglot parse_one(sql, dialect="mysql")
  -> 确认只有一个表达式
  -> 确认根节点是 SELECT 或 WITH SELECT
  -> 提取涉及的表
  -> 检查危险语句和危险节点
  -> 返回 SafeSelectQuery
```

## 必须拒绝的输入

- 非 SELECT。
- 多语句。
- 无法解析 SQL。
- 用户直接传入 EXPLAIN。
- INSERT、UPDATE、DELETE、CREATE、ALTER、DROP、TRUNCATE。
- CALL、LOAD DATA、SET、USE。
- 事务控制语句。
- 任何会修改数据库状态或会话状态的语句。

## 占位符和参数

一期允许参数化 SQL 出现在 `inspect_query` 中，例如：

```sql
select * from orders where user_id = ?
```

规则：

- 可以对带占位符 SQL 做解析、表识别、表结构和索引上下文返回。
- 执行 EXPLAIN 时，如果 SQL 包含占位符但未提供参数，则跳过 EXPLAIN。
- 不自动猜测参数值。
- 不为了执行 EXPLAIN 编造业务参数。
- 后续如支持 `params`，必须只用于参数绑定，不允许字符串拼接。

跳过 EXPLAIN 时应返回明确状态，例如 `skipped_missing_params`。

## 配置和密钥

- 配置文件不得保存明文密码。
- 密钥来源必须可诊断。
- 返回给 MCP 客户端的错误中不得包含密钥、密码或完整连接串。

## 待确认

- 服务器模式鉴权策略。
- 审计日志最小字段。
- EXPLAIN 参数绑定方式。
