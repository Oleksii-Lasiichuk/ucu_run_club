from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import sqlite3
import os
import secrets
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.config['DATABASE'] = os.path.join(app.root_path, 'running_event.db')
app.secret_key = secrets.token_hex(16)  # Generate a random secret key for sessions

# Admin credentials - should be changed in production
ADMIN_PASSWORD = "admin123"

# Faculties with their corresponding colors (updated as requested)
FACULTIES = {
    'Філософсько-Богословський факультет': '#FF0000',  # Red
    'Гуманітарний факультет': '#FFA500',              # Orange
    'Факультет Наук про Здоровʼя': '#008000',         # Green
    'Факультет Суспільних Наук': '#0000FF',           # Blue
    'Факультет Прикладних Наук': '#800080'            # Purple
}

# Define participant types and their points
PARTICIPANT_TYPES = {
    'student': {'name': 'Студент', 'points': 1},
    'employee': {'name': 'Працівник', 'points': 1},
    'teacher': {'name': 'Викладач', 'points': 2},
    'dean': {'name': 'Декан/Адміністратор', 'points': 3}
}

def get_db_connection():
    """Create a database connection"""
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the database with required tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Update laps table to include participant data
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS laps_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            faculty TEXT NOT NULL,
            participant_type TEXT NOT NULL,
            participant_number TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Check if old laps table exists and migrate data if needed
    old_table_exists = cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='laps'").fetchone()
    if old_table_exists:
        try:
            # Try to check if the table has the new columns
            cursor.execute("SELECT participant_type FROM laps LIMIT 1")
            # If there's no error, the table already has the new structure
        except sqlite3.OperationalError:
            # If there's an error, it means the table has the old structure and we need to migrate
            print("Migrating laps table to new structure...")
            # Copy existing data with default values for new columns
            cursor.execute('''
                INSERT INTO laps_new (faculty, participant_type, participant_number, timestamp)
                SELECT faculty, 
                       CASE WHEN is_teacher = 1 THEN 'teacher' ELSE 'student' END as participant_type,
                       'legacy' as participant_number,
                       timestamp
                FROM laps
            ''')
            
            # Drop old table and rename new one
            cursor.execute("DROP TABLE laps")
            cursor.execute("ALTER TABLE laps_new RENAME TO laps")
            print("Migration completed.")
    else:
        # If laps doesn't exist yet, rename the new table
        cursor.execute("ALTER TABLE laps_new RENAME TO laps")
    
    # Continue with other tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS donations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            faculty TEXT NOT NULL,
            amount REAL NOT NULL,
            comment TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create participants table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS participants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            number TEXT UNIQUE NOT NULL,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            faculty TEXT NOT NULL,
            participant_type TEXT NOT NULL,
            registration_time DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create event_status table to store event state
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS event_status (
            id INTEGER PRIMARY KEY CHECK (id = 1), 
            status TEXT NOT NULL DEFAULT 'registration',
            registration_open BOOLEAN NOT NULL DEFAULT 1
        )
    ''')
    
    # Insert default event status if not exists
    cursor.execute('''
        INSERT OR IGNORE INTO event_status (id, status, registration_open)
        VALUES (1, 'registration', 1)
    ''')
    
    conn.commit()
    conn.close()

# Initialize database on startup
init_db()

# Admin authentication decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# Public pages - accessible without login
@app.route('/')
def public_home():
    """Public home page showing faculty standings"""
    conn = get_db_connection()
    status = conn.execute('SELECT status FROM event_status WHERE id = 1').fetchone()
    conn.close()
    
    # If event hasn't started, show a different message
    event_started = status['status'] == 'running'
    
    # Get current standings data for faculties
    standings_data = get_standings().json
    
    return render_template('public/index.html', 
                          standings=standings_data, 
                          faculties=FACULTIES,
                          event_started=event_started)

@app.route('/rankings')
def public_rankings():
    """Public page showing individual rankings"""
    # Get participant ranking data
    ranking_data = get_participant_ranking().json
    
    return render_template('public/rankings.html', 
                          participants=ranking_data, 
                          faculties=FACULTIES)

@app.route('/find-me')
def find_participant():
    """Page to help a participant find themselves in the rankings"""
    participant_number = request.args.get('number')
    result = None
    
    if participant_number:
        # Get participant ranking data
        all_rankings = get_participant_ranking().json
        
        # Find participant by number
        for participant in all_rankings:
            if participant['participant_number'] == participant_number:
                result = participant
                break
    
    return render_template('public/find_me.html', 
                          participant=result,
                          number=participant_number)

# Admin routes
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login page"""
    error = None
    
    if request.method == 'POST':
        password = request.form.get('password', '')
        
        if password == ADMIN_PASSWORD:
            session['is_admin'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            error = 'Невірний пароль. Спробуйте ще раз.'
    
    return render_template('admin/login.html', error=error)

@app.route('/admin/logout')
def admin_logout():
    """Admin logout"""
    session.pop('is_admin', None)
    return redirect(url_for('public_home'))

@app.route('/admin')
@admin_required
def admin_dashboard():
    """Admin dashboard - main admin page"""
    conn = get_db_connection()
    
    # Get event status
    status = conn.execute('SELECT status, registration_open FROM event_status WHERE id = 1').fetchone()
    
    # Get counts for summary
    participant_count = conn.execute('SELECT COUNT(*) as count FROM participants').fetchone()['count']
    lap_count = conn.execute('SELECT COUNT(*) as count FROM laps').fetchone()['count']
    donation_sum = conn.execute('SELECT SUM(amount) as sum FROM donations').fetchone()['sum'] or 0
    
    # Get latest activities
    latest_laps = conn.execute('''
        SELECT l.timestamp, l.faculty, l.participant_number, l.participant_type, 
               p.first_name, p.last_name
        FROM laps l
        LEFT JOIN participants p ON l.participant_number = p.number
        ORDER BY l.timestamp DESC LIMIT 5
    ''').fetchall()
    
    latest_donations = conn.execute('''
        SELECT timestamp, faculty, amount, comment
        FROM donations 
        ORDER BY timestamp DESC LIMIT 5
    ''').fetchall()
    
    conn.close()
    
    return render_template('admin/dashboard.html', 
                          status=status,
                          participant_count=participant_count,
                          lap_count=lap_count,
                          donation_sum=donation_sum,
                          latest_laps=latest_laps,
                          latest_donations=latest_donations,
                          faculties=FACULTIES,
                          participant_types=PARTICIPANT_TYPES)

@app.route('/admin/participants')
@admin_required
def admin_participants():
    """Admin page for participant management"""
    conn = get_db_connection()
    
    # Get all participants
    participants = conn.execute(
        'SELECT * FROM participants ORDER BY number'
    ).fetchall()
    
    # Get event status
    status = conn.execute('SELECT status, registration_open FROM event_status WHERE id = 1').fetchone()
    
    conn.close()
    
    return render_template(
        'admin/participants.html', 
        participants=participants, 
        faculties=FACULTIES, 
        participant_types=PARTICIPANT_TYPES,
        event_status=status
    )

@app.route('/admin/laps')
@admin_required
def admin_laps():
    """Admin page for managing laps"""
    return render_template('admin/laps.html', 
                          faculties=FACULTIES, 
                          participant_types=PARTICIPANT_TYPES)

@app.route('/admin/donations')
@admin_required
def admin_donations():
    """Admin page for managing donations"""
    conn = get_db_connection()
    
    # Get all donations
    donations = conn.execute('''
        SELECT id, faculty, amount, comment, timestamp
        FROM donations 
        ORDER BY timestamp DESC
    ''').fetchall()
    
    conn.close()
    
    return render_template('admin/donations.html', 
                          donations=donations, 
                          faculties=FACULTIES)

@app.route('/admin/settings')
@admin_required
def admin_settings():
    """Admin settings page"""
    conn = get_db_connection()
    
    # Get event status
    status = conn.execute('SELECT status, registration_open FROM event_status WHERE id = 1').fetchone()
    
    # Get counts for summary
    participant_count = conn.execute('SELECT COUNT(*) as count FROM participants').fetchone()['count']
    lap_count = conn.execute('SELECT COUNT(*) as count FROM laps').fetchone()['count']
    donation_count = conn.execute('SELECT COUNT(*) as count FROM donations').fetchone()['count']
    
    # Get participant counts by faculty
    faculty_participants = {}
    for faculty in FACULTIES:
        count = conn.execute('SELECT COUNT(*) as count FROM participants WHERE faculty = ?', 
                            (faculty,)).fetchone()['count']
        faculty_participants[faculty] = count
    
    conn.close()
    
    return render_template('admin/settings.html', 
                          event_status=status,
                          participant_count=participant_count,
                          lap_count=lap_count,
                          donation_count=donation_count,
                          faculties=FACULTIES,
                          faculty_participants=faculty_participants)

@app.route('/admin/run-management')
@admin_required
def admin_run_management():
    """Admin page for run management"""
    # Get faculties for faculty buttons
    return render_template('admin/run_management.html', faculties=FACULTIES)

@app.route('/admin/reset_laps', methods=['POST'])
@admin_required
def reset_laps():
    """Reset all laps but keep participants"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get count of records that will be deleted
        count_result = conn.execute('SELECT COUNT(*) as count FROM laps').fetchone()
        deleted_count = count_result['count'] if count_result else 0
        
        # Delete all lap records
        cursor.execute('DELETE FROM laps')
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'All laps have been reset', 'deleted_count': deleted_count})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/reset_donations', methods=['POST'])
@admin_required
def reset_donations():
    """Reset all donations"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get count of records that will be deleted
        count_result = conn.execute('SELECT COUNT(*) as count FROM donations').fetchone()
        deleted_count = count_result['count'] if count_result else 0
        
        # Delete all donation records
        cursor.execute('DELETE FROM donations')
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'All donations have been reset', 'deleted_count': deleted_count})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/reset_donations', methods=['POST'])
def reset_donations_api():
    """Delete all donations from the database"""
    try:
        from reset_donations import reset_donations
        result = reset_donations()
        
        if result:
            return jsonify({'success': True, 'message': 'Всі донати було успішно видалено!'})
        else:
            return jsonify({'success': False, 'message': 'Помилка при видаленні донатів'}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/reset_race', methods=['POST'])
@admin_required
def reset_race():
    """Reset everything related to the race (laps, donations) and set status to registration"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Delete all lap records
        lap_count = conn.execute('SELECT COUNT(*) as count FROM laps').fetchone()['count']
        cursor.execute('DELETE FROM laps')
        
        # Delete all donation records
        donation_count = conn.execute('SELECT COUNT(*) as count FROM donations').fetchone()['count']
        cursor.execute('DELETE FROM donations')
        
        # Reset event status to registration
        cursor.execute('UPDATE event_status SET status = "registration", registration_open = 1 WHERE id = 1')
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True, 
            'message': 'Race has been completely reset',
            'deleted_laps': lap_count,
            'deleted_donations': donation_count
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/backup_database', methods=['GET'])
def backup_database():
    """Download a backup of the database file"""
    import flask
    import datetime
    import shutil
    import tempfile
    
    # Create a temporary copy of the database
    temp_file = tempfile.NamedTemporaryFile(delete=False)
    temp_file.close()
    
    try:
        # Copy the database to the temporary file
        shutil.copy2(app.config['DATABASE'], temp_file.name)
        
        # Generate a timestamped filename for the download
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        download_name = f"running_event_backup_{timestamp}.db"
        
        # Send the file to the client
        return flask.send_file(
            temp_file.name,
            as_attachment=True,
            download_name=download_name,
            mimetype="application/octet-stream"
        )
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error creating backup: {str(e)}'}), 500

@app.route('/participants')
def participants():
    """Participants management page"""
    conn = get_db_connection()
    
    # Get all participants
    participants = conn.execute(
        'SELECT * FROM participants ORDER BY number'
    ).fetchall()
    
    # Get event status
    status = conn.execute('SELECT status, registration_open FROM event_status WHERE id = 1').fetchone()
    
    conn.close()
    
    return render_template(
        'participants.html', 
        participants=participants, 
        faculties=FACULTIES, 
        participant_types=PARTICIPANT_TYPES,
        event_status=status
    )

@app.route('/register_participant', methods=['POST'])
def register_participant():
    """Register a new participant"""
    number = request.form['number']
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    faculty = request.form['faculty']
    participant_type = request.form['participant_type']
    
    conn = get_db_connection()
    
    # Check if participant with this number already exists
    existing = conn.execute('SELECT id FROM participants WHERE number = ?', (number,)).fetchone()
    
    if existing:
        conn.close()
        return jsonify({'success': False, 'message': 'Учасник з таким номером вже існує'}), 400
    
    # Insert new participant
    conn.execute(
        'INSERT INTO participants (number, first_name, last_name, faculty, participant_type) VALUES (?, ?, ?, ?, ?)',
        (number, first_name, last_name, faculty, participant_type)
    )
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True}), 200

@app.route('/update_participant', methods=['POST'])
def update_participant():
    """Update an existing participant"""
    participant_id = request.form['id']
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    faculty = request.form['faculty']
    participant_type = request.form['participant_type']
    
    conn = get_db_connection()
    
    # Update participant
    conn.execute(
        'UPDATE participants SET first_name = ?, last_name = ?, faculty = ?, participant_type = ? WHERE id = ?',
        (first_name, last_name, faculty, participant_type, participant_id)
    )
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True}), 200

@app.route('/delete_participant', methods=['POST'])
def delete_participant():
    """Delete a participant"""
    data = request.json
    participant_id = data['id']
    
    conn = get_db_connection()
    
    # Delete participant
    conn.execute('DELETE FROM participants WHERE id = ?', (participant_id,))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True}), 200

@app.route('/toggle_registration', methods=['POST'])
def toggle_registration():
    """Toggle registration status"""
    conn = get_db_connection()
    
    # Get current status
    status = conn.execute('SELECT registration_open FROM event_status WHERE id = 1').fetchone()
    new_status = not status['registration_open']
    
    # Update status
    conn.execute('UPDATE event_status SET registration_open = ? WHERE id = 1', (new_status,))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'registration_open': new_status}), 200

@app.route('/start_event', methods=['POST'])
def start_event():
    """Start the event"""
    conn = get_db_connection()
    
    # Update event status
    conn.execute('UPDATE event_status SET status = "running", registration_open = 0 WHERE id = 1')
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True}), 200

@app.route('/reset_database', methods=['POST'])
def reset_database():
    """Reset the database by deleting all tables and reinitializing"""
    try:
        # Delete the database file
        if os.path.exists(app.config['DATABASE']):
            os.remove(app.config['DATABASE'])
            
        # Reinitialize the database
        init_db()
        
        return jsonify({'success': True, 'message': 'База даних успішно скинута'}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Помилка при скиданні бази даних: {str(e)}'}), 500

@app.route('/lookup_participant_info', methods=['GET'])
def lookup_participant_info():
    """Lookup participant information by number"""
    participant_number = request.args.get('participantNumber')
    
    conn = get_db_connection()
    
    # Find participant
    participant = conn.execute(
        'SELECT faculty, participant_type FROM participants WHERE number = ?',
        (participant_number,)
    ).fetchone()
    
    conn.close()
    
    if participant:
        return jsonify({
            'success': True,
            'faculty': participant['faculty'],
            'participantType': participant['participant_type']
        }), 200
    else:
        return jsonify({'success': False}), 404

@app.route('/add_lap', methods=['POST'])
def add_lap():
    """Add a lap for a faculty"""
    data = request.json
    faculty = data['faculty']
    participant_type = data['participantType']
    participant_number = data['participantNumber']
    
    conn = get_db_connection()
    conn.execute('INSERT INTO laps (faculty, participant_type, participant_number) VALUES (?, ?, ?)',
                (faculty, participant_type, participant_number))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True}), 200

@app.route('/add_faculty_lap', methods=['POST'])
def add_faculty_lap():
    """Add a lap directly for a faculty (without specific participant)"""
    data = request.json
    faculty = data['faculty']
    participant_type = data['participantType'] 
    
    # Use a generic participant number for faculty laps
    participant_number = f"faculty_{faculty}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    conn = get_db_connection()
    conn.execute('INSERT INTO laps (faculty, participant_type, participant_number) VALUES (?, ?, ?)',
                (faculty, participant_type, participant_number))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True}), 200

@app.route('/subtract_lap', methods=['POST'])
def subtract_lap():
    """Remove a lap for a faculty"""
    data = request.json
    faculty = data['faculty']
    participant_type = data['participantType']
    participant_number = data['participantNumber']
    
    conn = get_db_connection()
    # Find the most recent lap entry for this faculty, type and participant to remove
    lap = conn.execute(
        'SELECT id FROM laps WHERE faculty = ? AND participant_type = ? AND participant_number = ? ORDER BY timestamp DESC LIMIT 1',
        (faculty, participant_type, participant_number)
    ).fetchone()
    
    if lap:
        conn.execute('DELETE FROM laps WHERE id = ?', (lap['id'],))
        conn.commit()
        conn.close()
        return jsonify({'success': True}), 200
    else:
        conn.close()
        return jsonify({'success': False, 'message': 'No laps found to remove'}), 404

@app.route('/subtract_faculty_lap', methods=['POST'])
def subtract_faculty_lap():
    """Remove a lap for a faculty without specific participant"""
    data = request.json
    faculty = data['faculty']
    participant_type = data.get('participantType', 'student')  # Default to student if not specified
    
    conn = get_db_connection()
    # Find the most recent lap entry for this faculty to remove
    lap = conn.execute(
        'SELECT id FROM laps WHERE faculty = ? AND participant_type = ? ORDER BY timestamp DESC LIMIT 1',
        (faculty, participant_type)
    ).fetchone()
    
    if lap:
        conn.execute('DELETE FROM laps WHERE id = ?', (lap['id'],))
        conn.commit()
        conn.close()
        return jsonify({'success': True}), 200
    else:
        conn.close()
        return jsonify({'success': False, 'message': 'No laps found to remove'}), 404

@app.route('/add_donation', methods=['POST'])
def add_donation():
    """Add a donation for a faculty"""
    try:
        # Check if the request is JSON or form data
        if request.is_json:
            data = request.json
        else:
            data = request.form
            
        faculty = data.get('faculty')
        amount = float(data.get('amount', 0))
        comment = data.get('comment', '')
        
        if not faculty:
            return jsonify({'success': False, 'message': 'Faculty is required'}), 400
            
        if amount <= 0:
            return jsonify({'success': False, 'message': 'Amount must be greater than 0'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Insert donation
        cursor.execute('INSERT INTO donations (faculty, amount, comment) VALUES (?, ?, ?)',
                    (faculty, amount, comment))
        
        # Get the ID of the last inserted row
        donation_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        print(f"Successfully added donation: faculty={faculty}, amount={amount}, comment={comment}, id={donation_id}")
        return jsonify({'success': True, 'donation_id': donation_id}), 200
    except Exception as e:
        print(f"ERROR adding donation: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/subtract_donation', methods=['POST'])
def subtract_donation():
    """Remove a donation for a faculty"""
    data = request.form
    faculty = data['faculty']
    amount = float(data['amount'])
    
    conn = get_db_connection()
    try:
        # Find a donation with matching amount or the most recent one
        donation = conn.execute(
            'SELECT id FROM donations WHERE faculty = ? AND amount = ? ORDER BY timestamp DESC LIMIT 1',
            (faculty, amount)
        ).fetchone()
        
        if donation:
            deleted_id = donation['id']
            conn.execute('DELETE FROM donations WHERE id = ?', (deleted_id,))
            conn.commit()
            conn.close()
            return jsonify({'success': True, 'deleted_id': deleted_id}), 200
        else:
            # If no exact match, try to find the most recent donation for this faculty
            donation = conn.execute(
                'SELECT id FROM donations WHERE faculty = ? ORDER BY timestamp DESC LIMIT 1',
                (faculty,)
            ).fetchone()
            
            if donation:
                deleted_id = donation['id']
                conn.execute('DELETE FROM donations WHERE id = ?', (deleted_id,))
                conn.commit()
                conn.close()
                return jsonify({'success': True, 'deleted_id': deleted_id}), 200
            else:
                conn.close()
                return jsonify({
                    'success': False, 
                    'message': f'Немає донатів для факультету "{faculty}" для віднімання'
                }), 404
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/delete_donation/<int:donation_id>', methods=['POST'])
def delete_donation(donation_id):
    """Delete a specific donation by ID"""
    try:
        conn = get_db_connection()
        
        # Check if donation exists
        donation = conn.execute('SELECT id FROM donations WHERE id = ?', (donation_id,)).fetchone()
        if not donation:
            conn.close()
            return jsonify({'success': False, 'message': 'Донат не знайдено'}), 404
        
        # Delete the donation
        conn.execute('DELETE FROM donations WHERE id = ?', (donation_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/get_standings', methods=['GET'])
def get_standings():
    """Get current standings data"""
    conn = get_db_connection()
    
    # Calculate laps points
    cursor = conn.cursor()
    standings = {}
    
    # Initialize standings for all faculties
    for faculty in FACULTIES:
        standings[faculty] = {
            'faculty': faculty,
            'student_laps': 0,
            'teacher_laps': 0,
            'dean_laps': 0,
            'employee_laps': 0,
            'donations': 0,
            'total_points': 0,
            'color': FACULTIES[faculty]
        }
    
    # Count laps and calculate points by participant type
    laps_query = '''
        SELECT faculty, participant_type, COUNT(*) as count 
        FROM laps 
        GROUP BY faculty, participant_type
    '''
    
    laps_results = cursor.execute(laps_query).fetchall()
    
    for row in laps_results:
        if row['faculty'] in standings:
            participant_type = row['participant_type']
            count = row['count']
            points = PARTICIPANT_TYPES[participant_type]['points'] * count
            
            if participant_type == 'student':
                standings[row['faculty']]['student_laps'] = count
            elif participant_type == 'teacher':
                standings[row['faculty']]['teacher_laps'] = count
            elif participant_type == 'dean':
                standings[row['faculty']]['dean_laps'] = count
            elif participant_type == 'employee':
                standings[row['faculty']]['employee_laps'] = count
                
            standings[row['faculty']]['total_points'] += points
    
    # Calculate donation points (100 UAH = 1 point) - updated from 500 to 100
    donations = cursor.execute(
        'SELECT faculty, SUM(amount) as total FROM donations GROUP BY faculty'
    ).fetchall()
    for row in donations:
        if row['faculty'] in standings:
            donation_amount = row['total']
            donation_points = int(donation_amount / 100)  # Changed from 500 to 100
            standings[row['faculty']]['donations'] = donation_amount
            standings[row['faculty']]['total_points'] += donation_points
    
    # Convert to list and sort by total points
    result = list(standings.values())
    result.sort(key=lambda x: x['total_points'], reverse=True)
    
    conn.close()
    return jsonify(result)

@app.route('/get_participant_ranking', methods=['GET'])
def get_participant_ranking():
    """Get ranking of individual participants by distance run"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Query to get participant ranking - exclude faculty laps
    ranking_query = '''
        SELECT 
            l.faculty, 
            l.participant_number, 
            l.participant_type,
            COUNT(*) as laps,
            p.first_name,
            p.last_name
        FROM laps l
        LEFT JOIN participants p ON l.participant_number = p.number
        WHERE l.participant_number NOT LIKE 'faculty_%'
        GROUP BY l.faculty, l.participant_number, l.participant_type
        ORDER BY laps DESC
        LIMIT 50
    '''
    
    participants = cursor.execute(ranking_query).fetchall()
    
    # Format data
    result = []
    for idx, row in enumerate(participants):
        # Calculate points contributed based on participant type and laps
        points = PARTICIPANT_TYPES[row['participant_type']]['points'] * row['laps']
        
        # Get first and last name (handle legacy entries without participant registration)
        first_name = row['first_name'] if row['first_name'] else ''
        last_name = row['last_name'] if row['last_name'] else ''
        
        result.append({
            'rank': idx + 1,
            'faculty': row['faculty'],
            'participant_number': row['participant_number'],
            'participant_type': PARTICIPANT_TYPES[row['participant_type']]['name'],
            'first_name': first_name,
            'last_name': last_name,
            'laps': row['laps'],
            'points': points,
            'color': FACULTIES[row['faculty']]
        })
    
    conn.close()
    return jsonify(result)

@app.route('/update_event_status', methods=['POST'])
def update_event_status():
    """Update the event status (running or registration)"""
    data = request.json
    new_status = data.get('status')
    
    if new_status not in ['running', 'registration']:
        return jsonify({'success': False, 'message': 'Invalid status value'}), 400
    
    conn = get_db_connection()
    
    # Update event status
    conn.execute('UPDATE event_status SET status = ? WHERE id = 1', (new_status,))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True}), 200

@app.route('/api/laps/recent', methods=['GET'])
def api_get_recent_laps():
    """Get recent laps for API"""
    try:
        conn = get_db_connection()
        
        # Get most recent laps
        laps = conn.execute('''
            SELECT l.id, l.faculty, l.participant_number, l.participant_type, 
                   strftime('%H:%M', l.timestamp) as time,
                   p.first_name, p.last_name
            FROM laps l
            LEFT JOIN participants p ON l.participant_number = p.number
            ORDER BY l.timestamp DESC 
            LIMIT 20
        ''').fetchall()
        
        # Format for API response
        result = []
        for lap in laps:
            # Fix for undefined name issue
            first_name = lap['first_name'] if lap['first_name'] else ""
            last_name = lap['last_name'] if lap['last_name'] else ""
            
            # If it's a faculty lap (without specific participant)
            if lap['participant_number'].startswith('faculty_'):
                participant_name = f"Факультетське коло ({PARTICIPANT_TYPES.get(lap['participant_type'], {}).get('name', 'Невідомо')})"
            else:
                participant_name = f"{first_name} {last_name}".strip() or f"Учасник #{lap['participant_number']}"
            
            result.append({
                'id': lap['id'],
                'faculty': lap['faculty'],
                'participant_number': lap['participant_number'],
                'participant_type': PARTICIPANT_TYPES.get(lap['participant_type'], {}).get('name', lap['participant_type']),
                'time': lap['time'],
                'name': participant_name
            })
        
        conn.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/statistics', methods=['GET'])
def api_get_statistics():
    """Get statistics for API"""
    try:
        conn = get_db_connection()
        
        # Get total laps
        total_laps = conn.execute('SELECT COUNT(*) as count FROM laps').fetchone()['count']
        
        # Calculate total distance (assuming each lap is 0.5km)
        total_distance = total_laps * 0.5
        
        conn.close()
        return jsonify({
            'laps': total_laps,
            'distance': total_distance
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/laps/add', methods=['POST'])
def api_add_lap():
    """Add a lap via API"""
    try:
        data = request.json
        participant_number = data.get('participant_number')
        count = data.get('count', 1)
        
        if not participant_number:
            return jsonify({'success': False, 'message': 'Participant number is required'}), 400
        
        conn = get_db_connection()
        
        # Get participant info
        participant = conn.execute(
            'SELECT faculty, participant_type FROM participants WHERE number = ?',
            (participant_number,)
        ).fetchone()
        
        if not participant:
            conn.close()
            return jsonify({'success': False, 'message': 'Participant not found'}), 404
        
        faculty = participant['faculty']
        participant_type = participant['participant_type']
        
        # Add the specified number of laps
        for _ in range(count):
            conn.execute(
                'INSERT INTO laps (faculty, participant_type, participant_number) VALUES (?, ?, ?)',
                (faculty, participant_type, participant_number)
            )
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': f'Added {count} lap(s) for participant #{participant_number}'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/faculty-lap/add', methods=['POST'])
def api_add_faculty_lap():
    """Add a lap for a faculty without specific participant"""
    try:
        data = request.json
        faculty = data.get('faculty')
        participant_type = data.get('participant_type', 'student')  # Default to student
        count = int(data.get('count', 1))
        
        if not faculty:
            return jsonify({'success': False, 'message': 'Faculty is required'}), 400
            
        # Use a generic participant number for faculty laps
        participant_number = f"faculty_{faculty}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        conn = get_db_connection()
        
        # Add multiple laps if requested
        for _ in range(count):
            conn.execute('INSERT INTO laps (faculty, participant_type, participant_number) VALUES (?, ?, ?)',
                        (faculty, participant_type, participant_number))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': f'Added {count} lap(s) for {faculty}'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/laps/remove', methods=['POST'])
def api_remove_lap():
    """Remove a lap via API"""
    try:
        data = request.json
        participant_number = data.get('participant_number')
        
        if not participant_number:
            return jsonify({'success': False, 'message': 'Participant number is required'}), 400
        
        conn = get_db_connection()
        
        # Find the most recent lap for this participant
        lap = conn.execute(
            'SELECT id FROM laps WHERE participant_number = ? ORDER BY timestamp DESC LIMIT 1',
            (participant_number,)
        ).fetchone()
        
        if not lap:
            conn.close()
            return jsonify({'success': False, 'message': 'No laps found for this participant'}), 404
        
        # Delete the lap
        conn.execute('DELETE FROM laps WHERE id = ?', (lap['id'],))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': f'Removed 1 lap for participant #{participant_number}'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/laps/<int:lap_id>', methods=['DELETE'])
def api_delete_lap(lap_id):
    """Delete a specific lap by ID via API"""
    try:
        conn = get_db_connection()
        
        # Check if lap exists
        lap = conn.execute('SELECT id FROM laps WHERE id = ?', (lap_id,)).fetchone()
        
        if not lap:
            conn.close()
            return jsonify({'success': False, 'message': 'Lap not found'}), 404
        
        # Delete the lap
        conn.execute('DELETE FROM laps WHERE id = ?', (lap_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': f'Deleted lap #{lap_id}'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/run-settings', methods=['GET', 'POST'])
def api_run_settings():
    """Get or update run settings"""
    conn = get_db_connection()
    
    if request.method == 'GET':
        # Get current settings
        status = conn.execute('SELECT status FROM event_status WHERE id = 1').fetchone()
        
        # Get today's date as default
        today = datetime.now().strftime('%Y-%m-%d')
        
        conn.close()
        return jsonify({
            'name': 'Благодійний забіг УКУ',
            'date': today,
            'status': status['status']
        })
    
    elif request.method == 'POST':
        # Update settings
        data = request.json
        
        # Update status if provided
        if 'status' in data:
            conn.execute('UPDATE event_status SET status = ? WHERE id = 1', (data['status'],))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'name': data.get('name', 'Благодійний забіг УКУ'),
            'date': data.get('date'),
            'status': data.get('status')
        })

@app.route('/get_recent_laps', methods=['GET'])
def get_recent_laps():
    """Get recent laps for laps page"""
    conn = get_db_connection()
    
    # Get most recent laps with participant info
    laps = conn.execute('''
        SELECT l.id, l.faculty, l.participant_number, l.participant_type, 
               l.timestamp, 
               p.first_name, p.last_name
        FROM laps l
        LEFT JOIN participants p ON l.participant_number = p.number
        ORDER BY l.timestamp DESC 
        LIMIT 50
    ''').fetchall()
    
    # Format for response
    result = []
    for lap in laps:
        # Format timestamp
        timestamp = datetime.strptime(lap['timestamp'], '%Y-%m-%d %H:%M:%S')
        formatted_time = timestamp.strftime('%H:%M:%S')
        
        # Get participant name
        first_name = lap['first_name'] if lap['first_name'] else ""
        last_name = lap['last_name'] if lap['last_name'] else ""
        
        # Is it a faculty lap?
        is_faculty_lap = lap['participant_number'].startswith('faculty_')
        
        # Get human-readable participant type
        participant_type = lap['participant_type']
        participant_type_name = PARTICIPANT_TYPES.get(participant_type, {}).get('name', 'Невідомо')
        
        # Get color
        faculty_color = FACULTIES.get(lap['faculty'], '#CCCCCC')
        
        # Name for display
        if is_faculty_lap:
            participant_name = f"Факультетське коло ({participant_type_name})"
        else:
            if first_name or last_name:
                participant_name = f"{first_name} {last_name}".strip()
            else:
                participant_name = f"Учасник #{lap['participant_number']}"
        
        result.append({
            'id': lap['id'],
            'timestamp': formatted_time,
            'time': formatted_time,
            'faculty': lap['faculty'],
            'participant_number': lap['participant_number'],
            'participant_type': participant_type,
            'participant_type_name': participant_type_name,
            'color': faculty_color,
            'name': participant_name,
            'participant_name': participant_name
        })
    
    conn.close()
    return jsonify(result)

@app.route('/get_laps_statistics', methods=['GET'])
def get_laps_statistics():
    """Get laps statistics for laps page"""
    conn = get_db_connection()
    
    # Get total laps
    total_laps = conn.execute('SELECT COUNT(*) as count FROM laps').fetchone()['count']
    
    # Get laps by faculty
    laps_by_faculty = {}
    for faculty in FACULTIES:
        count = conn.execute('SELECT COUNT(*) as count FROM laps WHERE faculty = ?', 
                            (faculty,)).fetchone()['count']
        laps_by_faculty[faculty] = count
    
    conn.close()
    
    return jsonify({
        'total_laps': total_laps,
        'laps_by_faculty': laps_by_faculty
    })

@app.route('/delete_lap/<int:lap_id>', methods=['POST'])
def delete_lap(lap_id):
    """Delete a specific lap by ID"""
    try:
        conn = get_db_connection()
        
        # Delete the lap
        conn.execute('DELETE FROM laps WHERE id = ?', (lap_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
