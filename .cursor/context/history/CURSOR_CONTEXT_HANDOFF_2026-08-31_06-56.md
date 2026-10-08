# Cursor Context Handoff — cutnbulk (Health Tracker)

**Generated:** 2026-08-31 (UTC)  
**Source chat:** cutnbulk Python/FastAPI health tracking app — full development history from MVP through OpenAI Vision integration  
**Current git branch (workspace):** `cursor/health-tracker-mvp-7132`  
**Latest commit on feature branch:** `a06daae` — "Add OpenAI vision meal estimation"  
**Base branch:** `main`  
**Open PR:** Draft PR #1 — "Create local health tracker MVP" on branch `cursor/health-tracker-mvp-7132`

---

## User Requirements

### Initial requirement (first message)

User asked (as senior full-stack/product engineer persona) to create from scratch a **Python local web app MVP** for personal health tracking covering:

- **Diet** (饮食)
- **Training** (训练)
- **Body data** (身体数据)

**Technical stack specified:**
- Python
- FastAPI
- Jinja2 templates
- SQLite
- SQLAlchemy
- Basic HTML/CSS/JS

**Initial MVP features:**
- Daily record keeping
- Dashboard
- Weekly review

---

### Requirement evolution — running the project

User is a **first-time project developer**. They needed extensive hand-holding:

1. How to run (venv, pip, uvicorn)
2. Whether to use **computer terminal vs Cursor terminal** → both work; Cursor terminal is fine for cloud dev
3. After running commands, what next → open browser at `http://127.0.0.1:8000`
4. Confusion about terminal prefix (`health_tracker`) — confirmed normal when inside project dir
5. Copy/paste issues (extra punctuation)
6. Where to find **Ports** in Cursor
7. Desktop "Take Control" → open `http://127.0.0.1:8000` — **confirmed success**
8. How to open on **local Google Chrome** on their Mac — run same commands locally in project folder
9. User successfully opened app in Cursor desktop environment

**Final requirement:** Clear step-by-step run instructions for both Cursor cloud and local Mac.

---

### Requirement evolution — functional convergence & mobile-first UI

User requested a **product convergence/refactor** as senior product + full-stack engineer:

**Initial refactor goals:**
- Simplify app to focus on **calendar-style daily record as homepage**
- Reduce page/field complexity
- Mobile-first design

**Later refined to:**
- Max width ~430px on desktop (phone-like shell)
- Top App Bar + bottom navigation
- Touch-friendly forms
- Consolidate daily records into single `/day/{date}` page using `DailyEntry`
- **Remove `waist_cm` input from daily record UI** (field kept in DB for compatibility)

**Navigation final state:**
- Bottom nav: 日历 (`/`), 今日 (`/today`), 趋势 (`/summary`)
- App bar: logo + brand "cutnbulk" + shortcut to today

**App naming:** Project branded **cutnbulk** (not generic "health tracker")

---

### Requirement evolution — multi-meal logging

**Initial:** Single "all-day food description" on `DailyEntry`

**Changed to:**
- Multiple meals per day via `MealEntry` table
- Each meal: type, optional custom name, description, photo, macros, notes
- Edit/delete individual meals
- Auto-aggregate daily totals from meals
- Calendar and summary pages use `MealEntry` totals (not legacy `DailyEntry` food fields)

**Meal types:** breakfast, lunch, dinner, snack, pre_workout, post_workout, night, custom

---

### Requirement evolution — goal setting + daily calorie advice

User requested **目标设置 + 每日建议热量**:

- Modes: **cut / maintain / bulk** (减脂 / 维持 / 增肌)
- Inputs: current weight, target weight, target days, activity level
- Optional manual maintenance calories override
- Calculate: recommended calories, daily energy delta, weekly weight change
- Validation for unrealistic goals (e.g., cut with target ≥ current)
- Display goal on homepage calendar + daily record page
- User-friendly advice/warnings in goal note

**UI requirement:** Segmented radio controls for mode and activity — user reported **"这些UI都对不齐"** (alignment issues) which was fixed.

---

### Requirement evolution — food nutrition database

User asked whether estimates were "瞎估算" (made up) and wanted accuracy.

**Initial question:** "如果要里面的估算正确的话是不是要接入模型"

**Final requirement for this phase:**
- Replace simplistic mock with **local `FoodItem` database**
- Chinese-friendly ingredients and dishes, per-100g nutrition
- Parsing algorithm for quantities: "150g chicken breast", "一碗米饭", "两个鸡蛋"
- Store `MealFoodMatch` per meal
- Confidence, reasoning, uncertainty factors
- `/foods` management page: search, view, add custom foods
- CSV import placeholder (not full UI)
- **Fallback chain:** Food DB → old mock (`food_ai_service.py`)

**NOT required at this stage:** Mandatory external AI for text-only estimation.

---

### Requirement evolution — TypeScript Chinese dish breakdown (standalone module)

Separate request for a **standalone TypeScript module** (`src/nutrition`):

