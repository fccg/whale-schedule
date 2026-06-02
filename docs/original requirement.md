Take-home-exam 大作业（预计需5天完成，略有难度）

背景与需求

• 背景：我们同事经常需要开 GPU。

• 需求：做一个公司内部的「GPU 调度平台」，整体体验对标 Vast.ai。

• (option)：slurm 调度

⚠️ 请务必认真调研并实操 vast.ai，理解其关键流程：资源展示 → 选择配置 → 一键开机 → 实例可用性与监控。

参考链接：

- Vast.ai 官网: http://vast.ai

- Vast.ai | Console: https://cloud.vast.ai/

目标与范围

GPU 来源（至少 3 家，跨供应商统一调度）

• AutoDL

• 潞晨云

• 派欧云

• 或其他中国云平台

GPU 型号（固定 3 种）

• A100

• H 卡

• 6090

预算

💰 100 元人民币（可报销，算力平台不限；如不足可联系增加）

交付物：网页端「一键开机」+ 实例要求

1) 性能测试报告（必须可展示 / 可导出）

• Per-GPU memory bandwidth、Per-GPU NVLink bandwidth

• PCIe lanes 数量、Per-GPU PCIe bandwidth

• Internet upload / download speed

• Disk bandwidth

2) 外网可达性（直连主站，不走镜像）

• Hugging Face

• Cloudflare

• AWS

• OpenAI

• Google

3) 预装基础环境（开机即用）

• Ubuntu 24.04

• CUDA 13

• NGC PyTorch 容器 (26.03-py3)：

  • NGC: nvidian/pytorch:26.03-py3

• 新版的 Codex CLI 和 Claude Code CLI

4) S3-compatible 存储自动化挂载 + 数据导入本地高速盘

• 示例数据 (33G)：

  • Hugging Face 数据集: FineWeb-Edu (CC-MAIN-2013-20)

• 流程要求：离线入桶 (S3) → 在线加载 → 落到实例本地盘

5) Telemetry UI（网页端实时监控）

• 实时展示 instance 关键状态与资源使用情况

6) （可选加分项）端口转发与安全性

• 不直接暴露公网 22 端口

• 提供网络与数据安全性测试结论/说明

界面参考

📷 以下截图来自 Vast.ai 控制台，供体验与 UI 设计参考。

(图片展示了包含 Disk Usage, Uptime, CPU Load, Memory, GPU Load, VRAM, Utilization 等指标的监控面板)

任务要求

项目 说明

时间要求 5天内完成任务或尽可能取得进展

演示日要求 展示实际成果（实际进度，思维过程比展示形式更重要）

计算预算 100元人民币（可报销），任何算力平台都可以，如有超出面试通过可考虑报销

辅助工具 允许并鼓励使用任何 LLM、编码助手和个人/专业帮助。

终面：30 分钟线下展示

🎓 完成大作业后，预约 30 分钟线下面试：
• 前 15 分钟：展示大作业完成情况

• 后 15 分钟：Q&A 环节

考核重点

• 完成质量：实际成果与功能完成度

• 思维链：过程中遇到哪些问题、如何解决，请认真准备

终面结束 2-3 个工作日内发送录取邀请

预约流程

1. 通过下方链接预约面试时间：
   https://whaletech.notion.site/2e35f589aa80800c9af0e5b6d0e753cf?pvs=105
2. 再通过企业微信将代码仓库和 Demo 发给我们