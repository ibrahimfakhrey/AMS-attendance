"""
Import schedules from floors 1, 3, 4, and 5
Enhanced version with thorough validation and verification
"""

import pdfplumber
import re
from datetime import time
from app import app, db, Floor, Class, Teacher, Subject, Schedule

# Day mapping
DAY_MAPPING = {
    'sunday': 6,
    'monday': 0,
    'tuesday': 1,
    'wednesday': 2,
    'thursday': 3,
    'friday': 4,
    'saturday': 5,
}

# Time periods mapping - Standard school schedule
TIME_PERIODS = {
    '1': ('08:30', '09:05'),
    '2': ('09:05', '09:40'),
    '3': ('09:40', '10:20'),
    '4': ('10:20', '11:00'),
    '5': ('11:00', '11:40'),
    '6': ('11:40', '12:20'),
    '7': ('12:20', '13:00'),
    '8': ('13:00', '13:40'),
    '9': ('13:40', '14:15'),
    '10': ('14:15', '14:50'),
}

def parse_time(time_str):
    """Parse time string to time object"""
    try:
        h, m = map(int, time_str.split(':'))
        return time(h, m)
    except:
        return None

def extract_subject_and_teacher(cell_text):
    """
    Extract subject and teacher from cell text
    Format typically: "Subject\nTeacher Name"
    Returns: (subject, teacher) or (None, None)
    """
    if not cell_text or cell_text.strip() == '':
        return None, None
    
    cell_text = cell_text.strip()
    
    # Skip non-academic cells (breaks, assembly, etc.)
    skip_keywords = ['assembly', 'breakfast', 'break', 'ylbmessa', 'tsafkaerb', 'kaerb', 'lunch', 'recess']
    if any(kw in cell_text.lower() for kw in skip_keywords):
        return None, None
    
    # Skip if cell is too short or just whitespace
    if len(cell_text) < 2:
        return None, None
    
    # Split by newline
    lines = [line.strip() for line in cell_text.split('\n') if line.strip()]
    
    if not lines:
        return None, None
    
    # First non-empty line is the subject
    subject = lines[0]
    
    # Remaining lines form the teacher name
    teacher = ' '.join(lines[1:]) if len(lines) > 1 else 'Unknown Teacher'
    
    # Clean up
    subject = subject.strip()
    teacher = teacher.strip()
    
    # Validate - must have reasonable content
    if len(subject) < 2:
        return None, None
    
    return subject, teacher

