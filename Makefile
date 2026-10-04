install:
	python -m pip install -r requirements.txt

seed:
	python etl/make_demo_data.py

refresh:
	python etl/run_pipeline.py --period 1y

run:
	streamlit run streamlit_app.py

test:
	pytest -q
