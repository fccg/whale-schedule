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

当前 README 为开发前初稿，以下命令将在功能落地后补充：

- 本地开发启动命令
- Docker Compose 启动方式
- 环境变量说明
- 初始化数据库方式
- Mock 模式运行方式
- 真实 Provider 接入说明

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

## 环境变量

后续预计需要以下环境变量：

```env
JWT_SECRET=
DATABASE_URL=
AUTO_DL_API_KEY=
LUCHEN_API_KEY=
PAIO_API_KEY=
S3_ENDPOINT=
S3_ACCESS_KEY=
S3_SECRET_KEY=
S3_BUCKET=
EXCHANGE_RATE_API=
```

实际字段以后端实现为准。

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
