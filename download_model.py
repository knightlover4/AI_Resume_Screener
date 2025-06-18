# download_model.py
from sentence_transformers import SentenceTransformer

# --- CHANGE THE MODEL NAME HERE ---
MODEL_NAME = 'all-MiniLM-L6-v2'
print(f"Downloading and caching model '{MODEL_NAME}'...")
SentenceTransformer(MODEL_NAME)
print("Model download complete.")