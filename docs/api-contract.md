# API Contract

GPU Scheduling Platform 的 API 约定文档。面向前后端协作、评审和后续扩展。

所有内容基于当前代码实现，不描述不存在的能力。

---

## 1. 设计目标

- **统一错误格式**：所有业务错误通过 `HTTPException` + `detail` 字典返回，前端可按 `error` 码做分支处理
- **最小抽象**：不在成功响应外包装统一 envelope，各接口按语义返回最直接的数据结构
- **REST-light**：不追求严格的 RESTful 资源嵌套，优先保证前端调用简洁

## 2. 成功响应约定

- 成功响应的 HTTP 状态码主要为 `200`
- 响应体直接返回业务数据，顶层无 `code` / `data` / `message` wrapper
- 典型结构为单资源对象、列表对象、或 `{"status": "ok"}` 确认

示例：

```json
// 登录成功 (200)
{"token": "eyJ...", "user": {"id": "u1", "username": "demo"}}

// 查询实例详情 (200)
{"instance": {...}, "metrics": {...}}

// 删除实例 (200)
{"status": "destroyed"}

// Agent heartbeat (200)
{"status": "ok"}

// 健康检查 (200)
{"status": "ok"}
```

## 3. 错误响应约定

**业务错误：** 所有 router 层业务错误通过 FastAPI `HTTPException` 抛出，响应体结构为：

```json
{
  "detail": {
    "error": "<ERROR_CODE>",
    "message": "<human-readable description>"
  }
}
```

`error` 字段为大写 snake_case 错误码，适合前端 `if (error === "NOT_FOUND")` 分支处理。`message` 字段为人可读描述，可直接展示或用于调试。

**基础设施错误：** 全局异常处理器捕获的 ProviderError 和未处理异常返回顶层格式（无 `detail` 包装）：

```json
{"error": "PROVIDER_ERROR", "message": "autodl: HTTP 500: ..."}
{"error": "INTERNAL_ERROR", "message": "An unexpected error occurred"}
```

> **已知差异：** 全局异常处理器返回顶层 `error` / `message`，而业务 HTTPException 返回 `detail.error` / `detail.message`。这是因为 FastAPI 对 `HTTPException` 自动包装 `detail` 字段，而自定义 `JSONResponse` 直接写入顶层。当前前端 `api.ts` 的 `request()` 方法对两类格式均做了兼容处理，不需在此文档覆盖范围内统一。

## 4. 错误码与 HTTP 状态码映射

以下所有错误码均来自当前真实代码：

| HTTP 状态码 | 错误码 | 含义 | 出现位置 |
|---|---|---|---|
| 400 | `VALIDATION` | 请求参数不合法 | auth, agent |
| 400 | `PROVIDER_DISABLED` | 指定 provider 未启用 | instances |
| 400 | `PROVIDER_MISMATCH` | bind 操作中 provider 不匹配 | instances |
| 400 | `INVALID_TYPE` | 测试类型不合法 | tests |
| 400 | `INVALID_FORMAT` | 导出格式不合法 | tests |
| 401 | `INVALID_CREDENTIALS` | 用户名或密码错误 | auth |
| 403 | `FORBIDDEN` | agent_token 验证失败 | agent |
| 404 | `NOT_FOUND` | 资源不存在（实例/GPU offering） | instances, tests, gpus |
| 409 | `CONFLICT` | 用户名已存在 | auth |
| 422 | `PROVIDER_WALLET_INSUFFICIENT` | Provider 钱包余额不足 | instances |
| 422 | `PROVIDER_BUDGET_EXCEEDED` | Provider 内部额度不足 | instances |
| 422 | `NOT_READY` | 实例状态不允许操作（如未 ready 时触发测试） | tests |
| 502 | `PROVIDER_ERROR` | Provider 调用失败或返回异常 | instances, 全局处理器 |
| 500 | `INTERNAL_ERROR` | 未预期的内部错误 | 全局异常处理器 |

## 5. 关键接口示例

以下示例基于当前代码真实请求/响应结构。

### 5.1 登录 — `POST /api/auth/login`

```
Request:
POST /api/auth/login
Content-Type: application/json

{"username": "demo", "password": "..."}
```

```
Success (200):
{
  "token": "eyJ...",
  "user": {"id": "u1", "username": "demo", ...}
}
```

```
Failure (401):
{
  "detail": {
    "error": "INVALID_CREDENTIALS",
    "message": "Invalid username or password"
  }
}
```

### 5.2 启动页详情 — `GET /api/gpus/{offering_id}/launch`

需要 Bearer token 认证。

```
Success (200):
{
  "offering": { "id": "autodl-rtx4090-1", "provider": "autodl", ... },
  "templates": [...],
  "defaults": {
    "template_id": "autodl-pytorch-2-0-cuda11-8",
    "disk_gb": 250,
    "duration_h": 6
  },
  "funding": {
    "provider": "autodl",
    "estimated_total": 19.2,
    "wallet_balance": 15.36,
    "wallet_currency": "CNY",
    "provider_budget_enabled": true,
    "provider_budget_total": 100.0,
    "provider_budget_remaining": 82.4,
    "effective_available": 15.36,
    "limiting_factor": "wallet"
  },
  "budget": {
    "remaining_budget": 82.4,
    "estimated_total": 19.2,
    "price_per_hour": 3.2
  },
  "recommended_config": {
    "template_id": "autodl-pytorch-2-0-cuda11-8",
    "template": "cuda11.8-cudnn8-devel-ubuntu20.04-py38-torch2.0.0",
    "image_uuid": "base-image-l2t43iu6uk",
    "disk_gb": 250,
    "duration_h": 6
  }
}
```

