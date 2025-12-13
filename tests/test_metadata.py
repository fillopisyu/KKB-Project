"""
Test script to verify page number metadata preservation in chunks.
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingestion.processor import process_vector
from langchain_chroma import Chroma
from core.config import embedding_model, VECTOR_DB_PATH

def test_metadata_preservation():
    """Test that page metadata is preserved in chunks."""
    print("=" * 60)
    print("TEST: Metadata Preservation in Chunks")
    print("=" * 60)
    
    # Find a PDF file in data/inputs
    test_dir = "data/inputs"
    pdf_files = []
    
    if os.path.exists(test_dir):
        for file in os.listdir(test_dir):
            if file.lower().endswith('.pdf'):
                pdf_files.append(os.path.join(test_dir, file))
    
    if not pdf_files:
        print("⚠️  No PDF files found in data/inputs/")
        print("   Please upload a PDF file first via the Streamlit interface.")
        return False
    
    # Test with first PDF found
    test_file = pdf_files[0]
    print(f"\n📄 Testing with: {os.path.basename(test_file)}")
    
    # Process the file
    print("\n🔄 Processing file...")
    chunks = process_vector(test_file, os.path.basename(test_file), '.pdf')
    
    if not chunks:
        print("❌ No chunks created!")
        return False
    
    print(f"✅ Created {len(chunks)} chunks\n")
    
    # Check first 3 chunks for metadata
    print("📊 Checking metadata in first 3 chunks:")
    print("-" * 60)
    
    has_page_numbers = False
    for i, chunk in enumerate(chunks[:3]):
        print(f"\n📌 Chunk {i+1}:")
        print(f"   Content preview: {chunk.page_content[:80]}...")
        print(f"   Metadata: {chunk.metadata}")
        
        # Verify metadata
        if 'source' in chunk.metadata:
            print(f"   ✓ Source: {chunk.metadata['source']}")
        else:
            print("   ✗ Source: MISSING!")
        
        if 'page' in chunk.metadata:
            print(f"   ✓ Page: {chunk.metadata['page'] + 1}")  # +1 for human-readable
            has_page_numbers = True
        else:
            print("   ✗ Page: MISSING!")
    
    print("\n" + "=" * 60)
    if has_page_numbers:
        print("✅ TEST PASSED: Page numbers are preserved!")
    else:
        print("❌ TEST FAILED: Page numbers are missing!")
    print("=" * 60)
    
    return has_page_numbers


def test_vector_db_metadata():
    """Test that stored chunks in vector DB have page metadata."""
    print("\n" + "=" * 60)
    print("TEST: Vector DB Metadata Check")
    print("=" * 60)
    
    if not os.path.exists(VECTOR_DB_PATH):
        print("⚠️  Vector DB not found. Please ingest files first.")
        return False
    
    # Connect to vector DB
    print("\n🔗 Connecting to Vector DB...")
    db = Chroma(persist_directory=VECTOR_DB_PATH, embedding_function=embedding_model)
    
    # Get all documents
    data = db.get()
    
    if not data or not data.get('metadatas'):
        print("❌ No documents in Vector DB!")
        return False
    
    total_docs = len(data['metadatas'])
    docs_with_page = sum(1 for meta in data['metadatas'] if meta and 'page' in meta)
    
    print(f"\n📊 Vector DB Statistics:")
    print(f"   Total documents: {total_docs}")
    print(f"   Documents with page numbers: {docs_with_page}")
    print(f"   Coverage: {docs_with_page/total_docs*100:.1f}%")
    
    # Show sample metadata
    print(f"\n📌 Sample metadata (first 3 documents):")
    print("-" * 60)
    for i, meta in enumerate(data['metadatas'][:3]):
        print(f"\nDocument {i+1}: {meta}")
    
    print("\n" + "=" * 60)
    if docs_with_page > 0:
        print(f"✅ TEST PASSED: {docs_with_page}/{total_docs} documents have page numbers!")
    else:
        print("❌ TEST FAILED: No page numbers found in Vector DB!")
        print("   💡 Tip: Delete vector_db folder and re-ingest PDFs with new code.")
    print("=" * 60)
    
    return docs_with_page > 0


if __name__ == "__main__":
    print("\n🧪 Running Metadata Tests...\n")
    
    # Test 1: Fresh processing
    test1_passed = test_metadata_preservation()
    
    # Test 2: Vector DB storage
    test2_passed = test_vector_db_metadata()
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 TEST SUMMARY")
    print("=" * 60)
    print(f"Metadata Preservation: {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(f"Vector DB Storage:     {'✅ PASSED' if test2_passed else '❌ FAILED'}")
    
    if not test2_passed and test1_passed:
        print("\n💡 Action Required:")
        print("   The new code works, but old data doesn't have page numbers.")
        print("   Delete 'data/vector_db' folder and re-upload your PDFs.")
    
    print("=" * 60 + "\n")