- Rule-based (NOT AI) breakdown of complex Chinese dishes
- Examples: 沙县鸭腿饭, 麻辣烫, 煎饼果子, 黄焖鸡米饭, 番茄炒蛋盖饭
- Output structured JSON: totals, confidence, uncertainty, ingredient breakdown, user-friendly explanation
- User modifiers (rice amount, skin eaten, sauce level, oil level, portion size, etc.)
- Demo cases in `demo.ts`

**Important:** This module is **independent** from the Python FastAPI app. It was NOT integrated into the Python meal estimation pipeline in this chat.

---

### Requirement evolution — OpenAI Vision photo estimation

User requested:

> "请帮我给 cutnbulk 增加'拍照估算热量和三大营养素'的功能，使用 OpenAI API 的视觉模型。"

**Requirements:**
- Use OpenAI Vision API (`gpt-5.4-mini` via Responses API + JSON Schema)
- Compress images before API call
- **Priority:** If image uploaded AND nutrition fields not manually filled → use Vision
- **Robust fallback:** Missing `OPENAI_API_KEY` or API failure → local food DB / mock
- Never break meal saving on API errors
- Display in UI: source (AI vs local), confidence, calorie range, uncertainty factors
- `.env.example` with `OPENAI_API_KEY` and `OPENAI_FOOD_MODEL`
- Instructions in README

**Final requirement:** Local-first MVP that works without API key; Vision is enhancement.

---

### Deployment / publishing discussions (informational, not fully implemented on feature branch)

User asked multiple product questions (no explicit implementation request in same messages):

1. **Publish website** — what's needed, cost?
2. **Fair monthly cost** if self-hosted/published
3. **ChatGPT API cost** if actually used
4. **App Store vs WeChat mini program** difficulty
5. **Run on phone locally** — detailed steps; user accepted that **computer must be on** for local LAN access
6. **"我不想只在本地运行了，我想让其他人也能在他们手机里运行"** — discussed options; user then decided **"那我还是先本地在我的手机上运行吧"**

**Note:** `main` branch has commit `9b19771` "Prepare cutnbulk for public deployment" with `render.yaml` and `/health` endpoint. This is **NOT merged into** `cursor/health-tracker-mvp-7132` as of handoff time.

---

### Explicit constraints / preferences from user messages

| Instruction | Detail |
|-------------|--------|
| Mobile-first | Phone vertical layout, ~375–430px preview widths |
| Local-first | App must run without API keys |
| Chinese UX copy | UI in Chinese |
| Manual override | User can always edit estimated nutrition |
| Don't break on API failure | Vision errors fall back silently with message |
| Simplify UX | Calendar homepage, fewer pages in primary flow |
| Remove waist from UI | `waist_cm` hidden from daily form |
| Keep legacy data | Don't delete old model fields unnecessarily |

**Not explicitly requested (do NOT assume user wants):**
- Full public deployment completion on current branch
- Integration of TypeScript `src/nutrition` into Python backend
- Authentication / multi-user
- App Store / WeChat mini program implementation
- Removing legacy routers (`/meals`, `/workouts`, `/body`, `/weekly`, `/dashboard`)

---

## Current Project State

### Project goal

**cutnbulk** is a personal, local-first fitness & diet tracking web app. Primary UX is a **mobile-style calendar** showing daily records, with per-day pages for body metrics, training, and multi-meal food logging. Includes goal-based calorie recommendations and layered nutrition estimation (Vision AI → food database → mock).

### What is fully implemented

1. **Calendar homepage** (`/`) — month view, meal calorie summaries, goal card, month overview
2. **Today redirect** (`/today` → `/day/{today}`)
3. **Daily record page** (`/day/{date}`) — weight, sleep, fatigue, training parts/notes, multi-meal CRUD
4. **Goal setting** (`/goal`) — cut/maintain/bulk with calculated recommendations
5. **Summary/trends** (`/summary`) — 7-day averages from `MealEntry`
6. **Food database** (`/foods`, `/foods/new`) — 78 seed items, search, add custom
7. **Local nutrition estimation** — `nutrition_estimator.py` with portion parsing + `MealFoodMatch`
8. **OpenAI Vision estimation** — `vision_food_estimator.py` with fallback
9. **Mobile-first UI** — app shell, app bar, bottom nav, responsive CSS
10. **TypeScript dish estimator** — standalone module at `src/nutrition/` with demo

### Partially implemented / legacy still present

1. **Legacy routers still mounted** in `main.py`: `meals`, `workouts`, `body`, `weekly` — old separate pages exist but are NOT in bottom navigation
2. **`DailyEntry` legacy food fields** — `food_description`, `calories`, etc. still saved via `save_day` POST; primary food UX is now `MealEntry`
3. **`dashboard.py` router exists** but is NOT included in `main.py`
4. **`food_import_service.py`** — CSV import raises `NotImplementedError`
5. **`food_ai_service.py`** — still has OpenAI placeholder that does NOT call real Vision (real Vision is in `vision_food_estimator.py`); used as final mock fallback
6. **Deployment prep on `main` only** — `render.yaml`, `/health`, `DATABASE_URL` env support partially on main, not on feature branch

