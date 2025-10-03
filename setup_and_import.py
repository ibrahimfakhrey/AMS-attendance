"""
Complete setup: Initialize database and import all floor schedules
"""

import os
import re
from app import app, db
from import_schedule_smart import extract_schedules_from_pdf, import_to_database

def init_database():
    """Initialize the database"""
    print("\n" + "="*80)
    print("🔧 Step 1: Initializing Database")
    print("="*80)
    
    with app.app_context():
        db.create_all()
        print("✅ Database tables created!")
        print("  - Floor, Class, Teacher, Subject, Schedule, Attendance")
    
    return True

def detect_floor_number(filename):
    """Extract floor number from filename"""
    match = re.search(r'(\d+)(?:st|nd|rd|th)\s+Floor', filename, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None

def import_all_floors():
    """Import schedules from all floor PDFs"""
    
    print("\n" + "="*80)
    print("🔧 Step 2: Importing Floor Schedules")
    print("="*80)
    
    # Find all floor PDF files
    floor_pdfs = []
    for file in os.listdir('.'):
        if file.lower().endswith('.pdf') and 'floor' in file.lower():
            floor_num = detect_floor_number(file)
            if floor_num:
                floor_pdfs.append((floor_num, file))
    
    floor_pdfs.sort(key=lambda x: x[0])
    
    if not floor_pdfs:
        print("\n❌ No floor PDF files found!")
        return False
    
    print(f"\n📚 Found {len(floor_pdfs)} floor PDF files:")
    for floor_num, filename in floor_pdfs:
        file_size = os.path.getsize(filename) / 1024
        print(f"   Floor {floor_num}: {filename} ({file_size:.1f} KB)")
    
    # Process each floor
    total_stats = {
        'floors_success': 0,
        'floors_failed': 0,
        'total_schedules': 0,
        'total_classes': set(),
        'total_teachers': set(),
        'total_subjects': set()
    }
    
    for floor_num, filename in floor_pdfs:
        print("\n" + "-"*80)
        print(f"📖 Processing Floor {floor_num}: {filename}")
        print("-"*80)
        
        try:
            # Extract schedules
            print(f"  🔍 Extracting...")
            schedules = extract_schedules_from_pdf(filename)
            
            if not schedules:
                print(f"  ⚠️  No schedules extracted")
                total_stats['floors_failed'] += 1
                continue
            
            print(f"  ✅ Extracted {len(schedules)} entries")
            
            # Collect unique classes, teachers, subjects
            classes = set(s['class_name'] for s in schedules)
            teachers = set(s['teacher'] for s in schedules)
            subjects = set(s['subject'] for s in schedules)
            
            print(f"  📊 {len(classes)} classes, {len(teachers)} teachers, {len(subjects)} subjects")
            
            # Import to database
            print(f"  📥 Importing to database...")
            import_to_database(schedules, floor_number=floor_num)
            
            total_stats['floors_success'] += 1
            total_stats['total_schedules'] += len(schedules)
            total_stats['total_classes'].update(classes)
            total_stats['total_teachers'].update(teachers)
            total_stats['total_subjects'].update(subjects)
            
            print(f"  ✅ Floor {floor_num} completed!")
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
            total_stats['floors_failed'] += 1
    
    # Final summary
    print("\n" + "="*80)
    print("🎉 IMPORT COMPLETE - FINAL SUMMARY")
    print("="*80)
    print(f"  ✅ Floors imported:      {total_stats['floors_success']}/{len(floor_pdfs)}")
    print(f"  📊 Total schedules:      {total_stats['total_schedules']}")
    print(f"  📚 Total classes:        {len(total_stats['total_classes'])}")
    print(f"  👨‍🏫 Total teachers:       {len(total_stats['total_teachers'])}")
    print(f"  📖 Total subjects:       {len(total_stats['total_subjects'])}")
    print("="*80)
    
    return total_stats['floors_success'] > 0

def main():
    """Main setup and import"""
    
    print("\n" + "="*80)
    print("🏫 COMPLETE SCHOOL SETUP")
    print("   Database Initialization + All Floors Import")
    print("="*80)
    
    # Step 1: Initialize database
    if not init_database():
        print("\n❌ Database initialization failed!")
        return
    
    # Step 2: Import all floors
    success = import_all_floors()
    
    if success:
        print("\n" + "="*80)
        print("✅ SETUP COMPLETE! 🎉")
        print("="*80)
        print("\n💡 Next Steps:")
        print("   1. Start the app: py app.py")
        print("   2. Open browser: http://localhost:5000")
        print("   3. Explore all floors and classes!")
        print("   4. Start tracking attendance!")
        print("="*80)
    else:
        print("\n❌ Setup incomplete. Please check errors above.")

if __name__ == '__main__':
    main()


