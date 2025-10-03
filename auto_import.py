"""
Auto-import schedule from PDF (no confirmation needed)
"""

from import_schedule_smart import extract_schedules_from_pdf, import_to_database

def main():
    pdf_path = "2nd Floor Schedule 28-Sep-25.pdf"
    
    print("\n" + "="*80)
    print("🏫 Auto-Import: 2nd Floor Schedule")
    print("="*80)
    
    # Extract
    print("\n🔍 Extracting schedules from PDF...")
    schedules = extract_schedules_from_pdf(pdf_path)
    
    if not schedules:
        print("\n❌ No schedules found!")
        return
    
    print(f"\n✅ Found {len(schedules)} schedule entries")
    
    # Import automatically
    print("\n📥 Importing to database...")
    import_to_database(schedules, floor_number=2)
    
    print("\n" + "="*80)
    print("✅ Import completed!")
    print("="*80)
    print("\n💡 You can now:")
    print("   1. Run the Flask app: py app.py")
    print("   2. Visit: http://localhost:5000")
    print("   3. Navigate to Floor 2 to see the imported schedules")
    print("="*80)

if __name__ == '__main__':
    main()


