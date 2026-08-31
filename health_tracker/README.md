# cutnbulk 本地健身饮食日历

这是一个个人使用的极简健身饮食记录 App，使用 FastAPI + Jinja2 + SQLAlchemy 构建。它可以在本地用 SQLite 运行，也可以部署到公网并连接 PostgreSQL，让手机 Safari 随时访问。

## 功能

- 首页日历：按月查看每日记录摘要
- 目标设置：支持减脂、维持、增肌，并估算每日建议摄入
- 每日记录：体重、睡眠、疲劳感
- 训练记录：用训练部位 + 训练备注快速记录
- 饮食记录：每天可添加多顿饭，每顿单独记录描述、照片、热量和三大营养素
- 食物数据库：支持搜索、查看和手动新增自定义食物
- 本地饮食估算：优先使用食物数据库匹配和份量解析，匹配不到时 fallback 到旧 mock 规则

## 技术栈

- Python
- FastAPI
- Jinja2 Templates
- SQLite（本地开发）
- PostgreSQL（线上部署）
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

健康检查：

```text
http://127.0.0.1:8000/health
```

核心页面：

- `/`：当月日历
- `/today`：跳转到今天
- `/day/YYYY-MM-DD`：某一天的记录页，例如 `/day/2026-07-01`
- `/goal`：设置当前阶段、目标体重和每日建议摄入
- `/summary`：最近 7 天趋势
- `/foods`：查看和搜索食物库
- `/foods/new`：新增自定义食物

## 手机端预览

当前 UI 以手机竖屏优先，桌面端打开时会居中显示为接近手机 App 的宽度。

在浏览器开发者工具中可以用这些宽度预览：

- 375px
- 390px
- 430px

## 数据库和上传文件

- 本地没有配置 `DATABASE_URL` 时，会自动创建 SQLite 数据库：`health_tracker.db`
- 线上配置 `DATABASE_URL` 后，会使用 PostgreSQL
- 食物照片会保存到：`app/uploads/`
- 上传文件和本地数据库不会提交到 Git

## 环境变量

复制 `.env.example` 为 `.env`，按需要填写：

```bash
cp .env.example .env
```

```text
DATABASE_URL=
SECRET_KEY=
OPENAI_API_KEY=
OPENAI_FOOD_MODEL=gpt-5.4-mini
```

- `DATABASE_URL`：线上 PostgreSQL 连接字符串；本地留空时使用 SQLite。
- `SECRET_KEY`：后续登录/会话功能使用；当前先预留。
- `OPENAI_API_KEY`：后续拍照估算热量时使用。
- `OPENAI_FOOD_MODEL`：拍照估算模型名，默认 `gpt-5.4-mini`。

## 部署到公网，让手机 Safari 随时访问

本地运行只适合在你的 Mac 或同一个 Wi-Fi 下测试。如果想在外面随时打开，需要把项目部署到公网服务器，并使用云数据库。

推荐第一版：

- 部署平台：Render 或 Railway
- 数据库：Supabase Postgres、Render Postgres 或 Railway Postgres
- 访问方式：部署完成后用公网 HTTPS 地址，例如 `https://cutnbulk.onrender.com`

### 1. 上传代码到 GitHub

确认不要提交这些本地文件：

```text
.env
.venv/
health_tracker.db
app/uploads/里的用户上传图片
```

仓库根目录的 `.gitignore` 已经忽略了这些内容。

### 2. 准备 PostgreSQL 数据库

创建一个 PostgreSQL 数据库，例如 Supabase Postgres。

拿到连接字符串后，保存为部署平台的环境变量：

```text
DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/DATABASE
```

如果平台给的是 `postgres://...`，代码会自动转换为 SQLAlchemy 可用的 `postgresql://...`。

### 3. 在 Render 部署

方式 A：使用仓库根目录的 `render.yaml`

1. 打开 Render。
2. 创建 Blueprint / New Blueprint。
3. 连接 GitHub 仓库。
4. Render 会读取根目录的 `render.yaml`。
5. 在环境变量里填入 `DATABASE_URL`、`OPENAI_API_KEY` 等。

方式 B：手动创建 Web Service

Render 设置：

```text
Root Directory: health_tracker
Build Command: pip install -r requirements.txt
Start Command: uvicorn main:app --host 0.0.0.0 --port $PORT
Health Check Path: /health
```

环境变量：

```text
DATABASE_URL=你的PostgreSQL连接字符串
SECRET_KEY=任意长随机字符串
OPENAI_API_KEY=可选
OPENAI_FOOD_MODEL=gpt-5.4-mini
```

