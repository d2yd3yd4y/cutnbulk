# 饮食 + 训练 + 身体数据记录本地 Web App MVP

这是一个个人使用的健康记录 MVP，使用 FastAPI + Jinja2 + SQLite 构建，可在本地浏览器运行。

## 功能

- 首页 Dashboard：今日热量、三大营养素、训练量、最近身体数据和每日建议
- 饮食记录：早餐、午餐、晚餐、加餐，支持文字描述、食物照片、快速模板和营养估算
- 训练记录：支持一次添加多条动作，记录组数、次数、重量、RPE、是否接近力竭
- 身体数据：记录体重、腰围、睡眠、疲劳感和备注
- 周复盘：基于最近 7 天数据生成中文总结和调整建议

## 技术栈

- Python
- FastAPI
- Jinja2 Templates
- SQLite
- SQLAlchemy
- 普通 HTML/CSS/少量 JavaScript

## 安装和运行

在仓库根目录执行：

```bash
cd health_tracker
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

启动后打开：

```text
http://127.0.0.1:8000
```

## 数据库和上传文件

- 首次启动会自动创建 SQLite 数据库：`health_tracker.db`
- 食物照片会保存到：`app/uploads/`
- 上传文件和本地数据库不会提交到 Git

## AI 饮食估算说明

第一版使用 `app/services/food_ai_service.py` 中的本地 mock 规则，不需要配置任何密钥。

如果未来要接入 OpenAI Vision API，可以在同一个 service 中扩展：

- 输入：图片路径、文字描述
- 输出：`calories`、`protein_g`、`carbs_g`、`fat_g`、`confidence`、`reasoning`

当前代码会检测 `OPENAI_API_KEY`，但 MVP 不强制调用真实 API，保证离线也能运行。

## 项目结构

```text
health_tracker/
  main.py
  requirements.txt
  README.md
  app/
    __init__.py
    database.py
    models.py
    schemas.py
    services/
      food_ai_service.py
      insight_service.py
      weekly_review_service.py
    routers/
      dashboard.py
      meals.py
      workouts.py
      body.py
      weekly.py
    templates/
      base.html
      dashboard.html
      meals.html
      workouts.html
      body.html
      weekly.html
    static/
      styles.css
      app.js
    uploads/
      .gitkeep
```
