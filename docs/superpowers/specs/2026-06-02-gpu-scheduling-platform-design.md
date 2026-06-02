# GPU 调度平台 - 架构设计文档

## 概述

构建公司内部 GPU 调度平台，体验对标 Vast.ai。跨供应商统一调度 GPU 资源（AutoDL、潞晨云、派欧云），支持 A100 / H 系列 / 6090 三种型号族。网页端完成「资源展示 → 选择配置 → 一键开机 → 实例监控」完整链路。

### 关键约束

- **时间**：5 天
- **预算**：¥100（GPU 按需计费）
- **部署**：火山引擎 ECS（2C2G, Ubuntu 24.04, 公网 115.191.43.252）+ 按需 GPU 实例
- **交付**：网页端 + 性能测试报告 + S3 数据挂载 + Telemetry 监控

## 一页摘要

- **目标**：做出公司内部 GPU 调度平台 MVP，体验对标 Vast.ai 的核心链路
- **MVP 边界**：至少 1 家供应商真实一键开机，另外 2 家完成统一展示与纳管兜底
- **核心闭环**：资源展示 → 配置选择 → 开机 → 环境就绪 → 监控 → 测试 → 销毁
- **答辩重点**：优先证明链路可跑通，其次证明测试报告、预算控制和安全设计成立
- **演示策略**：真实 Provider 优先，Mock 仅作为 API 不稳定或预算耗尽时的兜底

---

## 技术选型

| 层 | 技术 | 理由 |
|---|------|------|
| 前端 | Next.js + TypeScript | 服务端渲染 + 页面路由，shadcn/ui 组件库 |
| 可视化 | Recharts | 半圆环仪表盘 + 时序折线图 |
| 后端 | FastAPI (Python 3.12) | 异步支持、自动 OpenAPI 文档、对接 ML 工具链 |
| 数据库 | SQLite (aiosqlite) | 零部署开销，单文件，够用 |
| 部署 | Docker Compose | 前端容器 + 后端容器，ECS 上一键启动 |

---

## 系统架构

```
┌─────────────────────────────────────────────────┐
│  Next.js 前端 (端口 3000)                         │
│  /gpus   /gpus/:id/configure   /instances/:id    │
└──────────────────┬──────────────────────────────┘
                   │ HTTP REST + WebSocket
┌──────────────────▼──────────────────────────────┐
│  FastAPI 后端 (端口 8000)                         │
│  ├─ 认证中间件（JWT）                             │
│  ├─ API 路由层                                   │
│  │   ├─ /api/auth/*         认证接口              │
│  │   ├─ /api/gpus/*         GPU 市场接口          │
│  │   ├─ /api/instances/*    实例管理接口           │
│  │   └─ /api/budget         预算查询              │
│  ├─ 调度服务层                                    │
│  │   ├─ InstanceService     实例生命周期管理       │
│  │   ├─ AgentService        Agent 回连 + 指标存储  │
│  │   └─ BudgetService       预算约束 + 追踪        │
│  └─ Provider 适配层（可插拔）                      │
│      ├─ AutoDLProvider       调 HTTP API           │
│      ├─ LuchenProvider       调 HTTP API           │
│      ├─ PaioProvider         调 HTTP API           │
│      └─ MockProvider         假数据（演示兜底）    │
└──────────────────┬──────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────┐
│  SQLite 数据库                                   │
│  users / instances / metrics / test_runs /       │
│  test_results / connectivity_tests /             │
│  gpu_offerings / budget_logs / provider_configs  │
└─────────────────────────────────────────────────┘
```

---

## 前端设计

### 页面路由

| 路由 | 功能 | 对应 Vast.ai 流程 |
|------|------|------------------|
| `/login` | 密码登录 | — |
| `/gpus` | GPU 资源展示 + 筛选 | 资源展示 |
| `/gpus/:id/configure` | 选择配置 + 一键开机 | 选择配置 |
| `/instances` | 我的实例列表 | — |
| `/instances/:id` | 实例详情 + 实时监控 + 测试报告 | 实例可用性与监控 |

### 可复用组件