### What is NOT implemented

- User authentication / accounts
- Cloud deployment on current feature branch
- TypeScript nutrition module wired into Python meal flow
- Real end-to-end Vision API test with user's API key (verified fallback only in cloud agent environment)
- `/foods` link in bottom navigation (page exists but reached via README/direct URL)
- Weekly review as primary UX (router exists, not in nav)
- CSV food bulk import UI
- Data export
- Weight trend charts

### Known bugs / issues

- **None confirmed open** at handoff time on feature branch
- **Branch divergence:** `main` is 1 commit ahead (`9b19771` deployment prep) of `cursor/health-tracker-mvp-7132`

### What was last being done

The **previous agent turn completed OpenAI Vision integration** (`a06daae`):
- Implemented `vision_food_estimator.py`
- Updated meal flow in `day.py`
- Updated UI for estimation source/confidence/range
- Verified fallback when `OPENAI_API_KEY` unset
- Updated README

The **user's last message before this handoff request** was:

> "还有token吗"

This was a **meta question** about whether the conversation could continue (token budget), NOT a feature request. Agent responded affirmatively and listed possible next steps.

**This handoff request** is the current task: generate this context document.

---

## Files and Codebase State

### Repository layout

```text
/workspace/
  README.md                          # Root pointer to health_tracker/
  package.json                       # TS nutrition demo (root level)
  package-lock.json
  tsconfig.json
  src/nutrition/                     # Standalone TS module (NOT wired to Python)
  health_tracker/                    # Main Python app
    main.py
    requirements.txt
    README.md
    .env.example
    health_tracker.db                # Created at runtime (gitignored)
    app/
      database.py
      models.py
      schemas.py
      routers/
      services/
      templates/
      static/
      uploads/
```

---

### `health_tracker/main.py`

**Purpose:** FastAPI entry point, DB init, router mounting, static/uploads mounts.

**Changes made:**
- Title: "cutnbulk"
- Calls `ensure_sqlite_schema()` and `seed_food_database()` at startup
- Includes routers: calendar, day, foods, goal, summary, meals, workouts, body, weekly

**Important current logic:**
- No `/health` endpoint on feature branch (exists on `main` only)
- Legacy routers still mounted

**Do not change without reason:**
- Startup seeding pattern (idempotent via `normalized_name` check)

---

### `health_tracker/app/database.py`

**Purpose:** SQLAlchemy engine, session, schema migration helper.

**Changes made:**
- `ensure_sqlite_schema()` adds columns to existing SQLite `meal_entries` if missing:
  - `meal_name`, `estimate_confidence`, `estimate_reasoning`
  - `estimate_source`, `calorie_range_low`, `calorie_range_high`, `uncertainty_factors`

**On `main` branch (NOT current feature branch):**
- Supports `DATABASE_URL` env var for non-SQLite deployment
- `pool_pre_ping=True`

**Known issues:** None

---

### `health_tracker/app/models.py`

**Purpose:** SQLAlchemy ORM models.

**Key models:**

| Model | Table | Purpose |
|-------|-------|---------|
| `MealEntry` | `meal_entries` | Per-meal food records with estimation metadata |
| `FoodItem` | `food_items` | Per-100g nutrition database |
| `MealFoodMatch` | `meal_food_matches` | Matched ingredients per meal estimate |
| `DailyEntry` | `daily_entries` | Daily body/training/legacy food fields |
| `GoalSetting` | `goal_settings` | Active fitness goal |
| `WorkoutEntry` | `workout_entries` | Legacy workout log |
| `BodyMetric` | `body_metrics` | Legacy body metrics |

**MealEntry estimation fields:**
- `estimate_confidence`, `estimate_reasoning`, `estimate_source`
- `calorie_range_low`, `calorie_range_high`
- `uncertainty_factors` (JSON string)

**Do not change:**
- Keep `waist_cm` on `DailyEntry` / `BodyMetric` for backward compatibility even though UI removed it

---

### `health_tracker/app/routers/calendar.py`

**Purpose:** Homepage calendar, `/today` redirect.

**Routes:**
- `GET /` — calendar with month navigation
- `GET /today` — redirect to today's day page

**Important logic:**
- Aggregates `MealEntry` calories per date for calendar cells
- Shows `active_goal`, `today_goal_progress`, `month_summary`

---

### `health_tracker/app/routers/day.py`

**Purpose:** Primary daily record + meal CRUD.

**Routes:**
- `GET /day/{entry_date}`
- `POST /day/{entry_date}` — save DailyEntry (body/training/legacy food)
- `POST /day/{entry_date}/meals` — create meal
- `POST /day/{entry_date}/meals/{meal_id}/update`
- `POST /day/{entry_date}/meals/{meal_id}/delete`

