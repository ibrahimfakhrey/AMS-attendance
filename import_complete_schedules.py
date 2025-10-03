"""
Complete Schedule Import - Includes ALL periods (1-10) even if empty
This ensures no sessions are missing
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

# Time periods mapping - ALL 10 periods
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
    Returns: (subject, teacher) or (None, None) for empty/break cells
    """
    if not cell_text or cell_text.strip() == '':
        return None, None
    
    cell_text = cell_text.strip()
    
    # Skip non-academic cells (breaks, assembly, etc.) - return None
    skip_keywords = ['assembly', 'breakfast', 'break', 'ylbmessa', 'tsafkaerb', 'kaerb', 
                     'lunch', 'recess', 'snack', 'prayer']
    if any(kw in cell_text.lower() for kw in skip_keywords):
        return None, None
    
    # Skip if cell is too short
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
    Extract schedule data from PDF - INCLUDING ALL PERIODS (1-10)
    """
    all_schedules = []
    
    print("="*80)
    print(f"📄 Extracting COMPLETE schedules from: {pdf_path}")
    print(f"🏢 Floor: {floor_number}")
    print("="*80)
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            print(f"📚 Total pages in PDF: {len(pdf.pages)}")
            
            for page_num, page in enumerate(pdf.pages, 1):
                print(f"\n{'='*80}")
                print(f"📖 Processing Page {page_num} of {len(pdf.pages)}")
                print(f"{'='*80}")
                
                tables = page.extract_tables()
                
                if not tables:
                    print("  ⚠️  No tables found on this page")
                    continue
                
                table = tables[0]
                print(f"  📏 Table dimensions: {len(table)} rows x {len(table[0]) if table else 0} columns")
                
                # Determine the day
                day_name = None
                day_num = None
                
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
                    print(f"  ⚠️  Could not determine day - SKIPPING")
                    continue
                
                print(f"  📅 Day: {day_name.upper()} (day number: {day_num})")
                
                # Find period columns
                period_row_idx = None
                period_columns = {}
                
                for row_idx in range(min(5, len(table))):
                    if not table[row_idx]:
                        continue
                    
                    temp_period_cols = {}
                    period_count = 0
                    
                    for col_idx, cell in enumerate(table[row_idx]):
                        if not cell:
                            continue
                        cell_str = str(cell)
                        
                        for period_num in ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10']:
                            if (f'\n{period_num}\n' in cell_str or 
                                cell_str.strip() == period_num or
                                cell_str.startswith(f'{period_num}\n') or
                                f'period {period_num}' in cell_str.lower()):
                                temp_period_cols[col_idx] = period_num
                                period_count += 1
                                break
                    
                    if period_count >= 3:
                        period_row_idx = row_idx
                        period_columns = temp_period_cols
                        break
                
                if not period_columns:
                    print(f"  ⚠️  Could not identify period columns - SKIPPING")
                    continue
                
                print(f"  📊 Found {len(period_columns)} period columns: {sorted(period_columns.values(), key=int)}")
                
                # Process class rows
                schedules_this_page = 0
                start_row = period_row_idx + 1
                
                for row_idx in range(start_row, len(table)):
                    row = table[row_idx]
                    
                    if not row or not row[0]:
                        continue
                    
                    class_name = str(row[0]).strip()
                    
                    if not class_name or len(class_name) < 2:
                        continue
                    
                    print(f"\n    📝 Class: {class_name}")
                    
                    # Process ALL 10 periods - even if empty
                    for period_num in ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10']:
                        # Find the column for this period
                        col_idx = None
                        for c_idx, p_num in period_columns.items():
                            if p_num == period_num:
                                col_idx = c_idx
                                break
                        
                        # Get time for this period
                        start_time_str, end_time_str = TIME_PERIODS.get(period_num, (None, None))
                        
                        if not start_time_str or not end_time_str:
                            continue
                        
                        start_time = parse_time(start_time_str)
                        end_time = parse_time(end_time_str)
                        
                        # Check if this period has data in the table
                        subject = None
                        teacher = None
                        is_free = False
                        
                        if col_idx is not None and col_idx < len(row):
                            cell = row[col_idx]
                            if cell:
                                subject, teacher = extract_subject_and_teacher(str(cell))
                        
                        # If no subject/teacher, mark as Free Period
                        if not subject or not teacher:
                            subject = "Free Period"
                            teacher = "No Teacher"
                            is_free = True
                        
                        # Create schedule entry for this period
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
                            'is_free': is_free
                        }
                        
                        all_schedules.append(schedule_entry)
                        schedules_this_page += 1
                        
                        if not is_free:
                            print(f"      ✅ Period {period_num:>2}: {subject:30} | {teacher:20}")
                        else:
                            print(f"      ⬜ Period {period_num:>2}: Free Period")
                
                print(f"\n  📈 Extracted {schedules_this_page} entries (including free periods)")
        
        print(f"\n{'='*80}")
        print(f"✅ COMPLETE EXTRACTION FOR FLOOR {floor_number}")
        print(f"📊 Total entries: {len(all_schedules)}")
        print(f"{'='*80}")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return []
    
    return all_schedules

def import_to_database(schedules, floor_number, clear_existing=False):
    """Import complete schedules to database"""
    
    with app.app_context():
        print("\n" + "="*80)
        print(f"📥 Importing Floor {floor_number} - COMPLETE SCHEDULE")
        print("="*80)
        
        # Get or create floor
        floor = Floor.query.filter_by(number=floor_number).first()
        if not floor:
            floor = Floor(name=f'الطابق {floor_number}', number=floor_number)
            db.session.add(floor)
            db.session.commit()
            print(f"✅ Created floor: {floor.name}")
        
        # Clear existing schedules for this floor if requested
        if clear_existing:
            classes_in_floor = Class.query.filter_by(floor_id=floor.id).all()
            for class_room in classes_in_floor:
                Schedule.query.filter_by(class_id=class_room.id).delete()
            db.session.commit()
            print(f"🗑️  Cleared existing schedules for Floor {floor_number}")
        
        # Get or create "Free Period" subject and "No Teacher" teacher
        free_subject = Subject.query.filter_by(name="Free Period").first()
        if not free_subject:
            free_subject = Subject(name="Free Period")
            db.session.add(free_subject)
            db.session.commit()
        
        no_teacher = Teacher.query.filter_by(name="No Teacher").first()
        if not no_teacher:
            no_teacher = Teacher(name="No Teacher")
            db.session.add(no_teacher)
            db.session.commit()
        
        stats = {
            'total': len(schedules),
            'imported': 0,
            'free_periods': 0,
            'academic': 0,
            'skipped': 0,
            'classes_created': set()
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
                
                # Get or create teacher and subject
                if entry['is_free']:
                    teacher = no_teacher
                    subject = free_subject
                else:
                    teacher_name = entry['teacher']
                    teacher = Teacher.query.filter_by(name=teacher_name).first()
                    if not teacher:
                        teacher = Teacher(name=teacher_name)
                        db.session.add(teacher)
                        db.session.commit()
                    
                    subject_name = entry['subject']
                    subject = Subject.query.filter_by(name=subject_name).first()
                    if not subject:
                        subject = Subject(name=subject_name)
                        db.session.add(subject)
                        db.session.commit()
                
                # Check if exists
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
                if entry['is_free']:
                    stats['free_periods'] += 1
                else:
                    stats['academic'] += 1
                
                if idx % 50 == 0:
                    print(f"  📊 Progress: {idx}/{stats['total']}...")
                
            except Exception as e:
                print(f"  ❌ Error on entry {idx}: {e}")
                db.session.rollback()
        
        print("\n" + "="*80)
        print(f"📊 IMPORT SUMMARY - FLOOR {floor_number}")
        print("="*80)
        print(f"  Total processed:      {stats['total']}")
        print(f"  ✅ Imported:           {stats['imported']}")
        print(f"  📚 Academic sessions:  {stats['academic']}")
        print(f"  ⬜ Free periods:       {stats['free_periods']}")
        print(f"  ⏭️  Skipped:            {stats['skipped']}")
        print(f"  📝 Classes: {len(stats['classes_created'])}")
        print("="*80)

def main():
    """Main import function"""
    
    floors_to_import = [
        (1, "1st Floor Schedule 28-Sep-25.pdf"),
        (2, "2nd Floor Schedule 28-Sep-25.pdf"),
        (3, "3rd Floor Schedule 28-Sep-25.pdf"),
        (4, "4th Floor Schedule 28-Sep-25.pdf"),
        (5, "5th Floor Schedule 28-Sep-25.pdf"),
    ]
    
    print("\n" + "="*80)
    print("🏫 COMPLETE SCHEDULE IMPORT - ALL PERIODS (1-10)")
    print("="*80)
    print("\n📚 This will import ALL periods including free periods")
    print("⚠️  Existing schedules will be cleared and re-imported")
    
    for floor_num, pdf_file in floors_to_import:
        print(f"\n🏢 Floor {floor_num}: {pdf_file}")
    
    print("\n" + "="*80)
    print("📥 Starting import...")
    print("="*80)
    
    for floor_num, pdf_file in floors_to_import:
        print("\n\n" + "🌟"*40)
        print(f"🏢 PROCESSING FLOOR {floor_num}")
        print("🌟"*40)
        
        try:
            schedules = extract_schedules_from_pdf(pdf_file, floor_num)
            
            if schedules:
                import_to_database(schedules, floor_num, clear_existing=True)
            else:
                print(f"\n⚠️  No schedules extracted from Floor {floor_num}")
                
        except Exception as e:
            print(f"\n❌ ERROR processing Floor {floor_num}: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n\n" + "🎉"*40)
    print("🎉 COMPLETE IMPORT FINISHED")
    print("🎉"*40)

if __name__ == '__main__':
    main()