| 组件 | 用途 | 出现位置 |
|------|------|---------|
| `CircularStatCard` | 半圆环仪表盘（品牌紫色 #8A5CF5） | 监控页 CPU/Memory/GPU |
| `GPURentalCard` | GPU 租赁卡片（型号、算力、价格、开机按钮） | 市场列表页 |
| `InstanceStatusBadge` | 状态标识（色标 + 文字 + 进度） | 监控页、实例列表 |
| `SearchAndFilter` | 搜索 + 多条件筛选侧栏 | 市场列表页 |
| `TemplateCard` | 镜像/模板选择卡片 | 配置页 |
| `TelemetryChart` | 时序折线图（利用率趋势） | 监控页 |
| `ConnectivityChecklist` | 外网可达性 ✅/❌ 列表 | 实例详情页 |
| `TestReportPanel` | 性能测试结果展示 + 导出按钮 | 实例详情页 |

### 设计风格

- 深色主题（监控页强制深色），品牌色 #8A5CF5
- CSS Grid 布局（市场列表 `repeat(auto-fill, minmax(300px, 1fr))`）
- 图表库 Recharts：半圆环用 PieChart 改造，时序图用 LineChart
- 筛选组件用 shadcn/ui 的 Slider、Checkbox、Select

---

## 实例生命周期状态机

从「机器已创建」到「环境已就绪」分 5 个状态，每步有明确的进入条件和验收信号。

```
provisioning → bootstrapping → testing → ready ⇄ degraded
                                   ↘ failed
```

### provisioning（分配中）
- **进入**：Provider.create_instance() 返回成功
- **期间**：轮询 Provider API 获取实例基础信息
- **出口**：实例启动 cloud-init / user-data → bootstrapping
- **超时**：5 分钟未进入 bootstrap → failed

### bootstrapping（环境安装中）
- **进入**：实例自启动脚本开始执行
- **执行**：bootstrap.sh 依次安装 6 步：
  1. apt update + build-essential + nvidia-container-toolkit
  2. CUDA 13 + cuDNN
  3. NGC PyTorch 容器 (nvidia/pytorch:26.03-py3)
  4. Codex CLI + Claude Code CLI
  5. S3 挂载 + FineWeb-Edu 数据集下载到本地盘
  6. 安装 `gpu-agent` 并开始 heartbeat 上报
- **出口**：Agent 首次 heartbeat 成功且 bootstrap 全部通过 → testing
- **失败**：任一步骤失败或长时间无 heartbeat → failed（记录失败步骤编号和错误日志）

### testing（健康检查中）
- **进入**：bootstrap.sh 全部通过
- **执行**：health_check.sh 依次验证：
  1. nvidia-smi 可用 + CUDA 13 版本校验
  2. PyTorch GPU 张量计算验证
  3. Codex CLI / Claude Code CLI 版本输出
  4. S3 挂载路径可读写 + 数据文件存在
  5. Metrics agent 正在运行
  6. 外网可达性（5 个目标站点 curl）
- **出口**：全部通过 → ready；部分通过 → ready(标注失败项)
- **失败**：关键项（CUDA/PyTorch）失败 → failed

### ready（就绪）
- 所有服务正常，用户可用
- Agent 每 10 秒持续上报 metrics，前端轮询展示
- 可手动触发性能测试

### failed（失败）
- 记录失败步骤 + 错误日志
- 用户可重试（从头开始 provisioning）或销毁

### 前端展示

| 状态 | 展示文字 | 额外信息 |
|------|---------|---------|
| provisioning | "正在分配 GPU 实例..." | — |
| bootstrapping | "正在安装环境..." | 当前步骤 X/6 |
| testing | "正在运行健康检查..." | 进度 |
| ready | "Running"（绿点） | 同 Vast.ai |
| degraded | "监控失联"（黄点） | 最近心跳时间 |
| failed | "启动失败"（红点） | 失败原因 |

---

## Provider 可行性矩阵

### 能力定义

「调度模式」= Provider 支持 `list_gpu_offerings/create_instance/destroy_instance`，平台可真实一键开机。

「纳管模式」= Provider 不负责创建实例，只负责绑定已有实例并接入 Agent、监控、测试。