说明：

- `funding.wallet_balance` 是 Provider 实时钱包余额
- `funding.provider_budget_remaining` 是平台对该 Provider 的内部额度剩余，未配置时为 `null`
- AutoDL 启动页应以 `funding` 为主；`budget` 仅为兼容字段
- AutoDL 的 `templates` 项使用官方基础镜像做底层数据源，前端展示名与真实 `image_uuid` 一一绑定

### 5.3 创建实例 — `POST /api/instances`

需要 Bearer token 认证。

```
Request:
POST /api/instances
Authorization: Bearer <token>
Content-Type: application/json

{
  "gpu_offering_id": "autodl-rtx4090-1",
  "template": "cuda11.8-cudnn8-devel-ubuntu20.04-py38-torch2.0.0",
  "image_uuid": "base-image-l2t43iu6uk",
  "disk_gb": 200,
  "duration_h": 1
}
```

```
Success (200):
{
  "instance": {
    "id": "uuid-...",
    "status": "provisioning",
    "provider": "autodl",
    ...
  },
  "estimated_cost": 3.20,
  "funding": {
    "provider": "autodl",
    "estimated_total": 3.20,
    "wallet_balance": 15.36,
    "wallet_currency": "CNY",
    "provider_budget_enabled": true,
    "provider_budget_total": 100.0,
    "provider_budget_remaining": 79.2,
    "effective_available": 15.36,
    "limiting_factor": "wallet"
  }
}
```

```
Failure — 钱包余额不足 (422):
{
  "detail": {
    "error": "PROVIDER_WALLET_INSUFFICIENT",
    "message": "AutoDL wallet balance is insufficient"
  }
}

Failure — 平台内部额度不足 (422):
{
  "detail": {
    "error": "PROVIDER_BUDGET_EXCEEDED",
    "message": "Estimated cost exceeds platform AutoDL budget"
  }
}

Failure — Provider 异常 (502):
{
  "detail": {
    "error": "PROVIDER_ERROR",
    "message": "Provider failed to create instance: ..."
  }
}
```

### 5.4 实例 Dashboard — `GET /api/instances/{instance_id}/dashboard`

需要 Bearer token 认证。

```
Request:
GET /api/instances/<id>/dashboard
Authorization: Bearer <token>
```

```
Success (200):
{
  "instance": { "id": "...", "status": "ready", ... },
  "offering": { "gpu_model": "RTX 4090", ... },
  "runtime": { "uptime_seconds": 3600, "gpus": [...], ... },
  "latest_metric": { "cpu_percent": 45.2, "gpu_util_percent": 92.1, ... },
  "metric_history": [...],
  "connect": { "ssh_host": "...", "jupyter_url": "...", ... },
  "connectivity_summary": [...],
  "tests_summary": [...]
}
```

无真实 metrics 时，`latest_metric` 使用 `_mock_latest_metric()` 回退，`metric_history` 使用 `_mock_history()` 回退。

```
Failure (404):
{
  "detail": {
    "error": "NOT_FOUND",
    "message": "Instance not found"
  }
}
```

### 5.5 触发性能测试 — `POST /api/instances/{instance_id}/tests`

实例必须处于 `ready` 状态。

```
Request:
POST /api/instances/<id>/tests
Authorization: Bearer <token>

{"type": "perf"}
```

```
Success (200):
{
  "test_run_id": "uuid-...",
  "status": "completed",
  "results": [
    {"test_run_id": "...", "metric_name": "GPU Memory Bandwidth", "value": null, "unit": "GB/s", "passed": 0},
    ...
  ]
}
```

```
Failure — 实例未就绪 (422):
{
  "detail": {
    "error": "NOT_READY",
    "message": "Instance must be in ready state"
  }
}
```

### 5.6 Agent Heartbeat — `POST /api/agent/heartbeat`

无需 Bearer token，通过 `agent_token` 验证。

```
Request:
POST /api/agent/heartbeat
Content-Type: application/json

{
  "agent_token": "<token>",
  "instance_id": "<id>",
  "bootstrap_status": "running",
  "bootstrap_step": 3,
  "bootstrap_total": 6,
  "cpu_percent": 45.2,
  "gpus": [{"utilization": 92.1, "vram_percent": 64.0}]
}
```

```
Success (200):
{"status": "ok"}

Failure — token 无效 (403):
{
  "detail": {
    "error": "FORBIDDEN",
    "message": "Invalid agent token"
  }
}
```

## 6. 当前边界与非目标

- **未使用 Pydantic 的 JSON Schema 自动验证错误** — FastAPI 的请求体校验失败会返回其内置格式（`detail: [{loc, msg, type}]`），与本文档定义的业务错误格式不同。当前未自定义校验错误处理器。
- **Agent 端点无 Bearer 认证** — heartbeat 和 health-check 使用 `agent_token` 字段验证，而非 Authorization header。这是刻意的设计选择，因为 Agent 运行在实例内，token 通过创建实例时下发。
- **测试结果导出不经由统一 JSON wrapper** — CSV 导出返回 `text/csv` 原始内容，JSON 导出返回含 `results` / `format` / `instance_id` 的字典，与普通查询接口格式不同。
- **healthz / readyz 端点独立于业务 API** — 不要求认证，不在 `/api/` 前缀下，格式为 `{"status": "ok"}`。
- **不做版本化 URL** — 当前所有接口无 `/v1/` 前缀。如需 API 版本演进，建议在下一步引入 `/api/v1/` 并保留 `/api/` 别名。
