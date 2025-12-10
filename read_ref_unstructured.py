from unstructured.partition.docx import partition_docx
import os

filename = "Greendeks Autofill Rehber Doküman.docx"

try:
    print(f"Reading {filename}...")
    elements = partition_docx(filename)
    print("--- CONTENT ---")
    for el in elements:
        print(el.text)
        print("-" * 10)
except Exception as e:
    print(f"Error: {e}")