### 交付收敛

- `Primary Provider`：优先选 1 家最容易调通 API 的供应商，必须实现真实一键开机
- `Fallback Provider`：其余 2 家允许先以纳管模式交付
- `Kill Criteria`：若 Day 2 结束前仍未打通第二家 `create_instance()`，立即收缩为“1 家调度 + 2 家纳管”

### 能力矩阵

| 能力 | Mock | AutoDL | 潞晨云 | 派欧云 |
|------|------|--------|--------|--------|
| list_gpu_offerings() | ✅ 假数据 | ⚠️ 待调研 | ⚠️ 待调研 | ⚠️ 待调研 |
| create_instance() | ✅ 假创建 | ⚠️ 待调研 | ⚠️ 待调研 | ⚠️ 待调研 |
| get_metrics() (平台 API) | ✅ 假数据 | ❌ 通常不全 | ❌ 通常不全 | ❌ 通常不全 |
| destroy_instance() | ✅ 假销毁 | ⚠️ 待调研 | ⚠️ 待调研 | ⚠️ 待调研 |
| cloud-init + Agent | n/a | ✅ | ✅ | ✅ |

### 实施顺序

1. **Day 1**：MockProvider 全流程跑通
2. **Day 2-3**：逐个调研 3 家供应商 API，按以下优先级实现：
   - 有 REST API → 实现 create_instance() + list_gpu_offerings()
   - 只有网页控制台 → bind_instance()，标记该 Provider 为「纳管模式」
   - 完全无接口 → 纯 bind_instance()
3. **面试回应**：主动说明「X 家实现完整 API 调度，Y 家当前纳管模式，架构已预留 Provider 接口，后续接入只需实现 BaseProvider」

---

## 控制链路与 Telemetry

### MVP 方案：Agent heartbeat + 前端轮询

GPU 实例在 bootstrapping 阶段安装 `gpu-agent`，Agent 每 10 秒通过 HTTPS 调用 `POST /api/agent/heartbeat`，上报：
- 生命周期进度与错误
- telemetry 指标
- health check 摘要

**原因**：跨供应商网络下，平台主动 SSH 不稳定；同时 heartbeat 比完整 WebSocket 控制面更适合 5 天 MVP。

### Phase 划分

- **Phase 1（默认实现）**：仅做 `heartbeat` 上报；前端每 10 秒轮询实例详情与 metrics
- **Phase 2（有余力再做）**：增加 WebSocket 推送与任务下发

### Agent 鉴权

1. `create_instance` 或 `bind_instance` 时生成实例级 `agent_token`
2. 通过 cloud-init / 环境变量把 `agent_token` 注入实例
3. Agent 每次 heartbeat 直接携带 `agent_token`
4. 实例销毁后 token 失效，Agent 停止上报

### 采集脚本输出格式

```json
{
  "cpu_percent": 35.2,
  "memory_percent": 62.1,
  "memory_used_gb": 28.9,
  "memory_total_gb": 46.6,
  "gpus": [{
    "index": 0,
    "utilization": 89,
    "vram_percent": 93,
    "vram_used_gb": 42.0,
    "vram_total_gb": 45.0,
    "temp_c": 61.0,
    "power_w": 244.0
  }],
  "disk_used_gb": 45.2,
  "disk_total_gb": 200.0,
  "net_up_mbps": 125.3,
  "net_down_mbps": 450.1
}
```

### 推送前端

- Agent → Backend：`POST /api/agent/heartbeat`
- Frontend → Backend：`GET /api/instances/:id`、`GET /api/instances/:id/metrics` 每 10 秒轮询
- WebSocket 推送列为 Phase 2，可选实现

### 核心状态字段

- `instances.current_step`：当前步骤编号
- `instances.progress_percent`：前端进度条
- `instances.last_error`：最近失败原因
- `instances.agent_token`：Agent 注册密钥
- `instances.last_heartbeat_at`：最近心跳时间

### Heartbeat 超时与降级规则

