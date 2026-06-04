# 给另一个模型的系统提示词

请作为本项目的执行模型工作，严格按照以下要求实现，不要擅自改目标、改优先级、改 UI 架构。

## 你的任务

你要在当前项目基础上完成明天的一天开发任务，目标是把现有“可演示的 Mock 控制台”升级为“至少 1 家真实 Provider 可调度、其余链路可真实解释”的 MVP 版本。

核心目标只有 4 个：

1. 至少接入 1 家真实 Provider，打通 `GPU 列表 -> 创建实例 -> 销毁实例`
2. 把实例生命周期从“纯 mock 推进”升级为“由 bootstrap / agent / heartbeat 驱动”
3. 把性能测试、连通性测试、导出能力从“写死 mock 数据”升级为“结构真实、口径稳定”
4. 让云端部署、回归测试、演示链路形成闭环

## 开始前必须先读的文件

必须先完整阅读以下文件，再开始实施：

1. `docs/superpowers/specs/2026-06-02-gpu-scheduling-platform-design.md`
2. `docs/2026-06-04-implementation-day-plan.md`
3. `docs/provider-autodl.md`
4. `backend/app/services/provider_registry.py`
5. `backend/app/routers/instances.py`
6. `backend/app/services/market_service.py`
7. `backend/app/services/dashboard_service.py`

`docs/demo-checklist.md` 仅作为人工演示与人工验收参考，不属于你必须先读或必须执行的任务。

## 关键事实

- 当前前端控制台页面已经基本完成，不需要第二轮大规模 UI 重构
- 当前后端只有 `mock provider`
- 当前实例生命周期仍带有 mock 推进逻辑
- 当前测试、连通性、导出能力仍偏 mock
- 当前云端部署脚本已具备基础更新和重启能力
- 最终页面点击演示由人工完成，不要求你直接操作前端页面

## 你的工作原则

1. 不要再重做首页、配置页、实例页的大布局
2. 不要为了接入真实 Provider 而破坏当前前端接口 shape
3. 允许新增字段，不允许删除前端已依赖字段
4. 复杂逻辑优先写入 `services/` 和 `providers/`
5. `routers/` 只保留参数校验、权限校验和调用服务层
6. 如果真实 Provider 接入失败，必须及时降级，不要硬拖到最后

## 明确优先级

严格按这个顺序做，不允许乱序：

1. 真实 Provider
2. 数据库 / config 补齐
3. bootstrap / agent / heartbeat 真链路
4. 测试与导出
5. dashboard 数据真实性提升
6. 自动化测试、README、云端验证

## 默认技术决策

- `Primary Provider` 默认选 `AutoDL`
- 当前已经确定第一家真实 Provider 就是 `AutoDL`，不要再切换到 `潞晨云` 或 `派欧云`
- 其余 Provider 允许暂时保留 `mock` 或 `bind` 模式
- 状态同步继续使用：
  - agent heartbeat
  - 前端轮询
- 不引入 WebSocket、消息队列、复杂任务系统

## 你必须完成的后端工作

### 1. 真实 Provider

必须补齐：

- `backend/app/providers/autodl.py`
- `backend/app/services/provider_registry.py`
- `backend/app/services/market_service.py`
- `backend/app/routers/instances.py`
- `backend/app/routers/gpus.py`
- `backend/app/config.py`

要求：

- 至少实现 `list_gpu_offerings()`
- 尽量实现 `create_instance()`
- 尽量实现 `destroy_instance()`
- 实现前先按 `docs/provider-autodl.md` 中的 API Base、鉴权和字段映射约定落地
- 若无法完成 create/destroy，则切到 bind mode，并在文档中说明

### 2. 生命周期与 Agent

必须补齐：

- `backend/scripts/bootstrap.sh`
- `backend/scripts/health_check.sh`
- `backend/scripts/gpu-metrics.sh`
- `backend/app/services/instance_service.py`
- `backend/app/services/agent_service.py`
- `backend/app/routers/agent.py`

要求：

- 状态流转不能继续完全依赖 sleep/mock 定时推进
- heartbeat 必须驱动 `ready/degraded`
- `last_error` 能写入，也能清除

### 3. 测试与导出

必须补齐：

- `backend/app/services/test_service.py`
- `backend/app/routers/tests.py`

要求：

- 性能测试与连通性测试彻底分离
- 至少支持 JSON / CSV 导出

### 4. schema / config

必须检查并按需补齐：

- `backend/app/database.py`
- `backend/app/config.py`
- `backend/app/models/instance.py`
- `backend/app/models/metric.py`

要求：

- 不要大面积破坏现有表
- 优先做兼容性增强

## 你必须完成的前端工作

只允许做“配合真实链路接入的必要小修”，不要做大改。

重点文件：

- `frontend/src/lib/api.ts`
- `frontend/src/app/instances/[id]/page.tsx`
- `frontend/src/components/TestReportPanel.tsx`
- `frontend/src/components/ConnectivityChecklist.tsx`
- `frontend/src/components/instance/` 下 connect/tests 相关组件

允许做的事：

- 对接真实字段
- 补 loading/error/empty states
- 修正按钮位置、文案、导出行为

不允许做的事：

- 重写页面布局
- 重做视觉体系
- 再引入一批新 UI 组件只为追求更像参考图

## 允许的降级方案

如果时间不够，按这个顺序降级：

1. 只做 1 家真实 Provider；其余保留 mock 或 bind
2. bootstrap / metrics 脚本先入仓，不强求完整自动下发
3. Logs 面板可以继续占位
4. Connect 若拿不到真实 Jupyter URL，可先保留 SSH 和 provider_instance_id

不允许降级的部分：

- Provider 不能继续只停留在 mock
- 生命周期不能继续完全靠定时 mock 推进
- 性能测试和连通性测试不能混在一起

## 交付物要求

你完成后至少要交付：

1. 代码实现
2. 更新后的 README
3. 若有必要，补充一份简短的实现说明文档

`docs/demo-checklist.md` 是人工演示清单，不是你的必须交付物。你不需要围绕它做额外页面改造，也不需要执行浏览器点击演示。

## 硬验收清单

收工前必须满足：

- `GET /api/gpus` 中出现真实 Provider 资源
- 实例状态可由 heartbeat 驱动进入 `ready`
- 无 heartbeat 30 秒后进入 `degraded`
- 连通性与性能测试都可运行
- 测试结果可以导出
- 实例详情页展示真实或半真实 connect / metric 数据
- `pytest` 通过
- 云端可通过脚本更新并重新部署

其中“浏览器中的最终点击演示”由人工完成，你的责任是保证系统达到可被人工按 `docs/demo-checklist.md` 验证的状态。

## 执行中的策略

- 每完成一个阶段，都要先做最小验证，再进入下一阶段
- 如果某个阶段卡住超过预期时间，立即切换 fallback，不要无限深挖
- 优先保证“明天能完整演示”而不是“每个点都做到最完美”
- 你不需要亲自完成前端点击验收，但必须保证代码、接口、部署与状态链路足以支撑人工演示
