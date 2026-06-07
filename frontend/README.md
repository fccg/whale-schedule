# GPU Scheduling Platform — Frontend

GPU 调度平台前端，提供 GPU 市场浏览、实例配置与创建、实例监控 Dashboard 和测试报告展示。

技术栈：Next.js + TypeScript + shadcn/ui + Recharts + Tailwind CSS。

## 本地开发

```bash
npm install
npm run dev
```

默认在 `http://localhost:3000` 启动。页面依赖后端 API，启动前请确保后端已运行（见下方联调说明）。

## 关键环境变量

| 变量 | 说明 | 默认值 |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | 后端 API 地址 | `http://localhost:8000` |

该变量在构建时注入浏览器端代码（`src/lib/api.ts`），Docker 构建通过 `--build-arg` 传入，本地开发通过 `.env.local` 设置。

## 构建

```bash
npm run build    # 生产构建
npm run lint     # ESLint 检查
```

## 与后端联调

后端为 FastAPI 服务，默认监听 `8000` 端口。联调步骤：

1. 在后端目录启动 API：
   ```bash
   cd ../backend
   pip install -r requirements.txt
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

2. 在本目录创建 `.env.local` 指向后端：
   ```env
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

3. 启动前端开发服务器：
   ```bash
   npm run dev
   ```

### Docker Compose 联调

项目根目录提供 `docker-compose.yml`，一步启动前后端：

```bash
cd ..
docker compose up -d --build
```

启动后前端在 `http://localhost:18761`，后端在 `http://localhost:18760`。

**注意：** 默认 Compose 配置中 `NEXT_PUBLIC_API_URL` 指向预设的公网地址 `http://115.191.43.252:18760`。如果在本机做纯本地联调，需先在根目录 `.env` 中覆盖：

```env
NEXT_PUBLIC_API_URL=http://localhost:18760
CORS_ORIGIN=http://localhost:18761
```

然后重新构建前端容器使新值生效。

## 目录结构

```
frontend/
├── src/
│   ├── app/          # Next.js App Router 页面
│   ├── components/   # 业务组件
│   └── lib/          # API 客户端、工具函数
├── public/
├── package.json
└── Dockerfile
```