- Agent 默认每 `10s` 上报一次 heartbeat
- 连续 `3` 个 heartbeat 周期（`30s`）未收到上报，实例标记为 `degraded`
- `degraded` 不等于 `failed`，表示实例可能仍在运行，但平台暂时失去 telemetry/控制链路
- 前端在实例详情页展示黄色告警条，并显示“最近心跳时间”
- 一旦 heartbeat 恢复，实例可自动从 `degraded` 回到 `ready`

---

## 测试模块

### 一、性能测试

| 测试项 | 指标定义 | 工具/命令 | 单位 |
|--------|---------|----------|------|
| GPU Memory Bandwidth | 单卡显存实测吞吐 | CUDA `bandwidthTest` | GB/s |
| NVLink | 链路状态 + 卡间 P2P 实测吞吐分开记录 | `nvidia-smi nvlink -s` + `p2pBandwidthLatencyTest` | GB/s |
| PCIe Lanes | 代际 / lane 数 / 当前链路宽度 | `lspci -vv` | xN / GenN |
| PCIe Bandwidth | Host↔GPU 实测吞吐 | CUDA `bandwidthTest` Host↔Device | GB/s |
| Internet Upload | 公网实测 | `speedtest-cli --json` | Mbps |
| Internet Download | 公网实测 | `speedtest-cli --json` | Mbps |
| Disk Bandwidth | 本地盘顺序读写实测 | `fio` | MB/s |

**报告口径**：页面分为“拓扑信息”和“实测结果”两栏，避免把链路状态误写成带宽结论。

**导出字段**：`metric_name / metric_group / value / unit / source_command / collected_at / passed`。

### 二、外网可达性测试

| 目标站点 | 测试方法 | 输出结论 |
|---------|---------|---------|
| huggingface.co | DNS + TLS + HTTP + body/title 指纹 | reachable / suspect-mirror / unreachable |
| cloudflare.com | 同上 | 同上 |
| aws.amazon.com | 同上 | 同上 |
| api.openai.com | DNS + TLS SAN + HTTP | 同上 |
| google.com | DNS + TLS + HTTP | 同上 |

**触发**：testing 阶段自动跑一次 + ready 后可手动重新测试。

**前端展示**：每行展示 `状态 / HTTP 状态码 / 延迟 / 最终域名 / 风险等级`。

### 数据模型

```sql
CREATE TABLE instances (
    id                  TEXT PRIMARY KEY,
    user_id             TEXT NOT NULL,
    provider            TEXT NOT NULL,
    provider_instance_id TEXT,
    gpu_offering_id     TEXT,
    status              TEXT DEFAULT 'provisioning', -- provisioning/bootstrapping/testing/ready/degraded/failed
    current_step        INTEGER DEFAULT 0,
    progress_percent    REAL DEFAULT 0,
    last_error          TEXT,
    agent_token         TEXT,
    last_heartbeat_at   TEXT,
    config_json         TEXT,
    created_at          TEXT DEFAULT (datetime('now')),
    destroyed_at        TEXT
);

CREATE TABLE metrics (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    instance_id      TEXT NOT NULL,
    timestamp        TEXT DEFAULT (datetime('now')),
    cpu_percent      REAL,
    memory_percent   REAL,
    memory_used_gb   REAL,
    memory_total_gb  REAL,
    gpu_util_percent REAL,
    gpu_vram_percent REAL,
    disk_used_gb     REAL,
    disk_total_gb    REAL,
    net_up_mbps      REAL,
    net_down_mbps    REAL,
    gpu_json         TEXT             -- 每张 GPU 的 utilization / vram / temp / power 明细
);

CREATE TABLE test_runs (
    id          TEXT PRIMARY KEY,
    instance_id TEXT NOT NULL,
    type        TEXT NOT NULL,        -- perf / connectivity
    status      TEXT DEFAULT 'running',
    started_at  TEXT,
    finished_at TEXT,
    trigger     TEXT DEFAULT 'manual' -- auto / manual
);

CREATE TABLE test_results (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    test_run_id TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    value       REAL,
    unit        TEXT,
    passed      INTEGER
);

CREATE TABLE connectivity_tests (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    instance_id   TEXT NOT NULL,
    target        TEXT NOT NULL,      -- huggingface / cloudflare / aws / openai / google
    status_code   INTEGER,
    latency_ms    REAL,
    is_direct     INTEGER,           -- 1 = 直连, 0 = 疑似镜像
    error_message TEXT,
    timestamp     TEXT DEFAULT (datetime('now'))
);
```

