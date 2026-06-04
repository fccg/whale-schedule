# 2026-06-04 一天实现规划

## 1. 目标

这一天的目标不是继续做前端样式微调，而是把当前“已能演示的 Mock 控制台”升级为“至少 1 家真实 Provider 可调度、其余链路可真实解释”的 MVP 版本。

明天必须完成的成果只有 4 类：

1. 至少接入 1 家真实 Provider，打通 `GPU 列表 -> 创建实例 -> 销毁实例`
2. 把实例生命周期从“纯 mock 推进”升级为“由 bootstrap / agent / heartbeat 驱动”
3. 把性能测试、连通性测试、导出能力从“写死 mock 数据”升级为“结构真实、口径稳定”
4. 让云端部署、回归测试、演示话术形成闭环

这份规划默认由另一个 LLM 模型执行，因此会明确写出：

- 要改哪些文件
- 每一步先做什么、后做什么
- 哪些地方允许降级
- 每个阶段的验收标准是什么
- 如果中途卡住该如何 fallback

## 2. 当前项目状态

### 2.1 已完成

- 前端控制台式页面已就位：
  - `frontend/src/app/page.tsx`
  - `frontend/src/app/gpus/[id]/configure/page.tsx`
  - `frontend/src/app/instances/page.tsx`
  - `frontend/src/app/instances/[id]/page.tsx`
- 市场 / 开机 / 实例仪表盘所需聚合接口已存在：
  - `backend/app/services/market_service.py`
  - `backend/app/services/dashboard_service.py`
- 实例主链路已接入 provider registry：
  - `backend/app/routers/instances.py`
  - `backend/app/services/provider_registry.py`
- 云端部署可用：
  - `docker-compose.yml`
  - `frontend/Dockerfile`
  - `backend/app/main.py`
  - `scripts/appctl.sh`

### 2.2 当前缺口

#### A. 真实 Provider 还没接

- `backend/app/providers/` 当前只有：
  - `base.py`
  - `mock.py`
- `backend/app/services/provider_registry.py` 只注册了 `mock`

#### B. 生命周期仍依赖 mock 推进

- `backend/app/services/instance_service.py` 仍是本地模拟步骤推进
- 实例侧脚本缺失：
  - `backend/scripts/bootstrap.sh`
  - `backend/scripts/health_check.sh`
  - `backend/scripts/gpu-metrics.sh`

#### C. 测试与导出还是 mock

- `backend/app/routers/tests.py` 目前写入的是假结果
- `tests/export` 目前还不是完整可交付导出能力

#### D. dashboard 仍部分依赖 fallback mock

- `backend/app/services/dashboard_service.py` 中 runtime / latest_metric / history / connect 仍有较多 fallback 逻辑

#### E. 数据模型还未完全支撑真实运行

- `backend/app/database.py` 尚未体现 `provider_configs`
- `instances` / `metrics` 缺少部分 connect / runtime / provider metadata 字段

## 3. 明天的总原则

### 3.1 优先级原则

明天严格按照下面的优先级推进：

1. `真实 Provider`
2. `真实生命周期`
3. `真实测试与导出`
4. `真实 dashboard 数据`
5. `补文档和回归`

### 3.2 不做事项

明天不要做这些事情：

- 不再进行第二轮大面积 UI 重构
- 不做 WebSocket
- 不做分页、搜索优化、动画优化
- 不追求 3 家 Provider 都实现调度模式
- 不做生产级多租户、复杂调度算法、任务队列

### 3.3 默认技术决策

- `Primary Provider` 默认选 `AutoDL`
- 当前已明确决定：第一家真实 Provider 固定为 `AutoDL`，明天不再切换到 `潞晨云` 或 `派欧云`
- 其余 Provider 明天统一保留 `mock` 或 `bind 纳管` 兜底
- 状态同步继续使用：
  - agent heartbeat
  - 前端轮询
- 不上消息队列

## 4. 给执行模型的硬约束

另一个 LLM 模型执行时，必须遵守以下约束：

1. 不允许为了接入真实 Provider 而破坏当前前端页面结构
2. `GET /api/gpus`、`GET /api/gpus/{id}/launch`、`GET /api/instances/{id}/dashboard` 的响应 shape 尽量保持兼容
3. 允许新增字段，不允许随意删除前端已依赖字段
4. 所有新增后端逻辑必须优先放到 `services/` 或 `providers/`，不要把复杂逻辑塞回 `routers/`
5. 如果真实 Provider 接入失败，最晚在下午第二阶段结束前切换为“1 家 bind 纳管 + mock 演示兜底”方案，不要拖到晚上

