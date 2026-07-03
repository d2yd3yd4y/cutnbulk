# cutnbulk 本地健身饮食日历

这是一个个人使用的极简健身饮食记录 App，使用 FastAPI + Jinja2 + SQLite 构建，可在本地浏览器运行。

## 功能

- 首页日历：按月查看每日记录摘要
- 目标设置：支持减脂、维持、增肌，并估算每日建议摄入
- 每日记录：体重、睡眠、疲劳感
- 训练记录：用训练部位 + 训练备注快速记录
- 饮食记录：每天可添加多顿饭，每顿单独记录描述、照片、热量和三大营养素
- 本地 mock 饮食估算：单顿饭营养数据留空时按描述和图片做估算

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

核心页面：

- `/`：当月日历
- `/today`：跳转到今天
- `/day/YYYY-MM-DD`：某一天的记录页，例如 `/day/2026-07-01`
- `/goal`：设置当前阶段、目标体重和每日建议摄入
- `/summary`：最近 7 天趋势

## 手机端预览

当前 UI 以手机竖屏优先，桌面端打开时会居中显示为接近手机 App 的宽度。

在浏览器开发者工具中可以用这些宽度预览：

- 375px
- 390px
- 430px

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
      calendar.py
      day.py
      dashboard.py
      meals.py
      workouts.py
      body.py
      weekly.py
    templates/
      base.html
      calendar.html
      day.html
      dashboard.html
      meals.html
      workouts.html
      body.html
      weekly.html
    static/
      images/
        logo.png
      styles.css
      app.js
    uploads/
      .gitkeep
```