---

## API 接口设计

```
# 认证
POST /api/auth/login          密码登录 → 返回 JWT token
GET  /api/auth/check          检查 token 有效性

# GPU 市场
GET  /api/gpus                跨供应商 GPU 列表（筛选: family/provider/price/available）
GET  /api/gpus/:id            单个 GPU 详情

# 实例管理
POST   /api/instances         一键开机（调用 Provider.create_instance）
       Body: { gpu_offering_id, template, disk_gb, duration_h, s3_mount }
       返回前 BudgetService 校验预估费用是否超预算，超则返回 422 BUDGET_EXCEEDED
POST   /api/instances/bind    手动录入已有实例（兜底）
GET    /api/instances         我的实例列表
GET    /api/instances/:id     实例详情 + 当前状态 + 最新指标
DELETE /api/instances/:id     销毁实例

# 实时监控
GET /api/instances/:id/metrics        当前指标快照（JSON，MVP 默认）
WS  /api/instances/:id/metrics/stream 实时指标推送（Phase 2，可选）

# 性能测试
POST /api/instances/:id/tests         触发性能测试（ready 状态可用）
GET  /api/instances/:id/tests         测试结果列表
GET  /api/instances/:id/tests/export  导出 JSON/CSV

# 外网可达性
POST /api/instances/:id/connectivity  手动触发外网可达性测试
GET  /api/instances/:id/connectivity  最新结果

# Agent
POST /api/agent/heartbeat             Agent 心跳 + 状态/指标上报（MVP 默认）
WS   /api/agent/stream                Agent 长连接流（Phase 2，可选）

# 预算
GET  /api/budget                      预算状态（总额/已用/剩余）
POST /api/instances/estimate          开机前预估费用
      Body: { gpu_offering_id, disk_gb, duration_h }
      返回: { estimated_cost_per_hour, estimated_total, remaining_budget }
```

**通用错误格式**：`{"error": "ERROR_CODE", "message": "人类可读消息", "detail": "调试信息（仅非生产环境）"}`

**HTTP 状态码**：200 成功 / 400 参数错误 / 401 未认证 / 403 越权 / 422 业务逻辑拒绝 / 502 Provider 不可用

---

## 预算控制

从「只记录」升级为「约束 + 记录」：

1. **开机前预估**：`POST /api/instances/estimate` 返回 `price_per_hour × duration_h = estimated_total`
2. **超预算阻断**：`POST /api/instances` 创建前校验 `estimated_total < remaining_budget`
3. **Burn-rate 告警**：AgentService 每小时汇总预算日志；剩余预算 < 20% 时提醒
4. **币种统一**：内部统一人民币（¥），供应商美元价格按当天汇率转换

---

## GPU 型号归一化

筛选和展示使用不同字段，避免型号混乱：

```
gpu_offerings 表：
  gpu_family  TEXT  — 归一化型号族: "A100" / "H" / "6090"  （筛选用）
  gpu_model   TEXT  — 展示型号:     "A100-80G" / "H800-80G" / "RTX 6090"  （展示用）
```

H100 / H800 / H20 都归入 `gpu_family = "H"`。

---

## 安全性

### 实例安全

- GPU 实例默认关闭公网 22，主控制链路依赖 Agent 回连，不依赖平台主动 SSH
- 平台对外仅开放 `443` 供 Agent 回连
- 如供应商允许，可为人工排障临时开启白名单 SSH，用后立即关闭
- 用户在实例详情页查看 Agent 在线状态、最近心跳和失败日志摘要

### 平台安全

- 密码哈希存储（bcrypt）
- JWT token 认证（24 小时过期）
- 应用层强制用户数据隔离（无跨用户访问）
- 所有外部 API 密钥存环境变量，不入仓库

### 安全测试

- nmap 端口扫描验证 22 端口关闭
- curl 验证未认证请求返回 401
- 验证跨用户实例访问返回 403
- 输出安全测试结论文档

