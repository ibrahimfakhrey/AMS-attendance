"""
Script to import schedule data from PDF file into the database
PDF Format: 2nd Floor Schedule - Each day on a separate page
"""

import pdfplumber
import re
from datetime import datetime, time
from app import app, db, Floor, Class, Teacher, Subject, Schedule

def parse_time(time_str):
    """
    Parse time string to time object
    Handles formats like: "08:00", "8:00 AM", "14:30"
    """
    time_str = time_str.strip()
    
    # Remove any extra whitespace
    time_str = re.sub(r'\s+', ' ', time_str)
    
    # Try different time formats
    formats = [
        '%H:%M',
        '%I:%M %p',
        '%I:%M%p',
        '%H.%M',
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(time_str, fmt)
            return dt.time()
        except:
            continue
    
    # Try extracting just numbers
    numbers = re.findall(r'\d+', time_str)
    if len(numbers) >= 2:
        hour = int(numbers[0])
        minute = int(numbers[1])
        
        # Convert to 24-hour format if needed
        if 'PM' in time_str.upper() and hour < 12:
            hour += 12
        elif 'AM' in time_str.upper() and hour == 12:
            hour = 0
            
        return time(hour, minute)
    
    return None

def extract_schedule_from_pdf(pdf_path):
    """
    Extract schedule information from PDF
    Returns a list of schedule entries
    """
    schedules = []
    
    # Day mapping (Arabic to English)
    day_mapping = {
        'الاثنين': 0,
        'الثلاثاء': 1,
        'الأربعاء': 2,
        'الخميس': 3,
        'الجمعة': 4,
        'السبت': 5,
        'الأحد': 6,
        'monday': 0,
        'tuesday': 1,
        'wednesday': 2,
        'thursday': 3,
        'friday': 4,
        'saturday': 5,
        'sunday': 6,
    }
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            print(f"📄 Found {len(pdf.pages)} pages in PDF")
            
            for page_num, page in enumerate(pdf.pages, 1):
                print(f"\n📖 Processing Page {page_num}...")
                
                # Extract text
                text = page.extract_text()
                if not text:
                    print(f"⚠️  No text found on page {page_num}")
                    continue
                
                print(f"Text preview:\n{text[:500]}...")
                
                # Try to extract tables
                tables = page.extract_tables()
                
                if tables:
                    print(f"📊 Found {len(tables)} table(s) on page {page_num}")
                    
                    for table_idx, table in enumerate(tables):
                        print(f"\n  Table {table_idx + 1}:")
                        
                        # Determine the day for this page
                        current_day = None
                        for day_name, day_num in day_mapping.items():
                            if day_name in text.lower():
                                current_day = day_num
                                print(f"  📅 Detected day: {day_name} ({day_num})")
                                break
                        
                        if current_day is None:
                            # Try to use page number to determine day (if each page is a day)
                            if page_num <= 7:
                                current_day = page_num - 1
                                print(f"  📅 Using page number for day: {current_day}")
                        
                        # Process table rows
                        headers = table[0] if table else []
                        print(f"  Headers: {headers}")
                        
                        for row_idx, row in enumerate(table[1:], 1):
                            if not row or all(cell is None or str(cell).strip() == '' for cell in row):
                                continue
                            
                            print(f"  Row {row_idx}: {row}")
                            
                            # Try to extract schedule information
                            # Common formats:
                            # [Time, Class, Subject, Teacher]
                            # [Class, Time Start, Time End, Subject, Teacher]
                            # etc.
                            
                            schedule_entry = {
                                'day': current_day,
                                'class_name': None,
                                'start_time': None,
                                'end_time': None,
                                'subject': None,
                                'teacher': None,
                                'raw_row': row
                            }
                            
                            # Extract information from row cells
                            for cell in row:
                                if cell is None:
                                    continue
                                    
                                cell_str = str(cell).strip()
                                if not cell_str:
                                    continue
                                
                                # Check if it's a time
                                if re.search(r'\d{1,2}[:.]\d{2}', cell_str):
                                    parsed_time = parse_time(cell_str)
                                    if parsed_time:
                                        if schedule_entry['start_time'] is None:
                                            schedule_entry['start_time'] = parsed_time
                                        elif schedule_entry['end_time'] is None:
                                            schedule_entry['end_time'] = parsed_time
                                
                                # Check if it's a class name (contains "فصل" or "class")
                                if 'فصل' in cell_str.lower() or 'class' in cell_str.lower():
                                    schedule_entry['class_name'] = cell_str
                                
                                # Other cells might be subject or teacher
                                elif schedule_entry['subject'] is None and len(cell_str) > 2:
                                    schedule_entry['subject'] = cell_str
                                elif schedule_entry['teacher'] is None and len(cell_str) > 2:
                                    schedule_entry['teacher'] = cell_str
                            
                            schedules.append(schedule_entry)
                else:
                    print(f"  ℹ️  No tables found, trying text extraction...")
                    
                    # Try to parse from text
                    lines = text.split('\n')
                    current_day = None
                    
                    # Detect day
                    for line in lines[:10]:  # Check first 10 lines
                        for day_name, day_num in day_mapping.items():
                            if day_name in line.lower():
                                current_day = day_num
                                print(f"  📅 Detected day from text: {day_name} ({day_num})")
                                break
                        if current_day is not None:
                            break
                    
                    if current_day is None and page_num <= 7:
                        current_day = page_num - 1
                    
                    # Try to find schedule entries in text
                    for line in lines:
                        # Look for time patterns
                        times = re.findall(r'\d{1,2}[:.]\d{2}', line)
                        if len(times) >= 2:
                            schedule_entry = {
                                'day': current_day,
                                'class_name': None,
                                'start_time': parse_time(times[0]),
                                'end_time': parse_time(times[1]),
                                'subject': None,
                                'teacher': None,
                                'raw_row': line
                            }
                            
                            # Try to extract other info from the line
                            # This would need more sophisticated parsing based on actual PDF structure
                            
                            if schedule_entry['start_time'] and schedule_entry['end_time']:
                                schedules.append(schedule_entry)
    
    except Exception as e:
        print(f"❌ Error reading PDF: {e}")
        import traceback
        traceback.print_exc()
    
    return schedules

def import_schedule_to_database(schedules, floor_number=2):
    """
    Import extracted schedule data into the database
    """
    with app.app_context():
        print("\n" + "="*60)
        print("📥 Importing schedules to database...")
        print("="*60)
        
        # Get or create floor
        floor = Floor.query.filter_by(number=floor_number).first()
        if not floor:
            floor = Floor(name=f'الطابق {floor_number}', number=floor_number)
            db.session.add(floor)
            db.session.commit()
            print(f"✅ Created floor: {floor.name}")
        else:
            print(f"📍 Using existing floor: {floor.name}")
        
        # Statistics
        stats = {
            'processed': 0,
            'imported': 0,
            'skipped': 0,
            'errors': 0,
            'classes_created': 0,
            'teachers_created': 0,
            'subjects_created': 0
        }
        
        for idx, entry in enumerate(schedules, 1):
            stats['processed'] += 1
            
            try:
                # Validate entry
                if entry['day'] is None:
                    print(f"⚠️  Entry {idx}: No day specified - {entry.get('raw_row', 'N/A')}")
                    stats['skipped'] += 1
                    continue
                
                if not entry['start_time'] or not entry['end_time']:
                    print(f"⚠️  Entry {idx}: Missing time - {entry.get('raw_row', 'N/A')}")
                    stats['skipped'] += 1
                    continue
                
                # Get or create class
                class_name = entry.get('class_name')
                if not class_name:
                    print(f"⚠️  Entry {idx}: No class name - {entry.get('raw_row', 'N/A')}")
                    stats['skipped'] += 1
                    continue
                
                class_room = Class.query.filter_by(name=class_name, floor_id=floor.id).first()
                if not class_room:
                    class_room = Class(name=class_name, floor_id=floor.id)
                    db.session.add(class_room)
                    db.session.commit()
                    print(f"  ➕ Created class: {class_name}")
                    stats['classes_created'] += 1
                
                # Get or create teacher
                teacher_name = entry.get('teacher')
                if not teacher_name:
                    print(f"⚠️  Entry {idx}: No teacher name - {entry.get('raw_row', 'N/A')}")
                    stats['skipped'] += 1
                    continue
                
                teacher = Teacher.query.filter_by(name=teacher_name).first()
                if not teacher:
                    teacher = Teacher(name=teacher_name)
                    db.session.add(teacher)
                    db.session.commit()
                    print(f"  ➕ Created teacher: {teacher_name}")
                    stats['teachers_created'] += 1
                
                # Get or create subject
                subject_name = entry.get('subject')
                if not subject_name:
                    print(f"⚠️  Entry {idx}: No subject name - {entry.get('raw_row', 'N/A')}")
                    stats['skipped'] += 1
                    continue
                
                subject = Subject.query.filter_by(name=subject_name).first()
                if not subject:
                    subject = Subject(name=subject_name)
                    db.session.add(subject)
                    db.session.commit()
                    print(f"  ➕ Created subject: {subject_name}")
                    stats['subjects_created'] += 1
                
                # Check if schedule already exists
                existing = Schedule.query.filter_by(
                    class_id=class_room.id,
                    day_of_week=entry['day'],
                    start_time=entry['start_time'],
                    end_time=entry['end_time']
                ).first()
                
                if existing:
                    print(f"  ⏭️  Entry {idx}: Schedule already exists - skipping")
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
                
                days = ['الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت', 'الأحد']
                day_name = days[entry['day']] if 0 <= entry['day'] <= 6 else str(entry['day'])
                
                print(f"  ✅ Entry {idx}: Imported - {class_name} | {day_name} | {entry['start_time'].strftime('%H:%M')}-{entry['end_time'].strftime('%H:%M')} | {subject_name} | {teacher_name}")
                stats['imported'] += 1
                
            except Exception as e:
                print(f"  ❌ Entry {idx}: Error - {e}")
                stats['errors'] += 1
                db.session.rollback()
        
        print("\n" + "="*60)
        print("📊 Import Statistics:")
        print("="*60)
        print(f"  Total processed:    {stats['processed']}")
        print(f"  ✅ Successfully imported: {stats['imported']}")
        print(f"  ⏭️  Skipped:         {stats['skipped']}")
        print(f"  ❌ Errors:          {stats['errors']}")
        print(f"  ➕ Classes created: {stats['classes_created']}")
        print(f"  ➕ Teachers created: {stats['teachers_created']}")
        print(f"  ➕ Subjects created: {stats['subjects_created']}")
        print("="*60)

def main():
    """Main function"""
    pdf_path = "2nd Floor Schedule 28-Sep-25.pdf"
    
    print("="*60)
    print("🏫 School Schedule PDF Import Tool")
    print("="*60)
    print(f"📄 PDF File: {pdf_path}")
    print(f"🏢 Target Floor: 2nd Floor")
    print("="*60)
    
    # Extract schedules from PDF
    print("\n🔍 Step 1: Extracting data from PDF...")
    schedules = extract_schedule_from_pdf(pdf_path)
    
    print(f"\n✅ Extracted {len(schedules)} schedule entries")
    
    if not schedules:
        print("\n⚠️  No schedule data extracted. Please check the PDF format.")
        print("The script expects tables or structured text with:")
        print("  - Day of week")
        print("  - Class name")
        print("  - Start time and end time")
        print("  - Subject name")
        print("  - Teacher name")
        return
    
    # Show sample entries
    print("\n📋 Sample entries:")
    for i, entry in enumerate(schedules[:5], 1):
        print(f"\n  Entry {i}:")
        print(f"    Day: {entry.get('day')}")
        print(f"    Class: {entry.get('class_name')}")
        print(f"    Time: {entry.get('start_time')} - {entry.get('end_time')}")
        print(f"    Subject: {entry.get('subject')}")
        print(f"    Teacher: {entry.get('teacher')}")
    
    if len(schedules) > 5:
        print(f"\n  ... and {len(schedules) - 5} more entries")
    
    # Ask for confirmation
    print("\n" + "="*60)
    response = input("📥 Import these schedules to database? (yes/no): ").strip().lower()
    
    if response in ['yes', 'y', 'نعم']:
        print("\n🔄 Step 2: Importing to database...")
        import_schedule_to_database(schedules, floor_number=2)
        print("\n✅ Import completed!")
    else:
        print("\n❌ Import cancelled.")

if __name__ == '__main__':
    main()