部署完成后，Render 会给你一个公网地址，例如：

```text
https://cutnbulk.onrender.com
```

手机 Safari 直接打开这个地址即可。先测试：

```text
https://cutnbulk.onrender.com/health
```

看到下面内容就说明服务在线：

```json
{"status":"ok","app":"cutnbulk"}
```

### 4. 在 Railway 部署

Railway 手动设置也类似：

```text
Root Directory: health_tracker
Build Command: pip install -r requirements.txt
Start Command: uvicorn main:app --host 0.0.0.0 --port $PORT
```

然后在 Variables 中添加：

```text
DATABASE_URL=你的PostgreSQL连接字符串
SECRET_KEY=任意长随机字符串
OPENAI_API_KEY=可选
OPENAI_FOOD_MODEL=gpt-5.4-mini
```

Railway 部署完成后会提供公网域名，手机 Safari 打开该域名即可。

### 本地 SQLite 和线上 PostgreSQL 的区别

- SQLite：一个本地 `.db` 文件，适合个人电脑开发测试。
- PostgreSQL：云数据库，适合公网部署和长期保存数据。
- 线上不要依赖 `health_tracker.db`，因为服务器重启、重新部署或换实例时，本地文件可能丢失。

### 上传图片提醒

当前图片仍然保存到 `app/uploads/`。这在本地没问题，但很多云平台的本地磁盘不是长期可靠存储。上线初期可以先测试，正式长期使用建议下一步改成 Supabase Storage 或 S3。

## 数据安全提醒

cutnbulk 会记录体重、饮食、训练等私人数据。部署到公网后请注意：

- 线上版本不建议公开给别人使用。
- 后续应该加入登录系统。
- 不要把 `.env`、API key、数据库密码提交到 GitHub。
- 不要把本地 `health_tracker.db` 提交到 GitHub。
- 如果网址被别人知道，在没有登录系统前，对方可能看到或修改你的记录。

## AI 饮食估算说明

第一版优先使用本地 Food Database，不需要配置任何密钥。也可以配置 OpenAI API，在上传食物照片时使用视觉模型做增强估算。

估算流程：

1. 根据食物名称和别名匹配 `FoodItem`
2. 尝试识别 `100g`、`200克`、`一碗`、`两个鸡蛋`、`一杯奶茶` 等份量
3. 按每 100g 营养数据计算热量、蛋白、碳水、脂肪
4. 如果上传照片且没有手动填写营养数字，会优先调用 OpenAI 视觉模型
5. 如果没有 API key、API 调用失败，或没有上传图片，则使用本地 Food Database
6. 如果完全匹配不到，再 fallback 到 `app/services/food_ai_service.py` 中的旧本地 mock 规则

食物库不会自动预置数据。可以在 `/foods/new` 手动新增自定义食物，新增后会参与后续饮食估算。

注意：这些估算不是医学级精确数据。中餐、外卖、火锅、烧烤等会因为油量、酱料、实际份量不同产生明显误差，建议把它作为辅助记录，并允许手动修正。

### OpenAI 拍照估算配置

复制 `.env.example` 为 `.env`：

```bash
cp .env.example .env
```

填写：

```text
OPENAI_API_KEY=你的 key
OPENAI_FOOD_MODEL=gpt-5.4-mini
```

如果要切换模型，可以把 `OPENAI_FOOD_MODEL` 改成其他支持视觉输入的模型，例如未来的 `gpt-5.5`。

拍照估算测试：

1. 打开 `/today`
2. 在“饮食”里添加一顿
3. 填写或不填写食物描述
4. 上传食物照片
5. 不填写热量、蛋白、碳水、脂肪
6. 保存后查看餐卡里的“AI 估算”、可信度、热量区间、误差来源和原材料拆解

没有 `OPENAI_API_KEY` 时不会报错，会自动使用本地食物数据库/旧 mock 估算。

## 项目结构

```text
health_tracker/
  main.py
  requirements.txt
  README.md
  .env.example
  app/
    __init__.py
    constants.py
    database.py
    models.py
    schemas.py
    utils/
      form_parsing.py
      food_names.py
      meal_totals.py
      stats.py
    services/
      food_ai_service.py
      food_import_service.py
      goal_service.py
      insight_service.py
      nutrition_estimator.py
      upload_service.py
      vision_food_estimator.py
      weekly_review_service.py
    routers/
      calendar.py
      day.py
      foods.py
      goal.py
      dashboard.py
      meals.py
      workouts.py
      body.py
      weekly.py
    templates/
      base.html
      calendar.html
      day.html
      foods.html
      food_new.html
      goal.html
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