def extract_schedules_from_pdf(pdf_path, floor_number):
    """
    Extract schedule data from PDF with thorough validation
    Returns list of schedule dictionaries
    """
    all_schedules = []
    
    print("="*80)
    print(f"📄 Extracting schedules from: {pdf_path}")
    print(f"🏢 Floor: {floor_number}")
    print("="*80)
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            print(f"📚 Total pages in PDF: {len(pdf.pages)}")
            
            for page_num, page in enumerate(pdf.pages, 1):
                print(f"\n{'='*80}")
                print(f"📖 Processing Page {page_num} of {len(pdf.pages)}")
                print(f"{'='*80}")
                
                # Extract tables from page
                tables = page.extract_tables()
                
                if not tables:
                    print("  ⚠️  No tables found on this page")
                    # Try extracting text to see what's on the page
                    text = page.extract_text()
                    if text:
                        print(f"  📝 Page text preview: {text[:200]}...")
                    continue
                
                print(f"  📊 Found {len(tables)} table(s) on this page")
                
                # Process the main table (usually the first and largest)
                table = tables[0]
                print(f"  📏 Table dimensions: {len(table)} rows x {len(table[0]) if table else 0} columns")
                
                # Determine the day from the page
                day_name = None
                day_num = None
                
                # Method 1: Look in the first few rows for day name
                for row_idx in range(min(3, len(table))):
                    if not table[row_idx]:
                        continue
                    for cell in table[row_idx]:
                        if not cell:
                            continue
                        cell_lower = str(cell).lower()
                        for day_key, day_value in DAY_MAPPING.items():
                            if day_key in cell_lower:
                                day_name = day_key
                                day_num = day_value
                                break
                        if day_name:
                            break
                    if day_name:
                        break
                
                # Method 2: Extract from page text
                if not day_name:
                    text = page.extract_text()
                    if text:
                        text_lower = text.lower()
                        for day_key, day_value in DAY_MAPPING.items():
                            if day_key in text_lower:
                                day_name = day_key
                                day_num = day_value
                                break
                
                if not day_name:
                    print(f"  ⚠️  Could not determine day for page {page_num} - SKIPPING")
                    continue
                
                print(f"  📅 Day detected: {day_name.upper()} (day number: {day_num})")
                
                # Find the row with period numbers (usually row 2 or 3)
                period_row_idx = None
                period_columns = {}
                
                for row_idx in range(min(5, len(table))):
                    if not table[row_idx]:
                        continue
                    
                    # Check if this row contains period numbers
                    period_count = 0
                    temp_period_cols = {}
                    
                    for col_idx, cell in enumerate(table[row_idx]):
                        if not cell:
                            continue
                        cell_str = str(cell)
                        
                        # Look for period numbers 1-10
                        for period_num in ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10']:
                            # Check various formats
                            if (f'\n{period_num}\n' in cell_str or 
                                cell_str.strip() == period_num or
                                cell_str.startswith(f'{period_num}\n') or
                                f'period {period_num}' in cell_str.lower() or
                                f'({period_num})' in cell_str):
                                temp_period_cols[col_idx] = period_num
                                period_count += 1
                                break
                    
                    if period_count >= 3:  # Found at least 3 periods, likely the period row
                        period_row_idx = row_idx
                        period_columns = temp_period_cols
                        break
                
                if not period_columns:
                    print(f"  ⚠️  Could not identify period columns - SKIPPING page")
                    print(f"  💡 Tip: Check if the PDF format is different from expected")
                    continue
                
                print(f"  📊 Identified {len(period_columns)} period columns: {sorted(period_columns.values(), key=int)}")
                print(f"  📍 Period row index: {period_row_idx}")
                
                # Process class rows (rows after the period row)
                schedules_this_page = 0
                start_row = period_row_idx + 1
                
                print(f"\n  Processing {len(table) - start_row} class rows...")
                
                for row_idx in range(start_row, len(table)):
                    row = table[row_idx]
                    
                    if not row or not row[0]:
                        continue
                    
                    # First column should be the class name
                    class_name = str(row[0]).strip()
                    
                    # Skip invalid class names
                    if not class_name or len(class_name) < 2 or class_name.lower() in ['class', 'total', 'sum']:
                        continue
                    
                    print(f"\n    📝 Class: {class_name}")
                    periods_found = 0
                    
                    # Process each period column
                    for col_idx, period_num in sorted(period_columns.items(), key=lambda x: int(x[1])):
                        if col_idx >= len(row):
                            continue
                        
                        cell = row[col_idx]
                        if not cell:
                            continue
                        
                        # Extract subject and teacher
                        subject, teacher = extract_subject_and_teacher(str(cell))
                        
                        if not subject or not teacher:
                            continue
                        
                        # Get time period
                        start_time_str, end_time_str = TIME_PERIODS.get(period_num, (None, None))
                        
                        if not start_time_str or not end_time_str:
                            print(f"      ⚠️  Period {period_num}: No time mapping - SKIPPING")
                            continue
                        
                        start_time = parse_time(start_time_str)
                        end_time = parse_time(end_time_str)
                        
                        if not start_time or not end_time:
                            print(f"      ⚠️  Period {period_num}: Invalid time format - SKIPPING")
                            continue
                        
                        # Create schedule entry
                        schedule_entry = {
                            'class_name': class_name,
                            'day': day_num,
                            'day_name': day_name,
                            'start_time': start_time,
                            'end_time': end_time,
                            'subject': subject,
                            'teacher': teacher,
                            'period': period_num,
                            'floor': floor_number,
                            'page': page_num
                        }
                        
                        all_schedules.append(schedule_entry)
                        periods_found += 1
                        schedules_this_page += 1
                        
                        print(f"      ✅ Period {period_num:>2}: {subject:30} | {teacher:20} | {start_time_str}-{end_time_str}")
                    
                    if periods_found == 0:
                        print(f"      ⚠️  No valid periods found for this class")
                
                print(f"\n  📈 Extracted {schedules_this_page} schedule entries from this page")
        
        print(f"\n{'='*80}")
        print(f"✅ EXTRACTION COMPLETE FOR FLOOR {floor_number}")
        print(f"📊 Total schedules extracted: {len(all_schedules)}")
        print(f"{'='*80}")
        
    except FileNotFoundError:
        print(f"\n❌ ERROR: PDF file not found: {pdf_path}")
        return []
    except Exception as e:
        print(f"\n❌ ERROR extracting from PDF: {e}")
        import traceback
        traceback.print_exc()
        return []
    
    return all_schedules

