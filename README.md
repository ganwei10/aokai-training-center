# 奥楷培训学习中心（前后端分离）

面向**售前工程师 / 销售 / 售后工程师**三类人群、从**初级到高阶**的肉类食品加工数字化设备
（灌装/扎线/扭结、包装、码垛）产品与技术培训平台。

所有教材正文 + 全网外链资源与培训视频（已下载归档）均内置，可离线学习。
全站资料（教材 / 资源 / 标准 / 公司文档）均带有**设备类型标签**（灌装/扎线/扭结、包装、码垛、通用），可按设备筛选；标准库覆盖**中国 / 美国 / 加拿大 / 欧盟**四个地区。

## 架构（前后端分离）

```
training-center/
├── api/                    # 后端 API 服务（FastAPI + SQLite）
│   ├── app.py              # REST API（分类/教材/资源/标准/搜索/设备）
│   ├── build_db.py         # 由教材 Markdown + resources.json + 标准库 Markdown 生成 learning.db
│   ├── data/
│   │   ├── learning.db     # 教材 + 资源库 + 标准库（SQLite，已预构建并提交）
│   │   └── resources.json  # 外链下载结果
│   └── requirements.txt
├── frontend/               # 前端 SPA（纯静态，无构建步骤）
│   ├── index.html
│   ├── app.js
│   └── styles.css
└── index.py                # Vercel serverless 入口（暴露 ASGI app）
```

- **后端**：`/api/*` 提供分类、教材、资源、标准、搜索、设备类型等 REST 接口，CORS 放开。
- **前端**：独立 SPA，通过 `fetch('/api/...')` 获取数据，可单独部署到任意静态托管。
- **标准库**：源文件位于仓库外 `../公司资料/标准库/`（中/美/加/欧），由 build_db.py 烘焙进 learning.db。

## 本地运行

```bash
# 1) 生成数据库（教材 + 已下载的外链资源 + 标准库）
python api/build_db.py

# 2) 启动后端（默认 8000 端口，同时托管前端）
python -m uvicorn api.app:app --host 0.0.0.0 --port 8000
# 或： python api/app.py

# 3) 浏览器打开 http://localhost:8000
```

## 重新下载外链内容

```bash
python download_resources.py     # 抓取外链正文 -> api/data/resources.json
python api/build_db.py           # 重建数据库
```

## 部署到 Vercel（需提供 Token）

1. 安装依赖：`pip install -r api/requirements.txt`
2. Vercel 由 `index.py` 暴露 ASGI `app`，并将 `frontend/` 作为静态目录、`/api/*` 路由到该
   serverless 函数（`learning.db` 已预构建并提交，运行时无需 markdown/uvicorn）。

## 数据来源说明

- 内部教材：中英双语 Markdown（见 `../培训教材/`），含奥楷产品内部讲义。
- 外链资源：从教材中引用的全网链接，已尽量抓取正文；个别站点拒绝抓取时保留
  原始链接与教材备注，学习中心内可一键跳转原页面。
- 标准库：覆盖中国（GB）、美国（USDA FSIS / 3-A / NSF）、加拿大（SFCR / CFIA）、
  欧盟（852/853/854/2004 / EN 1672-2），均为基于官方公开文本的整理/概述版。