**Critical logic — `_apply_meal_form`:**
```python
prefer_vision = bool(image_path) and not _has_manual_nutrition(calories, protein_g, carbs_g, fat_g)
if prefer_vision:
    estimate = estimate_food_from_image(db, image_path or meal.image_path, clean_description)
else:
    estimate = estimate_meal_nutrition(db, clean_description, image_path or meal.image_path)
```

**Important functions:**
- `_apply_meal_form`, `_sync_meal_matches`, `_meal_totals`, `_save_upload`

**Known issues:** None confirmed

---

### `health_tracker/app/routers/goal.py`

**Purpose:** Goal setting form.

**Routes:** `GET/POST /goal`

**Uses:** `validate_goal`, `calculate_goal`, `get_active_goal`

---

### `health_tracker/app/routers/foods.py`

**Purpose:** Food database browse/search and add custom food.

**Routes:**
- `GET /foods`, `GET /foods/new`
- `POST /foods/new`

**Note:** `active_page` set to `"summary"` (not a dedicated nav item)

---

### `health_tracker/app/routers/summary.py`

**Purpose:** 7-day trend summary using `MealEntry` aggregates.

**Route:** `GET /summary`

---

### Legacy routers (still in codebase)

| File | Prefix | Status |
|------|--------|--------|
| `meals.py` | `/meals` | Mounted, not in primary nav |
| `workouts.py` | `/workouts` | Mounted, not in primary nav |
| `body.py` | `/body` | Mounted, not in primary nav |
| `weekly.py` | `/weekly` | Mounted, not in primary nav |
| `dashboard.py` | unknown | **NOT mounted** in `main.py` |

---

### `health_tracker/app/services/nutrition_estimator.py`

**Purpose:** Primary local text-based estimation via `FoodItem` DB.

**Key types:**
- `MatchedFood`, `NutritionEstimateResult`

**Estimation flow:**
1. `normalize_text(description)`
2. `_match_food_items` against all `FoodItem` names/aliases
3. `estimate_portion_grams` with `_parse_explicit_grams`, `_parse_count`, portion keywords
4. Aggregate macros + confidence + reasoning
5. If no matches → `_fallback_estimate` → `food_ai_service.estimate_food_nutrition`

**Critical regex (portion fix):**
```python
def _parse_explicit_grams(before: str, after: str) -> float | None:
    match = re.search(r"(\d+(?:\.\d+)?)\s*(?:g|克)\s*$", before)
    if match:
        return float(match.group(1))
    match = re.search(r"^\s*(\d+(?:\.\d+)?)\s*(?:g|克)(?:\s|$)", after)
    if match:
        return float(match.group(1))
    return None
```

**Source values:** `"food_database"`, `"fallback"` (via `_fallback_estimate`)

---

### `health_tracker/app/services/vision_food_estimator.py`

**Purpose:** OpenAI Vision photo estimation with fallback.

**Env vars:**
- `OPENAI_API_KEY=[REDACTED]`
- `OPENAI_FOOD_MODEL` (default `gpt-5.4-mini`)

**API:** OpenAI `client.responses.create` with `json_schema` strict output

**Image processing:** Resize to max 1024px, JPEG quality 78, base64 data URL

**Source values:**
- `"vision_ai"` — successful API call
- `"fallback"` — no key or API error (prepends reason to reasoning)

**Do not change:**
- Exception handling must remain non-blocking for meal save

---

### `health_tracker/app/services/food_ai_service.py`

**Purpose:** Original mock estimation; final fallback.

**Important:** Contains `_estimate_with_openai_placeholder` that does NOT call real Vision API even if key is set. Real Vision is ONLY in `vision_food_estimator.py`.

**Template estimates:** 鸡胸肉+米饭+西兰花, 牛肉面, 黄焖鸡米饭, etc.

---

### `health_tracker/app/services/food_seed_service.py`

**Purpose:** Seed ~78 Chinese-friendly food items at startup.

**Function:** `seed_food_database(db) -> int` — inserts only new `normalized_name`

**Constant:** `SEED_FOOD_ITEMS` — staples, proteins, Chinese dishes, drinks, snacks

---

### `health_tracker/app/services/food_import_service.py`

**Purpose:** Placeholder for CSV import.

**Status:** `raise NotImplementedError("CSV food import UI is not implemented in the MVP.")`

---

### `health_tracker/app/services/goal_service.py`

**Purpose:** Goal calculation and daily progress.

**Constants:**
- `KCAL_PER_KG = 7700`
- `ACTIVITY_FACTORS`: sedentary=28, light=31, moderate=34, active=38 (kcal per kg bodyweight)

**Key functions:**
- `validate_goal`, `calculate_goal`, `build_goal_note`
- `get_active_goal`, `get_goal_progress_for_day`

---

### Templates

| File | Purpose |
|------|---------|
| `base.html` | App shell, app-bar, bottom-nav |
| `calendar.html` | Homepage calendar + goal card |
| `day.html` | Daily record + meal list/cards |
| `goal.html` | Goal form with segmented radios |
| `foods.html`, `food_new.html` | Food DB |
| `summary.html` | Trends |
| `partials/meal_form_fields.html` | Reusable meal form |

