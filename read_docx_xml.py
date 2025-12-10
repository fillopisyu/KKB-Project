import zipfile
import re

filename = "Greendeks Autofill Rehber Doküman.docx"

try:
    print(f"Opening {filename} as ZIP...")
    with zipfile.ZipFile(filename) as z:
        # Read the main document XML
        xml_content = z.read("word/document.xml").decode("utf-8")
        
        # Identify text nodes specifically to add spacing
        # <w:t>Text</w:t>
        texts = re.findall(r'<w:t[^>]*>(.*?)</w:t>', xml_content)
        
        full_text = " ".join(texts)
        print(full_text[:5000]) # Print valid chars
except Exception as e:
    print(f"Error: {e}")
