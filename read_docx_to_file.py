import zipfile
import re

filename = "Greendeks Autofill Rehber Doküman.docx"
outfile = "extracted_text.txt"

try:
    with zipfile.ZipFile(filename) as z:
        xml_content = z.read("word/document.xml").decode("utf-8")
        # Find text
        texts = re.findall(r'<w:t[^>]*>(.*?)</w:t>', xml_content)
        full_text = "\n".join(texts)
        
        with open(outfile, "w", encoding="utf-8") as f:
            f.write(full_text)
            
    print(f"Authored {outfile}")
except Exception as e:
    print(f"Error: {e}")
