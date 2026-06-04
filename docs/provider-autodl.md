# AutoDL Provider 对接说明

## 1. 目的

这份文档用于给执行模型提供项目内统一口径，避免它在实现 `backend/app/providers/autodl.py` 时再次从零整理网页文档。

当前项目已确定：

- 第一家真实 Provider 固定为 `AutoDL`
- `PPIO`、`潞晨云` 等暂不作为明天的首接 Provider
- 若 `AutoDL` 的 `create/destroy` 最终无法打通，可降级为 `bind mode`

## 2. 本次 MVP 只做的能力

本次接入只要求覆盖最小闭环：

1. `list_gpu_offerings()`
2. `create_instance(gpu_offering_id, config)`
3. `destroy_instance(provider_instance_id)`

允许补充但不是首要目标：

- `get_instance_status(provider_instance_id)`
- `get_instance_snapshot(provider_instance_id)`
- provider 侧连接信息映射

## 3. API Base 与鉴权

- API Base: `https://api.autodl.com`
- 鉴权方式：请求头携带 `Authorization: <AUTODL_API_KEY>`
- Token 获取位置：AutoDL 控制台 -> 账号/设置 -> 开发者 Token

建议在项目配置中增加：

- `PRIMARY_PROVIDER=autodl`
- `AUTODL_API_BASE=https://api.autodl.com`
- `AUTODL_API_KEY=...`

## 4. 当前应优先使用的接口

### 4.1 创建实例

- 方法：`POST`
- 路径：`/api/v1/dev/instance/pro/create`

建议请求体最小集合：

```json
{
  "req_gpu_amount": 1,
  "expand_system_disk_by_gb": 0,
  "gpu_spec_uuid": "pro6000-p",
  "image_uuid": "image-xxxxxxxxx",
  "cuda_v_from": 113,
  "instance_name": "API创建的实例",
  "start_command": "sleep 1"
}
```

可选字段：

- `data_center_list`

成功响应中的 `data` 是实例 ID，例如：

```json
{
  "code": "Success",
  "data": "pro-76419909953e",
  "msg": ""
}
```

项目内建议映射：

- `provider_instance_id <- data`

### 4.2 获取实例状态

- 方法：`GET`
- 路径：`/api/v1/dev/instance/pro/status`

请求体核心字段：

```json
{
  "instance_uuid": "pro-76576c61fdf1"
}
```

成功时 `data` 为字符串状态，例如：

- `running`

项目内建议用途：

- provider 创建后用于轮询状态
- 后端实例状态机的辅助判断

### 4.3 获取实例详情

- 方法：`GET`
- 路径：`/api/v1/dev/instance/pro/snapshot`

请求体核心字段：

```json
{
  "instance_uuid": "pro-76576c61fdf1"
}
```

该接口返回的信息对本项目很重要，可能包含：

- `region_sign`
- `payg_price`
- `snapshot_gpu_alias_name`
- `ssh_command`
- `proxy_host`
- `root_password`
- `ssh_port`
- `jupyter_token`
- `jupyter_domain`
- `service_6006_domain`
- `service_6008_domain`

项目内建议用途：

- 补 `instances` 表中的连接字段
- 支撑 dashboard 的 `connect` 面板
- 在 provider create 成功后同步连接元信息

### 4.4 获取实例列表

- 方法：`POST`
- 路径：`/api/v1/dev/instance/pro/list`

请求体最小集合：

```json
{
  "page_index": 1,
  "page_size": 20
}
```

项目内建议用途：

- 作为调试和 bind mode 的辅助能力
- 在缺少单实例详情时辅助回查 provider_instance_id

### 4.5 获取账户余额

- 方法：`POST`
- 路径：`/api/v1/dev/wallet/balance`

不是主链路必需，但可用于：

- 后台诊断
- Provider 健康检查

### 4.6 获取私有镜像列表

- 方法：`POST`
- 路径：`/api/v1/dev/image/private/list`

项目内建议用途：

- 在配置中校验 `image_uuid`
- 后续支持用户选择镜像

