"""
Diagnostic script to examine PDF structure
"""

import pdfplumber
import sys

def diagnose_pdf(pdf_path):
    """Examine the PDF structure"""
    print("="*80)
    print(f"📄 Analyzing PDF: {pdf_path}")
    print("="*80)
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            print(f"\n📚 Total pages: {len(pdf.pages)}")
            
            for page_num, page in enumerate(pdf.pages, 1):
                print(f"\n{'='*80}")
                print(f"📖 PAGE {page_num}")
                print(f"{'='*80}")
                
                # Page dimensions
                print(f"\n📏 Dimensions: {page.width} x {page.height}")
                
                # Extract text
                text = page.extract_text()
                if text:
                    print(f"\n📝 Text Content (first 800 characters):")
                    print("-" * 80)
                    print(text[:800])
                    if len(text) > 800:
                        print(f"\n... ({len(text) - 800} more characters)")
                else:
                    print("\n⚠️  No text found on this page")
                
                # Extract tables
                tables = page.extract_tables()
                print(f"\n📊 Number of tables: {len(tables)}")
                
                if tables:
                    for table_idx, table in enumerate(tables, 1):
                        print(f"\n  Table {table_idx}:")
                        print(f"  Rows: {len(table)}, Columns: {len(table[0]) if table else 0}")
                        
                        print(f"\n  First 5 rows:")
                        for row_idx, row in enumerate(table[:5], 1):
                            print(f"    Row {row_idx}: {row}")
                        
                        if len(table) > 5:
                            print(f"    ... and {len(table) - 5} more rows")
                
                # Extract words with positions
                words = page.extract_words()
                if words:
                    print(f"\n🔤 Number of words: {len(words)}")
                    print(f"\n  First 10 words:")
                    for word in words[:10]:
                        print(f"    '{word['text']}' at ({word['x0']:.1f}, {word['top']:.1f})")
                
                print(f"\n{'-'*80}")
                
                if page_num >= 3:  # Only show first 3 pages in detail
                    remaining = len(pdf.pages) - page_num
                    if remaining > 0:
                        print(f"\n... {remaining} more pages (skipped for brevity)")
                    break
    
    except FileNotFoundError:
        print(f"\n❌ Error: PDF file '{pdf_path}' not found!")
        print(f"   Current directory: {sys.path[0]}")
        return False
    except Exception as e:
        print(f"\n❌ Error reading PDF: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print(f"\n{'='*80}")
    print("✅ Analysis complete!")
    print(f"{'='*80}")
    return True

if __name__ == '__main__':
    pdf_path = "2nd Floor Schedule 28-Sep-25.pdf"
    diagnose_pdf(pdf_path)