def import_to_database(schedules, floor_number):
    """Import schedules to database with validation"""
    
    if not schedules:
        print("\n⚠️  No schedules to import")
        return
    
    with app.app_context():
        print("\n" + "="*80)
        print(f"📥 Importing Floor {floor_number} schedules to database...")
        print("="*80)
        
        # Get or create floor
        floor = Floor.query.filter_by(number=floor_number).first()
        if not floor:
            floor = Floor(name=f'الطابق {floor_number}', number=floor_number)
            db.session.add(floor)
            db.session.commit()
            print(f"✅ Created floor: {floor.name}")
        else:
            print(f"📍 Using existing floor: {floor.name} (ID: {floor.id})")
        
        stats = {
            'total': len(schedules),
            'imported': 0,
            'skipped_duplicate': 0,
            'skipped_invalid': 0,
            'errors': 0,
            'classes_created': set(),
            'teachers_created': set(),
            'subjects_created': set()
        }
        
        print(f"\n📊 Processing {stats['total']} schedule entries...")
        
        for idx, entry in enumerate(schedules, 1):
            try:
                # Validate entry
                if not all([entry.get('class_name'), entry.get('subject'), entry.get('teacher'),
                           entry.get('start_time'), entry.get('end_time'), entry.get('day') is not None]):
                    print(f"  ⚠️  Entry {idx}: Missing required fields - SKIPPING")
                    stats['skipped_invalid'] += 1
                    continue
                
                # Get or create class
                class_name = entry['class_name']
                class_room = Class.query.filter_by(name=class_name, floor_id=floor.id).first()
                if not class_room:
                    class_room = Class(name=class_name, floor_id=floor.id)
                    db.session.add(class_room)
                    db.session.commit()
                    stats['classes_created'].add(class_name)
                    print(f"  ➕ Created class: {class_name}")
                
                # Get or create teacher
                teacher_name = entry['teacher']
                teacher = Teacher.query.filter_by(name=teacher_name).first()
                if not teacher:
                    teacher = Teacher(name=teacher_name)
                    db.session.add(teacher)
                    db.session.commit()
                    stats['teachers_created'].add(teacher_name)
                    print(f"  ➕ Created teacher: {teacher_name}")
                
                # Get or create subject
                subject_name = entry['subject']
                subject = Subject.query.filter_by(name=subject_name).first()
                if not subject:
                    subject = Subject(name=subject_name)
                    db.session.add(subject)
                    db.session.commit()
                    stats['subjects_created'].add(subject_name)
                    print(f"  ➕ Created subject: {subject_name}")
                
                # Check if schedule already exists
                existing = Schedule.query.filter_by(
                    class_id=class_room.id,
                    day_of_week=entry['day'],
                    start_time=entry['start_time'],
                    end_time=entry['end_time']
                ).first()
                
                if existing:
                    stats['skipped_duplicate'] += 1
                    if idx % 50 == 0:
                        print(f"  📊 Progress: {idx}/{stats['total']} processed...")
                    continue
                
                # Create new schedule
                schedule = Schedule(
                    class_id=class_room.id,
                    teacher_id=teacher.id,
                    subject_id=subject.id,
                    day_of_week=entry['day'],
                    start_time=entry['start_time'],
                    end_time=entry['end_time']
                )
                
                db.session.add(schedule)
                db.session.commit()
                
                stats['imported'] += 1
                
                # Progress indicator
                if idx % 50 == 0:
                    print(f"  ✅ Progress: {idx}/{stats['total']} processed, {stats['imported']} imported...")
                
            except Exception as e:
                print(f"  ❌ Entry {idx}: Error - {e}")
                stats['errors'] += 1
                db.session.rollback()
        
        # Print detailed summary
        print("\n" + "="*80)
        print(f"📊 IMPORT SUMMARY - FLOOR {floor_number}")
        print("="*80)
        print(f"  Total processed:         {stats['total']}")
        print(f"  ✅ Successfully imported:  {stats['imported']}")
        print(f"  ⏭️  Skipped (duplicate):    {stats['skipped_duplicate']}")
        print(f"  ⚠️  Skipped (invalid):      {stats['skipped_invalid']}")
        print(f"  ❌ Errors:                 {stats['errors']}")
        print(f"\n  📝 New entities created:")
        print(f"     Classes:  {len(stats['classes_created'])}")
        print(f"     Teachers: {len(stats['teachers_created'])}")
        print(f"     Subjects: {len(stats['subjects_created'])}")
        
        if stats['classes_created']:
            print(f"\n  📚 Classes created for Floor {floor_number}:")
            for class_name in sorted(stats['classes_created']):
                print(f"     • {class_name}")
        
        print("="*80)

