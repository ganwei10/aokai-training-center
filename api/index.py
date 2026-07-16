# Vercel serverless 入口：Vercel 的 Python 运行时原生支持 ASGI 应用，
# 只需在本文件暴露名为 `app` 的 ASGI 应用即可（无需 Mangum，那是 AWS Lambda 适配器）。
# 前端静态文件由 Vercel 从 frontend/ 目录托管，API 由本函数处理 /api/*。
import os

# 在导入 app 之前关闭前端挂载（Vercel 由平台托管静态文件）
os.environ['SERVE_FRONTEND'] = '0'

from app import app  # noqa: E402,F401  Vercel 会将此 ASGI app 作为函数处理器
