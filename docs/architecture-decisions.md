# Architecture Decisions

GPU Scheduling Platform 的架构决策记录，面向评审与后续开发者。每条决策说明**做了什么、为什么、边界在哪**。

---

## 1. 单体 FastAPI + SQLite

**决策：** 后端为单一 FastAPI 进程，数据存储为单文件 SQLite，不做数据库服务分离。

**为什么：**

- 项目目标是 5 天 MVP 演示，不是生产系统。单体 + 文件数据库消除所有运维复杂度——不需要额外进程、不需要网络连接串、不需要迁移工具。
- SQLite 对单机并发足够（WAL 模式下读不阻塞写），且当前负载模型是"单用户操作几个实例"，不存在写竞争。
- 数据库文件与代码同目录，备份/重置只需要复制或删除一个文件。这在演示场景下是优势——可以随时"重置到干净状态"。

**代码事实：** `backend/app/database.py:11-26` 在首次请求时懒初始化连接，schema 与 migration 内联为 SQL 字符串，无 ORM。`backend/app/config.py:7` 中 `DATABASE_PATH` 默认为 `data/schedule.db`。

**边界：** SQLite 不支持并发写伸缩。如果实例数超过数百且 heartbeat 频率提高，写入竞争会显现。此时才需要切换 PostgreSQL。

---

## 2. Provider 抽象：mock + AutoDL，不引入多供应商复杂度

**决策：** Provider 接口只定义 4 个方法（list / create / get / destroy），注册两个实现——MockProvider（始终可用）和 AutoDLProvider（按 API Key 存在与否切换为真实/bind 模式）。

**为什么：**

- 跨供应商统一纳管是产品目标，但在 MVP 阶段至少要有一个真实供应商跑通完整闭环（create → bootstrap → monitor → destroy），其余允许 mock。
- 4 方法接口是刻意做的最小抽象——不假设供应商支持"重启""暂停""快照"等高级操作，因为真实供应商 API 能力不一致。
- bind mode（无 API Key 时 AutoDLProvider 仍注册但返回静态规格）保证前端开发和演示不依赖外部服务可用性。
- 不在 MVP 阶段设计多供应商路由/调度层，因为只有一个真实供应商时调度决策是退化的。

**代码事实：** `backend/app/providers/base.py:11` 定义 `BaseProvider`（ABC，4 个抽象方法）。`backend/app/services/provider_registry.py:10-15` 无条件注册 mock，条件注册 autodl。`backend/app/providers/autodl.py:259-339` 的 destroy 实现为三步异步流程（power_off → poll shutdown → release），是当前最复杂的供应商交互逻辑。

**边界：** 当前抽象不处理供应商的异构计费模型、异构地域/可用区语义、异构镜像体系。当接入第二家真实供应商时需要重新审视接口是否需要扩展（例如增加 `list_images`、`list_regions` 方法）。

---

## 3. Agent Heartbeat 驱动生命周期，而非服务端轮询

**决策：** 实例状态推进由实例内 Agent 通过 heartbeat 上报（POST /api/agent/heartbeat），后端被动响应。服务端保留一个 fallback 轮询协程用于 mock/degraded 检测。

**为什么：**

- 真实 GPU 实例可能在 NAT 后、无固定公网 IP，服务端无法主动连接。Agent push 模式是唯一可跨网络环境工作的方案。
- heartbeat 同时承担三重职责：①上报 bootstrap 进度（当前步骤/总步骤/状态）→ 驱动状态流转；②上报 telemetry 指标（CPU/内存/GPU/磁盘/网络）→ 写入 metrics 表；③更新时间戳 → 用于 degraded 检测。
- 一个心跳请求完成三件事，减少 Agent 端复杂度和网络往返。
- 服务端 fallback 协程（`instance_service.py:8-39`）仅在 mock 场景使用，真实实例由 Agent 接管。

**代码事实：** `backend/app/routers/agent.py:10-26` 的 heartbeat 端点无认证（通过 agent_token 验证）。`backend/app/services/agent_service.py:9-97` 处理状态流转逻辑：bootstrap 进度决定 provisioning → bootstrapping → testing → ready 转换。`backend/app/main.py:12-17` 在 lifespan 中启动 `_degraded_check_loop()`，每 15 秒检查超过 30 秒无心跳的实例并标记为 degraded。

**边界：** Agent 离线或崩溃时，实例会进入 degraded 状态但不会自动恢复或重试。当前没有 Agent 看门狗或自动重启机制。Agent 本身是否运行取决于实例 bootstrap 是否成功——bootstrap 失败时服务端只能等待超时。

---

## 4. 测试与监控链路允许部分模拟

**决策：** Dashboard 在无真实 metrics 时返回 mock 数据；性能与连通性测试当前为 schema 预置 + 空结果占位，真实执行与回填链路尚未落地。

**为什么：**

- Telemetry 数据依赖 Agent 在实例内采集并上报。在 mock 场景或 Agent 尚未就绪时，Dashboard 仍需要展示合理的 UI 结构，因此 `dashboard_service.py:86-112` 提供 mock fallback。
- 性能测试定义（9 项 GPU/网络/磁盘测试）作为 schema 预置在 `test_service.py:8-18`，`run_perf_test()` 会创建 test_run 并写入 9 条空 test_result 行后立即标记为 completed。这套"定义 + 记录"框架允许前后端先联调测试报告 UI（触发、列表、导出），不依赖 Agent 实现。
- 连通性测试同理——5 个目标硬编码，触发后创建空占位记录，不执行实际网络探测。
- 当前 `agent_service.py` 的 heartbeat 处理只写入 `metrics` 表，不写入 `test_results` 表。真实测试执行与结果回填链路属于后续演进方向。