## 5. 明天的详细执行清单

下面按时间段拆解，每一段都写出目标、操作文件、输出结果、验收方式。

---

## 6. 09:00 - 09:45：环境确认与真实 Provider 预研

### 目标

- 确认明天到底接哪一家真实 Provider
- 把执行模型的起手式固定下来，避免它一上来盲改代码

### 必做事项

1. 阅读并确认：
   - `docs/superpowers/specs/2026-06-02-gpu-scheduling-platform-design.md`
   - `docs/provider-autodl.md`
   - `backend/app/providers/base.py`
   - `backend/app/services/provider_registry.py`
   - `backend/app/routers/gpus.py`
   - `backend/app/routers/instances.py`
2. 如果仓库里已有任一真实 Provider 草稿文件，优先复用
3. 如果没有真实 Provider 实现，则创建：
   - `backend/app/providers/autodl.py`
4. 确认真实 Provider 所需配置项，统一放到：
   - `backend/app/config.py`
   - `.env.example` 或 README 对应部署说明中

### 输出物

- 一个明确结论：
  - “明天使用 AutoDL 作为唯一真实调度 Provider”
- 一份项目内 AutoDL 对接说明：
  - `docs/provider-autodl.md`
- 一份真实 Provider 所需环境变量清单

### 验收标准

- 执行模型在这个阶段结束时，能够明确回答：
  - 接哪一家
  - 用什么 API Key / Endpoint
  - `list/create/destroy` 这 3 个动作如何映射

### 如果卡住

- 如果 45 分钟内无法拿到任何可调用 API 文档或认证方式
- 立刻切换策略：
  - Provider 保持 mock
  - 明天主目标改为完成 `bind_instance + bootstrap + agent + dashboard 真链路`

---

## 7. 09:45 - 11:30：接入真实 Provider 主链路

### 目标

- 把 Provider 抽象从“只有 mock”变成“真实 provider + mock fallback”

### 必改文件

- `backend/app/providers/autodl.py`
- `backend/app/services/provider_registry.py`
- `backend/app/services/market_service.py`
- `backend/app/routers/instances.py`
- `backend/app/routers/gpus.py`
- `backend/app/config.py`

### 具体任务

#### 7.1 新建真实 Provider 实现

在 `backend/app/providers/autodl.py` 中：

- 实现 `BaseProvider`
- 至少实现 3 个方法：
  - `list_gpu_offerings()`
  - `create_instance(gpu_offering_id, config)`
  - `destroy_instance(provider_instance_id)`
- 将第三方字段映射到平台字段：
  - `provider`
  - `gpu_family`
  - `gpu_model`
  - `vram_gb`
  - `cpu_cores`
  - `memory_gb`
  - `disk_gb`
  - `price_per_hour`
  - `currency`
  - `region`
  - `available`

#### 7.2 升级 provider registry

在 `backend/app/services/provider_registry.py` 中：

- 不再写死只注册 `mock`
- 改为按环境变量决定 active providers
- 推荐接口：
  - `get_provider(name: str)`
  - `get_active_providers()`
  - `is_provider_enabled(name: str)`

推荐默认策略：

- 若真实 Provider 配置齐全，则注册：
  - `autodl`
  - `mock`
- 若配置缺失，则只注册：
  - `mock`

#### 7.3 升级 market 聚合

在 `backend/app/services/market_service.py` 中：

- 把当前 `seed_mock_offerings()` 驱动的列表逻辑改为：
  - 先拉真实 provider 列表
  - 再拉 mock fallback
  - 最终统一 enrich
- 把 `PROVIDER_META` 从单一 `mock` 扩展为可覆盖多 provider
- `filters.providers` 不能继续只返回 `["mock"]`

#### 7.4 升级实例创建与销毁

在 `backend/app/routers/instances.py` 中：

- 继续保持通过 provider registry 调用
- 但要增加更明确的错误处理：
  - provider 未启用
  - provider create 失败
  - provider destroy 失败
- `bind_instance` 必须校验：
  - `body.provider` 与 `gpu_offering.provider` 一致

### 输出物

- 真实 Provider 可被 registry 识别
- 市场页可看到真实 Provider 资源
- 创建实例时能走真实 Provider
- 删除实例时能走真实 Provider

### 验收标准

- `GET /api/gpus` 至少返回一条 `provider != "mock"` 的资源
- `POST /api/instances` 成功返回真实 `provider_instance_id`
- `DELETE /api/instances/{id}` 能成功调用 provider 销毁