**UI labels for estimation source in `day.html`:**
- `estimate_source == "vision_ai"` → "AI 估算"
- `estimate_source == "fallback"` → "本地估算"

---

### Static assets

| File | Purpose |
|------|---------|
| `styles.css` | Mobile-first styles, app-shell, goal cards, meal cards, segmented controls |
| `app.js` | Meal templates, workout rows, training parts exclusivity, meal type custom name toggle |
| `images/logo.png` | App bar logo (placeholder/generated icon) |

---

### TypeScript module (`src/nutrition/`)

**Purpose:** Standalone rule-based Chinese dish breakdown. **NOT integrated into Python app.**

| File | Purpose |
|------|---------|
| `types.ts` | Interfaces: `EstimateResult`, `DishTemplate`, `UserModifiers`, etc. |
| `data/ingredients.ts` | ~20 base ingredients per 100g |
| `data/dishTemplates.ts` | 5 dishes: 沙县鸭腿饭, 煎饼果子, 黄焖鸡米饭, 番茄炒蛋盖饭, 麻辣烫 |
| `utils/matchDish.ts` | Exact/contains/fuzzy dish matching |
| `utils/applyModifiers.ts` | Modifier multipliers for rice, skin, sauce, oil, portion |
| `utils/calculateConfidence.ts` | Confidence + calorie range |
| `estimateDishNutrition.ts` | Main export |
| `demo.ts` | Demo cases |

**Run demo:**
```bash
npm install
npm run nutrition:demo
```

---

### Config / env

**`health_tracker/.env.example`:**
```text
OPENAI_API_KEY=
OPENAI_FOOD_MODEL=gpt-5.4-mini
```

**`health_tracker/requirements.txt`:**
```
fastapi
uvicorn[standard]
sqlalchemy
jinja2
python-multipart
openai
python-dotenv
pillow
```

**`.gitignore`:** `.venv/`, `.env`, `health_tracker.db`, `app/uploads/*`

---

### On `main` branch only (not on feature branch)

**`render.yaml`:**
- Render.com web service
- `rootDir: health_tracker`
- `healthCheckPath: /health`
- Env: `DATABASE_URL`, `SECRET_KEY`, `OPENAI_API_KEY`, `OPENAI_FOOD_MODEL`

**`main.py` addition:**
```python
@app.get("/health")
def health_check():
    return {"status": "ok", "app": "cutnbulk"}
```

---

## Changes Made in This Chat

Chronological / logical order across the full conversation:

1. **Created MVP from scratch** (`3a607b3`)
   - FastAPI + SQLite + Jinja2 health tracker
   - Routers: dashboard, meals, workouts, body, weekly
   - Basic templates and mock food AI

2. **Added Cursor Cloud dev environment docs** (`677abf3`)

3. **Functional convergence — calendar-centric** (`67d816c`)
   - Refocused around daily calendar entries
   - Introduced `DailyEntry` consolidated model

4. **Mobile-first redesign** (`81995e4`, `77e819d`)
   - App shell, app-bar, bottom-nav
   - Max-width mobile layout
   - Calendar as homepage

5. **Logo update** (`7602630`)
   - `app/static/images/logo.png`

6. **Multi-meal per day** (`a807b4e`, `082ec97`)
   - `MealEntry` CRUD on day page
   - Daily meal totals aggregation

7. **Goal setting + calorie targets** (`595a049`, `2dbdf1f`)
   - `GoalSetting` model, `/goal` page
   - Goal card on calendar, progress on day page

8. **Fix goal UI alignment** (`2520643`)
   - Segmented radio `.choice-input` / `.choice-label` pattern

9. **Food database + local estimator** (`65f19e3`, `81bb7ba`)
   - `FoodItem`, `MealFoodMatch`, `food_seed_service.py`
   - `nutrition_estimator.py`, `/foods` pages
   - Portion parsing regex fix

10. **TypeScript Chinese dish module** (`321bc8b`)
    - Root `src/nutrition/` with demo

11. **OpenAI Vision integration** (`a06daae`)
    - `vision_food_estimator.py`
    - MealEntry estimation metadata fields
    - UI for AI/local labels, ranges, uncertainty
    - `.env.example`, README updates

12. **On `main` (user/local, not feature branch):** Deployment prep (`9b19771`)
    - `render.yaml`, `/health`, DATABASE_URL support

---

## Critical Code / Snippets

### Meal vision priority (`day.py`)

```python
prefer_vision=bool(image_path) and not _has_manual_nutrition(calories, protein_g, carbs_g, fat_g)
```

### Vision fallback (`vision_food_estimator.py`)

```python
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    fallback = estimate_meal_nutrition(db, description, image_path)
    return _with_fallback_reason(fallback, "未配置 OPENAI_API_KEY，已使用本地食物库估算。")
```

### Goal calorie formula (`goal_service.py`)