**代码事实：** `backend/app/services/dashboard_service.py:144-166` 的 `build_instance_dashboard()` 在无 metrics 时调用 `_mock_latest_metric()`。`backend/app/services/test_service.py:29-62` 的 `run_perf_test()` 创建 test_run → 插入 9 条 `value=null, passed=0` 的 test_result → 立即标记 test_run 为 completed。`backend/app/services/agent_service.py` 无任何 `test_result` 引用。`backend/app/services/test_service.py:20-26` 硬编码 5 个连通性目标。

**边界：** 当前测试系统是"定义 + 记录"框架，不包含实际测试执行、调度、超时控制、重试策略。所有 test_result 的 value 在无外部回填逻辑时将永远停留在 `null`。真实 Agent 执行链路需要新增：①Agent 端的测试脚本；②服务端的结果回填 API/端点；③心跳或独立通道上报测试结果。

---

## 5. 前端全客户端渲染 + 轮询，不做 SSR/ISR

**决策：** 所有页面标记 `"use client"`，数据通过 3 秒间隔的 `fetch` 轮询获取，不做服务端渲染或增量静态生成。

**为什么：**

- 所有数据都是用户相关的实时数据（GPU 库存、实例状态、telemetry 指标），SSR/ISR 无意义——缓存的数据立即可能过时。
- 全客户端渲染消除了 Next.js 服务端与后端 API 之间的通信层，前端直接调用后端，架构简单。
- 3 秒轮询间隔对演示场景足够灵敏，且实现成本最低。WebSocket 或 SSE 会增加后端复杂度，对最多几十个实例的场景没有实际收益。

**代码事实：** `frontend/src/app/layout.tsx` 和所有 `page.tsx` 均以 `"use client"` 开头。`frontend/src/app/instances/[id]/page.tsx` 中 `useEffect` 以 3 秒间隔调用 `api.getInstanceDashboard()`。

**边界：** 轮询在实例数增长后会产生大量无意义请求（大部分轮询返回无变化数据）。如果实例数超过数十个，应切换到 WebSocket 或 Server-Sent Events。

---

## 已知风险与边界

| 风险 | 当前缓解措施 | 遗留问题 |
|---|---|---|
| AutoDL destroy 链路不可靠（网络超时、release 被拒） | 三步销毁 + 30 次轮询 + warning 日志 | 失败后不自动重试，需人工确认 AutoDL 控制台 |
| Agent 无认证（仅 agent_token） | token 在实例创建时生成，通过 heartbeat 匹配验证 | token 通过 HTTP 明文传输（无 TLS），可被中间人截获 |
| JWT Secret 硬编码默认值 `dev-secret-change-in-production` | 提供 `.env.example` 提示替换 | 无启动时强校验，漏配时仍可运行但不安全 |
| SQLite 无连接池 | aiosqlite 单连接，WAL 模式 | 并发 heartbeat 写入时可能排队 |
| 前端无错误边界组件 | `api.ts` 中 try-catch + 页面级 error 状态 | 未捕获的渲染错误会导致白屏 |
| 无用户权限隔离 | 所有用户看到相同的 GPU 列表 | 实例归属检查存在（按 user_id 过滤），但 GPU 市场全量可见 |

---

## 如果继续演进

以下演进方向按优先级排列，每一项都基于当前代码的明确边界：

1. **Agent 通信安全升级。** heartbeat 端点加 TLS + HMAC 签名，替代当前的明文 agent_token。这是最紧迫的安全改进，因为 Agent 上报的数据包含实例内敏感信息（Jupyter URL、SSH 端口）。

2. **Provider 接口扩展。** 接入第二家真实供应商时，`BaseProvider` 大概率需要增加 `list_images()` 和 `list_regions()` 方法。当前 AutoDL 的镜像 UUID 和地区列表是通过环境变量静态配置的，不支持动态查询。

3. **数据库切换为 PostgreSQL。** 当实例数增长或 heartbeat 频率提高时，SQLite 的写入串行化会成为瓶颈。迁移成本可控——当前所有数据库操作集中在 `database.py` 和 `models/` 下，无 ORM 耦合。

4. **前端切换到 WebSocket/SSE。** 当实例数超过数十个时，3 秒轮询的无效请求量会显著增长。Dashboard 页面是唯一需要实时更新的页面，可以只对该页面做增量改造。

5. **预算系统从一次性检查升级为运行时闭环。** 当前后端已在创建实例时通过 `check_budget()` 执行预算拦截（超预算返回 422，`instances.py:39-44`）。但尚未实现运行中按小时扣费、余额不足自动停机、续时、退款/结算等闭环。当前预算模型适合演示场景的单次创建-销毁模式。

6. **引入 provider 级别的健康检查与自动降级。** 当前 provider 故障只能在用户操作时发现（API 调用报错）。可以加后台健康检查协程，在 provider 不可用时自动从市场列表中移除其 offerings。

---

## 不做什么

以下内容在 MVP 阶段明确不做，避免过度工程化：

- **微服务拆分。** 当前单体在单机上的吞吐量远超 MVP 需求。
- **Kubernetes / 容器编排。** Docker Compose 单机部署满足演示需求，K8s 引入的复杂度（Pod 网络、存储卷、配置管理）对当前规模是负收益。
- **多租户权限系统。** 当前只有一个隐式角色（登录用户），无管理员/审计需求。
- **任务队列（Celery / Redis）。** 后台任务（lifecycle advance、degraded check）当前用 asyncio 协程处理，不需要独立 worker。
- **前端 E2E 测试。** 后端 pytest 覆盖了 API 级别的主要路径，前端交互通过手动演示验证。
