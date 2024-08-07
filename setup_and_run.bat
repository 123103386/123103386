@echo off
cd "C:\Users\navy\OneDrive - University College Cork\Desktop\Streamlit_App"
python -m venv venv
call venv\Scripts\activate
pip install streamlit pandas folium streamlit-folium scipy numpy matplotlib scikit-learn
mkdir labeled_data
streamlit run labeling_app.py