```python
KCAL_PER_KG = 7700
estimated_maintenance = current_weight_kg * ACTIVITY_FACTORS[activity]
total_energy_delta = weight_delta * KCAL_PER_KG
daily_energy_delta = total_energy_delta / target_days
recommended_calories = final_maintenance + daily_energy_delta
```

### Standard run commands

```bash
cd health_tracker
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
# Open http://127.0.0.1:8000
```

### Cloud env fix (recurring)

```bash
sudo apt-get install -y python3.12-venv
```

### Test pages (curl)

```bash
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/today
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/foods
```

### OpenAI env setup

```bash
cp .env.example .env
# Edit .env: OPENAI_API_KEY=[REDACTED]
```

---

## Technical Architecture

| Layer | Technology | Notes |
|-------|------------|-------|
| Backend | FastAPI | Python ASGI |
| Templates | Jinja2 | Server-rendered HTML |
| ORM | SQLAlchemy 2.x style | `Mapped`, `mapped_column` |
| Database | SQLite (local) | File: `health_tracker.db` |
| Database (main branch) | SQLite or via `DATABASE_URL` | Deployment support on main only |
| Auth | None | Single-user local app |
| Frontend | HTML/CSS/vanilla JS | No React/Vue |
| File uploads | FastAPI `UploadFile` | Saved to `app/uploads/` |
| Static files | FastAPI `StaticFiles` | `/static`, `/uploads` |
| AI — Vision | OpenAI Responses API | Model: `gpt-5.4-mini` default |
| AI — Text fallback | Rule-based local | Food DB + mock |
| Image processing | Pillow | Resize/compress before Vision API |
| Env loading | python-dotenv | `.env` in health_tracker |
| TS module runtime | Node + tsx | Separate from Python app |
| Package managers | pip (Python), npm (TS demo) | |
| Hosting | Unknown / not deployed on feature branch | `render.yaml` exists on `main` only |
| CI/CD | Unknown / not confirmed | |
| Authentication | None | |
| Multi-user | Not supported | |

### Estimation pipeline (meals)

```text
User submits meal with optional photo + description
        │
        ▼
Has photo AND no manual nutrition fields?
   YES │ NO
       ▼    └──────────────────┐
estimate_food_from_image()      │
       │                        ▼
       ├─ No API key ──► estimate_meal_nutrition() + source=fallback
       ├─ API error ───► estimate_meal_nutrition() + source=fallback
       └─ Success ─────► source=vision_ai
                                │
                                ▼
                    estimate_meal_nutrition()
                                │
                    Match FoodItem DB + portion parse
                                │
                         No match?
                                ▼
                    food_ai_service mock fallback
```

### TypeScript module

Completely separate CLI/demo module. Does NOT connect to FastAPI.

---

## Decisions Made

### Decision: Local-first, no mandatory API keys

**Reason:** User is beginner, wants app to work offline/locally; explicitly discussed cost concerns.

**Alternatives:** Require OpenAI for all estimates — rejected.

---

### Decision: Calendar homepage, not dashboard

**Reason:** User requested functional convergence to daily calendar record.

**Alternatives:** Keep multi-page dashboard as homepage — rejected.

---

### Decision: Multi-meal via `MealEntry`, not single daily food field

**Reason:** User wanted per-meal photos, edits, aggregation.

**Alternatives:** Keep only `DailyEntry.food_description` — superseded but legacy fields retained.

---

### Decision: Keep legacy routers mounted

**Reason:** Minimize breaking changes; low cost to keep.

**Alternatives:** Delete old routes — not requested.

---

### Decision: Vision in separate service, not extending `food_ai_service.py`

**Reason:** Clear separation; `food_ai_service` remains mock fallback; meal router calls `vision_food_estimator` directly.

**Alternatives:** Put Vision inside `food_ai_service` placeholder — partially started in placeholder but real impl is separate file.

---

### Decision: TypeScript dish module as standalone

**Reason:** User asked for independent module with demo; integration into Python not requested.

**Alternatives:** Port logic to Python — not done.

---

### Decision: Mobile shell max-width ~430px on desktop

**Reason:** User wants phone-like experience even on desktop.

---

### Decision: Hide `waist_cm` in UI, keep in DB

**Reason:** User wanted simpler daily form; avoid data loss.

---

### Decision: SQLite schema migration via `ensure_sqlite_schema()` ALTER TABLE

**Reason:** MVP simplicity; avoid Alembic for local single-user app.

**Alternatives:** Full migration framework — not adopted.

---

### Decision: Use OpenAI Responses API + JSON Schema (strict)

**Reason:** Structured nutrition output with confidence, ranges, ingredients.

---

### Decision: `render.yaml` on main for future deploy

**Reason:** User discussed publishing; deployment prep added on main.

**Status on feature branch:** Not merged as of handoff.

---

## Failed Attempts / Things That Did Not Work

### Attempt: Headless Chrome for mobile UI verification

**Result:** Hung/crashed in cloud environment.

**Do NOT retry:** `google-chrome --headless=new` for layout verification in Cursor cloud.

