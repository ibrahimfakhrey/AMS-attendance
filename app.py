from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, time, timedelta
import os
import tempfile

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
# Database configuration for Vercel

if os.environ.get('VERCEL'):
    # For Vercel, use a temporary database file
    db_path = os.path.join(tempfile.gettempdir(), 'school_attendance.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
else:
    # For local development
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///school_attendance.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Database Models
class Floor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    number = db.Column(db.Integer, nullable=False, unique=True)
    classes = db.relationship('Class', backref='floor', lazy=True, cascade='all, delete-orphan')

class Class(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    floor_id = db.Column(db.Integer, db.ForeignKey('floor.id'), nullable=False)
    schedules = db.relationship('Schedule', backref='class_room', lazy=True, cascade='all, delete-orphan')
    attendances = db.relationship('Attendance', backref='class_room', lazy=True, cascade='all, delete-orphan')

class Teacher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    schedules = db.relationship('Schedule', backref='teacher', lazy=True)
    attendances = db.relationship('Attendance', backref='teacher', lazy=True)

class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    schedules = db.relationship('Schedule', backref='subject', lazy=True)

class Schedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teacher.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    day_of_week = db.Column(db.Integer, nullable=False)  # 0=Monday, 6=Sunday
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    attendances = db.relationship('Attendance', backref='schedule', lazy=True)

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    schedule_id = db.Column(db.Integer, db.ForeignKey('schedule.id'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teacher.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False)  # Present, Late, Absent
    actual_time = db.Column(db.Time, nullable=True)
    minutes_late = db.Column(db.Integer, nullable=True)
    notes = db.Column(db.Text, nullable=True)

# Main Routes
@app.route('/')
def index():
    try:
        floors = Floor.query.order_by(Floor.number).all()
        return render_template('index.html', floors=floors)
    except Exception as e:
        print(f"Error in index route: {e}")
        # Return empty floors list if database error
        return render_template('index.html', floors=[])

@app.route('/floor/<int:floor_id>')
def floor_detail(floor_id):
    floor = Floor.query.get_or_404(floor_id)
    return render_template('floor_detail.html', floor=floor)

@app.route('/class/<int:class_id>')
def class_detail(class_id):
    """Show available days for a class"""
    class_room = Class.query.get_or_404(class_id)
    current_day = datetime.now().weekday()
    
    # Get all unique days that have schedules for this class
    schedules = Schedule.query.filter_by(class_id=class_id).all()
    available_days = sorted(set([s.day_of_week for s in schedules]))
    
    # Day names in Arabic
    day_names = {
        0: 'الاثنين',
        1: 'الثلاثاء', 
        2: 'الأربعاء',
        3: 'الخميس',
        4: 'الجمعة',
        5: 'السبت',
        6: 'الأحد'
    }
    
    # Prepare days data with schedule counts
    days_data = []
    for day_num in available_days:
        day_schedules_count = Schedule.query.filter_by(
            class_id=class_id,
            day_of_week=day_num
        ).count()
        
        days_data.append({
            'number': day_num,
            'name': day_names.get(day_num, f'يوم {day_num}'),
            'schedules_count': day_schedules_count,
            'is_today': day_num == current_day
        })
    
    return render_template('class_detail.html', 
                         class_room=class_room,
                         days_data=days_data,
                         current_day=current_day)

@app.route('/class/<int:class_id>/day/<int:day_num>')
def class_day_sessions(class_id, day_num):
    """Show all sessions for a specific day of a class"""
    class_room = Class.query.get_or_404(class_id)
    current_time = datetime.now()
    current_day = current_time.weekday()
    today_date = current_time.date()
    
    # Day names in Arabic
    day_names = {
        0: 'الاثنين',
        1: 'الثلاثاء',
        2: 'الأربعاء',
        3: 'الخميس',
        4: 'الجمعة',
        5: 'السبت',
        6: 'الأحد'
    }
    
    # Get all schedules for this day
    day_schedules = Schedule.query.filter_by(
        class_id=class_id,
        day_of_week=day_num
    ).order_by(Schedule.start_time).all()
    
    # Get attendance records for today if it's the selected day
    attendance_records = {}
    if day_num == current_day:
        attendances = Attendance.query.filter_by(
            class_id=class_id,
            date=today_date
        ).all()
        for att in attendances:
            attendance_records[att.schedule_id] = att
    
    # Check which session is currently active
    current_session_id = None
    if day_num == current_day:
        for schedule in day_schedules:
            if schedule.start_time <= current_time.time() <= schedule.end_time:
                current_session_id = schedule.id
                break
    
    return render_template('class_day_sessions.html',
                         class_room=class_room,
                         day_num=day_num,
                         day_name=day_names.get(day_num, f'يوم {day_num}'),
                         day_schedules=day_schedules,
                         attendance_records=attendance_records,
                         current_session_id=current_session_id,
                         is_today=day_num == current_day,
                         current_time=current_time)

@app.route('/mark_attendance/<int:schedule_id>', methods=['POST'])
def mark_attendance(schedule_id):
    schedule = Schedule.query.get_or_404(schedule_id)
    status = request.form.get('status')
    actual_time_str = request.form.get('actual_time')
    notes = request.form.get('notes', '')
    
    current_date = datetime.now().date()
    
    # Check if attendance already exists
    existing = Attendance.query.filter_by(
        schedule_id=schedule_id,
        date=current_date
    ).first()
    
    if existing:
        existing.status = status
        existing.notes = notes
        
        if status == 'Late' and actual_time_str:
            actual_time = datetime.strptime(actual_time_str, '%H:%M').time()
            existing.actual_time = actual_time
            
            # Calculate minutes late
            scheduled_start = datetime.combine(current_date, schedule.start_time)
            actual_arrival = datetime.combine(current_date, actual_time)
            minutes_late = int((actual_arrival - scheduled_start).total_seconds() / 60)
            existing.minutes_late = max(0, minutes_late)
        else:
            existing.actual_time = None
            existing.minutes_late = None
    else:
        attendance = Attendance(
            schedule_id=schedule_id,
            class_id=schedule.class_id,
            teacher_id=schedule.teacher_id,
            date=current_date,
            status=status,
            notes=notes
        )
        
        if status == 'Late' and actual_time_str:
            actual_time = datetime.strptime(actual_time_str, '%H:%M').time()
            attendance.actual_time = actual_time
            
            # Calculate minutes late
            scheduled_start = datetime.combine(current_date, schedule.start_time)
            actual_arrival = datetime.combine(current_date, actual_time)
            minutes_late = int((actual_arrival - scheduled_start).total_seconds() / 60)
            attendance.minutes_late = max(0, minutes_late)
        
        db.session.add(attendance)
    
    db.session.commit()
    flash('تم تسجيل الحضور بنجاح', 'success')
    return redirect(url_for('class_day_sessions', class_id=schedule.class_id, day_num=schedule.day_of_week))

# Admin Routes - Floor Management
@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/admin/floors')
def admin_floors():
    floors = Floor.query.order_by(Floor.number).all()
    return render_template('admin_floors.html', floors=floors)

@app.route('/admin/floor/add', methods=['GET', 'POST'])
def add_floor():
    if request.method == 'POST':
        name = request.form.get('name')
        number = request.form.get('number')
        
        floor = Floor(name=name, number=number)
        db.session.add(floor)
        db.session.commit()
        
        flash('تمت إضافة الطابق بنجاح', 'success')
        return redirect(url_for('admin_floors'))
    
    return render_template('add_floor.html')

@app.route('/admin/floor/<int:floor_id>/edit', methods=['GET', 'POST'])
def edit_floor(floor_id):
    floor = Floor.query.get_or_404(floor_id)
    
    if request.method == 'POST':
        floor.name = request.form.get('name')
        floor.number = request.form.get('number')
        db.session.commit()
        
        flash('تم تحديث الطابق بنجاح', 'success')
        return redirect(url_for('admin_floors'))
    
    return render_template('edit_floor.html', floor=floor)

@app.route('/admin/floor/<int:floor_id>/delete', methods=['POST'])
def delete_floor(floor_id):
    floor = Floor.query.get_or_404(floor_id)
    db.session.delete(floor)
    db.session.commit()
    
    flash('تم حذف الطابق بنجاح', 'success')
    return redirect(url_for('admin_floors'))

# Admin Routes - Class Management
@app.route('/admin/classes')
def admin_classes():
    classes = Class.query.join(Floor).order_by(Floor.number, Class.name).all()
    return render_template('admin_classes.html', classes=classes)

@app.route('/admin/class/add', methods=['GET', 'POST'])
def add_class():
    if request.method == 'POST':
        name = request.form.get('name')
        floor_id = request.form.get('floor_id')
        
        class_room = Class(name=name, floor_id=floor_id)
        db.session.add(class_room)
        db.session.commit()
        
        flash('تمت إضافة الفصل بنجاح', 'success')
        return redirect(url_for('admin_classes'))
    
    floors = Floor.query.order_by(Floor.number).all()
    return render_template('add_class.html', floors=floors)

@app.route('/admin/class/<int:class_id>/edit', methods=['GET', 'POST'])
def edit_class(class_id):
    class_room = Class.query.get_or_404(class_id)
    
    if request.method == 'POST':
        class_room.name = request.form.get('name')
        class_room.floor_id = request.form.get('floor_id')
        db.session.commit()
        
        flash('تم تحديث الفصل بنجاح', 'success')
        return redirect(url_for('admin_classes'))
    
    floors = Floor.query.order_by(Floor.number).all()
    return render_template('edit_class.html', class_room=class_room, floors=floors)

@app.route('/admin/class/<int:class_id>/delete', methods=['POST'])
def delete_class(class_id):
    class_room = Class.query.get_or_404(class_id)
    db.session.delete(class_room)
    db.session.commit()
    
    flash('تم حذف الفصل بنجاح', 'success')
    return redirect(url_for('admin_classes'))

# Admin Routes - Teacher Management
@app.route('/admin/teachers')
def admin_teachers():
    teachers = Teacher.query.order_by(Teacher.name).all()
    return render_template('admin_teachers.html', teachers=teachers)

@app.route('/admin/teacher/add', methods=['GET', 'POST'])
def add_teacher():
    if request.method == 'POST':
        name = request.form.get('name')
        
        teacher = Teacher(name=name)
        db.session.add(teacher)
        db.session.commit()
        
        flash('تمت إضافة المعلم بنجاح', 'success')
        return redirect(url_for('admin_teachers'))
    
    return render_template('add_teacher.html')

@app.route('/admin/teacher/<int:teacher_id>/edit', methods=['GET', 'POST'])
def edit_teacher(teacher_id):
    teacher = Teacher.query.get_or_404(teacher_id)
    
    if request.method == 'POST':
        teacher.name = request.form.get('name')
        db.session.commit()
        
        flash('تم تحديث المعلم بنجاح', 'success')
        return redirect(url_for('admin_teachers'))
    
    return render_template('edit_teacher.html', teacher=teacher)

@app.route('/admin/teacher/<int:teacher_id>/delete', methods=['POST'])
def delete_teacher(teacher_id):
    teacher = Teacher.query.get_or_404(teacher_id)
    
    # Check if teacher has schedules
    if teacher.schedules:
        flash('لا يمكن حذف المعلم لأنه مرتبط بجدول دراسي', 'error')
        return redirect(url_for('admin_teachers'))
    
    db.session.delete(teacher)
    db.session.commit()
    
    flash('تم حذف المعلم بنجاح', 'success')
    return redirect(url_for('admin_teachers'))

# Admin Routes - Subject Management
@app.route('/admin/subjects')
def admin_subjects():
    subjects = Subject.query.order_by(Subject.name).all()
    return render_template('admin_subjects.html', subjects=subjects)

@app.route('/admin/subject/add', methods=['GET', 'POST'])
def add_subject():
    if request.method == 'POST':
        name = request.form.get('name')
        
        subject = Subject(name=name)
        db.session.add(subject)
        db.session.commit()
        
        flash('تمت إضافة المادة بنجاح', 'success')
        return redirect(url_for('admin_subjects'))
    
    return render_template('add_subject.html')

@app.route('/admin/subject/<int:subject_id>/edit', methods=['GET', 'POST'])
def edit_subject(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    
    if request.method == 'POST':
        subject.name = request.form.get('name')
        db.session.commit()
        
        flash('تم تحديث المادة بنجاح', 'success')
        return redirect(url_for('admin_subjects'))
    
    return render_template('edit_subject.html', subject=subject)

@app.route('/admin/subject/<int:subject_id>/delete', methods=['POST'])
def delete_subject(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    
    # Check if subject has schedules
    if subject.schedules:
        flash('لا يمكن حذف المادة لأنها مرتبطة بجدول دراسي', 'error')
        return redirect(url_for('admin_subjects'))
    
    db.session.delete(subject)
    db.session.commit()
    
    flash('تم حذف المادة بنجاح', 'success')
    return redirect(url_for('admin_subjects'))

# Admin Routes - Schedule Management
@app.route('/admin/schedules')
def admin_schedules():
    classes = Class.query.join(Floor).order_by(Floor.number, Class.name).all()
    return render_template('admin_schedules.html', classes=classes)

@app.route('/admin/class/<int:class_id>/schedules')
def class_schedules(class_id):
    class_room = Class.query.get_or_404(class_id)
    schedules = Schedule.query.filter_by(class_id=class_id).order_by(
        Schedule.day_of_week, Schedule.start_time
    ).all()
    
    # Group schedules by day
    days = ['الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت', 'الأحد']
    schedules_by_day = {i: [] for i in range(7)}
    
    for schedule in schedules:
        schedules_by_day[schedule.day_of_week].append(schedule)
    
    return render_template('class_schedules.html', 
                         class_room=class_room,
                         schedules_by_day=schedules_by_day,
                         days=days)

@app.route('/admin/class/<int:class_id>/schedule/add', methods=['GET', 'POST'])
def add_schedule(class_id):
    class_room = Class.query.get_or_404(class_id)
    
    if request.method == 'POST':
        teacher_id = request.form.get('teacher_id')
        subject_id = request.form.get('subject_id')
        day_of_week = request.form.get('day_of_week')
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')
        
        schedule = Schedule(
            class_id=class_id,
            teacher_id=teacher_id,
            subject_id=subject_id,
            day_of_week=day_of_week,
            start_time=datetime.strptime(start_time, '%H:%M').time(),
            end_time=datetime.strptime(end_time, '%H:%M').time()
        )
        
        db.session.add(schedule)
        db.session.commit()
        
        flash('تمت إضافة الحصة بنجاح', 'success')
        return redirect(url_for('class_schedules', class_id=class_id))
    
    teachers = Teacher.query.order_by(Teacher.name).all()
    subjects = Subject.query.order_by(Subject.name).all()
    days = ['الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت', 'الأحد']
    
    return render_template('add_schedule.html', 
                         class_room=class_room,
                         teachers=teachers,
                         subjects=subjects,
                         days=days)

@app.route('/admin/schedule/<int:schedule_id>/edit', methods=['GET', 'POST'])
def edit_schedule(schedule_id):
    schedule = Schedule.query.get_or_404(schedule_id)
    
    if request.method == 'POST':
        schedule.teacher_id = request.form.get('teacher_id')
        schedule.subject_id = request.form.get('subject_id')
        schedule.day_of_week = request.form.get('day_of_week')
        schedule.start_time = datetime.strptime(request.form.get('start_time'), '%H:%M').time()
        schedule.end_time = datetime.strptime(request.form.get('end_time'), '%H:%M').time()
        
        db.session.commit()
        
        flash('تم تحديث الحصة بنجاح', 'success')
        return redirect(url_for('class_schedules', class_id=schedule.class_id))
    
    teachers = Teacher.query.order_by(Teacher.name).all()
    subjects = Subject.query.order_by(Subject.name).all()
    days = ['الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت', 'الأحد']
    
    return render_template('edit_schedule.html',
                         schedule=schedule,
                         teachers=teachers,
                         subjects=subjects,
                         days=days)

@app.route('/admin/schedule/<int:schedule_id>/delete', methods=['POST'])
def delete_schedule(schedule_id):
    schedule = Schedule.query.get_or_404(schedule_id)
    class_id = schedule.class_id
    
    db.session.delete(schedule)
    db.session.commit()
    
    flash('تم حذف الحصة بنجاح', 'success')
    return redirect(url_for('class_schedules', class_id=class_id))

# Statistics Routes
@app.route('/statistics')
def statistics():
    return render_template('statistics.html')

@app.route('/statistics/daily', methods=['GET', 'POST'])
def daily_statistics():
    if request.method == 'POST':
        date_str = request.form.get('date')
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    else:
        selected_date = datetime.now().date()
    
    # Get all attendance records for the selected date
    attendances = Attendance.query.filter_by(date=selected_date).all()
    
    # Statistics by status
    total = len(attendances)
    present = len([a for a in attendances if a.status == 'Present'])
    late = len([a for a in attendances if a.status == 'Late'])
    absent = len([a for a in attendances if a.status == 'Absent'])
    
    # Statistics by floor
    floor_stats = {}
    for attendance in attendances:
        floor = attendance.class_room.floor
        if floor.id not in floor_stats:
            floor_stats[floor.id] = {
                'floor': floor,
                'present': 0,
                'late': 0,
                'absent': 0,
                'total': 0
            }
        
        floor_stats[floor.id]['total'] += 1
        if attendance.status == 'Present':
            floor_stats[floor.id]['present'] += 1
        elif attendance.status == 'Late':
            floor_stats[floor.id]['late'] += 1
        elif attendance.status == 'Absent':
            floor_stats[floor.id]['absent'] += 1
    
    # Statistics by teacher
    teacher_stats = {}
    for attendance in attendances:
        teacher = attendance.teacher
        if teacher.id not in teacher_stats:
            teacher_stats[teacher.id] = {
                'teacher': teacher,
                'present': 0,
                'late': 0,
                'absent': 0,
                'total': 0,
                'total_minutes_late': 0
            }
        
        teacher_stats[teacher.id]['total'] += 1
        if attendance.status == 'Present':
            teacher_stats[teacher.id]['present'] += 1
        elif attendance.status == 'Late':
            teacher_stats[teacher.id]['late'] += 1
            if attendance.minutes_late:
                teacher_stats[teacher.id]['total_minutes_late'] += attendance.minutes_late
        elif attendance.status == 'Absent':
            teacher_stats[teacher.id]['absent'] += 1
    
    return render_template('daily_statistics.html',
                         selected_date=selected_date,
                         total=total,
                         present=present,
                         late=late,
                         absent=absent,
                         floor_stats=floor_stats.values(),
                         teacher_stats=teacher_stats.values())

# API endpoint for teacher search
@app.route('/api/teachers/search')
def search_teachers():
    try:
        query = request.args.get('q', '').strip()
        if len(query) < 2:
            return jsonify([])
        
        teachers = Teacher.query.filter(Teacher.name.contains(query)).limit(10).all()
        return jsonify([{'id': teacher.id, 'name': teacher.name} for teacher in teachers])
    except Exception as e:
        print(f"Error in teacher search: {e}")
        return jsonify([])

# Attendance Reports Route
@app.route('/reports/attendance')
def attendance_reports():
    """View all attendance records"""
    # Get filter parameters
    date_filter = request.args.get('date')
    class_filter = request.args.get('class_id')
    teacher_filter = request.args.get('teacher_id')
    
    # Build query
    query = Attendance.query
    
    if date_filter:
        date_obj = datetime.strptime(date_filter, '%Y-%m-%d').date()
        query = query.filter_by(date=date_obj)
    
    if class_filter:
        query = query.filter_by(class_id=int(class_filter))
    
    if teacher_filter:
        query = query.filter_by(teacher_id=int(teacher_filter))
    
    # Get all matching records, ordered by date and time
    records = query.join(Schedule).order_by(
        Attendance.date.desc(), 
        Schedule.start_time
    ).all()
    
    # Get filter options
    classes = Class.query.join(Floor).order_by(Floor.number, Class.name).all()
    teachers = Teacher.query.order_by(Teacher.name).all()
    
    return render_template('attendance_reports.html',
                         records=records,
                         classes=classes,
                         teachers=teachers,
                         date_filter=date_filter,
                         class_filter=class_filter,
                         teacher_filter=teacher_filter)

# Initialize database
def init_db():
    with app.app_context():
        try:
            db.create_all()
            
            # Add sample data for Vercel deployment if database is empty
            if os.environ.get('VERCEL') and Floor.query.count() == 0:
                # Add floors
                for i in range(1, 6):
                    floor = Floor(name=f'الطابق {i}', number=i)
                    db.session.add(floor)
                
                db.session.commit()
                
                # Add sample classes
                floors = Floor.query.all()
                for floor in floors[:3]:  # Add classes to first 3 floors
                    for j in range(1, 4):
                        class_room = Class(name=f'فصل {floor.number}-{j}', floor_id=floor.id)
                        db.session.add(class_room)
                
                # Add sample teachers
                teachers_names = ['أحمد محمد', 'فاطمة علي', 'محمود حسن', 'سارة إبراهيم', 'خالد يوسف']
                for name in teachers_names:
                    teacher = Teacher(name=name)
                    db.session.add(teacher)
                
                # Add sample subjects
                subjects_names = ['الرياضيات', 'العلوم', 'اللغة العربية', 'اللغة الإنجليزية', 'التاريخ']
                for name in subjects_names:
                    subject = Subject(name=name)
                    db.session.add(subject)
                
                db.session.commit()
                
        except Exception as e:
            print(f"Database initialization error: {e}")
            # Continue without database for now

# For Vercel deployment
app.wsgi_app = app.wsgi_app

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5001)


