import os
from ingestion.processor import ingest_files

# data/inputs klasöründeki dosyaları bul
input_folder = os.path.join(os.getcwd(), "data", "inputs")
files = [os.path.join(input_folder, f) for f in os.listdir(input_folder) if f.endswith(('.pdf', '.xlsx'))]

if files:
    vdb, store = ingest_files(files)
    print("\n--- SONUÇ ---")
    print(f"DataFrame Deposundaki Dosyalar: {list(store.keys())}")
else:
    print("⚠️ data/inputs klasörüne test için dosya ekleyin!")