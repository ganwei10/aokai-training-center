# 奥楷培训学习中心（前后端分离）

面向**售前工程师 / 销售 / 售后工程师**三类人群、从**初级到高阶**的肉类食品加工数字化设备
（灌装/扎线/扭结、包装、码垛）产品与技术培训平台。

所有教材正文 + 全网收集的 33 条外链资源（已下载归档）均内置，可离线学习。

## 架构（前后端分离）

```
training-center/
├── backend/                # 后端 API 服务（FastAPI + SQLite）
│   ├── app.py              # REST API + 本地托管前端
│   ├── build_db.py         # 由 13 篇 Markdown + resources.json 生成 learning.db
│   ├── data/
│   │   ├── learning.db     # 教材 + 资源库（SQLite）
│   │   └── resources.json  # 外链下载结果
│   └── requirements.txt
└── frontend/               # 前端 SPA（纯静态，无构建步骤）
    ├── index.html
    ├── app.js
    └── styles.css
```

- **后端**：`/api/*` 提供分类、教材、资源、搜索等 REST 接口，CORS 放开。
- **前端**：独立 SPA，通过 `fetch('/api/...')` 获取数据，可单独部署到任意静态托管。

## 本地运行

```bash
# 1) 生成数据库（教材 + 已下载的外链资源）
python backend/build_db.py

# 2) 启动后端（默认 8000 端口，同时托管前端）
python -m uvicorn backend.app:app --host 0.0.0.0 --port 8000
# 或： python backend/app.py

# 3) 浏览器打开 http://localhost:8000
```

## 重新下载外链内容

```bash
python download_resources.py     # 抓取 33 条外链正文 -> backend/data/resources.json
python backend/build_db.py       # 重建数据库
```

## 部署到 Vercel（需提供 Token）

1. 安装依赖：`pip install -r backend/requirements.txt`
2. 设置环境变量 `SERVE_FRONTEND=0`，将 `frontend/` 作为静态目录、`backend/app.py` 经
   mangum 包装为 `/api` serverless 函数即可。

## 数据来源说明

- 内部教材：13 篇 Markdown（见 `../培训教材/`），含奥楷产品内部讲义。
- 外链资源：从教材中引用的 33 个全网链接，已尽量抓取正文；个别站点拒绝抓取时保留
  原始链接与教材备注，学习中心内可一键跳转原页面。