## 5. 与项目 Provider 抽象的映射建议

### 5.1 `list_gpu_offerings()`

优先目标不是“完整复刻 AutoDL 所有规格”，而是尽快返回项目前端可消费的统一结构。

如果短时间内拿不到完整公共规格接口，可接受以下顺序：

1. 先实现一小组写死但真实可用的 `AutoDL` 规格映射
2. 确保 `provider="autodl"`、`gpu_spec_uuid`、`image_uuid`、`cuda_v_from` 可贯通
3. 后续再补真实规格自动发现

返回结构至少要能稳定映射：

- `provider`
- `provider_gpu_id` 或等价字段
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

建议把 AutoDL 侧创建所需但前端不会直接展示的字段放入 metadata：

- `gpu_spec_uuid`
- `image_uuid`
- `cuda_v_from`
- `data_center_list`
- `expand_system_disk_by_gb`

### 5.2 `create_instance(gpu_offering_id, config)`

建议流程：

1. 从 `gpu_offering` 或 metadata 中取到 `gpu_spec_uuid`
2. 从配置或默认值中取到 `image_uuid`
3. 组装 AutoDL create body
4. 调用 `/instance/pro/create`
5. 保存返回的 `provider_instance_id`
6. 立刻补一次 `status` 或 `snapshot`，回填连接信息

建议把以下字段回写到本项目实例记录：

- `provider_instance_id`
- `provider`
- `region`
- `hourly_price`
- `ssh_host`
- `ssh_port`
- `connect_url`
- `jupyter_url`
- `provider_status`

### 5.3 `destroy_instance(provider_instance_id)`

执行模型需要优先确认 AutoDL 是否有明确的 Pro 实例销毁接口。

如果文档或接口权限在实现当日仍不明确：

- 不要卡死在这里
- 最晚在第二阶段结束前切到 `bind mode`
- 在 README 和演示文档中明确说明：
  - 当前 AutoDL 已完成真实 `list/create`
  - `destroy` 若未打通则暂由纳管/人工释放兜底

## 6. dashboard / connect 字段建议

如果 `snapshot` 成功返回连接信息，建议优先映射：

- `ssh_host <- proxy_host`
- `ssh_port <- ssh_port`
- `connect_url <- ssh_command`
- `jupyter_url <- jupyter_domain`
- `hourly_price <- payg_price / 1000`
- `region <- region_sign`
- `gpu_model <- snapshot_gpu_alias_name`

如果接口仅返回域名且未带协议：

- `jupyter_domain`、`service_6006_domain`、`service_6008_domain` 默认按 `https://` 或文档给出的端口协议补全

## 7. 已知不确定点

以下点在真正编码前需要快速复核，但不应阻塞大方向：

- AutoDL 的完整 GPU 规格/公共镜像查询是否能完全满足市场页动态展示
- Pro 实例销毁接口是否已在当前权限下可用
- 某些详情接口是否使用 `GET` 但仍要求 JSON body

处理原则：

- 若接口文档已明确，按文档实现
- 若文档与实际请求方式冲突，优先以真实可调用结果为准
- 若 `list/create/destroy` 不能一次全部落地，优先保住 `list + create`

## 8. 实现优先级建议

执行模型应按下列顺序推进：

1. 在 `backend/app/config.py` 增加 AutoDL 配置项
2. 新建 `backend/app/providers/autodl.py`
3. 先打通 `create` 和最小字段映射
4. 再补 `status/snapshot` 连接信息
5. 再接入 `provider_registry` 和 `market_service`
6. 最后根据实际接口情况确认 `destroy` 或切换 `bind mode`

## 9. 对执行模型的明确要求

- 不要因为 AutoDL 字段名与本项目不同，就修改前端既有响应结构
- 优先把第三方差异收敛在 `providers/autodl.py`
- 不要把 AutoDL 的原始字段散落到多个 router
- 允许在 `metadata/raw` 中保留 provider 原始响应，方便排错
- 一旦确认某个接口当天无法稳定打通，立即按 fallback 方案降级，不要继续深挖到影响主链路
