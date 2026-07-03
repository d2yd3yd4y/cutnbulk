# cutnbulk 本地健身饮食日历

这是一个个人使用的极简健身饮食记录 App，使用 FastAPI + Jinja2 + SQLite 构建，可在本地浏览器运行。

## 功能

- 首页日历：按月查看每日记录摘要
- 目标设置：支持减脂、维持、增肌，并估算每日建议摄入
- 每日记录：体重、睡眠、疲劳感
- 训练记录：用训练部位 + 训练备注快速记录
- 饮食记录：每天可添加多顿饭，每顿单独记录描述、照片、热量和三大营养素
- 食物数据库：内置常见主食、蛋白质食材、中餐菜品、外卖、饮品和零食
- 本地饮食估算：优先使用食物数据库匹配和份量解析，匹配不到时 fallback 到旧 mock 规则

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
- `/foods`：查看和搜索食物库
- `/foods/new`：新增自定义食物

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

## 饮食估算说明

第一版优先使用本地 Food Database，不需要配置任何密钥。也可以配置 OpenAI API，在上传食物照片时使用视觉模型做增强估算。

估算流程：

1. 根据食物名称和别名匹配 `FoodItem`
2. 尝试识别 `100g`、`200克`、`一碗`、`两个鸡蛋`、`一杯奶茶` 等份量
3. 按每 100g 营养数据计算热量、蛋白、碳水、脂肪
4. 如果上传照片且没有手动填写营养数字，会优先调用 OpenAI 视觉模型
5. 如果没有 API key、API 调用失败，或没有上传图片，则使用本地 Food Database
6. 如果完全匹配不到，再 fallback 到 `app/services/food_ai_service.py` 中的旧本地 mock 规则

食物库会在项目启动时自动初始化，使用 `normalized_name` 避免重复插入。

可以在 `/foods/new` 新增自定义食物，新增后会参与后续饮食估算。

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
    database.py
    models.py
    schemas.py
    services/
      food_ai_service.py
      food_import_service.py
      food_seed_service.py
      goal_service.py
      insight_service.py
      nutrition_estimator.py
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