**Resolution:** Use `curl` + HTML inspection (`rg` for CSS classes/structure).

---

### Attempt: `curl -L -X POST` following 303 redirects

**Result:** POST replayed on redirect → duplicate submissions / bad test data.

**Do NOT retry:** `-L` on POST for form testing.

**Resolution:** POST without `-L`, then GET to verify; or inspect DB directly.

---

### Attempt: `curl -d` with Chinese form fields

**Result:** Encoding issues, garbled DB text, test failures.

**Resolution:** Use `--data-urlencode "name=中文"`.

---

### Attempt: User-provided Mac local logo path in cloud

**Result:** Cloud agent cannot access user's Mac filesystem.

**Resolution:** Created `app/static/images/logo.png` in repo; user can replace.

---

### Attempt: `python3 -m venv` without python3-venv package

**Error:**
```text
The virtual environment was not created because ensurepip is not available.
```

**Resolution:**
```bash
sudo apt-get install -y python3.12-venv
```

**Note:** Recurring in cloud environments — install venv package when needed.

---

## Errors and Debugging History

### 1. TemplateResponse TypeError: unhashable type 'dict'

**Error:**
```text
TypeError: unhashable type: 'dict'
```

**Cause:** Starlette/FastAPI API change — old positional `TemplateResponse("x.html", {...})` signature.

**Fix:** Use keyword args:
```python
templates.TemplateResponse(name="day.html", request=request, context={...})
```

**Status:** Fixed across all routers.

---

### 2. Router 307 redirects on trailing slash

**Cause:** `/meals` vs `/meals/` mismatch.

**Fix:** Dual decorators:
```python
@router.get("")
@router.get("/")
```

**Status:** Fixed.

---

### 3. Food portion parsing — 150g applied to wrong item

**Cause:** Overly broad regex for grams.

**Fix:** Require word boundary after unit: `(?:g|克)(?:\s|$)`

**File:** `nutrition_estimator.py` → `_parse_explicit_grams`

**Status:** Fixed.

---

### 4. Goal setting UI misalignment

**User feedback:** "这些UI都对不齐"

**Cause:** Native radio buttons visible; segmented CSS not applied correctly.

**Fix:** Hidden `.choice-input` + styled `.choice-label` in `goal.html` + `styles.css`

**Status:** Fixed (`2520643`).

---

### 5. MealEntry creation missing fields / estimate not returned

**Cause:** Incomplete `_apply_meal_form` refactor.

**Fix:** `_apply_meal_form` returns `estimate`; `_sync_meal_matches` called after flush.

**Status:** Fixed.

---

### 6. User confusion — desktop folder named cutnbulk with only an image

**Context:** User had a desktop folder that wasn't the project repo.

**Resolution:** Clarified project lives in git repo `health_tracker/` subdirectory.

---

## Commands Used

```bash
# Project setup
cd health_tracker
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Cloud venv fix
sudo apt-get install -y python3.12-venv

# Run server
uvicorn main:app --reload
uvicorn main:app --host 0.0.0.0 --port 8000 --reload   # LAN access for phone

# TS nutrition demo
npm install
npm run nutrition:demo

# Git
git checkout -b cursor/<name>-7132
git add -A && git commit -m "..."
git push -u origin cursor/health-tracker-mvp-7132

# Testing
curl -s http://127.0.0.1:8000/
curl --data-urlencode "description=米饭" ...   # Chinese form posts

# Env
cp .env.example .env
```

---

## User Preferences

### Product / UX

- **Mobile-first** — primary design target; desktop shows phone-width shell
- **Simple, focused UX** — calendar-centric; don't over-expand page count in primary flow
- **Chinese UI copy** — all user-facing text in Chinese
- **Practical honesty about estimates** — user questioned if estimates were fake; prefers transparent confidence/reasoning
- **Manual correction allowed** — estimates are helpers, not authoritative
- **Local use first** — user chose local phone access over immediate public deployment

### Technical

- **Python stack** as specified (FastAPI, Jinja2, SQLite, SQLAlchemy)
- **Beginner-friendly explanations** — user is first-time developer; needs step-by-step run instructions
- **Works without paid API** — important given cost discussions
- **Cursor cloud AND local Mac** — both environments matter to user

### Communication

- User asks practical "what do I type next" questions
- User confirms success briefly ("OK成功打开了")
- User may pause and return next day

### Not confirmed

- Preferred commit message style
- Whether user wants bullet-heavy vs prose responses (no strong preference stated)

---

## Important User Quotes

> "你是一名资深全栈工程师和产品工程师。请从 0 开始帮我创建一个 Python 项目：一个'饮食 + 训练 + 身体数据记录'的本地网页 App MVP。"

> "我第一次做project，你告诉我这些怎么运行"

> "是在电脑的terminal还是cursor的terminal"

> "OK成功打开了。我明天再找你做修改"

> "你是一名资深产品工程师和全栈工程师。请帮我对我当前 cutnbulk 项目做一次功能收敛和重构。"

> "我不想只在本地运行了，我想让其他人也能在他们手机里运行"

