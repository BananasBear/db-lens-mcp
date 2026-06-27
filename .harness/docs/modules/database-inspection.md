# Database Inspection Domain Model

## 核心概念

- Connection Profile：一个数据库连接配置，包含 host、port、database、user、加密后的 password 等。
- Database Catalog：数据库列表和基础元信息。
- Table Summary：表名、注释、行数估算、容量估算。
- Table Schema：字段、类型、是否可空、默认值、主键、注释。
- Index Summary：索引名、字段顺序、唯一性、索引类型、基数估算。
- Explain Request：用户提交的 SELECT SQL 和连接配置引用。
- Explain Plan：数据库返回的执行计划。
- Risk Hint：基于执行计划生成的基础风险提示。

## 第一版能力边界

- 支持 MySQL / MariaDB。
- 读取表结构、索引、行数和容量估算。
- 只对 SELECT 执行 EXPLAIN。
- 根据 SQL 自动识别相关表，返回相关表结构、索引和执行计划组合结果。
- 提供基础风险提示，例如全表扫描、未使用索引、扫描行数偏大。
- 不提供通用 SQL 执行入口。

## 非目标

- 第一版不自动执行数据修改语句。
- 第一版不做通用 SQL 客户端。
- 第一版不提供强索引自动生成或自动变更能力。
- 第一版不做完整 DBA 诊断平台。
- 第一版不做跨数据库统一抽象的复杂兼容层。