---

## 错误处理

- **Provider 层**：外部 API 调用失败 → 重试 1 次 → 仍失败抛 `ProviderError(name, detail)`
- **Service 层**：捕获 ProviderError → 转友好消息 + 记录日志
- **API 层**：`@app.exception_handler` 统一返回标准 JSON 错误格式
- **前端**：全局 ErrorBoundary + API 调用 toast 提示，网络超时 15 秒

---

## 测试策略

仅覆盖核心链路（时间约束）：

- Provider 接口单元测试（Mock 数据进出验证）
- InstanceService 创建/销毁流程测试
- 认证中间件测试
- **smoke test**：MockProvider 创建实例 → 状态机推进到 ready → 采集一轮 metrics → 运行一次性能测试 → 销毁，验证跨模块交界
- 不写前端测试、不搞完整集成测试

---

## 需求映射表

| # | 原始需求 | 页面 | API | 数据表 | 验收方式 |
|---|---------|------|-----|--------|---------|
| 1 | 性能测试报告 | /instances/:id → 测试 Tab | POST/GET /api/instances/:id/tests, /export | test_runs, test_results | 页面查看 + JSON/CSV 下载 |
| 2 | 外网可达性 | /instances/:id → 连通性卡片 | POST/GET /api/instances/:id/connectivity | connectivity_tests | ✅/❌ 列表 + 延迟 + 直连判断 |
| 3 | 预装基础环境 | bootstrap.sh（bootstrapping 阶段） | 状态机自动推进 | instances.config_json | testing → ready 状态转换 |
| 4 | S3 挂载 + 数据导入 | bootstrap.sh 步骤 5 | 同上 | 同上 | testing 阶段验证文件存在 |
| 5 | Telemetry UI | /instances/:id → 监控 Tab | GET /api/instances/:id/metrics（MVP） | metrics | 轮询更新圆环 + 时序图 |
| 6 | 端口转发与安全（加分项） | 关闭公网 22 + Agent 回连 | 安全测试文档 | — | nmap 扫描报告 |

---

## 演示降级策略

| 场景 | 对策 |
|------|------|
| 所有供应商 API 都调不通 | MockProvider 演示完整流程，展示 Provider 可插拔架构 |
| 预算烧完了 | Mock 模式 + 历史采集的 metrics 数据 |
| 供应商实例启动超时 | 状态机走到 failed，展示错误处理 |
| bootstrap 或 Agent heartbeat 失败 | 展示 failed 状态 + 失败步骤编号 + 错误日志 |
| 外网可达性部分失败 | 展示部分 ✅ 部分 ❌，体现「测试结论」考核要求 |
| 某家供应商无 API | bind_instance() 纳管模式，主动说明原因和扩展方案 |

## MVP 验收标准

- **链路完成**：用户可从市场页完成 1 次真实或 Mock 的完整开机流程
- **环境就绪**：实例进入 `ready` 前完成 CUDA、PyTorch、CLI、S3、数据落盘校验
- **监控可见**：实例详情页可看到实时 CPU、内存、GPU、磁盘、网络指标
- **测试可交付**：性能测试和外网可达性测试结果可展示、可导出
- **预算可控**：创建前可预估费用，超预算创建会被阻断
- **安全可说明**：22 端口策略、认证隔离、密钥管理和安全测试结论可讲清楚

## 5 天执行计划

| Day | 目标 |
|-----|------|
| Day 1 | 跑通 Mock 全链路，定型页面与数据模型 |
| Day 2 | 打通 1 家真实 Provider 的列表与开机 |
| Day 3 | 完成 bootstrap、监控采集、实例详情页 |
| Day 4 | 完成性能测试、连通性测试、导出与预算控制 |
| Day 5 | 补 smoke test、整理文档、录制 demo、准备答辩 |

## 主要风险与取舍

- **Provider API 风险**：优先保 1 家真实调度成功，其余允许纳管模式交付
- **预算风险**：所有重测试均手动触发，避免机器空转和重复测速
- **网络风险**：若供应商实例初始化或 Agent 回连不稳定，优先保证核心链路可演示
- **时间风险**：不追求生产级多租户与复杂调度算法，聚焦 MVP 核心闭环

