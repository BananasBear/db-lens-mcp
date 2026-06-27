# Testing Standards

## 测试重点

- SQL 安全校验：SELECT 允许，非 SELECT 拒绝。
- 多语句、注释绕过、DDL/DML/CALL 等危险输入拦截。
- 配置加载优先级：CLI 配置、配置文件、环境变量覆盖。
- 加密和解密失败场景。
- MySQL/MariaDB 元数据解析。
- EXPLAIN 结果和风险提示转换。

## 测试分层

- 单元测试覆盖解析、校验、配置、风险规则。
- 集成测试通过容器数据库验证元数据和 EXPLAIN。
- MCP 工具测试验证输入输出结构和错误处理。

## 待确认

- 测试框架。
- 是否使用 Testcontainers 或 Docker Compose。
- CI 环境是否可用数据库容器。
