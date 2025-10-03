"""
Initialize the database before importing schedules
"""

from app import app, db

print("="*80)
print("🔧 Initializing Database")
print("="*80)

with app.app_context():
    # Create all tables
    db.create_all()
    print("✅ Database tables created successfully!")
    print("\n📊 Tables created:")
    print("  - Floor")
    print("  - Class")
    print("  - Teacher")
    print("  - Subject")
    print("  - Schedule")
    print("  - Attendance")
    
print("\n" + "="*80)
print("✅ Database initialized and ready!")
print("="*80)
print("\n💡 You can now import schedules:")
print("   py import_all_floors.py")
print("="*80)


