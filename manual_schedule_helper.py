"""
Manual Schedule Entry Helper
Use this if automatic PDF extraction doesn't work perfectly
"""

from app import app, db, Floor, Class, Teacher, Subject, Schedule
from datetime import time

def get_or_create_floor(floor_number, floor_name=None):
    """Get or create a floor"""
    with app.app_context():
        floor = Floor.query.filter_by(number=floor_number).first()
        if not floor:
            if not floor_name:
                floor_name = f'الطابق {floor_number}'
            floor = Floor(name=floor_name, number=floor_number)
            db.session.add(floor)
            db.session.commit()
            print(f"✅ Created floor: {floor.name}")
        return floor

def get_or_create_class(class_name, floor_id):
    """Get or create a class"""
    with app.app_context():
        class_room = Class.query.filter_by(name=class_name, floor_id=floor_id).first()
        if not class_room:
            class_room = Class(name=class_name, floor_id=floor_id)
            db.session.add(class_room)
            db.session.commit()
            print(f"✅ Created class: {class_name}")
        return class_room

def get_or_create_teacher(teacher_name):
    """Get or create a teacher"""
    with app.app_context():
        teacher = Teacher.query.filter_by(name=teacher_name).first()
        if not teacher:
            teacher = Teacher(name=teacher_name)
            db.session.add(teacher)
            db.session.commit()
            print(f"✅ Created teacher: {teacher_name}")
        return teacher

def get_or_create_subject(subject_name):
    """Get or create a subject"""
    with app.app_context():
        subject = Subject.query.filter_by(name=subject_name).first()
        if not subject:
            subject = Subject(name=subject_name)
            db.session.add(subject)
            db.session.commit()
            print(f"✅ Created subject: {subject_name}")
        return subject

def add_schedule(class_name, floor_number, day_of_week, start_time, end_time, subject_name, teacher_name):
    """
    Add a schedule entry
    
    Parameters:
    - class_name: e.g., "فصل 2-1"
    - floor_number: e.g., 2
    - day_of_week: 0=Monday, 1=Tuesday, ..., 6=Sunday
    - start_time: time object or "HH:MM" string
    - end_time: time object or "HH:MM" string
    - subject_name: e.g., "الرياضيات"
    - teacher_name: e.g., "أحمد محمد"
    """
    with app.app_context():
        try:
            # Get or create entities
            floor = get_or_create_floor(floor_number)
            class_room = get_or_create_class(class_name, floor.id)
            teacher = get_or_create_teacher(teacher_name)
            subject = get_or_create_subject(subject_name)
            
            # Parse times if strings
            if isinstance(start_time, str):
                h, m = map(int, start_time.split(':'))
                start_time = time(h, m)
            
            if isinstance(end_time, str):
                h, m = map(int, end_time.split(':'))
                end_time = time(h, m)
            
            # Check if schedule already exists
            existing = Schedule.query.filter_by(
                class_id=class_room.id,
                day_of_week=day_of_week,
                start_time=start_time,
                end_time=end_time
            ).first()
            
            if existing:
                print(f"⚠️  Schedule already exists: {class_name} - {days[day_of_week]} {start_time}-{end_time}")
                return existing
            
            # Create schedule
            schedule = Schedule(
                class_id=class_room.id,
                teacher_id=teacher.id,
                subject_id=subject.id,
                day_of_week=day_of_week,
                start_time=start_time,
                end_time=end_time
            )
            
            db.session.add(schedule)
            db.session.commit()
            
            days = ['الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت', 'الأحد']
            print(f"✅ Added: {class_name} | {days[day_of_week]} | {start_time.strftime('%H:%M')}-{end_time.strftime('%H:%M')} | {subject_name} | {teacher_name}")
            
            return schedule
            
        except Exception as e:
            print(f"❌ Error: {e}")
            db.session.rollback()
            return None

def bulk_add_schedules(schedules_data):
    """
    Add multiple schedules at once
    
    schedules_data: list of dicts with keys:
        class_name, floor_number, day_of_week, start_time, end_time, subject_name, teacher_name
    """
    print(f"\n📥 Adding {len(schedules_data)} schedules...")
    success = 0
    failed = 0
    
    for data in schedules_data:
        result = add_schedule(**data)
        if result:
            success += 1
        else:
            failed += 1
    
    print(f"\n✅ Success: {success}")
    print(f"❌ Failed: {failed}")

# Example usage
if __name__ == '__main__':
    days = ['الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت', 'الأحد']
    
    print("="*60)
    print("📝 Manual Schedule Entry Helper")
    print("="*60)
    
    # Example: Add schedules for 2nd floor
    example_schedules = [
        {
            'class_name': 'فصل 2-1',
            'floor_number': 2,
            'day_of_week': 0,  # Monday
            'start_time': '08:00',
            'end_time': '08:45',
            'subject_name': 'الرياضيات',
            'teacher_name': 'أحمد محمد'
        },
        {
            'class_name': 'فصل 2-1',
            'floor_number': 2,
            'day_of_week': 0,  # Monday
            'start_time': '08:45',
            'end_time': '09:30',
            'subject_name': 'اللغة العربية',
            'teacher_name': 'فاطمة علي'
        },
        # Add more schedules here...
    ]
    
    print("\n📋 Example schedules defined. To add them, uncomment the line below:\n")
    print("# bulk_add_schedules(example_schedules)\n")
    print("="*60)
    print("\n💡 To use this helper:")
    print("1. Edit the example_schedules list above")
    print("2. Add your schedule data")
    print("3. Uncomment the bulk_add_schedules line")
    print("4. Run: python manual_schedule_helper.py")
    print("="*60)