> "那我还是先本地在我的手机上运行吧，你给我最详细的步骤"

> "所以只有在电脑开着的时候才能运行"

> "这个估算是瞎估算的吧"

> "这些UI都对不齐。"

> "请帮我给 cutnbulk 增加'拍照估算热量和三大营养素'的功能，使用 OpenAI API 的视觉模型。"

> "还有token吗"

---

## Open Tasks / TODO

### Completed in this chat window

- [x] MVP creation (diet + training + body)
- [x] Mobile-first calendar-centric refactor
- [x] Multi-meal logging per day
- [x] Goal setting + daily calorie recommendations
- [x] Food database + local nutrition estimator
- [x] TypeScript standalone Chinese dish module
- [x] OpenAI Vision photo estimation with fallback
- [x] Goal UI alignment fix
- [x] Portion parsing regex fix
- [x] Context handoff document (this file)

### Pending / not done

- [ ] **Merge deployment commit from `main`** (`9b19771`) into feature branch OR reconcile branches — includes `render.yaml`, `/health`, `DATABASE_URL` support
- [ ] **End-to-end Vision API test with real `OPENAI_API_KEY`** — only fallback path verified in cloud agent environment without key
- [ ] **Integrate TypeScript `src/nutrition` into Python meal estimation** — if user wants unified dish breakdown in app (not requested yet)
- [ ] **Add `/foods` to bottom navigation** — page exists but not linked in nav
- [ ] **Remove or redirect legacy routes** (`/meals`, `/workouts`, `/body`, `/weekly`) — if user wants full cleanup
- [ ] **Clean up `DailyEntry` legacy food fields** in `save_day` — still writes old food fields alongside `MealEntry` flow
- [ ] **CSV food import UI** — placeholder only
- [ ] **Public deployment** — discussed but user chose local-first; `render.yaml` on main not on feature branch
- [ ] **Weight trend charts / data export** — not requested but natural extensions
- [ ] **Replace placeholder logo** — user may have own logo image locally

### Need user decision

- [ ] Whether to merge `main`'s deployment prep into feature branch
- [ ] Whether to wire TS nutrition module into Python backend
- [ ] Whether to proceed with Render/public hosting
- [ ] Whether to remove legacy pages from codebase

### Need verification (by user locally)

- [ ] Vision estimation with real API key + actual food photo on user's Mac
- [ ] Phone access via LAN (`uvicorn --host 0.0.0.0`) on user's home network

---

## Recommended Next Steps

1. **Read actual codebase** on checkout branch — confirm branch vs `main` divergence (`render.yaml`, `/health`, vision columns in `ensure_sqlite_schema` on main may differ).

2. **If user wants deployment:** Merge or cherry-pick `9b19771` from `main`; verify `/health` and `DATABASE_URL`; deploy to Render using `render.yaml`.

3. **If user wants Vision testing:** Have user set `OPENAI_API_KEY=[REDACTED]` in `health_tracker/.env`, restart uvicorn, upload meal photo without filling macros, confirm "AI 估算" label and ingredient breakdown.

4. **If user wants better text estimates for combo dishes:** Consider integrating `src/nutrition/estimateDishNutrition.ts` logic into Python (port templates) OR call Node subprocess — discuss tradeoffs first.

5. **If user wants UX polish:** Add `/foods` link somewhere visible; consider removing legacy nav pages or adding redirects.

6. **Do NOT restart from scratch** — extend existing `day.py` meal flow and services.

---

## Git / PR State

| Item | Value |
|------|-------|
| Feature branch | `cursor/health-tracker-mvp-7132` |
| Latest commit | `a06daae` Add OpenAI vision meal estimation |
| `main` ahead by | `9b19771` Prepare cutnbulk for public deployment |
| Draft PR | #1 "Create local health tracker MVP" |
| Branch naming convention (cloud agent) | `cursor/<descriptive-name>-7132` |

---

## Instructions for the Next Cursor Agent

Before doing anything:

1. **Read this entire document carefully.**
2. **Treat this document as the continuation context of the previous Cursor chat.**
3. **Do not restart the task from scratch.**
4. **Do not undo previous decisions** unless the user explicitly requests it.
5. **Inspect the actual current codebase before editing** because files may contain changes made after parts of this document were discussed (especially check `main` vs feature branch divergence).
6. **Continue from the `Current Project State`, `Open Tasks`, and `Recommended Next Steps` sections.**
7. **Preserve all user preferences and constraints documented above.**
8. **If the current code conflicts with this document, prefer the actual current code for implementation state**, but use this document to understand intent and reasoning.
9. **Do not ask the user to repeat information already contained in this document.**
10. **User is a beginner** — provide concrete terminal commands when explaining how to run or test.
11. **Never commit secrets** — use `.env` locally; reference `OPENAI_API_KEY=[REDACTED]` only.
12. **Cloud agent branch naming:** use `cursor/<descriptive-name>-7132` suffix pattern when creating branches.

---

*End of context handoff.*
