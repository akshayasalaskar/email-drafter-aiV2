Run the backend (FastAPI)
In one terminal:

cd D:\email-drafter
python -m pip install -r requirements.txt
# set your key (in .env) first, then:
uvicorn server:app --reload --host 127.0.0.1 --port 8001
Quick check in browser: http://127.0.0.1:8001/health

Run the frontend (Streamlit)
In a second terminal:

cd D:\email-drafter
# point Streamlit to the backend port
$env:API_BASE_URL="http://127.0.0.1:8001"
streamlit run streamlit_app.py
