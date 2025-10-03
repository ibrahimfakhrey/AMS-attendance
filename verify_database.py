"""
Verify database contents - check all floors have their schedules
"""

from app import app, db, Floor, Class, Teacher, Subject, Schedule

def verify_database():
    """Check what's in the database"""
    with app.app_context():
        print("\n" + "="*80)
        print("🔍 DATABASE VERIFICATION")
        print("="*80)
        
        # Count all entities
        floors_count = Floor.query.count()
        classes_count = Class.query.count()
        teachers_count = Teacher.query.count()
        subjects_count = Subject.query.count()
        schedules_count = Schedule.query.count()
        
        print(f"\n📊 Overall Statistics:")
        print(f"  Floors:    {floors_count}")
        print(f"  Classes:   {classes_count}")
        print(f"  Teachers:  {teachers_count}")
        print(f"  Subjects:  {subjects_count}")
        print(f"  Schedules: {schedules_count}")
        
        # Check each floor
        print(f"\n{'='*80}")
        print("📚 Floor-by-Floor Breakdown:")
        print("="*80)
        
        floors = Floor.query.order_by(Floor.number).all()
        
        for floor in floors:
            classes = Class.query.filter_by(floor_id=floor.id).all()
            
            # Count schedules for this floor
            floor_schedules_count = 0
            for class_room in classes:
                floor_schedules_count += Schedule.query.filter_by(class_id=class_room.id).count()
            
            print(f"\n🏢 {floor.name} (Floor {floor.number}):")
            print(f"   Classes: {len(classes)}")
            print(f"   Schedules: {floor_schedules_count}")
            
            if classes:
                print(f"   📝 Classes:")
                for class_room in classes:
                    class_schedules = Schedule.query.filter_by(class_id=class_room.id).count()
                    print(f"      • {class_room.name}: {class_schedules} schedules")
        
        # Show all teachers
        print(f"\n{'='*80}")
        print("👨‍🏫 Teachers in Database:")
        print("="*80)
        teachers = Teacher.query.order_by(Teacher.name).all()
        for teacher in teachers:
            schedules_count = Schedule.query.filter_by(teacher_id=teacher.id).count()
            print(f"  • {teacher.name}: {schedules_count} schedules")
        
        # Show all subjects
        print(f"\n{'='*80}")
        print("📚 Subjects in Database:")
        print("="*80)
        subjects = Subject.query.order_by(Subject.name).all()
        for subject in subjects:
            schedules_count = Schedule.query.filter_by(subject_id=subject.id).count()
            print(f"  • {subject.name}: {schedules_count} schedules")
        
        # Check for days distribution
        print(f"\n{'='*80}")
        print("📅 Schedule Distribution by Day:")
        print("="*80)
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        for day_num, day_name in enumerate(days):
            count = Schedule.query.filter_by(day_of_week=day_num).count()
            print(f"  {day_name}: {count} schedules")
        
        print(f"\n{'='*80}")
        print("✅ Verification Complete!")
        print("="*80)

if __name__ == '__main__':
    verify_database()