def main():
    """Main import function"""
    
    # Define floors to import (skip floor 2 as it's already done)
    floors_to_import = [
        (1, "1st Floor Schedule 28-Sep-25.pdf"),
        (3, "3rd Floor Schedule 28-Sep-25.pdf"),
        (4, "4th Floor Schedule 28-Sep-25.pdf"),
        (5, "5th Floor Schedule 28-Sep-25.pdf"),
    ]
    
    print("\n" + "="*80)
    print("🏫 SCHOOL SCHEDULE IMPORT - FLOORS 1, 3, 4, 5")
    print("="*80)
    print("\n📚 PDFs to process:")
    for floor_num, pdf_file in floors_to_import:
        print(f"   Floor {floor_num}: {pdf_file}")
    
    print("\n" + "="*80)
    print("📥 Starting import process...")
    print("="*80)
    
    # Process each floor
    total_stats = {
        'floors_attempted': 0,
        'floors_success': 0,
        'floors_failed': 0,
        'total_schedules_extracted': 0,
        'total_schedules_imported': 0
    }
    
    for floor_num, pdf_file in floors_to_import:
        print("\n\n" + "🌟"*40)
        print(f"🏢 PROCESSING FLOOR {floor_num}")
        print("🌟"*40)
        
        total_stats['floors_attempted'] += 1
        
        try:
            # Extract schedules
            schedules = extract_schedules_from_pdf(pdf_file, floor_num)
            
            if not schedules:
                print(f"\n⚠️  No schedules extracted from Floor {floor_num}")
                total_stats['floors_failed'] += 1
                continue
            
            total_stats['total_schedules_extracted'] += len(schedules)
            
            # Show sample
            print(f"\n📋 Sample entries from Floor {floor_num}:")
            for i, entry in enumerate(schedules[:3], 1):
                print(f"  {i}. {entry['class_name']} | {entry['day_name'].title()} | Period {entry['period']}")
                print(f"     {entry['start_time'].strftime('%H:%M')}-{entry['end_time'].strftime('%H:%M')} | {entry['subject']} | {entry['teacher']}")
            if len(schedules) > 3:
                print(f"  ... and {len(schedules) - 3} more entries")
            
            # Import to database
            import_to_database(schedules, floor_num)
            
            total_stats['floors_success'] += 1
            
        except Exception as e:
            print(f"\n❌ CRITICAL ERROR processing Floor {floor_num}: {e}")
            total_stats['floors_failed'] += 1
            import traceback
            traceback.print_exc()
    
    # Final summary
    print("\n\n" + "🎉"*40)
    print("🎉 IMPORT COMPLETE - FINAL SUMMARY")
    print("🎉"*40)
    print(f"\n  Floors attempted:           {total_stats['floors_attempted']}")
    print(f"  ✅ Successfully processed:   {total_stats['floors_success']}")
    print(f"  ❌ Failed:                   {total_stats['floors_failed']}")
    print(f"  📊 Total schedules extracted: {total_stats['total_schedules_extracted']}")
    print("\n" + "="*80)
    
    if total_stats['floors_success'] > 0:
        print("\n💡 Next steps:")
        print("   1. Run the Flask app: python app.py")
        print("   2. Visit: http://localhost:5000")
        print("   3. Check all floors and verify schedules are correct!")
    
    print("\n" + "="*80)

if __name__ == '__main__':
    main()

