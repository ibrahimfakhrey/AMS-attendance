"""
Smart Schedule Import for 2nd Floor PDF
Specifically designed for Al-Alamiya School schedule format
"""

import pdfplumber
import re
from datetime import datetime, time
from app import app, db, Floor, Class, Teacher, Subject, Schedule

# Day mapping
DAY_MAPPING = {
    'sunday': 6,     # In many countries Sunday is the first day
    'monday': 0,
    'tuesday': 1,
    'wednesday': 2,
    'thursday': 3,
    'friday': 4,
    'saturday': 5,
}

# Time periods mapping based on the schedule
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
    Format: "Subject\nTeacher Name"
    """
    if not cell_text or cell_text.strip() == '':
        return None, None
    
    cell_text = cell_text.strip()
    
    # Skip non-academic cells
    skip_keywords = ['ylbmessa', 'tsafkaerb', 'kaerb', 'assembly', 'breakfast', 'break']
    if any(kw in cell_text.lower() for kw in skip_keywords):
        return None, None
    
    # Split by newline
    lines = [line.strip() for line in cell_text.split('\n') if line.strip()]
    
    if not lines:
        return None, None
    
    # First line is usually the subject
    subject = lines[0]
    
    # Remaining lines are teacher name(s)
    teacher = ' '.join(lines[1:]) if len(lines) > 1 else 'Unknown'
    
    return subject, teacher

def extract_schedules_from_pdf(pdf_path):
    """Extract schedule data from the Al-Alamiya school PDF"""
    all_schedules = []
    
    print("="*80)
    print("📄 Extracting schedules from:", pdf_path)
    print("="*80)
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            print(f"\n📖 Processing Page {page_num}...")
            
            # Extract tables
            tables = page.extract_tables()
            
            if not tables:
                print("  ⚠️  No tables found")
                continue
            
            # Process the main table (first table)
            table = tables[0]
            
            # Find the day from row 2
            day_name = None
            if len(table) > 1 and table[1]:
                day_cell = str(table[1][1]).lower() if table[1][1] else ''
                for day_key in DAY_MAPPING:
                    if day_key in day_cell:
                        day_name = day_key
                        day_num = DAY_MAPPING[day_key]
                        break
            
            if not day_name:
                print(f"  ⚠️  Could not determine day for page {page_num}")
                continue
            
            print(f"  📅 Day: {day_name.title()} (day {day_num})")
            
            # Row 3 contains time periods - find column indices for periods 1-10
            period_columns = {}
            if len(table) > 2 and table[2]:
                for col_idx, cell in enumerate(table[2]):
                    if cell:
                        cell_text = str(cell)
                        # Look for period numbers
                        for period in ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10']:
                            if f'\n{period}\n' in cell_text or cell_text.startswith(f'{period}\n'):
                                period_columns[col_idx] = period
                                break
            
            print(f"  📊 Found {len(period_columns)} period columns")
            
            # Process rows 4 onwards (classes)
            schedules_count = 0
            for row_idx in range(3, len(table)):
                row = table[row_idx]
                
                if not row or not row[0]:
                    continue
                
                class_name = str(row[0]).strip()
                
                # Skip if not a valid class name
                if not class_name or len(class_name) < 2:
                    continue
                
                print(f"\n    📝 Class: {class_name}")
                
                # Process each period column
                for col_idx, period_num in period_columns.items():
                    if col_idx >= len(row):
                        continue
                    
                    cell = row[col_idx]
                    if not cell:
                        continue
                    
                    subject, teacher = extract_subject_and_teacher(str(cell))
                    
                    if not subject or not teacher:
                        continue
                    
                    # Get time period
                    start_time_str, end_time_str = TIME_PERIODS.get(period_num, (None, None))
                    
                    if not start_time_str or not end_time_str:
                        continue
                    
                    start_time = parse_time(start_time_str)
                    end_time = parse_time(end_time_str)
                    
                    if not start_time or not end_time:
                        continue
                    
                    schedule_entry = {
                        'class_name': class_name,
                        'day': day_num,
                        'day_name': day_name,
                        'start_time': start_time,
                        'end_time': end_time,
                        'subject': subject,
                        'teacher': teacher,
                        'period': period_num
                    }
                    
                    all_schedules.append(schedule_entry)
                    schedules_count += 1
                    
                    print(f"      ✅ Period {period_num}: {subject} - {teacher} ({start_time_str}-{end_time_str})")
            
            print(f"\n  📈 Extracted {schedules_count} schedule entries from this page")
    
    print(f"\n{'='*80}")
    print(f"✅ Total extracted: {len(all_schedules)} schedule entries")
    print(f"{'='*80}")
    
    return all_schedules

def import_to_database(schedules, floor_number=2):
    """Import schedules to database"""
    with app.app_context():
        print("\n" + "="*80)
        print("📥 Importing to database...")
        print("="*80)
        
        # Get or create floor
        floor = Floor.query.filter_by(number=floor_number).first()
        if not floor:
            floor = Floor(name=f'الطابق {floor_number}', number=floor_number)
            db.session.add(floor)
            db.session.commit()
            print(f"✅ Created floor: {floor.name}")
        
        stats = {
            'total': len(schedules),
            'imported': 0,
            'skipped': 0,
            'errors': 0,
            'classes_created': set(),
            'teachers_created': set(),
            'subjects_created': set()
        }
        
        for idx, entry in enumerate(schedules, 1):
            try:
                # Get or create class
                class_name = entry['class_name']
                class_room = Class.query.filter_by(name=class_name, floor_id=floor.id).first()
                if not class_room:
                    class_room = Class(name=class_name, floor_id=floor.id)
                    db.session.add(class_room)
                    db.session.commit()
                    stats['classes_created'].add(class_name)
                
                # Get or create teacher
                teacher_name = entry['teacher']
                teacher = Teacher.query.filter_by(name=teacher_name).first()
                if not teacher:
                    teacher = Teacher(name=teacher_name)
                    db.session.add(teacher)
                    db.session.commit()
                    stats['teachers_created'].add(teacher_name)
                
                # Get or create subject
                subject_name = entry['subject']
                subject = Subject.query.filter_by(name=subject_name).first()
                if not subject:
                    subject = Subject(name=subject_name)
                    db.session.add(subject)
                    db.session.commit()
                    stats['subjects_created'].add(subject_name)
                
                # Check if schedule exists
                existing = Schedule.query.filter_by(
                    class_id=class_room.id,
                    day_of_week=entry['day'],
                    start_time=entry['start_time'],
                    end_time=entry['end_time']
                ).first()
                
                if existing:
                    stats['skipped'] += 1
                    continue
                
                # Create schedule
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
                
                if idx % 20 == 0:
                    print(f"  ✅ Imported {idx}/{stats['total']}...")
                
            except Exception as e:
                print(f"  ❌ Error on entry {idx}: {e}")
                stats['errors'] += 1
                db.session.rollback()
        
        # Print summary
        print("\n" + "="*80)
        print("📊 Import Summary:")
        print("="*80)
        print(f"  Total processed:      {stats['total']}")
        print(f"  ✅ Successfully imported: {stats['imported']}")
        print(f"  ⏭️  Skipped (duplicates):  {stats['skipped']}")
        print(f"  ❌ Errors:               {stats['errors']}")
        print(f"  ➕ New classes:          {len(stats['classes_created'])}")
        print(f"  ➕ New teachers:         {len(stats['teachers_created'])}")
        print(f"  ➕ New subjects:         {len(stats['subjects_created'])}")
        
        if stats['classes_created']:
            print(f"\n  📝 Classes created: {', '.join(sorted(stats['classes_created']))}")
        
        print("="*80)

def main():
    """Main function"""
    pdf_path = "2nd Floor Schedule 28-Sep-25.pdf"
    
    print("\n" + "="*80)
    print("🏫 Al-Alamiya School Schedule Import Tool")
    print("="*80)
    print(f"📄 PDF File: {pdf_path}")
    print(f"🏢 Target: 2nd Floor")
    print("="*80)
    
    # Extract
    schedules = extract_schedules_from_pdf(pdf_path)
    
    if not schedules:
        print("\n❌ No schedules extracted. Please check the PDF.")
        return
    
    # Show sample
    print(f"\n📋 Sample of extracted data (first 3 entries):")
    for i, entry in enumerate(schedules[:3], 1):
        print(f"\n  {i}. Class: {entry['class_name']}")
        print(f"     Day: {entry['day_name'].title()}")
        print(f"     Period: {entry['period']}")
        print(f"     Time: {entry['start_time'].strftime('%H:%M')} - {entry['end_time'].strftime('%H:%M')}")
        print(f"     Subject: {entry['subject']}")
        print(f"     Teacher: {entry['teacher']}")
    
    if len(schedules) > 3:
        print(f"\n  ... and {len(schedules) - 3} more entries")
    
    # Confirm
    print("\n" + "="*80)
    response = input("📥 Import these schedules to the database? (yes/no): ").strip().lower()
    
    if response in ['yes', 'y', 'نعم']:
        import_to_database(schedules, floor_number=2)
        print("\n✅ Import completed successfully!")
    else:
        print("\n❌ Import cancelled.")

if __name__ == '__main__':
    main()


