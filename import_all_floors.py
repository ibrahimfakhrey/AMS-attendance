"""
Import schedules from all floor PDFs
"""

import os
import re
from import_schedule_smart import extract_schedules_from_pdf, import_to_database

def detect_floor_number(filename):
    """Extract floor number from filename"""
    # Look for patterns like "1st Floor", "2nd Floor", etc.
    match = re.search(r'(\d+)(?:st|nd|rd|th)\s+Floor', filename, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None

def import_all_floors():
    """Import schedules from all floor PDFs"""
    
    print("\n" + "="*80)
    print("🏫 Multi-Floor Schedule Import Tool")
    print("="*80)
    
    # Find all floor PDF files
    floor_pdfs = []
    for file in os.listdir('.'):
        if file.lower().endswith('.pdf') and 'floor' in file.lower():
            floor_num = detect_floor_number(file)
            if floor_num:
                floor_pdfs.append((floor_num, file))
    
    # Sort by floor number
    floor_pdfs.sort(key=lambda x: x[0])
    
    if not floor_pdfs:
        print("\n❌ No floor PDF files found!")
        print("   Looking for files like: '1st Floor Schedule.pdf'")
        return
    
    print(f"\n📚 Found {len(floor_pdfs)} floor PDF files:")
    for floor_num, filename in floor_pdfs:
        file_size = os.path.getsize(filename) / 1024  # KB
        print(f"   {floor_num}. Floor {floor_num}: {filename} ({file_size:.1f} KB)")
    
    # Ask for confirmation
    print("\n" + "="*80)
    response = input("📥 Import all floors? (yes/no): ").strip().lower()
    
    if response not in ['yes', 'y', 'نعم']:
        print("\n❌ Import cancelled.")
        return
    
    # Process each floor
    total_stats = {
        'floors_processed': 0,
        'floors_success': 0,
        'floors_failed': 0,
        'total_schedules': 0
    }
    
    for floor_num, filename in floor_pdfs:
        print("\n" + "="*80)
        print(f"📖 Processing Floor {floor_num}: {filename}")
        print("="*80)
        
        try:
            # Extract schedules
            schedules = extract_schedules_from_pdf(filename)
            
            if not schedules:
                print(f"⚠️  No schedules extracted from Floor {floor_num}")
                total_stats['floors_failed'] += 1
                continue
            
            print(f"\n✅ Extracted {len(schedules)} schedule entries")
            
            # Import to database
            import_to_database(schedules, floor_number=floor_num)
            
            total_stats['floors_processed'] += 1
            total_stats['floors_success'] += 1
            total_stats['total_schedules'] += len(schedules)
            
        except Exception as e:
            print(f"\n❌ Error processing Floor {floor_num}: {e}")
            total_stats['floors_failed'] += 1
            import traceback
            traceback.print_exc()
    
    # Final summary
    print("\n" + "="*80)
    print("🎉 IMPORT COMPLETE - FINAL SUMMARY")
    print("="*80)
    print(f"  Floors processed:        {total_stats['floors_processed']}")
    print(f"  ✅ Successfully imported: {total_stats['floors_success']}")
    print(f"  ❌ Failed:               {total_stats['floors_failed']}")
    print(f"  📊 Total schedules:      {total_stats['total_schedules']}")
    print("="*80)
    
    print("\n💡 Next steps:")
    print("   1. Run the Flask app: py app.py")
    print("   2. Visit: http://localhost:5000")
    print("   3. Browse all floors and classes with their complete schedules!")
    print("="*80)

if __name__ == '__main__':
    import_all_floors()


