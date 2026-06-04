# GPU 调度平台

公司内部 GPU 调度平台，目标体验对标 Vast.ai，支持跨供应商统一展示 GPU 资源，并完成「资源展示 → 选择配置 → 一键开机 → 实例监控 → 测试报告」的核心链路。

## 项目目标

本项目是一个面向内部使用的 GPU 调度平台 MVP，目标是在有限时间和预算下，完成以下能力：

- 跨供应商统一展示 GPU 资源
- 支持 A100 / H 系列 / 6090 三种型号族筛选
- 支持网页端一键开机
- 支持实例状态追踪与 Telemetry 监控
- 支持性能测试报告展示与导出
- 支持外网可达性检测
- 支持 S3-compatible 存储挂载与数据导入本地高速盘
- 支持预算控制与演示降级策略

## 当前状态

当前仓库处于 MVP 设计与开发阶段。

已完成：

- 原始需求拆解
- 系统架构设计
- 页面与 API 设计
- 测试模块与验收思路设计
- Provider 分层与降级方案设计

开发中：

- 前端页面实现
- 后端 API 实现
- Provider 接入
- 实例 bootstrap 流程
- Telemetry 与测试链路

最近更新 (2026-06-04)：

- AutoDL 真实 Provider 已接入（支持 list / create / destroy）
- 无 API Key 时自动降级为 bind mode
- 实例生命周期已改为事件驱动（heartbeat 驱动状态流转）
- 性能测试与连通性测试已分离为独立逻辑
- 支持 JSON / CSV 测试结果导出
- Dashboard 优先使用真实 metrics / connect 数据
- 新增 bootstrap.sh / health_check.sh / gpu-metrics.sh 脚本
- destroy 链路已真实验证：power_off → 轮询 shutdown → release 可用

## AutoDL Provider 模式

- 配置 `AUTODL_API_KEY` → 真实 API 调度模式：
  - `list`：从 AutoDL 拉取实例列表并映射为 GPU offerings（无实例时 fallback 到静态规格）
  - `create`：调用真实 AutoDL create API，返回 `pro-` 开头的真实实例 ID
  - `destroy`：已真实验证 `power_off` → 轮询 `shutdown` → `release` 链路可用。正常路径为全自动两步销毁。异常场景（power_off 失败、release 失败、轮询超时）会记录 warning 并清理本地状态，需人工复核 AutoDL 远端是否已释放
  - `get_instance`：通过 list API 搜索实例 UUID 获取当前状态
- 未配置 `AUTODL_API_KEY` → bind mode（list 返回静态规格，create 返回 bind-ID，destroy 静默释放）
- Provider 已在 `provider_registry` 中自动注册，无需手动配置
- **已知限制**：destroy 在 power_off 或 release 失败/超时时不会自动重试，仅清理本地。极端场景建议登录 AutoDL 控制台确认实例是否已释放

## 核心能力

### 1. GPU 市场页

统一展示多个供应商的 GPU 资源，支持：

- 按型号族筛选：A100 / H / 6090
- 按供应商筛选
- 按价格筛选
- 按可用状态筛选

### 2. 一键开机

用户在配置页选择：

- GPU 资源
- 镜像 / 模板
- 磁盘容量
- 使用时长
- S3 挂载配置

然后发起实例创建，平台负责推进实例生命周期状态：

- provisioning
- bootstrapping
- testing
- ready
- failed

### 3. 实例监控

实例详情页提供 Telemetry 监控，包括：

- CPU
- 内存
- GPU 利用率
- 显存占用
- 磁盘使用
- 网络上下行

### 4. 测试报告

平台支持两类测试结果展示与导出：

- 性能测试
- 外网可达性测试

性能测试目标包括：

- Per-GPU memory bandwidth
- NVLink 相关链路/吞吐信息
- PCIe lanes / PCIe bandwidth
- Internet upload / download
- Disk bandwidth

### 5. 基础环境自动化

实例启动后自动完成基础环境准备，目标开机即用：

- Ubuntu 24.04
- CUDA 13
- NGC PyTorch 容器
- Codex CLI
- Claude Code CLI
- S3-compatible 存储挂载
- 指定数据集导入本地盘

## MVP 边界

为了在 5 天内完成可演示版本，项目采用以下 MVP 策略：

- 至少 1 家供应商实现真实一键开机
- 其余供应商允许先以“统一纳管”方式接入
- MockProvider 作为演示与预算兜底方案
- 优先保证核心链路可跑通，不追求完整生产级调度系统

## 技术选型

### 前端

