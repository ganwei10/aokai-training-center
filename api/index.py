# Vercel serverless 入口：将 FastAPI 应用包装为 /api 函数（前后端分离部署）。
# 前端静态文件由 Vercel 从 frontend/ 目录托管，API 由本函数处理 /api/*。
import os

# 在导入 app 之前关闭前端挂载（Vercel 由平台托管静态文件）
os.environ['SERVE_FRONTEND'] = '0'

from mangum import Mangum
from app import app

handler = Mangum(app)
