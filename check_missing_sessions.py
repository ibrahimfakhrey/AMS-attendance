"""
Check which sessions are missing from the database
"""

from app import app, db, Floor, Class, Schedule

def check_sessions():
    """Check for missing sessions"""
    with app.app_context():
        print("\n" + "="*80)
        print("🔍 CHECKING FOR MISSING SESSIONS")
        print("="*80)
        
        days = ['الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت', 'الأحد']
        
        # Check each floor
        floors = Floor.query.order_by(Floor.number).all()
        
        for floor in floors:
            print(f"\n{'='*80}")
            print(f"🏢 {floor.name}")
            print(f"{'='*80}")
            
            classes = Class.query.filter_by(floor_id=floor.id).order_by(Class.name).all()
            
            for class_room in classes:
                print(f"\n📝 {class_room.name}")
                
                # Check each day
                for day_num in range(7):
                    day_schedules = Schedule.query.filter_by(
                        class_id=class_room.id,
                        day_of_week=day_num
                    ).order_by(Schedule.start_time).all()
                    
                    if day_schedules:
                        print(f"  {days[day_num]}: {len(day_schedules)} حصص", end="")
                        
                        # Show which periods are present
                        periods = []
                        for sched in day_schedules:
                            # Determine period number from time
                            time_str = sched.start_time.strftime('%H:%M')
                            period_map = {
                                '08:30': '1', '09:05': '2', '09:40': '3', '10:20': '4',
                                '11:00': '5', '11:40': '6', '12:20': '7', '13:00': '8',
                                '13:40': '9', '14:15': '10'
                            }
                            period = period_map.get(time_str, '?')
                            periods.append(period)
                        
                        print(f" - Periods: {', '.join(periods)}")
                        
                        # Check if all 10 periods are there
                        if len(day_schedules) < 10:
                            missing = set(['1','2','3','4','5','6','7','8','9','10']) - set(periods)
                            if missing:
                                print(f"    ⚠️  Missing periods: {', '.join(sorted(missing, key=int))}")

if __name__ == '__main__':
    check_sessions()

