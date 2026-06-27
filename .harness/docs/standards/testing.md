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
- 当前单元测试使用 fake connection / monkeypatch 覆盖元数据和 EXPLAIN 路径，不依赖真实数据库。
- 后续集成测试可通过容器数据库验证真实 MySQL/MariaDB 元数据和 EXPLAIN。
- MCP 工具测试验证输入输出结构和错误处理。
- 每个阶段完成后，用只读子代理按项目规则 review 新增代码，不使用外部 Code Review skill。

## 当前验证命令

```bash
rtk sh -n scripts/install.sh
rtk python -m pytest
rtk python -m compileall src tests
```

## 待确认

- 是否使用 Testcontainers 或 Docker Compose。
- CI 环境是否可用数据库容器。
