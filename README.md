How to start

pip install -r requirements.txt

go to .env.example and then fill your api key and email

create to terminal
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

streamlit run /frontend/streamlit_app.py
