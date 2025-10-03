"""
Import schedule from a single floor PDF
Usage: py import_single_floor.py <floor_number>
Example: py import_single_floor.py 3
"""

import sys
import os
import re
from import_schedule_smart import extract_schedules_from_pdf, import_to_database

def find_floor_pdf(floor_number):
    """Find PDF file for the specified floor"""
    patterns = [
        f"{floor_number}st Floor",
        f"{floor_number}nd Floor",
        f"{floor_number}rd Floor",
        f"{floor_number}th Floor",
    ]
    
    for file in os.listdir('.'):
        if file.lower().endswith('.pdf'):
            for pattern in patterns:
                if pattern.lower() in file.lower():
                    return file
    return None

def import_floor(floor_number):
    """Import schedules for a specific floor"""
    
    print("\n" + "="*80)
    print(f"🏫 Floor {floor_number} Schedule Import")
    print("="*80)
    
    # Find PDF file
    pdf_file = find_floor_pdf(floor_number)
    
    if not pdf_file:
        print(f"\n❌ No PDF file found for Floor {floor_number}")
        print(f"   Looking for: '{floor_number}st/nd/rd/th Floor ....pdf'")
        return False
    
    print(f"\n📄 Found: {pdf_file}")
    
    # Extract schedules
    print(f"\n🔍 Extracting schedules...")
    schedules = extract_schedules_from_pdf(pdf_file)
    
    if not schedules:
        print(f"\n❌ No schedules extracted from {pdf_file}")
        return False
    
    print(f"\n✅ Extracted {len(schedules)} schedule entries")
    
    # Show sample
    print(f"\n📋 Sample (first 3 entries):")
    for i, entry in enumerate(schedules[:3], 1):
        print(f"\n  {i}. Class: {entry['class_name']}")
        print(f"     Day: {entry['day_name'].title()}")
        print(f"     Time: {entry['start_time'].strftime('%H:%M')} - {entry['end_time'].strftime('%H:%M')}")
        print(f"     Subject: {entry['subject']}")
        print(f"     Teacher: {entry['teacher']}")
    
    if len(schedules) > 3:
        print(f"\n  ... and {len(schedules) - 3} more entries")
    
    # Import
    print(f"\n📥 Importing to database...")
    import_to_database(schedules, floor_number=floor_number)
    
    print("\n" + "="*80)
    print(f"✅ Floor {floor_number} import completed successfully!")
    print("="*80)
    
    return True

def main():
    if len(sys.argv) < 2:
        print("\n" + "="*80)
        print("📚 Single Floor Import Tool")
        print("="*80)
        print("\nUsage:")
        print("  py import_single_floor.py <floor_number>")
        print("\nExamples:")
        print("  py import_single_floor.py 1    # Import 1st floor")
        print("  py import_single_floor.py 3    # Import 3rd floor")
        print("  py import_single_floor.py 5    # Import 5th floor")
        print("="*80)
        
        # Show available PDFs
        print("\n📄 Available floor PDFs:")
        found = False
        for file in sorted(os.listdir('.')):
            if file.lower().endswith('.pdf') and 'floor' in file.lower():
                print(f"   - {file}")
                found = True
        
        if not found:
            print("   (None found)")
        
        print("="*80)
        return
    
    try:
        floor_number = int(sys.argv[1])
        
        if floor_number < 1 or floor_number > 10:
            print(f"\n❌ Invalid floor number: {floor_number}")
            print("   Please use a number between 1 and 10")
            return
        
        import_floor(floor_number)
        
    except ValueError:
        print(f"\n❌ Invalid floor number: {sys.argv[1]}")
        print("   Please provide a number (e.g., 1, 2, 3)")

if __name__ == '__main__':
    main()


