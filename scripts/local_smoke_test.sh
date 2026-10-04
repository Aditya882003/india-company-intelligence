#!/bin/bash
set -euo pipefail
python3 -m py_compile streamlit_app.py etl/run_pipeline.py etl/live_market.py etl/news_sources.py
python3 scripts/migrate_db.py
pytest -q
printf '\nSmoke test complete. Start the dashboard with:\n  streamlit run streamlit_app.py\n'
