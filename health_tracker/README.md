# cutnbulk 多用户饮食日历网站

个人可用的饮食记录网站：注册登录后进入自己的日历，记录体重与多顿饮食，支持拍照估算。基于 FastAPI + Jinja2 + SQLAlchemy，可部署到 Render，认证与私有图片使用 Supabase。

## 功能

- 邮箱注册 / 登录 / 退出 / 忘记密码
- 用户数据隔离（日历、饮食、目标、照片）
- 目标热量设置（按用户）
- 一天多顿饮食；手动填营养或拍照 AI 估算
- PostgreSQL（线上）/ SQLite（本地）
- Alembic 数据库迁移
- Supabase Auth + 私有 Storage

本次**不包含**新用户问卷；`UserProfile.onboarding_completed` 已预留，默认 `false`，登录后直接进入空日历。

## 本地运行（开发）

```bash
cd health_tracker
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

`.env` 最小本地配置示例：

```text
APP_ENV=development
APP_BASE_URL=http://127.0.0.1:8000
AUTH_MODE=local
SECRET_KEY=dev-secret
DATABASE_URL=
COOKIE_SECURE=false
ALLOWED_HOSTS=localhost,127.0.0.1
```

`AUTH_MODE=local` 仅用于本地/测试：密码哈希存在 `user_profiles`，不依赖真实 Supabase。生产必须 `AUTH_MODE=supabase`。

初始化数据库并启动：

```bash
alembic upgrade head
uvicorn main:app --reload
```

打开：http://127.0.0.1:8000

## 数据库迁移

```bash
cd health_tracker
alembic upgrade head
```

- 空库：创建全部表
- 旧 SQLite：添加 `user_id` 等字段；旧记录 `user_id` 为空，**不会**自动归属任何用户

### 旧数据归属（一次性）

先备份数据库，再 dry-run：

```bash
python scripts/assign_orphan_data.py --user-id <你的用户UUID> --dry-run
python scripts/assign_orphan_data.py --user-id <你的用户UUID> --apply
```

本地 SQLite **不会自动出现在云端 Postgres**，需要自行导出/导入。

### 本地图片迁到 Supabase

配置好云存储后：

```bash
python scripts/migrate_local_images.py --dry-run
python scripts/migrate_local_images.py --apply
```

## 你需要在控制台完成的配置

### 1) Supabase Auth

1. 创建 Supabase 项目
2. Authentication → Providers → Email 开启
3. 建议开启邮箱验证
4. URL Configuration 中设置：
   - Site URL：`https://你的域名`
   - Redirect URLs：
     - `https://你的域名/auth/callback`
     - `https://你的域名/auth/reset-password`
     - 本地调试可加 `http://127.0.0.1:8000/auth/callback` 等
5. 复制 Project URL、anon/publishable key、service role key

生产 `.env` / Render 环境变量：

```text
APP_ENV=production
APP_BASE_URL=https://你的域名
AUTH_MODE=supabase
DATABASE_URL=postgresql://...
SECRET_KEY=长随机字符串
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_PUBLISHABLE_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...
SUPABASE_STORAGE_BUCKET=meal-photos
ALLOWED_HOSTS=你的域名
COOKIE_SECURE=true
```

### 2) Supabase Storage（私有 bucket）

1. 创建 bucket：`meal-photos`
2. 设为 **Private**
3. 不要把 service role key 放到前端
4. 业务表若启用 Supabase Data API，请加 RLS；本应用默认通过 FastAPI + 自己的 Postgres/SQLite 访问业务数据，并用 `user_id` 强制隔离

### 3) Render 部署

仓库根目录 `render.yaml`：

- `rootDir: health_tracker`
- `preDeployCommand: alembic upgrade head`
- `startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT`
- `/health` 健康检查

在 Render 填入上述环境变量；`DATABASE_URL` 可用 Render Postgres。部署后打开站点完成注册登录。

## 测试

```bash
cd health_tracker
pytest -q
```

自动化覆盖：注册登录退出、用户隔离、同日双用户、外链 next 拒绝、手动模式不调 Vision、Alembic 空库/旧库升级。

**尚未用真实凭据验证的外部流程：**

- Supabase 邮箱验证邮件送达
- 真实重置密码邮件与回调
- 生产环境签名 URL 长期可用性
- Render 多实例下的进程内限流（当前限流为单实例）

## 安全说明

- 浏览器 Cookie 仅存不透明会话 ID；Supabase token 存在服务端 `auth_sessions`
- 表单写操作有 CSRF
- 登录/注册/忘记密码有进程内限流（单实例）
- 生产禁止回退 SQLite / 临时公开上传目录
- `service role key` 仅后端使用

## 目录结构（关键）

```text
health_tracker/
  main.py
  alembic/
  app/
    auth/
    security/
    routers/   # auth, calendar, day, goal, summary, meals, media
    services/  # storage, vision, nutrition, goal
    templates/auth/
  scripts/
  tests/
```