### 失败时的 fallback

如果真实 provider 只能实现 `list`，无法实现 `create/destroy`：

- 明确转为“纳管模式”
- 保留：
  - `list_gpu_offerings()`
  - `bind_instance()`
- 通过文档解释：
  - 当前该 Provider 处于 `bind mode`
  - 架构已经预留 `BaseProvider`

---

## 8. 11:30 - 12:30：数据库与配置模型补齐

### 目标

- 让 schema 至少具备支撑真实 provider / connect / runtime 的最低能力

### 必改文件

- `backend/app/database.py`
- `backend/app/models/instance.py`
- `backend/app/models/metric.py`
- `backend/app/config.py`

### 具体任务

#### 8.1 补 schema

优先考虑最小必要字段，不要大改全表。

建议新增或补齐：

- `provider_configs`
  - `provider`
  - `api_base`
  - `enabled`
  - `created_at`
- `instances`
  - `display_name`
  - `hourly_price`
  - `region`
  - `ssh_host`
  - `ssh_port`
  - `connect_url`
- `metrics`
  - 若不方便增列，则继续复用 `gpu_json`
  - 但需要确保后端 dashboard 能把 runtime/connect 信息拼完整

#### 8.2 配置统一入口

在 `backend/app/config.py` 中增加：

- `PRIMARY_PROVIDER`
- `AUTODL_API_BASE`
- `AUTODL_API_KEY`
- `ALLOW_ORIGINS`
- 其他 provider 的占位配置

### 输出物

- 数据模型不再只服务 mock 演示
- 后端服务能通过 config 识别是否启用真实 provider

### 验收标准

- 新字段不会破坏现有启动
- 本地数据库首次初始化正常
- 旧实例记录还能正常读取

---

## 9. 13:30 - 15:30：补齐 bootstrap / health check / metrics agent

### 目标

- 把实例生命周期从“服务端 sleep 推进”升级为“实例自举 + 心跳 + 指标上报”

### 必建文件

- `backend/scripts/bootstrap.sh`
- `backend/scripts/health_check.sh`
- `backend/scripts/gpu-metrics.sh`

### 必改文件

- `backend/app/services/instance_service.py`
- `backend/app/services/agent_service.py`
- `backend/app/routers/agent.py`

### 具体任务

#### 9.1 新建 `bootstrap.sh`

脚本职责：

1. 安装 Docker / NVIDIA Container Toolkit（如果环境需要）
2. 拉起容器环境
3. 写入 agent token
4. 启动指标采集与心跳上报
5. 执行基础健康检查
6. 将状态上报到平台

要求：

- 明确返回码
- 每一步有日志输出
- 失败时写清楚哪一步失败

#### 9.2 新建 `health_check.sh`

脚本至少检查：

- `nvidia-smi` 是否可用
- GPU 数量是否大于 0
- Docker 是否可用
- 目标镜像或容器是否能启动
- 网络是否基本可达

输出必须便于后端解析，可以是：

- JSON
- 或一行一项的 shell key-value

#### 9.3 新建 `gpu-metrics.sh`

脚本采集：

- CPU 占用
- 内存占用
- 磁盘使用
- 上下行带宽
- 每张 GPU 的：
  - `utilization`
  - `vram_percent`
  - `vram_used_gb`
  - `vram_total_gb`
  - `temp_c`
  - `power_w`

输出格式必须与 `backend/app/services/agent_service.py` 当前消费逻辑对齐

#### 9.4 改 `instance_service.py`

当前服务若仍有“定时 mock 推进 ready”的逻辑，明天必须改掉：

- 创建实例后只负责写入初始状态：
  - `provisioning`
- 后续状态由以下事件推进：
  - bootstrap 开始
  - health check 成功
  - agent heartbeat 到达
  - health check 失败
  - heartbeat 超时

建议状态流转：

- `provisioning`
- `bootstrapping`
- `testing`
- `ready`
- `degraded`
- `failed`
- `destroyed`

#### 9.5 改 `agent_service.py`

必须确认以下逻辑：

- heartbeat 按规范读取 `gpus[]`
- `last_error` 可被清空
- 30 秒无 heartbeat 自动进入 `degraded`
- heartbeat 恢复后回到 `ready`

### 输出物

- 三个脚本存在且可执行
- agent/heartbeat 能驱动状态变化

### 验收标准

- 手动调用 agent heartbeat 后，实例状态会变化
- 没 heartbeat 时，实例会进入 `degraded`
- 恢复 heartbeat 后，实例可回到 `ready`

### 如果卡住