## 非目标

- 不实现生产级多租户权限体系
- 不实现复杂排队调度、抢占式调度和计费结算系统
- 不实现完整 Agent 任务下发控制面，WebSocket 与流式控制列为 Phase 2
- 不覆盖前端自动化测试和大规模集群场景

## 提交物说明

- 本文档定义 MVP 范围、架构、接口、验收标准与风险取舍
- 代码仓库以可运行 Demo 为目标，优先覆盖 1 家真实 Provider + Mock 兜底
- 演示时若真实供应商链路波动，可切换到文档中的降级策略继续完成说明

---

## 项目目录结构

```
schedule/
├── frontend/
│   └── src/
│       ├── app/
│       │   ├── page.tsx                      # GPU 市场
│       │   ├── login/page.tsx                # 登录
│       │   ├── gpus/[id]/configure/page.tsx  # 选配 + 一键开机
│       │   └── instances/
│       │       ├── page.tsx                  # 实例列表
│       │       └── [id]/page.tsx             # 监控面板 + 测试报告
│       ├── components/
│       │   ├── CircularStatCard.tsx
│       │   ├── GPURentalCard.tsx
│       │   ├── InstanceStatusBadge.tsx
│       │   ├── SearchAndFilter.tsx
│       │   ├── TemplateCard.tsx
│       │   ├── TelemetryChart.tsx
│       │   ├── ConnectivityChecklist.tsx
│       │   └── TestReportPanel.tsx
│   └── lib/
│           ├── api.ts
│           └── polling.ts
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── middleware/auth.py
│   │   ├── routers/{auth,gpus,instances,budget,agent}.py
│   │   ├── services/{instance_service,agent_service,budget_service,test_service}.py
│   │   ├── providers/{base,autodl,luchen,paio,mock}.py
│   │   └── models/{user,instance,metric,gpu_offering,test}.py
│   ├── tests/
│   │   ├── test_providers.py
│   │   ├── test_instance_service.py
│   │   ├── test_auth.py
│   │   └── test_smoke.py
│   ├── scripts/
│   │   ├── bootstrap.sh            # 实例环境初始化脚本
│   │   ├── health_check.sh         # 健康检查脚本
│   │   └── gpu-metrics.sh         # 指标采集脚本（部署到 GPU 实例）
│   └── requirements.txt
└── docs/
    └── ...
```

---

## 决策记录

| 决策 | 选择 | 原因 |
|------|------|------|
| 从零写 vs 基于开源改 | 从零写 | 中国供应商 API 不兼容，改造 ≈ 重写 |
| 技术栈 | Next.js + FastAPI | 前端生态好 + Python 对接 ML/GPU 工具链 |
| 后端分层 | 三层（路由→服务→Provider） | 可插拔 Provider + 未来本地集群扩展 |
| 认证 | JWT + 用户表 | 代价小，按生产级设计 |
| 外键 | 不加 | 应用层校验，更灵活 |
| 一键开机 | 至少 1 家 create_instance() + bind 兜底 | 满足核心需求，诚实处理供应商差异 |
| 实例初始化 | cloud-init/bootstrap → Agent heartbeat → testing → ready | 避免把 SSH 可达误当成环境就绪 |
| 监控采集 | Agent heartbeat + 前端轮询 | 跨供应商更稳，且比完整 WebSocket 控制面更适合 MVP |
| Agent 范围 | 仅 heartbeat/status/metrics 上报 | 避免控制面过重，5 天内先完成最小闭环 |
| Mock | 内置 MockProvider | 预算风险兜底 + 演示保障 |
| 安全 | 关闭公网 22 + Agent 回连 + nmap 验证 | 满足加分项要求且更贴近跨云现实 |
| 预算 | 预估 + 阻断 + burn-rate 告警 | 100 元预算太紧，必须主动控制 |
| 部署 | Docker Compose on ECS | 一键启动，ECS 已有 |
| 图表 | Recharts | 轻量，React 生态原生支持 |
| UI 组件 | shadcn/ui | 加速开发，可定制 |