- Next.js
- TypeScript
- shadcn/ui
- Recharts

### 后端

- FastAPI
- Python 3.12
- SQLite
- aiosqlite

### 部署

- Docker Compose
- 火山引擎 ECS

## 架构概览

系统分为 4 层：

1. 前端页面层  
   负责 GPU 市场、配置页、实例列表、实例详情与监控展示。

2. 后端 API 层  
   提供认证、GPU 列表、实例管理、预算、测试报告等接口。

3. 服务层  
   负责实例生命周期推进、监控采集、预算控制、测试执行。

4. Provider 适配层  
   对接不同 GPU 供应商，统一抽象为标准接口。

## 计划中的目录结构

```text
schedule/
├── frontend/
│   └── src/
├── backend/
│   └── app/
├── docs/
└── README.md
```

更完整的目录结构与设计说明见：

- `docs/original requirement.md`
- `docs/superpowers/specs/2026-06-02-gpu-scheduling-platform-design.md`

## 需求映射

本项目围绕以下交付要求展开：

- 网页端一键开机
- 性能测试报告可展示 / 可导出
- 外网可达性验证
- 预装基础环境
- S3 自动挂载与数据导入
- Telemetry UI
- 端口转发与安全性说明

## 开发计划

### Day 1
- 跑通 Mock 全链路
- 确定数据模型与 API 结构
- 搭建前后端基础工程

### Day 2
- 接入至少 1 家真实 Provider 的 GPU 列表与实例创建
- 实现市场页与配置页

### Day 3
- 完成实例生命周期推进
- 完成 bootstrap / health check 方案
- 完成实例详情页初版

### Day 4
- 接入 Telemetry
- 完成性能测试与外网可达性测试
- 完成导出能力与预算控制

### Day 5
- 补 smoke test
- 修文档
- 准备演示与答辩材料

## 运行方式

当前仓库已经具备基础的 Docker Compose 部署方式，真实 Provider 的首选接入方案已固定为 `AutoDL`。

相关文档：

- `docs/provider-autodl.md`
- `docs/2026-06-04-implementation-day-plan.md`
- `docs/executor-system-prompt.md`

### 当前云端部署方式

项目当前可直接使用 Docker Compose 部署到云端实例：

```bash
docker compose up -d --build
```

部署配置已默认写入当前云服务器公网地址：

- 前端访问：`http://115.191.43.252:18761`
- 后端 API：`http://115.191.43.252:18760`

部署时请确保云安全组仅开放以下端口：

- `18760`：后端 API
- `18761`：前端页面

说明：

- 当前配置不依赖开放 `22` 端口给公网访问
- 浏览器端 API 地址已固定为公网地址 `115.191.43.252:18760`
- 后端 CORS 已允许 `http://115.191.43.252:18761`

如果使用根目录下的 `.env.example` 生成 `.env`，可再结合实际公网 IP 修改：

- `CORS_ORIGIN`
- `NEXT_PUBLIC_API_URL`

### 云端更新脚本

为方便频繁更新和重启，仓库已提供统一脚本：

```bash
chmod +x scripts/appctl.sh
```

常用命令：

```bash
# 拉取最新代码并重建前后端
./scripts/appctl.sh update

# 强制无缓存重建
./scripts/appctl.sh update --no-cache

# 用当前代码重启服务
./scripts/appctl.sh restart

# 查看服务状态
./scripts/appctl.sh status

# 查看日志
./scripts/appctl.sh logs backend
./scripts/appctl.sh logs frontend
```

建议你在云端实例的项目目录中始终通过这个脚本管理服务，避免手动拼接 `docker compose` 命令。

### 本地开发最小启动说明

1. 复制环境变量模板：

```bash
cp .env.example .env
```

2. 按实际情况修改 `.env` 中的关键字段：

- `JWT_SECRET`
- `CORS_ORIGIN`
- `NEXT_PUBLIC_API_URL`
- `AUTODL_API_KEY`（需要接入真实 Provider 时）

3. 使用 Docker Compose 启动：

```bash
docker compose up -d --build
```

4. 验证服务：

- 前端：`http://localhost:18761` 或你的公网地址
- 后端：`http://localhost:18760` 或你的公网地址

如果只是跑当前后端测试，重点环境变量是：

- `DATABASE_PATH`
- `JWT_SECRET`

## 环境变量

根目录提供了 `.env.example` 作为模板。

当前仓库中已经实际使用的环境变量如下：

```env
JWT_SECRET=
DATABASE_PATH=
DEFAULT_BUDGET=
EXCHANGE_RATE_USD_TO_CNY=
CORS_ORIGIN=
NEXT_PUBLIC_API_URL=
```