如果真实实例侧脚本当天无法完整下发到云端：

- 至少把三份脚本写出来并纳入仓库
- 后端状态机按真实事件驱动改好
- 演示时可人工触发 agent API 模拟脚本结果

---

## 10. 15:30 - 17:00：升级测试、连通性和导出能力

### 目标

- 保持当前实例页结构不变
- 让 Tests tab 从“假按钮 + 假数据”升级为“可解释结果 + 可导出”

### 必改文件

- `backend/app/routers/tests.py`
- `backend/app/services/test_service.py`（新建）
- `frontend/src/lib/api.ts`
- `frontend/src/components/TestReportPanel.tsx`
- `frontend/src/components/ConnectivityChecklist.tsx`

### 具体任务

#### 10.1 新建测试服务层

在 `backend/app/services/test_service.py` 中拆出：

- `run_perf_test(instance)`
- `run_connectivity_test(instance)`
- `export_test_results(instance_id, format)`

要求：

- `perf` 与 `connectivity` 逻辑彻底分离
- `routers/tests.py` 不再直接写 mock 数据

#### 10.2 导出能力

至少支持：

- `JSON`
- `CSV`

导出内容至少覆盖：

- 测试时间
- 指标名称
- 指标值
- 单位
- 是否通过
- 对应实例

#### 10.3 前端对接

- `TestReportPanel.tsx` 只负责性能测试
- `ConnectivityChecklist.tsx` 只负责外网可达性
- `api.ts` 新增导出 API
- 如果后端支持不同 `Content-Type`，前端要能正确下载文件

### 输出物

- 可重新运行性能测试
- 可重新运行连通性测试
- 可导出结果

### 验收标准

- 页面按钮位置正确
- 运行结果可在页面看到
- 导出文件能下载并打开

---

## 11. 17:00 - 18:30：让 dashboard 尽量使用真实数据

### 目标

- 把实例详情页从“主要靠 fallback mock 填满”转为“真实数据优先、mock 仅兜底”

### 必改文件

- `backend/app/services/dashboard_service.py`
- `frontend/src/lib/api.ts`
- `frontend/src/app/instances/[id]/page.tsx`
- `frontend/src/components/instance/ConnectPanel.tsx`（如果已有）
- `frontend/src/components/instance/LogsPanel.tsx`（如果已有）

### 具体任务

#### 11.1 改 dashboard 聚合

在 `backend/app/services/dashboard_service.py` 中：

- `runtime` 优先来自真实 metrics / instance 字段
- `connect` 优先来自真实实例连接信息
- `tests_summary` 与 `connectivity_summary` 使用真实库数据
- `metric_history` 若不足则保留 fallback，但必须标清楚是 fallback

#### 11.2 前端细化

如果当前前端只展示静态 connect 信息，要改为读取真实 payload：

- `jupyter_url`
- `ssh_host`
- `ssh_port`
- `docker_image`
- `env`
- `command_preview`

### 输出物

- 实例详情页中的 Connect / Telemetry / Tests 不再严重依赖假数据

### 验收标准

- 页面能展示真实心跳或真实测试记录
- 没数据时 fallback 行为稳定，不报错

---

## 12. 18:30 - 20:00：补测试、回归、云端验证

### 目标

- 把今天的改动用自动化和云端演示都跑一遍

### 必做文件

- `backend/tests/test_providers.py`
- `backend/tests/test_dashboard.py`
- `backend/tests/test_export.py`
- `backend/tests/test_instance_service.py`
- `README.md`

### 具体任务

#### 12.1 后端测试

至少新增以下测试：

- provider registry 选择逻辑
- 真实 provider 的字段映射逻辑
- dashboard 聚合接口在有数据和无数据时的返回
- 测试导出接口返回 JSON / CSV
- degraded 自动检测与恢复

#### 12.2 README 收口

把以下内容补进 README：

- 真实 Provider 环境变量
- 云端更新命令：
  - `./scripts/appctl.sh update`
  - `./scripts/appctl.sh restart`
- 常见错误：
  - provider 未启用
  - CORS
  - 前端 API 地址错误

#### 12.3 云端验证

在云端执行：

```bash
./scripts/appctl.sh update --no-cache
./scripts/appctl.sh status
./scripts/appctl.sh logs backend
./scripts/appctl.sh logs frontend
```

然后浏览器验证：

- `http://115.191.43.252:18761`

至少走通：

1. 登录
2. 看 GPU 列表
3. 创建实例
4. 查看实例详情
5. 跑性能测试
6. 跑外网可达性测试
7. 导出结果
8. 销毁实例

