# cutnbulk

多用户饮食日历网站。应用代码在 `health_tracker/`。

```bash
cd health_tracker
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn main:app --reload
```

完整说明见 `health_tracker/README.md`。