说明：

- `JWT_SECRET`：后端登录态签名密钥
- `DATABASE_PATH`：SQLite 文件路径，默认值为 `data/schedule.db`
- `DEFAULT_BUDGET`：预算默认值
- `EXCHANGE_RATE_USD_TO_CNY`：汇率换算默认值
- `CORS_ORIGIN`：后端允许的前端来源，多个值可用逗号分隔
- `NEXT_PUBLIC_API_URL`：前端请求后端 API 的地址

为接入首个真实 Provider `AutoDL`，项目内已经约定以下环境变量，应由执行模型在实现时接入 `backend/app/config.py`：

```env
PRIMARY_PROVIDER=autodl
AUTODL_API_BASE=https://api.autodl.com
AUTODL_API_KEY=
AUTODL_DEFAULT_IMAGE_UUID=
AUTODL_DEFAULT_CUDA_V_FROM=113
AUTODL_DEFAULT_GPU_AMOUNT=1
AUTODL_DEFAULT_SYSTEM_DISK_GB=0
AUTODL_DATA_CENTER_LIST=
```

说明：

- `PRIMARY_PROVIDER`：首选真实 Provider，当前固定为 `autodl`
- `AUTODL_API_BASE`：AutoDL API Host
- `AUTODL_API_KEY`：AutoDL 开发者 Token
- `AUTODL_DEFAULT_IMAGE_UUID`：创建实例时默认镜像
- `AUTODL_DEFAULT_CUDA_V_FROM`：最低 CUDA 驱动要求，例如 `113` 代表 `>= 11.3`
- `AUTODL_DEFAULT_GPU_AMOUNT`：默认 GPU 数量
- `AUTODL_DEFAULT_SYSTEM_DISK_GB`：系统盘扩容大小
- `AUTODL_DATA_CENTER_LIST`：可选地区列表，多个值建议用逗号分隔

如需具体接口映射和字段回填口径，请直接查看：

- `docs/provider-autodl.md`

## 常见问题

- `provider 未启用`
  - 通常是 `AUTODL_API_KEY` 未配置，或执行模型尚未把 AutoDL 配置接入 `backend/app/config.py` 与 `provider_registry.py`
- `CORS 报错`
  - 检查 `CORS_ORIGIN` 是否包含当前前端地址，例如 `http://localhost:18761` 或公网地址
- `前端 API 地址错误`
  - 检查 `NEXT_PUBLIC_API_URL` 是否指向正确的后端地址和端口
- `数据库初始化异常`
  - 检查 `DATABASE_PATH` 所在目录是否可写
- `真实 Provider 接口调用失败`
  - 优先检查 `AUTODL_API_BASE`、`AUTODL_API_KEY` 和镜像/规格配置；实现细节以 `docs/provider-autodl.md` 为准
- `destroy 返回成功但 AutoDL 侧未释放`
  - destroy 链路已真实验证（power_off → 轮询 shutdown → release）。正常路径远程释放成功，本地状态同步清理。如遇网络中断、API 超时或 release 被拒，代码记录 warning 后仍清理本地状态——此时需登录 AutoDL 控制台确认远端实例是否已释放。

## 风险与取舍

本项目的主要风险包括：

- 不同供应商 API 能力不一致
- 预算有限，无法长时间占用真实 GPU
- 外网直连与测试结果受供应商网络环境影响
- 跨云实例初始化与监控链路存在不确定性

因此项目采取以下取舍：

- 优先保证 1 家真实可用 Provider
- 其余 Provider 允许先纳管或 Mock
- 优先完成核心闭环，不展开复杂调度算法
- 测试结果以“可展示、可解释、可导出”为目标

## 非目标

当前 MVP 不重点覆盖以下内容：

- 多租户权限体系
- 复杂计费系统
- 生产级任务队列与分布式调度
- 大规模集群管理
- 完整前端自动化测试体系

## 后续规划

MVP 完成后，可继续扩展：

- 更多 Provider 接入
- 更强的预算与告警系统
- 更完整的实例管理能力
- 任务队列与异步执行框架
- 生产级监控与日志平台
- 更细粒度的权限与审计能力

## 说明

这是一个面向面试作业 / MVP 验证场景的项目仓库，强调：

- 核心能力闭环
- 工程取舍合理
- 可演示性
- 可继续扩展的架构设计

后续会随着开发进展补充：

- 实际运行截图
- API 示例
- Provider 接入结果
- 测试报告样例
- Demo 演示说明