### 输出物

- 自动化测试通过
- 云端演示链路可复现

### 验收标准

- `pytest` 通过
- 前端构建通过
- 云端能完整演示

---

## 13. 20:00 - 20:30：答辩版收口

### 目标

- 把“做成了什么”和“没做成但架构已预留什么”整理清楚

### 必做事项

在 `docs/` 下新增一份简短答辩材料，建议命名：

- `docs/demo-checklist.md`

内容包括：

1. 当前真实完成项
2. 哪一家 Provider 已完成真实调度
3. 哪些 Provider 当前是 bind / mock 兜底
4. 如何演示完整链路
5. 如果 API 文档追问，如何解释架构可扩展性

### 验收标准

- 演示前 3 分钟内能快速看完
- 别的模型或人工都能照着演示

## 14. 明天必须新增或重点修改的文件清单

### 后端必须新增

- `backend/app/providers/autodl.py`
- `backend/app/services/test_service.py`
- `backend/scripts/bootstrap.sh`
- `backend/scripts/health_check.sh`
- `backend/scripts/gpu-metrics.sh`
- `backend/tests/test_dashboard.py`
- `backend/tests/test_export.py`
- `backend/tests/test_instance_service.py`

### 后端重点修改

- `backend/app/config.py`
- `backend/app/database.py`
- `backend/app/services/provider_registry.py`
- `backend/app/services/market_service.py`
- `backend/app/services/dashboard_service.py`
- `backend/app/services/instance_service.py`
- `backend/app/services/agent_service.py`
- `backend/app/routers/gpus.py`
- `backend/app/routers/instances.py`
- `backend/app/routers/tests.py`
- `backend/app/routers/agent.py`

### 前端重点修改

- `frontend/src/lib/api.ts`
- `frontend/src/app/instances/[id]/page.tsx`
- `frontend/src/components/TestReportPanel.tsx`
- `frontend/src/components/ConnectivityChecklist.tsx`
- `frontend/src/components/instance/*` 中与 connect/tests 相关的组件

### 文档重点修改

- `README.md`
- `docs/demo-checklist.md`
- `docs/provider-autodl.md`

## 15. 给执行模型的明确实施顺序

另一个 LLM 模型必须按下面顺序执行，不允许乱序：

1. 读设计文档与现有 provider / router / service
2. 先做真实 Provider 接入
3. 再做数据库 / config 补齐
4. 再做 bootstrap / agent / heartbeat 真链路
5. 再做测试与导出
6. 再做 dashboard 数据真实性提升
7. 最后做测试、README、云端验证

原因：

- 如果先改 dashboard 或前端，会继续依赖 mock
- 如果先补测试再改 provider，测试会重写两遍
- 只有 provider 和状态机先稳定，后续功能才不会返工

## 16. 明天的硬验收清单

明天收工前，必须全部满足：

- `GET /api/gpus` 中出现真实 Provider 资源
- 能从前端成功一键开机至少 1 次
- 实例状态可由 heartbeat 驱动进入 `ready`
- 无 heartbeat 30 秒后进入 `degraded`
- 连通性与性能测试都可运行
- 测试结果可以导出
- 实例详情页展示真实或半真实 connect / metric 数据
- `pytest` 通过
- 云端可通过脚本更新并重新部署

## 17. 允许的降级方案

如果明天时间不足，允许按下面顺序降级，但必须记录在 README 或 docs 中：

1. 只做 1 家真实 Provider；其余全部保留 mock 或 bind
2. bootstrap 脚本先入仓，不要求完全自动下发
3. dashboard 的 Logs 可以继续占位
4. Connect 若拿不到真实 Jupyter URL，可先保留 SSH 字段和 provider_instance_id

不允许降级的部分：

- Provider 抽象不能继续只停留在 mock
- 状态机不能继续完全靠 sleep/定时推进
- 性能测试与连通性测试不能混在一个逻辑里

## 18. 交接说明

这份计划是给另一个模型直接执行的。

执行模型开始前，应该先读：

1. `docs/superpowers/specs/2026-06-02-gpu-scheduling-platform-design.md`
2. `docs/2026-06-04-implementation-day-plan.md`
3. `docs/provider-autodl.md`
4. `backend/app/services/provider_registry.py`
5. `backend/app/routers/instances.py`
6. `backend/app/services/market_service.py`
7. `backend/app/services/dashboard_service.py`

执行模型完成后，应该至少新增一个总结文档：

- `docs/demo-checklist.md`

用于你自己演示和复盘。
