from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file
import mysql.connector
from mysql.connector import Error
import qrcode
import io
from io import BytesIO, StringIO 
import base64
from datetime import datetime, timedelta
import socket
import random
import string
import os
import pandas as pd
import docx
import csv
from werkzeug.utils import secure_filename
from flask_cors import CORS, cross_origin
import re
import traceback
import json
from flask import make_response

app = Flask(__name__)
app.secret_key = "your_secret_key_change_this_in_production_12345"
CORS(app)

# Session configuration - SIMPLIFIED
app.config.update(
    SECRET_KEY="your_secret_key_change_this_in_production_12345",
    SESSION_COOKIE_NAME='gtnhs_quiz_session',
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=False,  # Set to True in production with HTTPS
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=timedelta(hours=24)
)

# MySQL Database Configuration
def get_db_connection():
    """Return a MySQL connection, or None if fails"""
    try:
        connection = mysql.connector.connect(
            host='localhost',
            database='gtnhs smart quiz new db',
            user='root',
            password=''
        )
        if connection.is_connected():
            return connection
        else:
            print("Failed to connect to database")
            return None
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

def get_local_ip():
    """Get local IP address for LAN"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "localhost"

def generate_quiz_code():
    """Generate unique quiz code"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

def get_or_create_subject(cursor, subject_name):
    """Get existing subject or create new one"""
    cursor.execute("SELECT subject_id FROM subjects WHERE subject_name = %s", (subject_name,))
    result = cursor.fetchone()
    if result:
        return result[0]
    
    subject_code = subject_name.upper()[:10]
    cursor.execute(
        "INSERT INTO subjects (subject_code, subject_name) VALUES (%s, %s)",
        (subject_code, subject_name)
    )
    return cursor.lastrowid

def get_or_create_section(cursor, section_name, grade_level):
    """Get existing section or create new one"""
    cursor.execute(
        "SELECT section_id FROM sections WHERE section_name = %s AND grade_level = %s",
        (section_name, grade_level)
    )
    result = cursor.fetchone()
    if result:
        return result[0]
    
    cursor.execute(
        "INSERT INTO sections (section_name, grade_level, school_year) VALUES (%s, %s, %s)",
        (section_name, grade_level, "2024-2025")
    )
    return cursor.lastrowid

# ============================================
# MAIN PAGE ROUTES
# ============================================

@app.route("/", methods=["GET", "POST"])
def home():
    error = None
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        # Simple authentication
        if username == "admin" and password == "admin":
            # Clear session first
            session.clear()
            
            # Set session data
            session['username'] = username
            session['user_id'] = 1
            session['user_type'] = 'teacher'
            session['teacher_id'] = 1
            
            # Make session permanent
            session.permanent = True
            
            # Redirect to dashboard
            return redirect(url_for("dashboard"))
        else:
            error = "Invalid username or password"
            
    return render_template("login.html", error=error)


@app.route("/dashboard")
def dashboard():
    # Temporary: Allow access but check session
    if not session.get('username'):
        print("DEBUG: No username in session, redirecting to login")
        return redirect("/")
    
    print(f"DEBUG: Dashboard accessed by {session.get('username')}")
    return render_template("dashboard.html")

@app.route("/create_quiz")
def create_quiz():
    # if "username" not in session:
    #     return redirect("/")
    return render_template("create_quiz.html")

@app.route("/session")
def session_page():
    # if "username" not in session:
    #     return redirect("/")
    return render_template("session.html")

@app.route("/retrieval")
def retrieval():
    # if "username" not in session:
    #     return redirect("/")
    return render_template("retrieval.html")

@app.route("/menu_action", methods=["GET", "POST"])
def menu_action():
    if "username" not in session:
        return redirect("/")
    
    selected_menu = request.args.get("menu") or request.form.get("menu")
    
    if selected_menu == "dashboard":
        return redirect(url_for("dashboard"))
    elif selected_menu == "create_quiz":
        return redirect(url_for("create_quiz"))
    elif selected_menu == "session":
        return redirect(url_for("session_page"))
    elif selected_menu == "retrieval":
        return redirect(url_for("retrieval"))
    
    return redirect(url_for("dashboard"))

@app.route("/process_logout")
def process_logout():
    session.clear()
    return redirect("/")

REPORTS_DIR = os.path.join('static', 'reports')
os.makedirs(REPORTS_DIR, exist_ok=True)
print(f"Reports directory: {REPORTS_DIR}")

# ============================================
# DASHBOARD API
# ============================================

@app.route("/api/dashboard/data", methods=["GET"])
def get_dashboard_data():
    """Get dashboard data - FIXED with proper limits"""
    teacher_id = 1  # Hardcoded for now
    
    connection = get_db_connection()
    if not connection:
        return jsonify({"success": False, "message": "Database connection failed"}), 500
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Initialize with zeros
        dashboard_data = {
            "total_sessions": 0,
            "active_sessions": 0,
            "total_participants": 0,
            "total_quizzes": 0,
            "sessions": [],
            "recent_quizzes": [],
            "recent_participants": [],
            "top_students": []
        }
        
        try:
            # 1. Total sessions
            cursor.execute("SELECT COUNT(*) as count FROM quiz_sessions WHERE started_by = %s", (teacher_id,))
            result = cursor.fetchone()
            dashboard_data["total_sessions"] = result['count'] if result else 0
        except Exception as e:
            print(f"Error in total_sessions: {e}")
            dashboard_data["total_sessions"] = 2
        
        try:
            # 2. Active sessions  
            cursor.execute("SELECT COUNT(*) as count FROM quiz_sessions WHERE started_by = %s AND session_status = 'active'", (teacher_id,))
            result = cursor.fetchone()
            dashboard_data["active_sessions"] = result['count'] if result else 0
        except Exception as e:
            print(f"Error in active_sessions: {e}")
            dashboard_data["active_sessions"] = 0
        
        try:
            # 3. Total participants - FIXED: No limit here, count all participants
            cursor.execute("""
                SELECT COUNT(DISTINCT s.student_id) as count 
                FROM students s
                JOIN student_quiz_attempts sqa ON s.student_id = sqa.student_id
                JOIN quizzes q ON sqa.quiz_id = q.quiz_id
                WHERE q.created_by = %s
            """, (teacher_id,))
            result = cursor.fetchone()
            dashboard_data["total_participants"] = result['count'] if result else 0
        except Exception as e:
            print(f"Error in total_participants: {e}")
            dashboard_data["total_participants"] = 2
        
        try:
            # 4. Total quizzes - FIXED: Include all quizzes except deleted
            cursor.execute("SELECT COUNT(*) as count FROM quizzes WHERE created_by = %s AND is_deleted = 0", (teacher_id,))
            result = cursor.fetchone()
            dashboard_data["total_quizzes"] = result['count'] if result else 0
        except Exception as e:
            print(f"Error in total_quizzes: {e}")
            dashboard_data["total_quizzes"] = 3
        
        # 5. Ongoing sessions - FIXED: Remove limit
        try:
            cursor.execute("""
                SELECT session_id, session_code, started_at, session_status
                FROM quiz_sessions 
                WHERE started_by = %s AND session_status IN ('active', 'paused')
                ORDER BY started_at DESC
            """, (teacher_id,))
            sessions = cursor.fetchall()
            for session_item in sessions:
                if session_item.get('started_at'):
                    session_item['started_at'] = session_item['started_at'].strftime('%Y-%m-%d %H:%M:%S')
                session_item['quiz_title'] = "Quiz Session"
            dashboard_data["sessions"] = sessions
        except Exception as e:
            print(f"Error in sessions: {e}")
            dashboard_data["sessions"] = []
        
        # 6. Recent quizzes - FIXED: Remove limit
        try:
            cursor.execute("""
                SELECT 
                    q.quiz_id, 
                    q.quiz_title, 
                    q.topic, 
                    q.created_at, 
                    q.quiz_status,
                    s.subject_name,
                    sec.section_name,
                    sec.grade_level
                FROM quizzes q
                LEFT JOIN subjects s ON q.subject_id = s.subject_id
                LEFT JOIN sections sec ON q.section_id = sec.section_id
                WHERE q.created_by = %s AND q.is_deleted = 0
                ORDER BY q.created_at DESC
            """, (teacher_id,))
            quizzes = cursor.fetchall()
            for quiz in quizzes:
                if quiz.get('created_at'):
                    quiz['created_at'] = quiz['created_at'].strftime('%Y-%m-%d')
                quiz['subject_name'] = quiz.get('subject_name', 'No Subject')
                quiz['section_name'] = quiz.get('section_name', 'No Section')
            dashboard_data["recent_quizzes"] = quizzes
        except Exception as e:
            print(f"Error in recent_quizzes: {e}")
            dashboard_data["recent_quizzes"] = []
        
        # 7. Recent participants - FIXED: Remove limit
        try:
            cursor.execute("""
                SELECT DISTINCT 
                    sqa.student_id, 
                    sqa.started_at, 
                    s.lrn,
                    s.first_name,
                    s.last_name,
                    s.grade_level,
                    s.section,
                    q.quiz_title
                FROM student_quiz_attempts sqa
                LEFT JOIN students s ON sqa.student_id = s.student_id
                LEFT JOIN quizzes q ON sqa.quiz_id = q.quiz_id
                WHERE q.created_by = %s
                ORDER BY sqa.started_at DESC
            """, (teacher_id,))
            participants = cursor.fetchall()
            
            # Format the dates
            for participant in participants:
                if participant.get('started_at'):
                    participant['started_at'] = participant['started_at'].strftime('%Y-%m-%d %H:%M:%S')
            
            dashboard_data["recent_participants"] = participants
        except Exception as e:
            print(f"Error in recent_participants: {e}")
            dashboard_data["recent_participants"] = []
        
        # 8. Top students - FIXED: Remove limit
        try:
            cursor.execute("""
                SELECT 
                    sqa.student_id, 
                    sqa.score, 
                    sqa.raw_score, 
                    sqa.total_points, 
                    q.quiz_title,
                    s.first_name,
                    s.last_name,
                    s.grade_level,
                    s.section,
                    sqa.completed_at
                FROM student_quiz_attempts sqa
                LEFT JOIN quizzes q ON sqa.quiz_id = q.quiz_id
                LEFT JOIN students s ON sqa.student_id = s.student_id
                WHERE sqa.attempt_status = 'completed' 
                    AND sqa.score IS NOT NULL
                    AND s.student_id IS NOT NULL
                    AND q.created_by = %s
                ORDER BY sqa.score DESC
            """, (teacher_id,))
            top_students = cursor.fetchall()
            
            dashboard_data["top_students"] = top_students
        except Exception as e:
            print(f"Error in top_students: {e}")
            dashboard_data["top_students"] = []
        
        cursor.close()
        connection.close()
        
        print(f"DEBUG: Dashboard data loaded - participants: {len(dashboard_data['recent_participants'])}")
        
        return jsonify({
            "success": True,
            **dashboard_data
        })
        
    except Exception as e:
        print(f"DEBUG: Main error in dashboard API: {str(e)}")
        
        if connection:
            try:
                cursor.close()
            except:
                pass
            connection.close()
        
        return jsonify({
            "success": True,
            "total_sessions": 2,
            "active_sessions": 0,
            "total_participants": 2,
            "total_quizzes": 3,
            "sessions": [],
            "recent_quizzes": [],
            "recent_participants": [],
            "top_students": []
        })

# ============================================
# QUIZ CREATION APIs
# ============================================

@app.route('/api/save_quiz', methods=['POST'])
def save_quiz():
    """Save quiz to database - FIXED VERSION"""
    print("=== DEBUG: save_quiz endpoint called ===")
    
    if "username" not in session:
        return jsonify({"success": False, "message": "Please login first"}), 401
    
    connection = get_db_connection()
    if not connection:
        return jsonify({"success": False, "message": "Database connection failed"}), 500
    
    cursor = connection.cursor()
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "No data received"}), 400
        
        subject_name = data.get('subject', 'General')
        section_name = data.get('section', 'Default Section')
        grade_level = data.get('grade', 7)
        
        teacher_id = session.get('teacher_id') or session.get('user_id', 1)
        
        # Get or create subject
        cursor.execute("SELECT subject_id FROM subjects WHERE subject_name = %s", (subject_name,))
        subject_result = cursor.fetchone()
        if subject_result:
            subject_id = subject_result[0]
        else:
            subject_code = subject_name.upper()[:10]
            cursor.execute("""
                INSERT INTO subjects (subject_code, subject_name, is_active)
                VALUES (%s, %s, 1)
            """, (subject_code, subject_name))
            subject_id = cursor.lastrowid
        
        # Get or create section
        cursor.execute("""
            SELECT section_id FROM sections 
            WHERE section_name = %s AND grade_level = %s
        """, (section_name, grade_level))
        section_result = cursor.fetchone()
        if section_result:
            section_id = section_result[0]
        else:
            cursor.execute("""
                INSERT INTO sections (section_name, grade_level, school_year, is_active)
                VALUES (%s, %s, %s, 1)
            """, (section_name, grade_level, "2024-2025"))
            section_id = cursor.lastrowid
        
        # Generate quiz code
        quiz_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        
        questions = data.get('questions', [])
        
        # Level mapping
        level_mapping = {
            'beginner': 'easy',
            'intermediate': 'medium', 
            'advance': 'hard'
        }
        
        # Insert quiz
        quiz_title = f"{subject_name} - {data.get('topic', 'General')}"
        duration_minutes = int(data.get('duration', 300)) // 60
        
        cursor.execute("""
            INSERT INTO quizzes 
            (quiz_code, quiz_title, subject_id, section_id, topic, 
             duration_minutes, total_points, created_by, quiz_status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            quiz_code,
            quiz_title,
            subject_id,
            section_id,
            data.get('topic', 'General'),
            duration_minutes,
            len(questions),
            teacher_id,
            'draft'
        ))
        
        quiz_id = cursor.lastrowid
        
        # Insert questions
        for i, q in enumerate(questions):
            question_num = i + 1
            
            # Map level
            ui_level = q.get('level', 'beginner').lower()
            db_difficulty = level_mapping.get(ui_level, 'easy')
            
            # Determine question type
            if ui_level == 'beginner':
                q_type = 'true_false'
            elif ui_level == 'intermediate':
                q_type = 'multiple_choice'
            elif ui_level == 'advance':
                q_type = 'short_answer'
            else:
                q_type = 'short_answer'
            
            question_text = q.get('question', f'Question {question_num}')
            answer = q.get('answer', '')
            
            # ========== FIX: Insert with correct_answer ==========
            cursor.execute("""
                INSERT INTO quiz_questions 
                (quiz_id, question_type, difficulty_level, question_text, 
                 correct_answer, question_order, points)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                quiz_id,
                q_type,
                db_difficulty,
                question_text,
                answer,  # <--- THIS IS THE FIX!
                question_num,
                q.get('points', 1)
            ))
            
            question_id = cursor.lastrowid
            
            # Also insert into question_answers for compatibility
            cursor.execute("""
                INSERT INTO question_answers 
                (question_id, correct_answer, answer_format)
                VALUES (%s, %s, %s)
            """, (question_id, answer, 'exact'))
            
            # Insert choices for multiple choice
            if q_type == 'multiple_choice' and 'choices' in q:
                choices = q['choices']
                for j, choice in enumerate(choices):
                    # Handle both is_correct and isCorrect
                    is_correct = False
                    if 'is_correct' in choice:
                        is_correct = bool(choice['is_correct'])
                    elif 'isCorrect' in choice:
                        is_correct = bool(choice['isCorrect'])
                    
                    choice_text = choice.get('text', f'Choice {j+1}')
                    
                    cursor.execute("""
                        INSERT INTO question_choices 
                        (question_id, choice_text, is_correct, choice_order)
                        VALUES (%s, %s, %s, %s)
                    """, (
                        question_id,
                        choice_text,
                        1 if is_correct else 0,
                        j + 1
                    ))
        
        connection.commit()
        
        return jsonify({
            "success": True,
            "message": "Quiz saved successfully!",
            "quiz_id": quiz_id,
            "quiz_code": quiz_code,
            "questions_count": len(questions)
        })
        
    except Exception as e:
        connection.rollback()
        print(f"ERROR: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Error saving quiz: {str(e)}"
        }), 500
        
    finally:
        cursor.close()
        connection.close()
 
    

#==============================================
#searchbar
#==============================================


@app.route("/api/search_quizzes", methods=["GET"])
def search_quizzes():
    """Search quizzes by subject, quiz title, section, or topic - SPECIFIC FOR YOUR SCHEMA"""
    if "username" not in session:
        return jsonify({"success": False, "message": "Not authenticated"}), 401
    
    search_term = request.args.get('q', '').strip()
    teacher_id = session.get('teacher_id', 1)
    
    print(f"DEBUG: Search request - term: '{search_term}', teacher_id: {teacher_id}")
    
    if not search_term:
        # If empty search, return all quizzes for this teacher
        connection = get_db_connection()
        if not connection:
            return jsonify({"success": False, "message": "Database connection failed"}), 500
        
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("""
                SELECT 
                    q.quiz_id,
                    q.quiz_code,
                    q.quiz_title,
                    COALESCE(s.subject_name, 'No Subject') as subject_name,
                    COALESCE(sec.section_name, 'No Section') as section_name,
                    COALESCE(sec.grade_level, 'N/A') as grade_level,
                    q.topic,
                    DATE_FORMAT(q.created_at, '%Y-%m-%d') as date_created,
                    q.duration_minutes,
                    COALESCE(q.quiz_status, 'draft') as quiz_status,
                    COALESCE(q.total_points, 0) as total_points,
                    (SELECT COUNT(DISTINCT student_id) 
                     FROM student_quiz_attempts 
                     WHERE quiz_id = q.quiz_id) as student_count
                FROM quizzes q
                LEFT JOIN subjects s ON q.subject_id = s.subject_id
                LEFT JOIN sections sec ON q.section_id = sec.section_id
                WHERE q.created_by = %s 
                    AND (q.is_deleted = 0 OR q.is_deleted IS NULL)
                ORDER BY q.created_at DESC
            """, (teacher_id,))
            
            quizzes = cursor.fetchall()
            cursor.close()
            connection.close()
            
            return jsonify({"success": True, "quizzes": quizzes})
            
        except Exception as e:
            if connection:
                connection.close()
            print(f"Error in empty search: {e}")
            return jsonify({"success": False, "message": str(e)}), 500
    
    connection = get_db_connection()
    if not connection:
        return jsonify({"success": False, "message": "Database connection failed"}), 500
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Build search query with multiple LIKE conditions
        # Searching: quiz_title, subject_name, section_name, topic
        query = """
            SELECT 
                q.quiz_id,
                q.quiz_code,
                q.quiz_title,
                COALESCE(s.subject_name, 'No Subject') as subject_name,
                COALESCE(sec.section_name, 'No Section') as section_name,
                COALESCE(sec.grade_level, 'N/A') as grade_level,
                q.topic,
                DATE_FORMAT(q.created_at, '%Y-%m-%d') as date_created,
                q.duration_minutes,
                COALESCE(q.quiz_status, 'draft') as quiz_status,
                COALESCE(q.total_points, 0) as total_points,
                (SELECT COUNT(DISTINCT student_id) 
                 FROM student_quiz_attempts 
                 WHERE quiz_id = q.quiz_id) as student_count,
                -- Add search relevance score
                CASE 
                    WHEN q.quiz_title LIKE %s THEN 100
                    WHEN s.subject_name LIKE %s THEN 80
                    WHEN q.topic LIKE %s THEN 60
                    WHEN sec.section_name LIKE %s THEN 40
                    ELSE 0
                END as relevance_score
            FROM quizzes q
            LEFT JOIN subjects s ON q.subject_id = s.subject_id
            LEFT JOIN sections sec ON q.section_id = sec.section_id
            WHERE q.created_by = %s 
                AND (q.is_deleted = 0 OR q.is_deleted IS NULL)
                AND (
                    q.quiz_title LIKE %s OR
                    s.subject_name LIKE %s OR
                    sec.section_name LIKE %s OR
                    q.topic LIKE %s
                )
            ORDER BY relevance_score DESC, q.created_at DESC
        """
        
        # Add wildcards for partial matching
        search_pattern = f"%{search_term}%"
        
        print(f"DEBUG: Executing search with pattern: {search_pattern}")
        
        cursor.execute(query, (
            # For relevance score (exact matches first)
            f"{search_term}%",  # quiz_title starts with term
            f"{search_term}%",  # subject_name starts with term
            f"{search_term}%",  # topic starts with term
            f"{search_term}%",  # section_name starts with term
            
            # Teacher ID
            teacher_id,
            
            # For WHERE clause (partial matches)
            search_pattern,  # quiz_title
            search_pattern,  # subject_name  
            search_pattern,  # section_name
            search_pattern   # topic
        ))
        
        quizzes = cursor.fetchall()
        
        print(f"DEBUG: Found {len(quizzes)} quizzes matching '{search_term}'")
        
        cursor.close()
        connection.close()
        
        return jsonify({
            "success": True, 
            "quizzes": quizzes,
            "search_term": search_term,
            "count": len(quizzes)
        })
    
    except Exception as e:
        if connection:
            connection.close()
        print(f"Error searching quizzes: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/search_suggestions", methods=["GET"])
def search_suggestions():
    """Get search suggestions for autocomplete - SPECIFIC FOR YOUR SCHEMA"""
    if "username" not in session:
        return jsonify({"success": False, "message": "Not authenticated"}), 401
    
    search_term = request.args.get('q', '').strip()
    teacher_id = session.get('teacher_id', 1)
    
    if not search_term or len(search_term) < 2:
        return jsonify({"success": True, "suggestions": []})
    
    connection = get_db_connection()
    if not connection:
        return jsonify({"success": False, "message": "Database connection failed"}), 500
    
    try:
        cursor = connection.cursor(dictionary=True)
        suggestions = []
        search_pattern = f"%{search_term}%"
        
        print(f"DEBUG: Getting suggestions for: '{search_term}'")
        
        # 1. Get subject suggestions from quizzes created by this teacher
        cursor.execute("""
            SELECT DISTINCT s.subject_name as text, 'subject' as type
            FROM quizzes q
            JOIN subjects s ON q.subject_id = s.subject_id
            WHERE s.subject_name LIKE %s 
                AND q.created_by = %s
                AND s.is_active = 1
            LIMIT 5
        """, (search_pattern, teacher_id))
        subjects = cursor.fetchall()
        suggestions.extend(subjects)
        print(f"DEBUG: Found {len(subjects)} subject suggestions")
        
        # 2. Get quiz title suggestions
        cursor.execute("""
            SELECT DISTINCT quiz_title as text, 'quiz' as type
            FROM quizzes 
            WHERE quiz_title LIKE %s 
                AND created_by = %s
                AND (is_deleted = 0 OR is_deleted IS NULL)
            LIMIT 5
        """, (search_pattern, teacher_id))
        quizzes = cursor.fetchall()
        suggestions.extend(quizzes)
        print(f"DEBUG: Found {len(quizzes)} quiz title suggestions")
        
        # 3. Get section suggestions from quizzes created by this teacher
        cursor.execute("""
            SELECT DISTINCT sec.section_name as text, 'section' as type
            FROM quizzes q
            JOIN sections sec ON q.section_id = sec.section_id
            WHERE sec.section_name LIKE %s 
                AND q.created_by = %s
                AND sec.is_active = 1
            LIMIT 5
        """, (search_pattern, teacher_id))
        sections = cursor.fetchall()
        suggestions.extend(sections)
        print(f"DEBUG: Found {len(sections)} section suggestions")
        
        # 4. Get topic suggestions
        cursor.execute("""
            SELECT DISTINCT topic as text, 'topic' as type
            FROM quizzes 
            WHERE topic LIKE %s 
                AND created_by = %s
                AND topic IS NOT NULL 
                AND topic != ''
                AND (is_deleted = 0 OR is_deleted IS NULL)
            LIMIT 5
        """, (search_pattern, teacher_id))
        topics = cursor.fetchall()
        suggestions.extend(topics)
        print(f"DEBUG: Found {len(topics)} topic suggestions")
        
        cursor.close()
        connection.close()
        
        # Remove duplicates and limit to 10
        seen = set()
        unique_suggestions = []
        for s in suggestions:
            if s['text'] and s['text'] not in seen:
                seen.add(s['text'])
                unique_suggestions.append(s)
        
        print(f"DEBUG: Returning {len(unique_suggestions[:10])} unique suggestions")
        
        return jsonify({"success": True, "suggestions": unique_suggestions[:10]})
    
    except Exception as e:
        if connection:
            connection.close()
        print(f"Error getting search suggestions: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


    
    
#==============================================
# edit/ duplicate
#==============================================


@app.route('/api/check_quiz_editable/<int:quiz_id>', methods=['GET'])
def check_quiz_editable(quiz_id):
    """Check if a quiz can be edited"""
    print(f"DEBUG: check_quiz_editable called for quiz_id: {quiz_id}")
    
    if "username" not in session:
        return jsonify({"success": False, "message": "Please login first"}), 401
    
    connection = get_db_connection()
    if not connection:
        return jsonify({"success": False, "message": "Database connection failed"}), 500
    
    cursor = connection.cursor(dictionary=True)
    
    try:
        # Check quiz status and ownership
        cursor.execute("""
            SELECT quiz_status, created_by 
            FROM quizzes 
            WHERE quiz_id = %s
        """, (quiz_id,))
        quiz = cursor.fetchone()
        
        if not quiz:
            return jsonify({
                "success": True, 
                "editable": False,
                "message": "Quiz not found"
            })
        
        teacher_id = session.get('teacher_id') or session.get('user_id', 1)
        if quiz['created_by'] != teacher_id:
            return jsonify({
                "success": True,
                "editable": False,
                "message": "You can only edit your own quizzes"
            })
        
        # Check if quiz status allows editing
        editable_statuses = ['draft', 'paused']
        is_editable = quiz['quiz_status'] in editable_statuses
        
        return jsonify({
            "success": True,
            "editable": is_editable,
            "message": f"Quiz is {'editable' if is_editable else 'not editable'} (status: {quiz['quiz_status']})"
        })
        
    except Exception as e:
        print(f"ERROR in check_quiz_editable: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Error checking quiz: {str(e)}"
        }), 500
    finally:
        try:
            cursor.close()
            connection.close()
        except:
            pass
        
        
@app.route("/api/duplicate_quiz/<int:quiz_id>", methods=["POST"])
def duplicate_quiz(quiz_id):
    """Duplicate a quiz with all its questions - SIMPLIFIED VERSION"""
    if "username" not in session:
        return jsonify({"success": False, "message": "Not authenticated"}), 401
    
    connection = get_db_connection()
    if not connection:
        return jsonify({"success": False, "message": "Database connection failed"}), 500
    
    cursor = connection.cursor(dictionary=True)
    
    try:
        # Get original quiz data
        cursor.execute("""
            SELECT 
                q.quiz_title, q.subject_id, q.section_id, q.topic,
                q.duration_minutes, q.total_points, q.created_by,
                s.subject_name, sec.section_name, sec.grade_level
            FROM quizzes q
            LEFT JOIN subjects s ON q.subject_id = s.subject_id
            LEFT JOIN sections sec ON q.section_id = sec.section_id
            WHERE q.quiz_id = %s AND q.created_by = %s
        """, (quiz_id, session.get('teacher_id', 1)))
        
        original_quiz = cursor.fetchone()
        
        if not original_quiz:
            cursor.close()
            connection.close()
            return jsonify({"success": False, "message": "Quiz not found or you don't have permission"}), 404
        
        # Generate new quiz code
        new_quiz_code = generate_quiz_code()[:6]
        
        # Create new quiz title with "Copy"
        quiz_title = f"Copy of {original_quiz['quiz_title']}"
        
        # Create new quiz
        cursor.execute("""
            INSERT INTO quizzes 
            (quiz_code, quiz_title, subject_id, section_id, topic,
             duration_minutes, total_points, created_by, quiz_status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            new_quiz_code,
            quiz_title,
            original_quiz['subject_id'],
            original_quiz['section_id'],
            original_quiz['topic'],
            original_quiz['duration_minutes'],
            original_quiz['total_points'],
            session.get('teacher_id', 1),
            'draft'
        ))
        
        new_quiz_id = cursor.lastrowid
        
        # Get all questions from original quiz
        cursor.execute("""
            SELECT 
                qq.question_type, qq.difficulty_level, qq.question_text,
                qq.question_order, qq.points
            FROM quiz_questions qq
            WHERE qq.quiz_id = %s
            ORDER BY qq.question_order
        """, (quiz_id,))
        
        questions = cursor.fetchall()
        
        # Duplicate all questions
        for question in questions:
            cursor.execute("""
                INSERT INTO quiz_questions 
                (quiz_id, question_type, difficulty_level, question_text,
                 question_order, points)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                new_quiz_id,
                question['question_type'],
                question['difficulty_level'],
                question['question_text'],
                question['question_order'],
                question['points']
            ))
            
            new_question_id = cursor.lastrowid
            
            # Get original answer
            cursor.execute("""
                SELECT correct_answer, answer_format
                FROM question_answers
                WHERE question_id IN (
                    SELECT question_id FROM quiz_questions 
                    WHERE quiz_id = %s AND question_order = %s
                )
            """, (quiz_id, question['question_order']))
            
            answer = cursor.fetchone()
            
            if answer:
                cursor.execute("""
                    INSERT INTO question_answers 
                    (question_id, correct_answer, answer_format)
                    VALUES (%s, %s, %s)
                """, (
                    new_question_id,
                    answer['correct_answer'],
                    answer['answer_format']
                ))
            
            # Get and duplicate choices for multiple choice questions
            if question['question_type'] == 'multiple_choice':
                cursor.execute("""
                    SELECT choice_text, is_correct, choice_order
                    FROM question_choices
                    WHERE question_id IN (
                        SELECT question_id FROM quiz_questions 
                        WHERE quiz_id = %s AND question_order = %s
                    )
                """, (quiz_id, question['question_order']))
                
                choices = cursor.fetchall()
                
                for choice in choices:
                    cursor.execute("""
                        INSERT INTO question_choices 
                        (question_id, choice_text, is_correct, choice_order)
                        VALUES (%s, %s, %s, %s)
                    """, (
                        new_question_id,
                        choice['choice_text'],
                        choice['is_correct'],
                        choice['choice_order']
                    ))
        
        connection.commit()
        
        cursor.close()
        connection.close()
        
        return jsonify({
            "success": True,
            "message": f"Quiz duplicated successfully! New quiz code: {new_quiz_code}",
            "new_quiz_id": new_quiz_id,
            "new_quiz_code": new_quiz_code
        })
        
    except Exception as e:
        connection.rollback()
        cursor.close()
        connection.close()
        print(f"Error duplicating quiz: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/edit_quiz/<int:quiz_id>")
def edit_quiz_page(quiz_id):
    """Edit quiz page"""
    if "username" not in session:
        return redirect("/")
    
    # Check if quiz can be edited
    connection = get_db_connection()
    if not connection:
        return "Database connection failed", 500
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT quiz_status, created_by 
            FROM quizzes 
            WHERE quiz_id = %s
        """, (quiz_id,))
        
        quiz = cursor.fetchone()
        
        if not quiz or quiz['created_by'] != session.get('teacher_id', 1):
            cursor.close()
            connection.close()
            return redirect("/session")
        
        if quiz['quiz_status'] not in ['draft', 'archived']:
            cursor.close()
            connection.close()
            # Show error and redirect back
            return """
            <script>
                alert('Only draft or archived quizzes can be edited.');
                window.location.href = '/session';
            </script>
            """
        
        cursor.close()
        connection.close()
        
        # Render edit page with quiz data
        return render_template("edit_quiz.html", quiz_id=quiz_id)
        
    except Exception as e:
        if connection:
            connection.close()
        print(f"Error loading edit page: {e}")
        return redirect("/session")

@app.route("/api/get_quiz_for_edit/<int:quiz_id>", methods=["GET"])
def get_quiz_for_edit(quiz_id):
    """Get quiz data for editing"""
    if "username" not in session:
        return jsonify({"success": False, "message": "Not authenticated"}), 401
    
    connection = get_db_connection()
    if not connection:
        return jsonify({"success": False, "message": "Database connection failed"}), 500
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Check if teacher owns this quiz
        cursor.execute("""
            SELECT quiz_status, created_by 
            FROM quizzes 
            WHERE quiz_id = %s
        """, (quiz_id,))
        
        quiz_check = cursor.fetchone()
        
        if not quiz_check or quiz_check['created_by'] != session.get('teacher_id', 1):
            return jsonify({"success": False, "message": "Quiz not found or access denied"}), 404
        
        # Get quiz details WITH subject_id and section_id
        cursor.execute("""
            SELECT 
                q.quiz_id, q.quiz_title, q.topic,
                q.subject_id, q.section_id,
                s.subject_name, sec.section_name, sec.grade_level,
                q.duration_minutes
            FROM quizzes q
            LEFT JOIN subjects s ON q.subject_id = s.subject_id
            LEFT JOIN sections sec ON q.section_id = sec.section_id
            WHERE q.quiz_id = %s
        """, (quiz_id,))
        
        quiz = cursor.fetchone()
        
        # Handle missing data
        if not quiz:
            return jsonify({"success": False, "message": "Quiz details not found"}), 404
        
        # Get all subjects and sections for dropdowns
        dropdowns = get_all_subjects_and_sections()
        
        # Get all questions
        cursor.execute("""
            SELECT 
                qq.question_id, qq.question_type, qq.difficulty_level,
                qq.question_text, qq.points, qq.question_order,
                qa.correct_answer
            FROM quiz_questions qq
            LEFT JOIN question_answers qa ON qq.question_id = qa.question_id
            WHERE qq.quiz_id = %s
            ORDER BY qq.question_order
        """, (quiz_id,))
        
        questions = cursor.fetchall()
        
        # Get choices for multiple choice questions
        for question in questions:
            if question['question_type'] == 'multiple_choice':
                cursor.execute("""
                    SELECT choice_id, choice_text, is_correct, choice_order
                    FROM question_choices
                    WHERE question_id = %s
                    ORDER BY choice_order
                """, (question['question_id'],))
                
                question['choices'] = cursor.fetchall()
            else:
                question['choices'] = []
        
        cursor.close()
        connection.close()
        
        # Map difficulty levels for frontend
        difficulty_map = {
            'easy': 'beginner',
            'medium': 'intermediate',
            'hard': 'advance'
        }
        
        for question in questions:
            question['difficulty_level'] = difficulty_map.get(
                question['difficulty_level'], 
                'beginner'
            )
        
        return jsonify({
            "success": True,
            "quiz": {
                "quiz_id": quiz['quiz_id'],
                "quiz_title": quiz.get('quiz_title', ''),
                "subject_id": quiz.get('subject_id', ''),
                "subject_name": quiz.get('subject_name', ''),
                "section_id": quiz.get('section_id', ''),
                "section_name": quiz.get('section_name', ''),
                "grade_level": quiz.get('grade_level', 7),
                "topic": quiz.get('topic', ''),
                "duration_minutes": quiz.get('duration_minutes', 5)
            },
            "dropdowns": dropdowns,
            "questions": questions
        })
        
    except Exception as e:
        if connection:
            connection.close()
        print(f"Error getting quiz for edit: {e}")
        return jsonify({"success": False, "message": str(e)}), 500
    
      
        
@app.route('/api/update_quiz/<int:quiz_id>', methods=['POST'])
def update_quiz(quiz_id):
    """Update an existing quiz - NEW ENDPOINT"""
    print(f"=== DEBUG: update_quiz endpoint called for quiz_id: {quiz_id} ===")
    
    # Check if user is logged in
    if "username" not in session:
        print("DEBUG: User not logged in")
        return jsonify({"success": False, "message": "Please login first"}), 401
    
    # Get database connection
    connection = get_db_connection()
    if not connection:
        print("DEBUG: Database connection failed")
        return jsonify({
            "success": False,
            "message": "Database connection failed"
        }), 500
    
    cursor = connection.cursor()
    
    try:
        # Get the data
        data = request.get_json()
        if not data:
            print("DEBUG: No data received")
            return jsonify({"success": False, "message": "No data received"}), 400
        
        print(f"DEBUG: Received data: {data}")
        
        # Get basic quiz info
        subject_name = data.get('subject_name') or data.get('subject', 'General')
        section_name = data.get('section_name') or data.get('section', 'Default Section')
        grade_level = data.get('grade_level') or data.get('grade', 7)
        topic = data.get('topic', '')
        duration_minutes = data.get('duration_minutes') or data.get('duration', 5)
        
        print(f"DEBUG: Updating quiz with - Subject: {subject_name}, Section: {section_name}, Grade: {grade_level}")
        
        # Check if quiz exists and belongs to teacher
        cursor.execute("""
            SELECT q.quiz_id, q.created_by, q.quiz_status 
            FROM quizzes q 
            WHERE q.quiz_id = %s
        """, (quiz_id,))
        quiz_data = cursor.fetchone()
        
        if not quiz_data:
            return jsonify({
                "success": False, 
                "message": "Quiz not found"
            }), 404
        
        teacher_id = session.get('teacher_id') or session.get('user_id', 1)
        if quiz_data[1] != teacher_id:
            return jsonify({
                "success": False,
                "message": "You can only edit your own quizzes"
            }), 403
        
        # Check if quiz can be edited (only draft or possibly paused quizzes)
        quiz_status = quiz_data[2]
        if quiz_status not in ['draft', 'paused']:
            return jsonify({
                "success": False,
                "message": f"Cannot edit quiz with status: {quiz_status}. Only draft or paused quizzes can be edited."
            }), 400
        
        # ============================================
        # Get or create subject (same as save_quiz)
        # ============================================
        cursor.execute("SELECT subject_id FROM subjects WHERE subject_name = %s", (subject_name,))
        subject_result = cursor.fetchone()
        
        if subject_result:
            subject_id = subject_result[0]
            print(f"DEBUG: Found existing subject_id: {subject_id}")
        else:
            # Create new subject
            subject_code = subject_name.upper()[:10]
            cursor.execute("""
                INSERT INTO subjects (subject_code, subject_name, is_active)
                VALUES (%s, %s, 1)
            """, (subject_code, subject_name))
            subject_id = cursor.lastrowid
            print(f"DEBUG: Created new subject with ID: {subject_id}")
        
        # ============================================
        # Get or create section (same as save_quiz)
        # ============================================
        cursor.execute("""
            SELECT section_id FROM sections 
            WHERE section_name = %s AND grade_level = %s
        """, (section_name, grade_level))
        section_result = cursor.fetchone()
        
        if section_result:
            section_id = section_result[0]
            print(f"DEBUG: Found existing section_id: {section_id}")
        else:
            # Create new section
            cursor.execute("""
                INSERT INTO sections (section_name, grade_level, school_year, is_active)
                VALUES (%s, %s, %s, 1)
            """, (section_name, grade_level, "2024-2025"))
            section_id = cursor.lastrowid
            print(f"DEBUG: Created new section with ID: {section_id}")
        
        # ============================================
        # Update the quiz
        # ============================================
        quiz_title = f"{subject_name} - {topic if topic else 'General'}"
        
        print(f"DEBUG: Updating quiz {quiz_id} with:")
        print(f"  Title: {quiz_title}")
        print(f"  Subject ID: {subject_id}")
        print(f"  Section ID: {section_id}")
        print(f"  Topic: {topic}")
        print(f"  Duration: {duration_minutes} minutes")
        
        cursor.execute("""
            UPDATE quizzes 
            SET quiz_title = %s,
                subject_id = %s,
                section_id = %s,
                topic = %s,
                duration_minutes = %s
            WHERE quiz_id = %s
        """, (
            quiz_title,
            subject_id,
            section_id,
            topic,
            duration_minutes,
            quiz_id
        ))
        
        # If questions are provided, update them too
        questions = data.get('questions', [])
        if questions and len(questions) > 0:
            print(f"DEBUG: Updating {len(questions)} questions")
            
            # Level mapping: UI → Database
            level_mapping = {
                'beginner': 'easy',
                'intermediate': 'medium', 
                'advance': 'hard'
            }
            
            # First, delete existing questions (cascade will delete answers and choices)
            cursor.execute("DELETE FROM quiz_questions WHERE quiz_id = %s", (quiz_id,))
            print("DEBUG: Deleted existing questions")
            
            # Insert new questions
            for i, q in enumerate(questions):
                question_num = i + 1
                
                # Map level
                ui_level = q.get('level', 'beginner').lower()
                db_difficulty = level_mapping.get(ui_level, 'easy')
                
                # Determine question type
                q_type = ''
                if ui_level == 'beginner':
                    q_type = 'true_false'
                elif ui_level == 'intermediate':
                    q_type = 'multiple_choice'
                elif ui_level == 'advance':
                    q_type = 'short_answer'
                else:
                    q_type = 'short_answer'  # default
                
                question_text = q.get('question', f'Question {question_num}')
                answer = q.get('answer', '')
                
                print(f"DEBUG: Q{question_num} - Type: {q_type}, Level: {db_difficulty}")
                
                # Insert question
                cursor.execute("""
                    INSERT INTO quiz_questions 
                    (quiz_id, question_type, difficulty_level, question_text, 
                     question_order, points)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    quiz_id,
                    q_type,
                    db_difficulty,
                    question_text,
                    question_num,
                    q.get('points', 1)
                ))
                
                question_id = cursor.lastrowid
                
                # Insert answer
                cursor.execute("""
                    INSERT INTO question_answers 
                    (question_id, correct_answer, answer_format)
                    VALUES (%s, %s, %s)
                """, (
                    question_id,
                    answer,
                    'exact'
                ))
                
                # Insert choices for multiple choice
                if q_type == 'multiple_choice' and 'choices' in q:
                    choices = q['choices']
                    for j, choice in enumerate(choices):
                        is_correct = choice.get('isCorrect', False) or choice.get('is_correct', False)
                        choice_text = choice.get('text', f'Choice {j+1}')
                        
                        cursor.execute("""
                            INSERT INTO question_choices 
                            (question_id, choice_text, is_correct, choice_order)
                            VALUES (%s, %s, %s, %s)
                        """, (
                            question_id,
                            choice_text,
                            1 if is_correct else 0,
                            j + 1
                        ))
                        print(f"DEBUG: Added choice {j+1}: {choice_text} (correct: {is_correct})")
            
            # Update total points
            cursor.execute("""
                UPDATE quizzes 
                SET total_points = %s
                WHERE quiz_id = %s
            """, (len(questions), quiz_id))
        
        # Commit
        connection.commit()
        print(f"DEBUG: Update committed successfully")
        
        return jsonify({
            "success": True,
            "message": "Quiz updated successfully!",
            "quiz_id": quiz_id
        })
        
    except Exception as e:
        # Rollback on error
        connection.rollback()
        print(f"ERROR in update_quiz: {str(e)}")
        import traceback
        error_details = traceback.format_exc()
        print(f"Full traceback:\n{error_details}")
        
        return jsonify({
            "success": False,
            "message": f"Error updating quiz: {str(e)}",
            "error_type": type(e).__name__
        }), 500
        
    finally:
        # Always close the cursor and connection
        try:
            cursor.close()
        except:
            pass
        try:
            connection.close()
        except:
            pass
            
            
def generate_unique_subject_code(connection, subject_name):
    """Generate a unique subject code"""
    import random
    import string
    
    base_code = subject_name.upper().replace(' ', '')[:8]
    if len(base_code) < 3:
        base_code = base_code + 'SUB'
    
    cursor = connection.cursor(dictionary=True)
    
    # Try the base code first
    subject_code = base_code
    for attempt in range(1, 21):  # Try up to 20 times
        cursor.execute("SELECT subject_id FROM subjects WHERE subject_code = %s", (subject_code,))
        if not cursor.fetchone():
            cursor.close()
            return subject_code
        
        # Add random suffix if not unique
        if attempt < 10:
            # First 10 attempts: add numbers
            subject_code = f"{base_code[:6]}{random.randint(10, 99)}"
        else:
            # Next 10 attempts: add letters
            suffix = ''.join(random.choices(string.ascii_uppercase, k=2))
            subject_code = f"{base_code[:6]}{suffix}"
    
    cursor.close()
    # Last resort: timestamp
    import time
    return f"{base_code[:4]}{int(time.time()) % 10000:04d}"

# Add this function to your Python backend
def get_all_subjects_and_sections():
    """Get all subjects and sections for dropdowns"""
    connection = get_db_connection()
    if not connection:
        return {'subjects': [], 'sections': []}
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Get all active subjects
        cursor.execute("""
            SELECT subject_id, subject_name 
            FROM subjects 
            WHERE is_active = 1 
            ORDER BY subject_name
        """)
        subjects = cursor.fetchall()
        
        # Get all active sections
        cursor.execute("""
            SELECT section_id, section_name, grade_level 
            FROM sections 
            WHERE is_active = 1 
            ORDER BY grade_level, section_name
        """)
        sections = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        return {
            'subjects': subjects,
            'sections': sections
        }
        
    except Exception as e:
        if connection:
            connection.close()
        print(f"Error getting subjects/sections: {e}")
        return {'subjects': [], 'sections': []}

#============================================
#real time update sa session
#============================================




@app.route("/api/check_quiz_updates/<int:quiz_id>")
def check_quiz_updates(quiz_id):
    """Check for new students or updated attempts"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get current student count
        cursor.execute("""
            SELECT COUNT(*) as student_count 
            FROM student_quiz_attempts 
            WHERE quiz_id = %s
        """, (quiz_id,))
        current_count = cursor.fetchone()[0]
        
        # Get previous count from session or database
        previous_count = session.get(f'quiz_{quiz_id}_student_count', 0)
        
        # Check for new completions in the last minute
        cursor.execute("""
            SELECT COUNT(*) as new_completions
            FROM student_quiz_attempts 
            WHERE quiz_id = %s 
              AND attempt_status = 'completed'
              AND completed_at >= DATE_SUB(NOW(), INTERVAL 1 MINUTE)
        """, (quiz_id,))
        new_completions = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        has_updates = (current_count > previous_count) or (new_completions > 0)
        
        # Store current count for next check
        session[f'quiz_{quiz_id}_student_count'] = current_count
        
        return jsonify({
            "success": True,
            "has_updates": has_updates,
            "new_students_count": current_count - previous_count,
            "completed_attempts_count": new_completions,
            "total_students": current_count
        })
        
    except Exception as e:
        print("Error checking updates:", e)
        return jsonify({"success": False, "message": str(e)})

@app.route("/api/get_quiz_students_realtime/<int:quiz_id>")
def get_quiz_students_realtime(quiz_id):
    """Get current students with real-time flags"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT sqa.*, 
                   s.first_name, 
                   s.last_name, 
                   s.lrn,
                   CASE 
                     WHEN sqa.started_at >= DATE_SUB(NOW(), INTERVAL 30 SECOND) THEN 1
                     ELSE 0 
                   END as joined_recently
            FROM student_quiz_attempts sqa
            LEFT JOIN students s ON sqa.student_id = s.student_id
            WHERE sqa.quiz_id = %s
            ORDER BY sqa.started_at DESC
        """, (quiz_id,))
        
        students = []
        for row in cursor.fetchall():
            student = {
                'student_id': row[0],
                'quiz_id': row[1],
                'attempt_status': row[2],
                'score': row[3],
                'started_at': row[4].strftime('%H:%M:%S') if row[4] else None,
                'completed_at': row[5].strftime('%H:%M:%S') if row[5] else None,
                'time_taken_seconds': row[6],
                'raw_score': row[7],
                'total_points': row[8],
                'first_name': row[9],
                'last_name': row[10],
                'lrn': row[11],
                'joined_recently': bool(row[12])
            }
            students.append(student)
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "students": students
        })
        
    except Exception as e:
        print("Error getting real-time students:", e)
        return jsonify({"success": False, "message": str(e)})
    
    
    
    
@app.route("/api/get_quiz_students/<int:quiz_id>", methods=["GET"])
def get_quiz_students(quiz_id):
    """Get only student data for a quiz - FIXED for your schema"""
    if "username" not in session:
        return jsonify({"success": False, "message": "Not authenticated"}), 401
    
    connection = get_db_connection()
    if not connection:
        return jsonify({"success": False, "message": "Database connection failed"}), 500
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Simplified query without created_at column
        cursor.execute("""
            SELECT 
                sqa.attempt_id,
                s.student_id,
                s.lrn,
                COALESCE(s.first_name, '') as first_name,
                COALESCE(s.last_name, '') as last_name,
                s.grade_level,
                s.section,
                sqa.attempt_status, 
                sqa.score,
                sqa.raw_score,
                sqa.total_points,
                sqa.time_taken_seconds,
                sqa.started_at,
                sqa.completed_at
            FROM student_quiz_attempts sqa
            LEFT JOIN students s ON sqa.student_id = s.student_id
            WHERE sqa.quiz_id = %s
            ORDER BY sqa.started_at DESC
        """, (quiz_id,))
        
        students = cursor.fetchall()
        
        # Convert datetime objects to strings
        for student in students:
            if student['started_at']:
                student['started_at'] = student['started_at'].strftime('%Y-%m-%d %H:%M:%S')
            if student['completed_at']:
                student['completed_at'] = student['completed_at'].strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.close()
        connection.close()
        
        return jsonify({
            "success": True,
            "students": students,
            "count": len(students),
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        if connection:
            connection.close()
        print(f"Error getting quiz students: {e}")
        return jsonify({"success": False, "message": str(e)}), 500
    
    
    

@app.route("/api/get_student_details/<int:student_id>")
def get_student_details(student_id):
    """Get detailed student information"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        quiz_id = request.args.get('quiz_id')
        
        cursor.execute("""
            SELECT s.*, sqa.*
            FROM students s
            JOIN student_quiz_attempts sqa ON s.student_id = sqa.student_id
            WHERE s.student_id = %s AND sqa.quiz_id = %s
        """, (student_id, quiz_id))
        
        row = cursor.fetchone()
        if row:
            student = {
                'student_id': row[0],
                'first_name': row[1],
                'last_name': row[2],
                'lrn': row[3],
                'grade_level': row[4],
                'section': row[5],
                'attempt_status': row[7],
                'score': row[8],
                'started_at': row[9].strftime('%Y-%m-%d %H:%M:%S') if row[9] else None,
                'completed_at': row[10].strftime('%Y-%m-%d %H:%M:%S') if row[10] else None,
                'time_taken_seconds': row[11],
                'raw_score': row[12],
                'total_points': row[13]
            }
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "student": student
        })
        
    except Exception as e:
        print("Error getting student details:", e)
        return jsonify({"success": False, "message": str(e)})


# ============================================
# SESSION MANAGEMENT APIs
# ============================================

@app.route("/api/get_quizzes", methods=["GET"])
def get_quizzes():
    """Get quizzes for session page - SHOW ACTIVE QUIZZES ONLY"""
    if "username" not in session:
        return jsonify({"success": False, "message": "Not authenticated"}), 401
    
    connection = get_db_connection()
    if not connection:
        return jsonify({"success": False, "message": "Database connection failed"}), 500
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Get quizzes for Session Page: is_deleted=0 AND quiz_status NOT 'archived'
        cursor.execute("""
            SELECT 
                q.quiz_id,
                q.quiz_code,
                q.quiz_title,
                COALESCE(s.subject_name, 'No Subject') as subject_name,
                COALESCE(sec.section_name, 'No Section') as section_name,
                COALESCE(sec.grade_level, 'N/A') as grade_level,
                q.topic,
                DATE_FORMAT(q.created_at, '%Y-%m-%d') as date_created,
                q.duration_minutes,
                q.quiz_status,
                q.total_points,
                (SELECT COUNT(*) FROM student_quiz_attempts WHERE quiz_id = q.quiz_id) as student_count
            FROM quizzes q
            LEFT JOIN subjects s ON q.subject_id = s.subject_id
            LEFT JOIN sections sec ON q.section_id = sec.section_id
            WHERE q.created_by = %s 
                AND q.is_deleted = 0  # NOT in trash
                AND q.quiz_status != 'archived'  # NOT in archive
            ORDER BY q.created_at DESC
        """, (session.get('teacher_id', 1),))
        
        quizzes = cursor.fetchall()
        
        print(f"DEBUG: Found {len(quizzes)} quizzes for Session page (is_deleted=0, status!=archived)")
        
        cursor.close()
        connection.close()
        
        return jsonify({"success": True, "quizzes": quizzes})
    
    except Exception as e:
        if connection:
            connection.close()
        print(f"Error in get_quizzes: {e}")
        return jsonify({"success": False, "message": str(e)}), 500
    
#===========================================
#import
#===========================================

@app.route("/api/import_questions", methods=["POST"])
def import_questions():
    """Import questions from various file formats"""
    if "username" not in session:
        return jsonify({"success": False, "message": "Not authenticated"}), 401
    
    try:
        if 'file' not in request.files:
            return jsonify({"success": False, "message": "No file uploaded"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"success": False, "message": "No file selected"}), 400
        
        filename = secure_filename(file.filename)
        file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        
        questions = []
        
        if file_ext == 'txt':
            # Parse text file
            content = file.read().decode('utf-8')
            questions = parse_text_file(content)
            
        elif file_ext == 'docx':
            # Parse Word document
            questions = parse_word_file(file)
            
        elif file_ext in ['xlsx', 'xls', 'csv']:
            # Parse Excel/CSV file
            questions = parse_excel_file(file, file_ext)
            
        else:
            return jsonify({"success": False, "message": f"Unsupported file type: {file_ext}"}), 400
        
        return jsonify({
            "success": True, 
            "questions": questions,
            "count": len(questions)
        })
        
    except Exception as e:
        print(f"Error importing questions: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

def parse_text_file(content):
    """Parse questions from text file content - FIXED for HTML content"""
    print("=== PARSING TEXT FILE (FIXED VERSION) ===")
    
    questions = []
    lines = content.split('\n')
    
    current_section = None
    question_counter = 0
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # DEBUG: Print each line being processed
        # print(f"Line {i}: '{line}'")
        
        # Check for section headers (case insensitive, with or without brackets)
        if re.search(r'^\[?\s*BEGINNER\s*\]?$', line, re.IGNORECASE):
            current_section = 'beginner'
            question_counter = 0
            i += 1
            continue
        elif re.search(r'^\[?\s*INTERMEDIATE\s*\]?$', line, re.IGNORECASE):
            current_section = 'intermediate'
            question_counter = 0
            i += 1
            continue
        elif re.search(r'^\[?\s*ADVANCED?\s*\]?$', line, re.IGNORECASE):
            current_section = 'advance'
            question_counter = 0
            i += 1
            continue
        
        if not current_section:
            i += 1
            continue
        
        # Skip empty lines
        if not line:
            i += 1
            continue
        
        # Check if it's a question line (starts with number)
        # FIX: Use a more flexible regex to handle HTML tags
        match = re.match(r'^(\d+)[\.\)]\s+(.+)$', line)
        if match:
            question_counter += 1
            full_line = line
            question_text = match.group(2).strip()
            
            print(f"\nDEBUG: Parsing Q{question_counter} in {current_section}")
            print(f"  Raw line: '{line}'")
            
            # For beginner questions, handle (TRUE) or (FALSE) at the end
            if current_section == 'beginner':
                # Look for (TRUE) or (FALSE) - could be anywhere in the line
                tf_match = re.search(r'\((TRUE|FALSE)\)\s*$', line, re.IGNORECASE)
                if tf_match:
                    answer = tf_match.group(1).upper()
                    # Remove the answer from the question text
                    question_text = re.sub(r'\s*\(TRUE|FALSE\)\s*$', '', line[match.end(1):], flags=re.IGNORECASE).strip()
                else:
                    answer = "TRUE"  # Default
                    question_text = question_text
                
                print(f"  Question: '{question_text}'")
                print(f"  Answer: {answer}")
                
                questions.append({
                    'level': current_section,
                    'question': question_text,
                    'answer': answer,
                    'type': 'true_false'
                })
            
            # For intermediate questions
            elif current_section == 'intermediate':
                # Remove any answer in parentheses
                question_text = re.sub(r'\s*\([^)]*\)\s*$', '', question_text).strip()
                
                print(f"  Question: '{question_text}'")
                
                # Collect choices from next lines
                choices = []
                correct_answer = ""
                
                j = i + 1
                while j < len(lines):
                    next_line = lines[j].strip()
                    
                    # Stop if we hit a new question or section
                    if not next_line or re.match(r'^\d+[\.\)]', next_line) or re.search(r'^\[', next_line, re.IGNORECASE):
                        break
                    
                    # Check for choice (A) Choice text ✓
                    choice_match = re.match(r'^([A-D])[\.\)]\s*(.*)', next_line, re.IGNORECASE)
                    if choice_match:
                        choice_text = choice_match.group(2).strip()
                        is_correct = '✓' in choice_text or '[CORRECT]' in choice_text.upper()
                        
                        # Clean the choice text
                        choice_text = re.sub(r'[✓✔]|\s*\[CORRECT\]', '', choice_text, flags=re.IGNORECASE).strip()
                        
                        choices.append({
                            'text': choice_text,
                            'isCorrect': is_correct
                        })
                        
                        if is_correct and not correct_answer:
                            correct_answer = choice_text
                    
                    j += 1
                
                # Try to extract answer from original line if not found in choices
                if not correct_answer:
                    ans_match = re.search(r'\((.*?)\)\s*$', full_line)
                    if ans_match:
                        correct_answer = ans_match.group(1).strip()
                
                print(f"  Choices: {len(choices)}")
                print(f"  Correct answer: '{correct_answer}'")
                
                questions.append({
                    'level': current_section,
                    'question': question_text,
                    'answer': correct_answer,
                    'type': 'multiple_choice',
                    'choices': choices
                })
            
            # For advance questions
            elif current_section == 'advance':
                # Check if answer is in parentheses
                ans_match = re.search(r'\((.*?)\)\s*$', question_text)
                if ans_match:
                    answer = ans_match.group(1).strip()
                    question_text = re.sub(r'\s*\(.*?\)\s*$', '', question_text).strip()
                else:
                    # Check next line for "Answer:"
                    answer = ""
                    if i + 1 < len(lines):
                        next_line = lines[i + 1].strip()
                        if next_line.lower().startswith('answer:'):
                            answer = next_line[7:].strip()
                            i += 1  # Skip the answer line
                
                print(f"  Question: '{question_text}'")
                print(f"  Answer: '{answer}'")
                
                questions.append({
                    'level': current_section,
                    'question': question_text,
                    'answer': answer,
                    'type': 'short_answer'
                })
            
            i += 1
        else:
            i += 1
    
    print(f"\n=== PARSING COMPLETE: Found {len(questions)} questions ===")
    
    # DEBUG: Print all parsed questions
    for idx, q in enumerate(questions):
        print(f"\nQ{idx+1} [{q['level']}]:")
        print(f"  Question: '{q['question'][:50]}...'")
        print(f"  Answer: '{q['answer']}'")
        if 'choices' in q:
            print(f"  Choices: {len(q['choices'])}")
            for c in q['choices']:
                print(f"    - '{c['text']}' {'✓' if c['isCorrect'] else ''}")
    
    return questions

def parse_beginner_question(question_text, lines, current_index):
    """Parse a beginner (true/false) question"""
    # Look for (TRUE) or (FALSE) at the end
    tf_match = re.search(r'\((TRUE|FALSE)\)$', question_text, re.IGNORECASE)
    
    if tf_match:
        answer = tf_match.group(1).upper()
        question_text = re.sub(r'\s*\(TRUE|FALSE\)$', '', question_text, flags=re.IGNORECASE).strip()
    else:
        # Default to TRUE if no answer specified
        answer = "TRUE"
    
    return {
        'question': question_text,
        'answer': answer,
        'type': 'true_false'
    }

def parse_intermediate_question(question_text, lines, current_index):
    """Parse an intermediate (multiple choice) question"""
    # Remove answer in parentheses if present
    answer_match = re.search(r'\((.*?)\)$', question_text)
    correct_answer = ""
    
    if answer_match:
        correct_answer = answer_match.group(1).strip()
        question_text = re.sub(r'\s*\(.*?\)$', '', question_text).strip()
    
    choices = []
    
    # Look for choices in next lines (format: A) Choice text ✓)
    i = current_index + 1
    while i < len(lines):
        line = lines[i].strip()
        
        # Stop if we hit a new question, empty line, or section header
        if not line or re.match(r'^\d+[\.\)]', line) or re.search(r'^\[', line):
            break
        
        # Check for choice pattern (A), B), C), D) or a), b), c), d))
        choice_match = re.match(r'^([A-Da-d])[\.\)]\s*(.*)', line)
        if choice_match:
            choice_text = choice_match.group(2).strip()
            
            # Check for correct marker (✓ or [CORRECT])
            is_correct = False
            if '✓' in choice_text or '[CORRECT]' in choice_text.upper():
                is_correct = True
                # Remove the marker
                choice_text = re.sub(r'[✓✔]|\s*\[CORRECT\]', '', choice_text, flags=re.IGNORECASE).strip()
            
            # If this choice matches the answer in parentheses, mark it as correct
            if correct_answer and choice_text.lower() == correct_answer.lower():
                is_correct = True
            
            choices.append({
                'text': choice_text,
                'isCorrect': is_correct
            })
            
            # If this choice is correct and we don't have an answer yet, use it
            if is_correct and not correct_answer:
                correct_answer = choice_text
        
        i += 1
    
    # If we still don't have an answer, use the first correct choice or first choice
    if not correct_answer and choices:
        correct_choices = [c for c in choices if c.get('isCorrect', False)]
        if correct_choices:
            correct_answer = correct_choices[0]['text']
        else:
            correct_answer = choices[0]['text']
    
    return {
        'question': question_text,
        'answer': correct_answer,
        'type': 'multiple_choice',
        'choices': choices
    }


def parse_advance_question(question_text, lines, current_index):
    """Parse an advance (short answer) question"""
    # Check if answer is in parentheses
    answer_match = re.search(r'\((.*?)\)$', question_text)
    
    if answer_match:
        answer = answer_match.group(1).strip()
        question_text = re.sub(r'\s*\(.*?\)$', '', question_text).strip()
    else:
        # Look for answer in next line starting with "Answer:"
        answer = ""
        i = current_index + 1
        if i < len(lines):
            next_line = lines[i].strip()
            if next_line.lower().startswith('answer:'):
                answer = next_line[7:].strip()
    
    return {
        'question': question_text,
        'answer': answer,
        'type': 'short_answer'
    }
    
    



def parse_word_file(file):
    """Parse questions from Word document"""
    questions = []
    doc = docx.Document(file)
    current_level = ''
    
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue
            
        # Check for level headers
        if text.upper() in ['BEGINNER', 'INTERMEDIATE', 'ADVANCED']:
            current_level = text.lower()
            continue
            
        if not current_level:
            continue
            
        # Parse questions (simplified)
        if text and text[0].isdigit() and '. ' in text:
            question_data = parse_question_line(text, current_level)
            if question_data:
                questions.append(question_data)
    
    return questions

def parse_excel_file(file, file_ext):
    """Parse questions from Excel/CSV file"""
    questions = []
    
    try:
        if file_ext == 'csv':
            df = pd.read_csv(io.BytesIO(file.read()))
        else:
            df = pd.read_excel(io.BytesIO(file.read()))
        
        for _, row in df.iterrows():
            try:
                level = str(row.get('Level', '')).strip().lower()
                if not level:
                    continue
                    
                question = str(row.get('Question', '')).strip()
                answer = str(row.get('Answer', '')).strip()
                
                if not question:
                    continue
                
                question_data = {
                    'level': level,
                    'question': question,
                    'answer': answer
                }
                
                # Add choices for multiple choice
                if level == 'intermediate':
                    choices = []
                    for i in range(1, 5):
                        choice = str(row.get(f'Choice{i}', '')).strip()
                        if choice:
                            choices.append({
                                'text': choice,
                                'isCorrect': choice == answer
                            })
                    question_data['choices'] = choices
                    question_data['type'] = 'multiple_choice'
                elif level == 'beginner':
                    question_data['type'] = 'true_false'
                elif level == 'advanced':
                    question_data['type'] = 'text'
                
                questions.append(question_data)
                
            except Exception as e:
                print(f"Error parsing row: {e}")
                continue
                
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        raise
    
    return questions

def parse_question_line(line, section):
    """Parse a single question line"""
    # Remove question number
    line = re.sub(r'^\d+[\.\)]\s*', '', line).strip()
    
    question_data = {
        'level': section,
        'question': '',
        'answer': '',
        'type': '',
        'choices': []
    }
    
    # BEGINNER (True/False)
    if section == 'beginner':
        question_data['type'] = 'true_false'
        
        # Look for (TRUE) or (FALSE) at the end
        tf_match = re.search(r'\((TRUE|FALSE)\)$', line, re.IGNORECASE)
        if tf_match:
            question_data['answer'] = tf_match.group(1).upper()
            question_data['question'] = re.sub(r'\s*\(TRUE|FALSE\)$', '', line, flags=re.IGNORECASE).strip()
        else:
            question_data['question'] = line
            question_data['answer'] = 'TRUE'  # default
    
    # INTERMEDIATE (Multiple Choice)
    elif section == 'intermediate':
        question_data['type'] = 'multiple_choice'
        
        # Remove answer in parentheses if present
        line = re.sub(r'\s*\([^)]+\)$', '', line).strip()
        question_data['question'] = line
        
        # For now, answer will be empty - choices will be added separately
        # In your UI, you'll need to handle choices separately
    
    # ADVANCE (Short Answer)
    elif section == 'advance':
        question_data['type'] = 'short_answer'
        
        # Look for answer in parentheses or after "Answer:"
        ans_match = re.search(r'\((.*?)\)$', line)
        if ans_match:
            question_data['answer'] = ans_match.group(1).strip()
            question_data['question'] = re.sub(r'\s*\(.*?\)$', '', line).strip()
        else:
            question_data['question'] = line
            # Answer will be entered manually in UI
    
    return question_data
    

@app.route("/api/get_quiz_detail/<int:quiz_id>", methods=["GET"])
def get_quiz_detail(quiz_id):
    """Get detailed information about a specific quiz - UPDATED"""
    if "username" not in session:
        return jsonify({"success": False, "message": "Not authenticated"}), 401
    
    connection = get_db_connection()
    if not connection:
        return jsonify({"success": False, "message": "Database connection failed"}), 500
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        print(f"DEBUG: Getting quiz detail for quiz_id: {quiz_id}")
        
        # Get quiz info
        quiz_query = """
            SELECT 
                q.quiz_id,
                q.quiz_code,
                q.quiz_title,
                COALESCE(s.subject_name, 'No Subject') as subject_name,
                COALESCE(sec.section_name, 'No Section') as section_name,
                sec.grade_level,
                q.topic,
                DATE_FORMAT(q.created_at, '%Y-%m-%d %H:%i') as date_created,
                q.duration_minutes,
                q.quiz_status,
                q.total_points
            FROM quizzes q
            LEFT JOIN subjects s ON q.subject_id = s.subject_id
            LEFT JOIN sections sec ON q.section_id = sec.section_id
            WHERE q.quiz_id = %s AND q.created_by = %s
        """
        cursor.execute(quiz_query, (quiz_id, session.get('teacher_id', 1)))
        quiz = cursor.fetchone()
        
        if not quiz:
            print(f"DEBUG: Quiz {quiz_id} not found or not owned by teacher")
            cursor.close()
            connection.close()
            return jsonify({"success": False, "message": "Quiz not found"}), 404
        
        print(f"DEBUG: Found quiz: {quiz['quiz_title']}")
        
        # Get ALL questions with their answers - FIXED QUERY
        questions_query = """
            SELECT 
                qq.question_id, 
                qq.difficulty_level, 
                qq.question_text, 
                qq.question_type, 
                qa.correct_answer, 
                qq.points,
                qq.question_order
            FROM quiz_questions qq
            LEFT JOIN question_answers qa ON qq.question_id = qa.question_id
            WHERE qq.quiz_id = %s
            ORDER BY qq.question_order ASC, qq.question_id ASC
        """
        cursor.execute(questions_query, (quiz_id,))
        questions = cursor.fetchall()
        
        print(f"DEBUG: Found {len(questions)} questions for quiz {quiz_id}")
        
        if len(questions) == 0:
            print(f"DEBUG: WARNING - No questions found for quiz {quiz_id}")
        else:
            # Debug print each question
            for q in questions:
                print(f"DEBUG: Question ID {q['question_id']}: {q['question_text'][:50]}... | Answer: {q['correct_answer']}")
        
        # Get choices for each question
        for question in questions:
            if question['question_type'] == 'multiple_choice':
                choices_query = """
                    SELECT choice_text, is_correct, choice_order
                    FROM question_choices
                    WHERE question_id = %s
                    ORDER BY choice_order
                """
                cursor.execute(choices_query, (question['question_id'],))
                choices = cursor.fetchall()
                question['choices'] = choices
                print(f"DEBUG: Question {question['question_id']} has {len(choices)} choices")
            else:
                question['choices'] = []
        
        # Get registered students
        students_query = """
            SELECT 
                sqa.attempt_id,
                s.student_id,
                s.lrn,
                COALESCE(s.first_name, '') as first_name,
                COALESCE(s.last_name, '') as last_name,
                s.grade_level,
                s.section,
                sqa.attempt_status, 
                sqa.score,
                sqa.raw_score,
                sqa.total_points,
                sqa.time_taken_seconds
            FROM student_quiz_attempts sqa
            LEFT JOIN students s ON sqa.student_id = s.student_id
            WHERE sqa.quiz_id = %s
            ORDER BY sqa.score DESC
        """
        cursor.execute(students_query, (quiz_id,))
        students = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        # Organize questions by difficulty - FIXED
        organized_questions = {
            'easy': [],
            'medium': [],
            'hard': []
        }
        
        for q in questions:
            if q['difficulty_level'] == 'easy':
                organized_questions['easy'].append(q)
            elif q['difficulty_level'] == 'medium':
                organized_questions['medium'].append(q)
            elif q['difficulty_level'] == 'hard':
                organized_questions['hard'].append(q)
        
        print(f"DEBUG: Organized questions - Easy: {len(organized_questions['easy'])}, Medium: {len(organized_questions['medium'])}, Hard: {len(organized_questions['hard'])}")
        
        return jsonify({
            "success": True,
            "quiz": quiz,
            "questions": organized_questions,
            "students": students
        })
    
    except Exception as e:
        print(f"DEBUG: Error in get_quiz_detail: {str(e)}")
        if connection:
            connection.close()
        return jsonify({"success": False, "message": str(e)}), 500
    
    
    
@app.route("/api/student/get_quiz_review/<int:quiz_id>", methods=["GET"])
def get_quiz_review_data(quiz_id):
    """Get quiz review data with correct answers - for post-submission review"""
    connection = get_db_connection()
    if not connection:
        return jsonify({"success": False, "message": "Database connection failed"}), 500
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Get questions with correct answers
        cursor.execute("""
            SELECT 
                qq.question_id,
                qq.question_text,
                qq.question_type,
                qq.difficulty_level,
                qq.points,
                qa.correct_answer
            FROM quiz_questions qq
            LEFT JOIN question_answers qa ON qq.question_id = qa.question_id
            WHERE qq.quiz_id = %s
            ORDER BY qq.question_order ASC, qq.question_id ASC
        """, (quiz_id,))
        
        questions = cursor.fetchall()
        
        # Get choices for multiple choice questions
        for question in questions:
            if question['question_type'] == 'multiple_choice':
                cursor.execute("""
                    SELECT choice_text, is_correct
                    FROM question_choices
                    WHERE question_id = %s
                    ORDER BY choice_order
                """, (question['question_id'],))
                question['choices'] = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        return jsonify({
            "success": True,
            "questions": questions
        })
        
    except Exception as e:
        if connection:
            connection.close()
        print(f"Error getting quiz review data: {e}")
        return jsonify({"success": False, "message": str(e)}), 500
    
    
    
@app.route("/api/student/get_quiz/<int:quiz_id>", methods=["GET"])
def student_get_quiz(quiz_id):
    """Get quiz for student - FIXED: Check quiz_status instead of session_status"""
    connection = get_db_connection()
    if not connection:
        return jsonify({"success": False, "message": "Database connection failed"}), 500
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Get quiz basic info including quiz_status
        cursor.execute("""
            SELECT quiz_id, quiz_title, topic, duration_minutes, total_points, quiz_status
            FROM quizzes WHERE quiz_id = %s
        """, (quiz_id,))
        quiz = cursor.fetchone()
        
        if not quiz:
            cursor.close()
            connection.close()
            return jsonify({"success": False, "message": "Quiz not found"}), 404
        
        # Get questions
        cursor.execute("""
            SELECT 
                qq.question_id,
                qq.question_type,
                qq.question_text,
                qq.difficulty_level,
                qq.points,
                qq.question_order
            FROM quiz_questions qq
            WHERE qq.quiz_id = %s
            ORDER BY qq.question_order ASC, qq.question_id ASC
        """, (quiz_id,))
        questions = cursor.fetchall()
        
        # Get choices for multiple choice questions
        for question in questions:
            if question['question_type'] == 'multiple_choice':
                cursor.execute("""
                    SELECT choice_id, choice_text, choice_order
                    FROM question_choices
                    WHERE question_id = %s
                    ORDER BY choice_order
                """, (question['question_id'],))
                question['choices'] = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        # Organize questions by easy/medium/hard difficulty levels for student
        organized_questions = {
            'easy': [q for q in questions if q['difficulty_level'] == 'easy'],
            'medium': [q for q in questions if q['difficulty_level'] == 'medium'],
            'hard': [q for q in questions if q['difficulty_level'] == 'hard']
        }
        
        # Add questions to quiz data for student
        quiz['questions'] = organized_questions
        
        # Add session_status based on quiz_status for frontend compatibility
        quiz['session_status'] = quiz['quiz_status']
        
        return jsonify({
            "success": True,
            "quiz": quiz
        })
        
    except Exception as e:
        if connection:
            connection.close()
        print(f"Error in student_get_quiz: {e}")
        return jsonify({"success": False, "message": str(e)}), 500
    
    

@app.route("/api/generate_qr/<int:quiz_id>", methods=["GET"])
def generate_qr(quiz_id):
    """Generate QR code for quiz"""
    if "username" not in session:
        return jsonify({"success": False, "message": "Not authenticated"}), 401
    
    try:
        # Get local IP for LAN access
        local_ip = get_local_ip()
        quiz_url = f"http://{local_ip}:5000/student/quiz/{quiz_id}"
        
        # Create QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(quiz_url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return jsonify({
            "success": True,
            "qr_code": f"data:image/png;base64,{img_str}",
            "url": quiz_url,
            "ip": local_ip
        })
    
    except Exception as e:
        print(f"Error generating QR: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/api/start_quiz/<int:quiz_id>", methods=["POST"])
def start_quiz_session(quiz_id):
    """Start a quiz session - FIXED: Update both quiz status and create session"""
    if "username" not in session:
        return jsonify({"success": False, "message": "Not authenticated"}), 401
    
    connection = get_db_connection()
    if not connection:
        return jsonify({"success": False, "message": "Database connection failed"}), 500
    
    try:
        cursor = connection.cursor()
        
        # Generate session code
        session_code = generate_quiz_code()[:6]
        
        # Get quiz duration
        cursor.execute("SELECT duration_minutes FROM quizzes WHERE quiz_id = %s", (quiz_id,))
        result = cursor.fetchone()
        if not result:
            cursor.close()
            connection.close()
            return jsonify({"success": False, "message": "Quiz not found"}), 404
        
        duration_minutes = result[0]
        
        # Check if session table exists and create session
        cursor.execute("SHOW TABLES LIKE 'quiz_session'")
        quiz_session_exists = cursor.fetchone()
        
        cursor.execute("SHOW TABLES LIKE 'quiz_sessions'")
        quiz_sessions_exists = cursor.fetchone()
        
        if quiz_session_exists:
            # Check if session already exists
            cursor.execute("SELECT session_id FROM quiz_session WHERE quiz_id = %s", (quiz_id,))
            existing_session = cursor.fetchone()
            
            if existing_session:
                cursor.execute("UPDATE quiz_session SET status = 'active' WHERE quiz_id = %s", (quiz_id,))
            else:
                # Try to insert session without duration columns first
                try:
                    cursor.execute("""
                        INSERT INTO quiz_session (quiz_id, session_code, started_at, status, started_by)
                        VALUES (%s, %s, NOW(), 'active', %s)
                    """, (quiz_id, session_code, session.get('teacher_id', 1)))
                except Exception as e:
                    print(f"DEBUG: Error inserting session: {e}")
                    # If that fails, just update quiz status
                    pass
        elif quiz_sessions_exists:
            # Check if session already exists
            cursor.execute("SELECT session_id FROM quiz_sessions WHERE quiz_id = %s", (quiz_id,))
            existing_session = cursor.fetchone()
            
            if existing_session:
                cursor.execute("UPDATE quiz_sessions SET session_status = 'active' WHERE quiz_id = %s", (quiz_id,))
            else:
                try:
                    cursor.execute("""
                        INSERT INTO quiz_sessions (quiz_id, session_code, started_at, session_status, started_by)
                        VALUES (%s, %s, NOW(), 'active', %s)
                    """, (quiz_id, session_code, session.get('teacher_id', 1)))
                except Exception as e:
                    print(f"DEBUG: Error inserting session: {e}")
                    # If that fails, just update quiz status
                    pass
        
        # MOST IMPORTANT: Update quiz status to active
        cursor.execute("UPDATE quizzes SET quiz_status = 'active' WHERE quiz_id = %s", (quiz_id,))
        
        connection.commit()
        cursor.close()
        connection.close()
        
        return jsonify({"success": True, "message": "Quiz started successfully"})
    
    except Exception as e:
        if connection:
            connection.rollback()
            connection.close()
        print(f"Error starting quiz: {e}")
        return jsonify({"success": False, "message": str(e)}), 500
    

@app.route("/api/pause_quiz/<int:quiz_id>", methods=["POST"])
def pause_quiz_session(quiz_id):
    """Pause a quiz session - FIXED: Handle both table names"""
    if "username" not in session:
        return jsonify({"success": False, "message": "Not authenticated"}), 401
    
    connection = get_db_connection()
    if not connection:
        return jsonify({"success": False, "message": "Database connection failed"}), 500
    
    try:
        cursor = connection.cursor()
        
        # Check which table exists
        cursor.execute("SHOW TABLES LIKE 'quiz_session'")
        quiz_session_exists = cursor.fetchone()
        
        # Update session status to paused
        if quiz_session_exists:
            cursor.execute("""
                UPDATE quiz_session 
                SET status = 'paused' 
                WHERE quiz_id = %s
            """, (quiz_id,))
        else:
            cursor.execute("""
                UPDATE quiz_sessions 
                SET session_status = 'paused' 
                WHERE quiz_id = %s
            """, (quiz_id,))
        
        # Update quiz status to paused
        cursor.execute("UPDATE quizzes SET quiz_status = 'paused' WHERE quiz_id = %s", (quiz_id,))
        
        connection.commit()
        cursor.close()
        connection.close()
        
        return jsonify({"success": True, "message": "Quiz paused successfully"})
    
    except Exception as e:
        if connection:
            connection.rollback()
            connection.close()
        print(f"Error pausing quiz: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/api/resume_quiz/<int:quiz_id>", methods=["POST"])
def resume_quiz_session(quiz_id):
    """Resume a quiz session - FIXED: Handle both table names"""
    if "username" not in session:
        return jsonify({"success": False, "message": "Not authenticated"}), 401
    
    connection = get_db_connection()
    if not connection:
        return jsonify({"success": False, "message": "Database connection failed"}), 500
    
    try:
        cursor = connection.cursor()
        
        # Check which table exists
        cursor.execute("SHOW TABLES LIKE 'quiz_session'")
        quiz_session_exists = cursor.fetchone()
        
        # Update session status to active
        if quiz_session_exists:
            cursor.execute("""
                UPDATE quiz_session 
                SET status = 'active' 
                WHERE quiz_id = %s
            """, (quiz_id,))
        else:
            cursor.execute("""
                UPDATE quiz_sessions 
                SET session_status = 'active' 
                WHERE quiz_id = %s
            """, (quiz_id,))
        
        # Update quiz status to active
        cursor.execute("UPDATE quizzes SET quiz_status = 'active' WHERE quiz_id = %s", (quiz_id,))
        
        connection.commit()
        cursor.close()
        connection.close()
        
        return jsonify({"success": True, "message": "Quiz resumed successfully"})
    
    except Exception as e:
        if connection:
            connection.rollback()
            connection.close()
        print(f"Error resuming quiz: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/stop_quiz/<int:quiz_id>", methods=["POST"])
def stop_quiz_session(quiz_id):
    """Stop quiz - COMPLETE VERSION that ends everything"""
    if "username" not in session:
        return jsonify({"success": False, "message": "Not authenticated"}), 401
    
    connection = get_db_connection()
    if not connection:
        return jsonify({"success": False, "message": "Database connection failed"}), 500
    
    try:
        cursor = connection.cursor()
        
        # 1. END ALL active/paused sessions for this quiz
        cursor.execute("""
            UPDATE quiz_sessions 
            SET session_status = 'ended', 
                ended_at = NOW()
            WHERE quiz_id = %s AND session_status IN ('active', 'paused')
        """, (quiz_id,))
        sessions_ended = cursor.rowcount
        
        # 2. Update quiz status to 'completed'
        cursor.execute("""
            UPDATE quizzes 
            SET quiz_status = 'completed',
                updated_at = NOW()
            WHERE quiz_id = %s
        """, (quiz_id,))
        
        # 3. Mark ALL student attempts as completed
        cursor.execute("""
            UPDATE student_quiz_attempts 
            SET attempt_status = 'completed', 
                completed_at = NOW(),
                time_taken_seconds = 
                    CASE 
                        WHEN started_at IS NOT NULL THEN 
                            TIMESTAMPDIFF(SECOND, started_at, NOW())
                        ELSE 0
                    END
            WHERE quiz_id = %s 
            AND attempt_status IN ('in_progress', 'started', 'not_started')
        """, (quiz_id,))
        attempts_ended = cursor.rowcount
        
        connection.commit()
        cursor.close()
        connection.close()
        
        return jsonify({
            "success": True, 
            "message": f"Quiz stopped successfully. Ended {sessions_ended} sessions and {attempts_ended} student attempts.",
            "sessions_ended": sessions_ended,
            "attempts_ended": attempts_ended
        })
    
    except Exception as e:
        if connection:
            connection.rollback()
            connection.close()
        print(f"Error stopping quiz: {e}")
        return jsonify({"success": False, "message": str(e)}), 500
    

@app.route("/api/teacher/check_quiz_status/<int:quiz_id>", methods=["GET"])
def teacher_check_quiz_status(quiz_id):
    """Teacher checks if quiz session is still active - SIMPLIFIED"""
    connection = get_db_connection()
    if not connection:
        return jsonify({"success": False}), 500
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # First, check quiz status directly from quizzes table
        cursor.execute("SELECT quiz_status FROM quizzes WHERE quiz_id = %s", (quiz_id,))
        quiz_result = cursor.fetchone()
        
        cursor.close()
        connection.close()
        
        if quiz_result:
            return jsonify({"success": True, "status": quiz_result['quiz_status']})
            
        return jsonify({"success": False}), 404
    
    except Exception as e:
        if connection:
            connection.close()
        print(f"Error checking quiz status: {e}")
        return jsonify({"success": False}), 500
    
    

@app.route("/api/student/check_quiz_status/<int:quiz_id>", methods=["GET"])
def student_check_quiz_status(quiz_id):
    """Check quiz status for student - FIXED: Use quiz_status"""
    connection = get_db_connection()
    if not connection:
        return jsonify({"success": False, "message": "Database connection failed"}), 500
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Get quiz status directly from quizzes table
        cursor.execute("SELECT quiz_status FROM quizzes WHERE quiz_id = %s", (quiz_id,))
        quiz_data = cursor.fetchone()
        
        cursor.close()
        connection.close()
        
        if not quiz_data:
            return jsonify({"success": False, "message": "Quiz not found"}), 404
        
        return jsonify({
            "success": True, 
            "status": quiz_data['quiz_status']
        })
    
    except Exception as e:
        if connection:
            connection.close()
        print(f"Error checking quiz status: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

# ============================================
# RETRIEVAL APIs
# ============================================


@app.route("/api/get_active_sessions_count", methods=["GET"])
def get_active_sessions_count():
    """Get count of active quiz sessions for dashboard"""
    if "username" not in session:
        return jsonify({"success": False, "message": "Not authenticated"}), 401
    
    conn = get_db_connection()
    if not conn:
        return jsonify({"success": False, "message": "Database connection failed"})

    try:
        cursor = conn.cursor()
        
        # Count active quiz sessions for this teacher
        cursor.execute("""
            SELECT COUNT(DISTINCT q.quiz_id) as active_sessions_count
            FROM quizzes q
            JOIN quiz_sessions qs ON q.quiz_id = qs.quiz_id
            WHERE q.created_by = %s 
              AND qs.session_status = 'active'
              AND q.is_deleted = 0
        """, (session.get('teacher_id', 1),))
        
        result = cursor.fetchone()
        active_sessions_count = result[0] if result else 0
        
        # Also get active students count
        cursor.execute("""
            SELECT COUNT(DISTINCT sqa.student_id) as active_students_count
            FROM student_quiz_attempts sqa
            JOIN quizzes q ON sqa.quiz_id = q.quiz_id
            WHERE q.created_by = %s 
              AND sqa.attempt_status = 'in_progress'
              AND q.is_deleted = 0
        """, (session.get('teacher_id', 1),))
        
        result = cursor.fetchone()
        active_students_count = result[0] if result else 0
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "active_sessions": active_sessions_count,
            "active_students": active_students_count
        })
        
    except Exception as e:
        print("Error in get_active_sessions_count:", e)
        if conn:
            conn.close()
        return jsonify({"success": False, "message": str(e)})
    
    
    
# Add these routes to your Flask app

@app.route('/api/get_active_quizzes_for_upload', methods=['GET'])
def get_active_quizzes_for_upload():
    """Get active quizzes that can accept student registration"""
    try:
        teacher_id = session.get('teacher_id')
        if not teacher_id:
            return jsonify({'success': False, 'message': 'Not authenticated'}), 401
        
        # Get quizzes that are not completed or archived
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT q.quiz_id, q.quiz_title, q.quiz_code, 
                   s.subject_name, sec.section_name, q.grade_level,
                   q.quiz_status
            FROM quizzes q
            LEFT JOIN subjects s ON q.subject_id = s.subject_id
            LEFT JOIN sections sec ON q.section_id = sec.section_id
            WHERE q.teacher_id = %s 
            AND q.quiz_status IN ('draft', 'active', 'paused')
            ORDER BY q.date_created DESC
        """, (teacher_id,))
        
        quizzes = []
        for row in cursor.fetchall():
            quizzes.append({
                'quiz_id': row[0],
                'quiz_title': row[1],
                'quiz_code': row[2],
                'subject_name': row[3],
                'section_name': row[4],
                'grade_level': row[5],
                'quiz_status': row[6]
            })
        
        cursor.close()
        return jsonify({'success': True, 'quizzes': quizzes})
        
    except Exception as e:
        print(f"Error getting active quizzes: {str(e)}")
        return jsonify({'success': False, 'message': 'Server error'}), 500



@app.route('/api/register_students', methods=['POST'])
def register_students():
    """ULTRA SIMPLE - JUST MAKE IT WORK"""
    print("\n" + "="*60)
    print("ULTRA SIMPLE REGISTER STUDENTS - MAKE IT WORK")
    print("="*60)
    
    try:
        # 1. Get data
        data = request.get_json()
        print(f"Received data: {data}")
        
        if not data:
            return jsonify({'success': False, 'message': 'No data'}), 400
        
        quiz_id = data.get('quiz_id')
        students = data.get('students', [])
        
        print(f"Quiz ID: {quiz_id}")
        print(f"Number of students: {len(students)}")
        
        if not quiz_id:
            return jsonify({'success': False, 'message': 'No quiz ID'}), 400
        
        if not students:
            return jsonify({'success': False, 'message': 'No students'}), 400
        
        # 2. Connect to DB
        connection = get_db_connection()
        if not connection:
            return jsonify({'success': False, 'message': 'Database error'}), 500
        
        cursor = connection.cursor(dictionary=True)
        
        # 3. Check quiz exists
        cursor.execute("SELECT quiz_id, quiz_title FROM quizzes WHERE quiz_id = %s", (quiz_id,))
        quiz = cursor.fetchone()
        
        if not quiz:
            cursor.close()
            connection.close()
            return jsonify({'success': False, 'message': 'Quiz not found'}), 404
        
        print(f"Quiz found: {quiz['quiz_title']}")
        
        # 4. Delete the other endpoint to avoid confusion
        # Remove the @app.route('/api/simple_register_students') completely
        
        registered_count = 0
        errors = []
        
        # 5. Process students ONE BY ONE
        for student in students:
            try:
                lrn = str(student.get('lrn', '')).strip()
                first_name = student.get('first_name', '').strip()
                last_name = student.get('last_name', '').strip()
                section = student.get('section', '').strip() or quiz.get('section_name', 'Default')
                grade_level = int(student.get('grade_level', quiz.get('grade_level', 7)))
                
                print(f"Processing: {lrn} - {first_name} {last_name}")
                
                # Skip if missing required fields
                if not lrn or not first_name or not last_name:
                    errors.append(f"Missing fields for {lrn}")
                    continue
                
                # STEP 1: Insert or get student
                try:
                    # Try to insert new student
                    cursor.execute("""
                        INSERT INTO students (lrn, first_name, last_name, grade_level, section, enrollment_status)
                        VALUES (%s, %s, %s, %s, %s, 'active')
                    """, (lrn, first_name, last_name, grade_level, section))
                    
                    student_id = cursor.lastrowid
                    print(f"  New student created: ID {student_id}")
                    
                except Exception as e:
                    # Student might already exist - get their ID
                    print(f"  Student exists, getting ID...")
                    cursor.execute("SELECT student_id FROM students WHERE lrn = %s", (lrn,))
                    existing = cursor.fetchone()
                    
                    if existing:
                        student_id = existing['student_id']
                        print(f"  Found existing student: ID {student_id}")
                    else:
                        # If still no student, skip
                        errors.append(f"Could not create/find student {lrn}: {str(e)}")
                        continue
                
                # STEP 2: Check if already registered for this quiz
                cursor.execute("""
                    SELECT attempt_id FROM student_quiz_attempts 
                    WHERE quiz_id = %s AND student_id = %s
                """, (quiz_id, student_id))
                
                if cursor.fetchone():
                    print(f"  Already registered for this quiz - skipping")
                    continue
                
                # STEP 3: Register for quiz
                cursor.execute("""
                    INSERT INTO student_quiz_attempts 
                    (quiz_id, student_id, attempt_status, attempt_number, started_at)
                    VALUES (%s, %s, 'not_started', 1, NULL)
                """, (quiz_id, student_id))
                
                registered_count += 1
                print(f"  ✅ Registered successfully!")
                
            except Exception as e:
                error_msg = f"Error with {student.get('lrn', 'unknown')}: {str(e)}"
                print(f"  ❌ {error_msg}")
                errors.append(error_msg)
        
        # 6. COMMIT
        connection.commit()
        
        # 7. Verify
        cursor.execute("SELECT COUNT(*) as count FROM student_quiz_attempts WHERE quiz_id = %s", (quiz_id,))
        total_count = cursor.fetchone()['count']
        
        cursor.close()
        connection.close()
        
        print(f"\nRESULTS:")
        print(f"  Registered: {registered_count}")
        print(f"  Errors: {len(errors)}")
        print(f"  Total in DB: {total_count}")
        print("="*60)
        
        response = {
            'success': True,
            'registered_count': registered_count,
            'database_count': total_count,
            'message': f'Successfully registered {registered_count} student(s)'
        }
        
        if errors:
            response['errors'] = errors[:10]  # First 10 errors only
        
        return jsonify(response)
        
    except Exception as e:
        print(f"\n🔥 CRITICAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500
    
    
#========================================
# new export report
#========================================

@app.route('/api/generate_report', methods=['POST'])
def generate_report():
    try:
        import csv
        from io import StringIO
        from flask import Response, jsonify
        from datetime import datetime
        
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
            
        quiz_id = data.get('quiz_id')
        filters = data.get('filters', {})
        
        print(f"DEBUG: Starting report generation for quiz_id: {quiz_id}")
        print(f"DEBUG: Filters: {filters}")
        
        if not quiz_id:
            return jsonify({'success': False, 'message': 'Quiz ID is required'}), 400
        
        # Get sort parameters
        sort_field = filters.get('sort_field', 'last_name')  # Default to last_name
        sort_order = filters.get('sort_order', 'asc')  # Default to ascending
        
        # Map sort field to database column
        sort_field_map = {
            'last_name': 's.last_name',
            'first_name': 's.first_name',
            'score': 'sqa.score',
            'lrn': 's.lrn',
            'section': 's.section',
            'grade_level': 's.grade_level',
            'attempt_number': 'sqa.attempt_number'
        }
        
        # Validate and get sort field
        db_sort_field = sort_field_map.get(sort_field, 's.last_name')
        
        # Validate sort order
        if sort_order.lower() not in ['asc', 'desc']:
            sort_order = 'asc'
        
        # Get database connection
        connection = get_db_connection()
        if not connection:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = connection.cursor(dictionary=True)
        
        # Build query with sorting
        query = f"""
            SELECT 
                s.lrn,
                s.first_name,
                s.last_name,
                s.grade_level,
                s.section,
                sqa.attempt_number,
                sqa.attempt_status,
                sqa.score,
                sqa.raw_score,
                sqa.total_points,
                sqa.time_taken_seconds,
                sqa.completed_at,
                sqa.started_at
            FROM students s
            INNER JOIN student_quiz_attempts sqa ON s.student_id = sqa.student_id
            WHERE sqa.quiz_id = %s
            ORDER BY {db_sort_field} {sort_order.upper()}, s.last_name ASC, s.first_name ASC
        """
        
        print(f"DEBUG: Query with sorting: {query}")
        print(f"DEBUG: Sorting by: {db_sort_field} {sort_order.upper()}")
        
        try:
            cursor.execute(query, (quiz_id,))
            students_data = cursor.fetchall()
            print(f"DEBUG: Successfully retrieved {len(students_data)} records")
        except Exception as db_error:
            print(f"DEBUG: Database error: {str(db_error)}")
            cursor.close()
            connection.close()
            return jsonify({'success': False, 'message': f'Database error: {str(db_error)}'}), 500
        
        # Get quiz info
        try:
            cursor.execute("""
                SELECT q.*, s.section_name, sub.subject_name
                FROM quizzes q
                LEFT JOIN sections s ON q.section_id = s.section_id
                LEFT JOIN subjects sub ON q.subject_id = sub.subject_id
                WHERE q.quiz_id = %s
            """, (quiz_id,))
            quiz = cursor.fetchone()
        except Exception as db_error:
            print(f"DEBUG: Quiz query error: {str(db_error)}")
            quiz = None
        
        cursor.close()
        connection.close()
        
        if not quiz:
            print(f"DEBUG: Quiz {quiz_id} not found")
            return jsonify({'success': False, 'message': 'Quiz not found'}), 404
        
        # Create CSV in memory
        output = StringIO()
        writer = csv.writer(output)
        
        # Write report header with sort info
        writer.writerow(['QUIZ REPORT'])
        writer.writerow([f'Quiz Title: {quiz.get("quiz_title", "N/A")}'])
        writer.writerow([f'Subject: {quiz.get("subject_name", "N/A")}'])
        writer.writerow([f'Section: {quiz.get("section_name", "N/A")}'])
        writer.writerow([f'Grade Level: Grade {quiz.get("grade_level", "N/A")}'])
        writer.writerow([f'Sorted By: {sort_field.replace("_", " ").title()} ({sort_order.upper()})'])
        writer.writerow([f'Report Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'])
        writer.writerow([])  # Empty row
        
        # Write headers
        headers = [
            'LRN', 'First Name', 'Last Name', 'Grade Level', 'Section',
            'Attempt Number', 'Status', 'Score (%)', 'Raw Score', 'Total Points',
            'Time Taken (seconds)', 'Started At', 'Completed At'
        ]
        writer.writerow(headers)
        
        # Write data rows - they're already sorted from the query
        for student in students_data:
            # Format status for display
            status = student.get('attempt_status', 'not_started')
            status_display = status.upper().replace('_', ' ')
            
            # Format score
            score = student.get('score')
            score_display = f"{score:.2f}%" if score is not None else 'N/A'
            
            # Format dates
            started_at = student.get('started_at')
            completed_at = student.get('completed_at')
            
            if started_at:
                if isinstance(started_at, datetime):
                    started_display = started_at.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    started_display = str(started_at)
            else:
                started_display = ''
                
            if completed_at:
                if isinstance(completed_at, datetime):
                    completed_display = completed_at.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    completed_display = str(completed_at)
            else:
                completed_display = ''
            
            row = [
                student.get('lrn', ''),
                student.get('first_name', ''),
                student.get('last_name', ''),
                student.get('grade_level', ''),
                student.get('section', ''),
                student.get('attempt_number', 1),
                status_display,
                score_display,
                student.get('raw_score', 0),
                student.get('total_points', 0),
                student.get('time_taken_seconds', 0),
                started_display,
                completed_display
            ]
            writer.writerow(row)
        
        # Add summary rows
        writer.writerow([])  # Empty row
        writer.writerow(['Quiz Summary'])
        writer.writerow(['Quiz Title:', quiz.get('quiz_title', 'N/A')])
        writer.writerow(['Subject:', quiz.get('subject_name', 'N/A')])
        writer.writerow(['Section:', quiz.get('section_name', 'N/A')])
        writer.writerow(['Grade Level:', quiz.get('grade_level', 'N/A')])
        writer.writerow(['Total Students:', len(students_data)])
        
        # Calculate statistics
        if students_data:
            completed = [s for s in students_data if s.get('attempt_status') == 'completed']
            scores = [s.get('score') for s in completed if s.get('score') is not None]
            
            if scores:
                writer.writerow(['Completed Students:', len(completed)])
                writer.writerow(['Average Score:', f"{sum(scores)/len(scores):.2f}%"])
                writer.writerow(['Highest Score:', f"{max(scores):.2f}%"])
                writer.writerow(['Lowest Score:', f"{min(scores):.2f}%"])
                writer.writerow(['Sort Order:', f"Sorted by {sort_field.replace('_', ' ')} ({sort_order})"])
        
        # Prepare response
        output.seek(0)
        csv_data = output.getvalue()
        
        # Create filename with sort info
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"quiz_report_{quiz_id}_sorted_by_{sort_field}_{timestamp}.csv"
        
        print(f"DEBUG: Report generated successfully, size: {len(csv_data)} bytes")
        print(f"DEBUG: File will be: {filename}")
        
        return Response(
            csv_data,
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
                'Content-Type': 'text/csv; charset=utf-8'
            }
        )
        
    except Exception as e:
        print(f"ERROR in generate_report: {str(e)}")
        import traceback
        traceback.print_exc()  # This will show the exact line of error
        return jsonify({'success': False, 'message': f'Report generation failed: {str(e)}'}), 500
    
    
    
@app.route('/api/generate_report_simple', methods=['POST'])
def generate_report_simple():
    """Super simple report that WILL work"""
    try:
        import csv
        from io import StringIO
        from flask import Response, jsonify
        
        print("=" * 60)
        print("SIMPLE REPORT: Starting")
        
        # Get quiz_id
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data'}), 400
        
        quiz_id = data.get('quiz_id')
        print(f"SIMPLE REPORT: Quiz ID: {quiz_id}")
        
        if not quiz_id:
            return jsonify({'success': False, 'message': 'Need quiz_id'}), 400
        
        # Connect to database
        connection = get_db_connection()
        if not connection:
            return jsonify({'success': False, 'message': 'DB connection failed'}), 500
        
        cursor = connection.cursor(dictionary=True)
        
        # SIMPLE QUERY WITH SORTING BY LAST NAME
        simple_query = """
            SELECT s.*, sqa.* 
            FROM students s
            INNER JOIN student_quiz_attempts sqa ON s.student_id = sqa.student_id
            WHERE sqa.quiz_id = %s
            ORDER BY s.last_name ASC, s.first_name ASC
        """
        print(f"SIMPLE REPORT: Executing: {simple_query}")
        print(f"SIMPLE REPORT: With param: ({quiz_id},)")
        
        cursor.execute(simple_query, (quiz_id,))
        results = cursor.fetchall()
        
        print(f"SIMPLE REPORT: Got {len(results)} rows")
        
        cursor.close()
        connection.close()
        
        # Create CSV
        output = StringIO()
        writer = csv.writer(output)
        
        if results:
            # Write headers
            headers = [
                'LRN', 'First Name', 'Last Name', 'Section', 'Grade Level',
                'Attempt Number', 'Status', 'Score', 'Raw Score', 'Total Points',
                'Time Taken', 'Started At', 'Completed At'
            ]
            writer.writerow(headers)
            
            # Write data (already sorted from query)
            for row in results:
                writer.writerow([
                    row.get('lrn', ''),
                    row.get('first_name', ''),
                    row.get('last_name', ''),
                    row.get('section', ''),
                    row.get('grade_level', ''),
                    row.get('attempt_number', 1),
                    row.get('attempt_status', 'not_started'),
                    f"{row.get('score', 0):.2f}%" if row.get('score') else 'N/A',
                    row.get('raw_score', 0),
                    row.get('total_points', 0),
                    row.get('time_taken_seconds', 0),
                    row.get('started_at', ''),
                    row.get('completed_at', '')
                ])
        else:
            writer.writerow(['No data found for quiz', quiz_id])
        
        output.seek(0)
        
        # Create filename with timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"quiz_report_{quiz_id}_{timestamp}.csv"
        
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename="{filename}"'}
        )
        
    except Exception as e:
        print(f"SIMPLE REPORT ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Simple report failed: {str(e)}'}), 500
    
    
def generate_empty_report(quiz):
    """Generate an empty report when no student data exists"""
    try:
        import pandas as pd
        from io import BytesIO
        from flask import send_file
        from datetime import datetime
        
        # Create empty DataFrame
        df = pd.DataFrame(columns=[
            'lrn', 'first_name', 'last_name', 'grade_level', 'section',
            'attempt_number', 'attempt_status', 'raw_score', 'total_points',
            'score', 'time_taken_minutes', 'time_taken_seconds',
            'started_at', 'completed_at'
        ])
        
        # Create Excel file
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Write empty student data
            df.to_excel(writer, sheet_name='Student Results', index=False)
            
            # Create summary sheet
            summary_data = {
                'Quiz Title': quiz.get('quiz_title', 'N/A'),
                'Subject': quiz.get('subject_name', 'N/A'),
                'Section': quiz.get('section_name', 'N/A'),
                'Grade Level': f"Grade {quiz.get('grade_level', 'N/A')}",
                'Total Students': 0,
                'Completed Students': 0,
                'Average Score': 'N/A',
                'Highest Score': 'N/A',
                'Lowest Score': 'N/A',
                'Note': 'No student data available for this quiz'
            }
            
            summary_df = pd.DataFrame(list(summary_data.items()), columns=['Metric', 'Value'])
            summary_df.to_excel(writer, sheet_name='Quiz Summary', index=False)
        
        output.seek(0)
        
        filename = f"quiz_report_{quiz.get('quiz_id', 'empty')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        print(f"DEBUG: Empty report generation error - {str(e)}")
        # Fallback to error response
        return jsonify({'success': False, 'message': 'No student data available for this quiz'}), 404

def generate_csv_file(quiz, students, stats):
    """Generate CSV file"""
    try:
        output = StringIO()
        writer = csv.writer(output)
        
        # Quiz Information
        writer.writerow(['QUIZ REPORT'])
        writer.writerow([f'Quiz Title: {quiz.get("quiz_title", "N/A")}'])
        writer.writerow([f'Subject: {quiz.get("subject_name", "N/A")}'])
        writer.writerow([f'Section: {quiz.get("section_name", "N/A")}'])
        writer.writerow([f'Grade Level: {quiz.get("grade_level", "N/A")}'])
        writer.writerow([f'Date Created: {quiz.get("date_created", "N/A")}'])
        writer.writerow([f'Report Generated: {stats["generated_at"]}'])
        writer.writerow([])
        
        # Statistics
        writer.writerow(['STATISTICS'])
        writer.writerow(['Total Students', stats['total_students']])
        writer.writerow(['Completed', stats['completed']])
        writer.writerow(['In Progress', stats['in_progress']])
        writer.writerow(['Absent', stats['absent']])
        writer.writerow(['Completion Rate', f"{stats['completion_rate']}%"])
        writer.writerow(['Average Score', f"{stats['average_score']}%"])
        writer.writerow([])
        
        # Student Data Header
        writer.writerow(['STUDENT LIST'])
        writer.writerow(['LRN', 'Name', 'Grade', 'Section', 'Status', 'Score %', 'Raw Score', 'Time Taken', 'Started At', 'Completed At'])
        
        # Student Data Rows
        for student in students:
            # Format time taken
            time_taken = format_report_time(student.get('time_taken_seconds'))
            
            # Format score
            score = student.get('score', '')
            if score is None:
                score_display = 'N/A'
            else:
                score_display = f"{score}%"
            
            # Raw score
            raw_score = student.get('raw_score', 0) or 0
            total_points = student.get('total_points', 0) or 0
            raw_score_display = f"{raw_score}/{total_points}"
            
            writer.writerow([
                student.get('lrn', 'N/A'),
                f"{student.get('first_name', '')} {student.get('last_name', '')}".strip(),
                student.get('grade_level', 'N/A'),
                student.get('section', 'N/A'),
                student.get('attendance_status', 'Unknown'),
                score_display,
                raw_score_display,
                time_taken,
                student.get('started_at', 'N/A'),
                student.get('completed_at', 'N/A')
            ])
        
        # Create response
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv; charset=utf-8'
        response.headers['Content-Disposition'] = f'attachment; filename=quiz_report_{quiz["quiz_id"]}.csv'
        return response
        
    except Exception as e:
        raise Exception(f"CSV generation failed: {str(e)}")
    
    
@app.route('/api/generate_excel_report', methods=['POST'])
def generate_excel_report():
    try:
        import pandas as pd
        from io import BytesIO
        from flask import send_file, jsonify
        from datetime import datetime
        
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
            
        quiz_id = data.get('quiz_id')
        filters = data.get('filters', {})
        
        print(f"DEBUG: Starting Excel report generation for quiz_id: {quiz_id}")
        
        if not quiz_id:
            return jsonify({'success': False, 'message': 'Quiz ID is required'}), 400
        
        # Get database connection
        connection = get_db_connection()
        if not connection:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = connection.cursor(dictionary=True)
        
        # Get student data with sorting
        sort_field = filters.get('sort_field', 'last_name')
        sort_order = filters.get('sort_order', 'asc')
        
        # Map sort field to database column
        sort_field_map = {
            'last_name': 's.last_name',
            'first_name': 's.first_name',
            'score': 'sqa.score',
            'lrn': 's.lrn',
            'section': 's.section',
            'grade_level': 's.grade_level',
            'attempt_number': 'sqa.attempt_number'
        }
        
        db_sort_field = sort_field_map.get(sort_field, 's.last_name')
        db_sort_order = 'ASC' if sort_order.lower() == 'asc' else 'DESC'
        
        query = f"""
            SELECT 
                s.lrn,
                s.last_name,
                s.first_name,
                s.grade_level,
                s.section,
                sqa.attempt_number,
                sqa.attempt_status,
                sqa.score,
                sqa.raw_score,
                sqa.total_points,
                sqa.time_taken_seconds,
                sqa.started_at,
                sqa.completed_at
            FROM students s
            INNER JOIN student_quiz_attempts sqa ON s.student_id = sqa.student_id
            WHERE sqa.quiz_id = %s
            ORDER BY {db_sort_field} {db_sort_order}, s.last_name ASC, s.first_name ASC
        """
        
        print(f"DEBUG: Excel query: {query}")
        
        cursor.execute(query, (quiz_id,))
        students_data = cursor.fetchall()
        
        # Get quiz info
        cursor.execute("""
            SELECT q.*, s.section_name, sub.subject_name
            FROM quizzes q
            LEFT JOIN sections s ON q.section_id = s.section_id
            LEFT JOIN subjects sub ON q.subject_id = sub.subject_id
            WHERE q.quiz_id = %s
        """, (quiz_id,))
        quiz = cursor.fetchone()
        
        cursor.close()
        connection.close()
        
        if not quiz:
            return jsonify({'success': False, 'message': 'Quiz not found'}), 404
        
        # Create DataFrame with specified column order
        if students_data:
            # Prepare data for Excel
            excel_data = []
            for student in students_data:
                # Format status
                status = student.get('attempt_status', 'not_started')
                status_display = status.upper().replace('_', ' ')
                
                # Format time taken
                time_seconds = student.get('time_taken_seconds', 0)
                if time_seconds:
                    minutes = time_seconds // 60
                    seconds = time_seconds % 60
                    time_taken = f"{minutes}:{seconds:02d}"
                else:
                    time_taken = "N/A"
                
                # Format dates
                started_at = student.get('started_at')
                completed_at = student.get('completed_at')
                
                started_at_display = started_at.strftime('%Y-%m-%d %H:%M:%S') if started_at else ''
                completed_at_display = completed_at.strftime('%Y-%m-%d %H:%M:%S') if completed_at else ''
                
                # Format score
                score = student.get('score')
                score_display = f"{score:.2f}%" if score is not None else 'N/A'
                
                excel_data.append({
                    'LRN': student.get('lrn', ''),
                    'Last Name': student.get('last_name', ''),
                    'First Name': student.get('first_name', ''),
                    'Grade Level': student.get('grade_level', ''),
                    'Section': student.get('section', ''),
                    'Attempt': student.get('attempt_number', 1),
                    'Status': status_display,
                    'Score': score_display,
                    'Raw Score': student.get('raw_score', 0),
                    'Total Points': student.get('total_points', 0),
                    'Time Taken': time_taken,
                    'Started At': started_at_display,
                    'Completed At': completed_at_display
                })
            
            df = pd.DataFrame(excel_data)
        else:
            # Create empty DataFrame with correct columns
            df = pd.DataFrame(columns=[
                'LRN', 'Last Name', 'First Name', 'Grade Level', 'Section',
                'Attempt', 'Status', 'Score', 'Raw Score', 'Total Points',
                'Time Taken', 'Started At', 'Completed At'
            ])
        
        # Create Excel file in memory
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Write student data
            df.to_excel(writer, sheet_name='Student Results', index=False)
            
            # Create summary sheet
            summary_data = []
            summary_data.append(['Quiz Report Summary'])
            summary_data.append([''])
            summary_data.append(['Quiz Title:', quiz.get('quiz_title', 'N/A')])
            summary_data.append(['Subject:', quiz.get('subject_name', 'N/A')])
            summary_data.append(['Section:', quiz.get('section_name', 'N/A')])
            summary_data.append(['Grade Level:', quiz.get('grade_level', 'N/A')])
            summary_data.append(['Total Students:', len(students_data)])
            summary_data.append(['Report Generated:', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
            summary_data.append(['Sorted By:', f"{sort_field.replace('_', ' ').title()} ({sort_order.upper()})"])
            summary_data.append([''])
            
            # Add statistics if there are students
            if students_data:
                completed = [s for s in students_data if s.get('attempt_status') == 'completed']
                scores = [s.get('score') for s in completed if s.get('score') is not None]
                
                summary_data.append(['Statistics:'])
                summary_data.append(['Completed Students:', len(completed)])
                
                if scores:
                    summary_data.append(['Average Score:', f"{sum(scores)/len(scores):.2f}%"])
                    summary_data.append(['Highest Score:', f"{max(scores):.2f}%"])
                    summary_data.append(['Lowest Score:', f"{min(scores):.2f}%"])
            
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Quiz Summary', index=False, header=False)
        
        output.seek(0)
        
        # Create filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"quiz_report_{quiz_id}_{timestamp}.xlsx"
        
        print(f"DEBUG: Excel report generated successfully")
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        print(f"ERROR in generate_excel_report: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Excel report generation failed: {str(e)}'}), 500


def generate_excel_file(quiz, students, stats):
    """Generate Excel file"""
    try:
        # Try to import openpyxl
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
        except ImportError:
            return jsonify({
                'success': False, 
                'message': 'Excel generation requires openpyxl library. Install with: pip install openpyxl'
            }), 500
        
        wb = Workbook()
        ws = wb.active
        ws.title = "Quiz Report"
        
        # Define styles
        header_font = Font(bold=True, color="FFFFFF", size=12)
        header_fill = PatternFill(start_color="1a3c34", end_color="1a3c34", fill_type="solid")
        title_font = Font(bold=True, size=14)
        center_alignment = Alignment(horizontal="center", vertical="center")
        left_alignment = Alignment(horizontal="left", vertical="center")
        
        # Write quiz information
        ws.append(['QUIZ REPORT'])
        ws.merge_cells('A1:J1')
        ws['A1'].font = title_font
        ws['A1'].alignment = center_alignment
        
        ws.append([f'Quiz Title: {quiz.get("quiz_title", "N/A")}'])
        ws.merge_cells('A2:J2')
        
        ws.append([f'Subject: {quiz.get("subject_name", "N/A")}'])
        ws.merge_cells('A3:J3')
        
        ws.append([f'Section: {quiz.get("section_name", "N/A")}'])
        ws.merge_cells('A4:J4')
        
        ws.append([f'Grade Level: {quiz.get("grade_level", "N/A")}'])
        ws.merge_cells('A5:J5')
        
        ws.append([f'Report Generated: {stats["generated_at"]}'])
        ws.merge_cells('A6:J6')
        
        ws.append([])  # Empty row
        
        # Write statistics header
        ws.append(['STATISTICS'])
        ws.merge_cells('A8:J8')
        ws['A8'].font = Font(bold=True, size=12)
        
        # Write statistics data
        ws.append(['Total Students', stats['total_students']])
        ws.append(['Completed', stats['completed']])
        ws.append(['In Progress', stats['in_progress']])
        ws.append(['Absent', stats['absent']])
        ws.append(['Completion Rate', f"{stats['completion_rate']}%"])
        ws.append(['Average Score', f"{stats['average_score']}%"])
        
        ws.append([])  # Empty row
        
        # Write student data header
        headers = ['LRN', 'Name', 'Grade', 'Section', 'Status', 'Score %', 'Raw Score', 'Time Taken', 'Started At', 'Completed At']
        ws.append(headers)
        
        # Apply styles to header row
        header_row = ws.max_row
        for col in range(1, len(headers) + 1):
            cell = ws.cell(row=header_row, column=col)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = center_alignment
        
        # Write student data
        for student in students:
            # Format time taken
            time_taken = format_report_time(student.get('time_taken_seconds'))
            
            # Format score
            score = student.get('score', '')
            if score is None:
                score_display = 'N/A'
            else:
                score_display = f"{score}%"
            
            # Raw score
            raw_score = student.get('raw_score', 0) or 0
            total_points = student.get('total_points', 0) or 0
            raw_score_display = f"{raw_score}/{total_points}"
            
            row = [
                student.get('lrn', 'N/A'),
                f"{student.get('first_name', '')} {student.get('last_name', '')}".strip(),
                student.get('grade_level', 'N/A'),
                student.get('section', 'N/A'),
                student.get('attendance_status', 'Unknown'),
                score_display,
                raw_score_display,
                time_taken,
                student.get('started_at', 'N/A'),
                student.get('completed_at', 'N/A')
            ]
            ws.append(row)
            
            # Color code status
            status_cell = ws.cell(row=ws.max_row, column=5)
            status = student.get('attendance_status', 'Unknown')
            if status == 'Present':
                status_cell.fill = PatternFill(start_color="d4edda", end_color="d4edda", fill_type="solid")
            elif status == 'Absent':
                status_cell.fill = PatternFill(start_color="f8d7da", end_color="f8d7da", fill_type="solid")
            elif status == 'In Progress':
                status_cell.fill = PatternFill(start_color="fff3cd", end_color="fff3cd", fill_type="solid")
        
        # Auto-adjust column widths
        for column in ws.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    cell_value = str(cell.value) if cell.value else ""
                    if len(cell_value) > max_length:
                        max_length = len(cell_value)
                except:
                    pass
            adjusted_width = min(max_length + 2, 30)
            ws.column_dimensions[column_letter].width = adjusted_width
        
        # Save to bytes
        excel_file = BytesIO()
        wb.save(excel_file)
        excel_file.seek(0)
        
        response = make_response(excel_file.read())
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response.headers['Content-Disposition'] = f'attachment; filename=quiz_report_{quiz["quiz_id"]}.xlsx'
        return response
        
    except Exception as e:
        raise Exception(f"Excel generation failed: {str(e)}")


def format_report_time(seconds):
    """Format seconds to MM:SS for reports"""
    if not seconds:
        return "N/A"
    try:
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes}:{seconds:02d}"
    except:
        return "N/A"


# Optional: Simple endpoint for direct download without POST
@app.route('/api/download_report/<int:quiz_id>', methods=['GET'])
def download_report(quiz_id):
    """Direct download endpoint for reports"""
    try:
        format_type = request.args.get('format', 'excel')
        
        # Create a simple JSON request
        data = {
            'quiz_id': quiz_id,
            'format': format_type,
            'filters': {
                'include_students': 'all',
                'sort_by': 'name_asc'
            }
        }
        
        # Set the JSON data in request
        import json
        request._cached_data = json.dumps(data).encode('utf-8')
        
        # Call the main generate_report function
        return generate_report()
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error downloading report: {str(e)}'}), 500
    
    
   
    
@app.route('/api/add_students_simple', methods=['POST'])
def add_students_simple():
    """SUPER SIMPLE - FIXED VERSION"""
    print("\n" + "="*60)
    print("ADD_STUDENTS_SIMPLE - FIXED VERSION")
    print("="*60)
    
    try:
        # 1. Get data
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data received'}), 400
        
        quiz_id = data.get('quiz_id')
        students = data.get('students', [])
        
        print(f"Quiz ID: {quiz_id}")
        print(f"Students count: {len(students)}")
        
        if not quiz_id:
            return jsonify({'success': False, 'message': 'No quiz ID'}), 400
        
        if not students:
            return jsonify({'success': False, 'message': 'No students'}), 400
        
        # 2. Connect to database
        connection = get_db_connection()
        if not connection:
            return jsonify({'success': False, 'message': 'Database error'}), 500
        
        print("Database connected")
        
        cursor = connection.cursor(dictionary=True)
        
        # 3. Check quiz exists
        cursor.execute("SELECT quiz_id FROM quizzes WHERE quiz_id = %s", (quiz_id,))
        quiz = cursor.fetchone()
        
        if not quiz:
            cursor.close()
            connection.close()
            return jsonify({'success': False, 'message': 'Quiz not found'}), 404
        
        print(f"Quiz exists: {quiz_id}")
        
        added_count = 0
        errors = []
        
        # 4. Process each student
        for student_data in students:
            try:
                lrn = str(student_data.get('lrn', '')).strip()
                first_name = student_data.get('first_name', '').strip()
                last_name = student_data.get('last_name', '').strip()
                section = student_data.get('section', 'Default').strip()
                grade_level = int(student_data.get('grade_level', 7))
                
                print(f"Processing: {lrn} - {first_name} {last_name}")
                
                # Skip if missing data
                if not lrn or not first_name or not last_name:
                    errors.append(f"Missing data: {lrn}")
                    continue
                
                # A. INSERT OR GET STUDENT
                try:
                    # Try to insert
                    cursor.execute("""
                        INSERT INTO students (lrn, first_name, last_name, grade_level, section, enrollment_status)
                        VALUES (%s, %s, %s, %s, %s, 'active')
                    """, (lrn, first_name, last_name, grade_level, section))
                    student_id = cursor.lastrowid
                    print(f"  New student created: {student_id}")
                except:
                    # Student exists - get ID
                    cursor.execute("SELECT student_id FROM students WHERE lrn = %s", (lrn,))
                    student = cursor.fetchone()
                    if student:
                        student_id = student['student_id']
                        print(f"  Existing student: {student_id}")
                    else:
                        errors.append(f"Could not find/create: {lrn}")
                        continue
                
                # B. CHECK IF ALREADY REGISTERED
                cursor.execute("""
                    SELECT attempt_id FROM student_quiz_attempts 
                    WHERE quiz_id = %s AND student_id = %s
                """, (quiz_id, student_id))
                
                if cursor.fetchone():
                    print(f"  Already registered")
                    continue
                
                # C. REGISTER FOR QUIZ
                cursor.execute("""
                    INSERT INTO student_quiz_attempts (quiz_id, student_id, attempt_status, attempt_number)
                    VALUES (%s, %s, 'not_started', 1)
                """, (quiz_id, student_id))
                
                added_count += 1
                print(f"  Registered successfully")  # REMOVED EMOJI
                
            except Exception as e:
                error_msg = f"Error with {lrn}: {str(e)}"
                print(f"  {error_msg}")
                errors.append(error_msg)
        
        # 5. COMMIT
        connection.commit()
        
        # 6. VERIFY
        cursor.execute("SELECT COUNT(*) as total FROM student_quiz_attempts WHERE quiz_id = %s", (quiz_id,))
        total = cursor.fetchone()['total']
        
        cursor.close()
        connection.close()
        
        print(f"\nResults: Added {added_count}, Total: {total}")
        if errors:
            print(f"Errors: {len(errors)}")
        print("="*60)
        
        return jsonify({
            'success': True,
            'added_count': added_count,
            'total_count': total,
            'errors': errors[:5] if errors else [],
            'message': f'Successfully added {added_count} student(s)'
        })
        
    except Exception as e:
        print(f"\nERROR: {str(e)}")
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500
        
    
@app.route('/api/check_db', methods=['GET'])
def check_db():
    """Check if database is working"""
    print("\n=== CHECKING DATABASE ===")
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'message': 'NO DATABASE CONNECTION'}), 500
    
    cursor = connection.cursor(dictionary=True)
    
    try:
        # Check students table
        cursor.execute("SELECT COUNT(*) as count FROM students")
        students_count = cursor.fetchone()['count']
        
        # Check attempts table
        cursor.execute("SELECT COUNT(*) as count FROM student_quiz_attempts")
        attempts_count = cursor.fetchone()['count']
        
        # Check quizzes table
        cursor.execute("SELECT quiz_id, quiz_title FROM quizzes LIMIT 5")
        quizzes = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        return jsonify({
            'success': True,
            'database': 'CONNECTED',
            'students_count': students_count,
            'attempts_count': attempts_count,
            'quizzes': quizzes,
            'message': 'Database is working'
        })
        
    except Exception as e:
        cursor.close()
        connection.close()
        return jsonify({'success': False, 'message': str(e)}), 500



app.route('/api/check_quiz_students/<int:quiz_id>', methods=['GET'])
def check_quiz_students(quiz_id):
    """Check which students are registered for a quiz"""
    print(f"\nChecking students for quiz {quiz_id}")
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'message': 'DB error'}), 500
    
    cursor = connection.cursor(dictionary=True)
    
    try:
        cursor.execute("""
            SELECT s.lrn, s.first_name, s.last_name, s.section,
                   sqa.attempt_id, sqa.attempt_status
            FROM students s
            JOIN student_quiz_attempts sqa ON s.student_id = sqa.student_id
            WHERE sqa.quiz_id = %s
            ORDER BY s.last_name
        """, (quiz_id,))
        
        students = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        return jsonify({
            'success': True,
            'quiz_id': quiz_id,
            'student_count': len(students),
            'students': students
        })
        
    except Exception as e:
        cursor.close()
        connection.close()
        return jsonify({'success': False, 'message': str(e)}), 500

#=========================================


@app.route("/api/get_deleted_quizzes")
def get_deleted_quizzes():
    """Get quizzes in TRASH BIN (is_deleted=1)"""
    if "username" not in session:
        return jsonify({"success": False, "message": "Not authenticated"}), 401
    
    conn = get_db_connection()
    if not conn:
        return jsonify({"success": False, "message": "Database connection failed"})

    try:
        cursor = conn.cursor(dictionary=True)
        
        # Get ALL quizzes in TRASH BIN (is_deleted=1)
        cursor.execute("""
            SELECT q.*,
                   s.subject_name,
                   sec.section_name,
                   DATE_FORMAT(q.deleted_at, '%Y-%m-%d %H:%i') as formatted_deleted_at,
                   DATEDIFF(NOW(), q.deleted_at) as days_in_trash,
                   q.quiz_status,  # Include status to see if it's 'deleted' or 'archived'
                   CASE 
                     WHEN q.quiz_status = 'archived' THEN 'Archived → Trash'
                     WHEN q.quiz_status = 'deleted' THEN 'Direct to Trash'
                     ELSE 'Other'
                   END as deletion_type
            FROM quizzes q
            LEFT JOIN subjects s ON q.subject_id = s.subject_id
            LEFT JOIN sections sec ON q.section_id = sec.section_id
            WHERE q.created_by = %s 
              AND q.is_deleted = 1  # ALL items in trash
            ORDER BY q.deleted_at DESC
        """, (session.get('teacher_id', 1),))
        
        quizzes = cursor.fetchall()
        
        print(f"DEBUG: Found {len(quizzes)} quizzes in trash bin (is_deleted=1)")
        
        cursor.close()
        conn.close()

        return jsonify({"success": True, "quizzes": quizzes})

    except Exception as e:
        if conn:
            conn.close()
        return jsonify({"success": False, "message": str(e)})


@app.route("/api/delete_quiz/<int:quiz_id>", methods=["POST"])
def soft_delete_quiz(quiz_id):
    """Move quiz to trash from Session page"""
    if "username" not in session:
        return jsonify({"success": False, "message": "Not authenticated"}), 401
    
    conn = get_db_connection()
    if not conn:
        return jsonify({"success": False, "message": "Database connection failed"})

    try:
        cursor = conn.cursor()
        
        # Check if quiz exists and belongs to teacher
        cursor.execute("""
            SELECT q.quiz_id, q.quiz_title, q.quiz_status, q.is_deleted
            FROM quizzes q
            WHERE q.quiz_id = %s AND q.created_by = %s
        """, (quiz_id, session.get('teacher_id', 1)))
        
        quiz_data = cursor.fetchone()
        
        if not quiz_data:
            cursor.close()
            conn.close()
            return jsonify({"success": False, "message": "Quiz not found or you don't have permission"}), 404
        
        quiz_title = quiz_data[1]
        quiz_status = quiz_data[2]
        is_deleted = quiz_data[3]
        
        # If already deleted, just return success
        if is_deleted == 1:
            cursor.close()
            conn.close()
            return jsonify({"success": True, "message": "Quiz is already in trash bin"})
        
        print(f"DEBUG: Moving quiz to trash: {quiz_id} - {quiz_title}")
        
        # First, ensure any active sessions are ended
        cursor.execute("""
            UPDATE quiz_sessions 
            SET session_status = 'ended', ended_at = NOW()
            WHERE quiz_id = %s AND session_status IN ('active', 'paused')
        """, (quiz_id,))
        
        # Mark any in-progress attempts as completed
        cursor.execute("""
            UPDATE student_quiz_attempts
            SET attempt_status = 'completed', 
                completed_at = NOW()
            WHERE quiz_id = %s AND attempt_status = 'in_progress'
        """, (quiz_id,))
        
        # Move to trash bin
        cursor.execute("""
            UPDATE quizzes
            SET is_deleted = 1, 
                deleted_at = NOW(), 
                quiz_status = 'deleted',
                updated_at = NOW()
            WHERE quiz_id = %s
        """, (quiz_id,))
        
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            "success": True, 
            "message": f"Quiz '{quiz_title}' moved to trash bin"
        })

    except Exception as e:
        print("Error in soft_delete_quiz:", e)
        if conn:
            conn.rollback()
            conn.close()
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500
    
    
@app.route("/api/delete_quiz_permanent/<int:quiz_id>", methods=["DELETE"])
def delete_quiz_permanent(quiz_id):
    """Permanently delete EVERYTHING related to the quiz - SINGLE TEACHER SYSTEM"""
    if "username" not in session:
        return jsonify({"success": False, "message": "Not authenticated"}), 401
    
    connection = None
    cursor = None
    
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({"success": False, "message": "Database connection failed"}), 500
        
        cursor = connection.cursor(dictionary=True)
        teacher_id = session.get('teacher_id', 1)
        
        # 1. Get ALL quiz details including subject_id and section_id
        cursor.execute("""
            SELECT q.quiz_id, q.quiz_title, q.quiz_code, 
                   q.subject_id, q.section_id,
                   s.subject_name, sec.section_name
            FROM quizzes q
            LEFT JOIN subjects s ON q.subject_id = s.subject_id
            LEFT JOIN sections sec ON q.section_id = sec.section_id
            WHERE q.quiz_id = %s 
                AND q.created_by = %s 
                AND q.is_deleted = 1
        """, (quiz_id, teacher_id))
        
        quiz = cursor.fetchone()
        
        if not quiz:
            return jsonify({
                "success": False, 
                "message": "Quiz not found in trash or access denied"
            }), 404
        
        print(f"DEBUG: COMPLETE deletion of quiz {quiz_id} - '{quiz['quiz_title']}'")
        print(f"DEBUG: Subject: {quiz.get('subject_name', 'N/A')} (ID: {quiz['subject_id']})")
        print(f"DEBUG: Section: {quiz.get('section_name', 'N/A')} (ID: {quiz['section_id']})")
        
        # Store IDs for complete cleanup
        subject_id = quiz['subject_id']
        section_id = quiz['section_id']
        
        # 2. Get ALL students who attempted this quiz
        cursor.execute("""
            SELECT DISTINCT sqa.student_id 
            FROM student_quiz_attempts sqa
            WHERE sqa.quiz_id = %s
        """, (quiz_id,))
        quiz_student_ids = [row['student_id'] for row in cursor.fetchall()]
        
        print(f"DEBUG: Found {len(quiz_student_ids)} students who attempted this quiz")
        
        # 3. Get question IDs
        cursor.execute("SELECT question_id FROM quiz_questions WHERE quiz_id = %s", (quiz_id,))
        question_ids = [row['question_id'] for row in cursor.fetchall()]
        
        # 4. Temporarily disable foreign key checks for clean deletion
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        
        # 5. DELETE IN CORRECT ORDER (child to parent)
        
        # A. Delete student_answers for this quiz's questions
        if question_ids:
            placeholders = ','.join(['%s'] * len(question_ids))
            cursor.execute(f"DELETE FROM student_answers WHERE question_id IN ({placeholders})", question_ids)
            print(f"DEBUG: Deleted {cursor.rowcount} student_answers")
        
        # B. Delete question_choices
        if question_ids:
            placeholders = ','.join(['%s'] * len(question_ids))
            cursor.execute(f"DELETE FROM question_choices WHERE question_id IN ({placeholders})", question_ids)
            print(f"DEBUG: Deleted {cursor.rowcount} question_choices")
        
        # C. Delete question_answers
        if question_ids:
            placeholders = ','.join(['%s'] * len(question_ids))
            cursor.execute(f"DELETE FROM question_answers WHERE question_id IN ({placeholders})", question_ids)
            print(f"DEBUG: Deleted {cursor.rowcount} question_answers")
        
        # D. Delete quiz_questions
        cursor.execute("DELETE FROM quiz_questions WHERE quiz_id = %s", (quiz_id,))
        print(f"DEBUG: Deleted {cursor.rowcount} quiz_questions")
        
        # E. Delete student_quiz_attempts for this quiz
        cursor.execute("DELETE FROM student_quiz_attempts WHERE quiz_id = %s", (quiz_id,))
        attempts_deleted = cursor.rowcount
        print(f"DEBUG: Deleted {attempts_deleted} student_quiz_attempts")
        
        # F. Delete quiz_sessions
        cursor.execute("DELETE FROM quiz_sessions WHERE quiz_id = %s", (quiz_id,))
        print(f"DEBUG: Deleted {cursor.rowcount} quiz_sessions")
        
        # G. Try quiz_analytics
        try:
            cursor.execute("DELETE FROM quiz_analytics WHERE quiz_id = %s", (quiz_id,))
            print(f"DEBUG: Deleted {cursor.rowcount} quiz_analytics records")
        except:
            print("DEBUG: quiz_analytics table doesn't exist")
        
        # H. Delete the quiz itself
        cursor.execute("DELETE FROM quizzes WHERE quiz_id = %s", (quiz_id,))
        quiz_deleted = cursor.rowcount
        print(f"DEBUG: Deleted {quiz_deleted} quiz record")
        
        # 6. COMPLETE CLEANUP - DELETE ALL RELATED MASTER DATA
        
        cleanup_log = []
        
        # I. Delete students who ONLY attempted this quiz
        if quiz_student_ids:
            # Check which students are ONLY in this quiz (not in any other quiz)
            students_to_delete = []
            for student_id in quiz_student_ids:
                cursor.execute("""
                    SELECT COUNT(*) as quiz_count 
                    FROM student_quiz_attempts 
                    WHERE student_id = %s AND quiz_id != %s
                """, (student_id, quiz_id))
                other_quizzes = cursor.fetchone()['quiz_count']
                
                if other_quizzes == 0:
                    students_to_delete.append(student_id)
            
            # Delete the students
            if students_to_delete:
                placeholders = ','.join(['%s'] * len(students_to_delete))
                cursor.execute(f"DELETE FROM students WHERE student_id IN ({placeholders})", students_to_delete)
                cleanup_log.append(f"Deleted {len(students_to_delete)} students (quiz-only participants)")
                print(f"DEBUG: Deleted {len(students_to_delete)} students")
            else:
                cleanup_log.append("No quiz-only students to delete (students exist in other quizzes)")
        
        # J. Delete subject if ONLY used by this quiz
        if subject_id:
            cursor.execute("SELECT COUNT(*) as count FROM quizzes WHERE subject_id = %s", (subject_id,))
            subject_used = cursor.fetchone()['count']
            
            if subject_used == 0:
                cursor.execute("DELETE FROM subjects WHERE subject_id = %s", (subject_id,))
                cleanup_log.append(f"Deleted subject: {quiz.get('subject_name', 'N/A')}")
                print(f"DEBUG: Deleted subject ID {subject_id}")
            else:
                cleanup_log.append(f"Subject '{quiz.get('subject_name', 'N/A')}' preserved (used in other quizzes)")
        
        # K. Delete section if ONLY used by this quiz
        if section_id:
            cursor.execute("SELECT COUNT(*) as count FROM quizzes WHERE section_id = %s", (section_id,))
            section_used = cursor.fetchone()['count']
            
            if section_used == 0:
                cursor.execute("DELETE FROM sections WHERE section_id = %s", (section_id,))
                cleanup_log.append(f"Deleted section: {quiz.get('section_name', 'N/A')}")
                print(f"DEBUG: Deleted section ID {section_id}")
            else:
                cleanup_log.append(f"Section '{quiz.get('section_name', 'N/A')}' preserved (used in other quizzes)")
        
        # 7. Re-enable foreign key checks
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
        
        # 8. Commit everything
        connection.commit()
        
        return jsonify({
            "success": True,
            "message": f"Quiz '{quiz['quiz_title']}' and ALL related data permanently deleted",
            "deleted_items": {
                "quiz": quiz_deleted,
                "questions": len(question_ids),
                "attempts": attempts_deleted,
                "students": len(students_to_delete) if 'students_to_delete' in locals() else 0
            },
            "cleanup_log": cleanup_log,
            "note": "Complete cleanup performed for single-teacher system"
        })
        
    except Exception as e:
        print(f"ERROR in delete_quiz_permanent: {str(e)}")
        import traceback
        traceback.print_exc()
        
        if connection:
            connection.rollback()
        return jsonify({
            "success": False, 
            "message": f"Error deleting quiz: {str(e)}"
        }), 500
        
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
    

@app.route("/api/retrieve_quiz/<int:quiz_id>", methods=["POST"])
def restore_quiz(quiz_id):
    """Restore quiz from trash to session page"""
    if "username" not in session:
        return jsonify({"success": False, "message": "Not authenticated"}), 401
    
    conn = get_db_connection()
    if not conn:
        return jsonify({"success": False, "message": "Database connection failed"})

    try:
        cursor = conn.cursor()
        
        # Get current quiz status before restoring
        cursor.execute("""
            SELECT quiz_status FROM quizzes 
            WHERE quiz_id = %s AND created_by = %s AND is_deleted = 1
        """, (quiz_id, session.get('teacher_id', 1)))
        
        quiz = cursor.fetchone()
        
        if not quiz:
            return jsonify({"success": False, "message": "Quiz not found in trash"}), 404
        
        old_status = quiz[0]
        
        # If it was archived before deletion, restore as draft
        # Otherwise restore with original status
        new_status = 'draft' if old_status == 'archived' else old_status
        
        # Restore the quiz
        cursor.execute("""
            UPDATE quizzes
            SET is_deleted = 0, 
                deleted_at = NULL,
                quiz_status = %s,
                updated_at = NOW()
            WHERE quiz_id = %s
        """, (new_status, quiz_id))
        
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            "success": True, 
            "message": f"Quiz restored to session page as {new_status}"
        })

    except Exception as e:
        print("Error:", e)
        if conn:
            conn.close()
        return jsonify({"success": False, "message": str(e)})
    

@app.route("/api/archive_quiz/<int:quiz_id>", methods=["POST"])
def archive_quiz(quiz_id):
    """Archive a quiz - moves to Archive/Retrieval page"""
    if "username" not in session:
        return jsonify({"success": False, "message": "Not authenticated"}), 401
    
    connection = get_db_connection()
    if not connection:
        return jsonify({"success": False, "message": "Database connection failed"}), 500
    
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        teacher_id = session.get('teacher_id', 1)
        
        # 1. Verify quiz exists and belongs to teacher
        cursor.execute("""
            SELECT quiz_id, quiz_title, quiz_status, is_deleted 
            FROM quizzes 
            WHERE quiz_id = %s AND created_by = %s
        """, (quiz_id, teacher_id))
        
        quiz = cursor.fetchone()
        
        if not quiz:
            return jsonify({
                "success": False, 
                "message": "Quiz not found or you don't have permission"
            }), 404
        
        # 2. Check if already archived (quiz_status='archived' AND is_deleted=0)
        if quiz['quiz_status'] == 'archived' and quiz['is_deleted'] == 0:
            return jsonify({
                "success": False, 
                "message": "Quiz is already archived"
            }), 400
        
        # 3. Check if in trash (is_deleted=1)
        if quiz['is_deleted'] == 1:
            return jsonify({
                "success": False, 
                "message": "Cannot archive a quiz that's in trash. Restore it first."
            }), 400
        
        print(f"DEBUG: Archiving quiz {quiz_id} - Current status: {quiz['quiz_status']}, is_deleted: {quiz['is_deleted']}")
        
        # 4. Archive the quiz - Set status='archived' but KEEP is_deleted=0
        cursor.execute("""
            UPDATE quizzes 
            SET quiz_status = 'archived',
                updated_at = NOW()
            WHERE quiz_id = %s
        """, (quiz_id,))
        
        # 5. Also end any active sessions for this quiz
        cursor.execute("""
            UPDATE quiz_sessions 
            SET session_status = 'ended', 
                ended_at = NOW()
            WHERE quiz_id = %s AND session_status IN ('active', 'paused')
        """, (quiz_id,))
        
        connection.commit()
        
        return jsonify({
            "success": True, 
            "message": f"Quiz '{quiz['quiz_title']}' has been archived",
            "quiz_id": quiz_id,
            "quiz_title": quiz['quiz_title']
        })
        
    except Exception as e:
        if connection:
            connection.rollback()
        print(f"Error in archive_quiz: {e}")
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@app.route("/api/get_archived_quizzes")
def get_archived_quizzes():
    """Get ONLY archived quizzes (quiz_status='archived' AND is_deleted=0)"""
    if "username" not in session:
        return jsonify({"success": False, "message": "Not authenticated"}), 401
    
    connection = get_db_connection()
    if not connection:
        return jsonify({"success": False, "message": "Database connection failed"})

    try:
        cursor = connection.cursor(dictionary=True)
        teacher_id = session.get('teacher_id', 1)
        
        # Get ONLY archived quizzes (quiz_status='archived' AND is_deleted=0)
        cursor.execute("""
            SELECT 
                q.quiz_id,
                q.quiz_code,
                q.quiz_title,
                COALESCE(s.subject_name, 'No Subject') as subject_name,
                COALESCE(sec.section_name, 'No Section') as section_name,
                COALESCE(sec.grade_level, 'N/A') as grade_level,
                q.topic,
                DATE_FORMAT(q.created_at, '%Y-%m-%d') as date_created,
                q.quiz_status,
                q.duration_minutes,
                q.total_points,
                (SELECT COUNT(DISTINCT student_id) FROM student_quiz_attempts WHERE quiz_id = q.quiz_id) as student_count
            FROM quizzes q
            LEFT JOIN subjects s ON q.subject_id = s.subject_id
            LEFT JOIN sections sec ON q.section_id = sec.section_id
            WHERE q.created_by = %s 
                AND q.quiz_status = 'archived'  # MUST BE 'archived'
                AND q.is_deleted = 0  # MUST NOT BE deleted
            ORDER BY q.created_at DESC
        """, (teacher_id,))
        
        quizzes = cursor.fetchall()
        
        print(f"DEBUG: Found {len(quizzes)} archived quizzes (is_deleted=0)")
        
        cursor.close()
        connection.close()

        return jsonify({
            "success": True, 
            "quizzes": quizzes,
            "count": len(quizzes)
        })

    except Exception as e:
        print(f"Error in get_archived_quizzes: {e}")
        if connection:
            connection.close()
        return jsonify({"success": False, "message": str(e)}), 500
    
    

@app.route("/api/unarchive_quiz/<int:quiz_id>", methods=["POST"])
def unarchive_quiz(quiz_id):
    """Unarchive a quiz - restore from archive to session page"""
    if "username" not in session:
        return jsonify({"success": False, "message": "Not authenticated"}), 401
    
    conn = get_db_connection()
    if not conn:
        return jsonify({"success": False, "message": "Database connection failed"})

    try:
        cursor = conn.cursor(dictionary=True)
        teacher_id = session.get('teacher_id', 1)
        
        # 1. Verify quiz is archived and belongs to teacher
        cursor.execute("""
            SELECT quiz_id, quiz_title, quiz_status, is_deleted
            FROM quizzes 
            WHERE quiz_id = %s 
                AND created_by = %s 
                AND quiz_status = 'archived'
                AND is_deleted = 0
        """, (quiz_id, teacher_id))
        
        quiz = cursor.fetchone()
        
        if not quiz:
            return jsonify({
                "success": False,
                "message": "Quiz not found in archive or access denied"
            }), 404
        
        # 2. Check if quiz has students to determine status
        cursor.execute("""
            SELECT COUNT(*) as student_count 
            FROM student_quiz_attempts 
            WHERE quiz_id = %s
        """, (quiz_id,))
        result = cursor.fetchone()
        student_count = result['student_count'] if result else 0
        
        # 3. Determine new status based on student attempts
        new_status = 'completed' if student_count > 0 else 'draft'
        
        # 4. Unarchive the quiz
        cursor.execute("""
            UPDATE quizzes 
            SET quiz_status = %s,
                updated_at = NOW()
            WHERE quiz_id = %s
        """, (new_status, quiz_id))
        
        rows_affected = cursor.rowcount
        
        conn.commit()
        cursor.close()
        conn.close()

        if rows_affected > 0:
            return jsonify({
                "success": True, 
                "message": f"Quiz '{quiz['quiz_title']}' restored to session page as {new_status}",
                "restored_status": new_status
            })
        else:
            return jsonify({
                "success": False,
                "message": "Failed to unarchive quiz"
            }), 500

    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        print(f"Error in unarchive_quiz: {e}")
        return jsonify({"success": False, "message": str(e)}), 500
    
    
@app.route("/api/archive_to_trash/<int:quiz_id>", methods=["POST"])
def move_archive_to_trash(quiz_id):
    """Move quiz from Archive to Trash Bin"""
    if "username" not in session:
        return jsonify({"success": False, "message": "Not authenticated"}), 401
    
    connection = get_db_connection()
    if not connection:
        return jsonify({"success": False, "message": "Database connection failed"}), 500
    
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        teacher_id = session.get('teacher_id', 1)
        
        # 1. Verify quiz exists, is archived, and belongs to teacher
        cursor.execute("""
            SELECT quiz_id, quiz_title, quiz_status, is_deleted 
            FROM quizzes 
            WHERE quiz_id = %s 
                AND created_by = %s 
                AND quiz_status = 'archived'
                AND is_deleted = 0
        """, (quiz_id, teacher_id))
        
        quiz = cursor.fetchone()
        
        if not quiz:
            return jsonify({
                "success": False, 
                "message": "Quiz not found in archive or access denied"
            }), 404
        
        # 2. Move from Archive to Trash
        cursor.execute("""
            UPDATE quizzes 
            SET is_deleted = 1,
                quiz_status = 'deleted',
                deleted_at = NOW(),
                updated_at = NOW()
            WHERE quiz_id = %s
        """, (quiz_id,))
        
        connection.commit()
        
        return jsonify({
            "success": True, 
            "message": f"Quiz '{quiz['quiz_title']}' moved from archive to trash bin",
            "quiz_id": quiz_id,
            "quiz_title": quiz['quiz_title']
        })
        
    except Exception as e:
        if connection:
            connection.rollback()
        print(f"Error in move_archive_to_trash: {e}")
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
    

@app.route("/api/update_quiz_status", methods=["POST"])
def update_quiz_status():
    """Update quiz status"""
    if "username" not in session:
        return jsonify({"success": False, "message": "Not authenticated"}), 401
    
    data = request.json
    quiz_id = data.get('quiz_id')
    status = data.get('status')
    
    if not quiz_id or not status:
        return jsonify({"success": False, "message": "Missing quiz_id or status"}), 400
    
    connection = get_db_connection()
    if not connection:
        return jsonify({"success": False, "message": "Database connection failed"}), 500
    
    try:
        cursor = connection.cursor()
        cursor.execute("""
            UPDATE quizzes 
            SET quiz_status = %s 
            WHERE quiz_id = %s AND created_by = %s
        """, (status, quiz_id, session.get('teacher_id', 1)))
        
        connection.commit()
        cursor.close()
        connection.close()
        
        return jsonify({"success": True, "message": "Quiz status updated"})
    
    except Exception as e:
        if connection:
            connection.rollback()
            connection.close()
        return jsonify({"success": False, "message": str(e)}), 500
    
    
@app.route("/api/check_new_students/<int:quiz_id>", methods=["GET"])
def check_new_students(quiz_id):
    """Check for new student registrations or updates"""
    if "username" not in session:
        return jsonify({"success": False, "message": "Not authenticated"}), 401
    
    connection = get_db_connection()
    if not connection:
        return jsonify({"success": False, "message": "Database connection failed"}), 500
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Get current student count
        cursor.execute("""
            SELECT COUNT(*) as student_count 
            FROM student_quiz_attempts 
            WHERE quiz_id = %s
        """, (quiz_id,))
        result = cursor.fetchone()
        current_count = result['student_count'] if result else 0
        
        # Get previous count from session or use timestamp-based check
        session_key = f'quiz_{quiz_id}_last_check'
        last_check = session.get(session_key)
        
        # Check for new students in the last 5 seconds
        cursor.execute("""
            SELECT COUNT(*) as new_students
            FROM student_quiz_attempts 
            WHERE quiz_id = %s 
              AND started_at >= DATE_SUB(NOW(), INTERVAL 5 SECOND)
        """, (quiz_id,))
        result = cursor.fetchone()
        new_students = result['new_students'] if result else 0
        
        # Check for updated attempts (completions)
        cursor.execute("""
            SELECT COUNT(*) as updated_attempts
            FROM student_quiz_attempts 
            WHERE quiz_id = %s 
              AND completed_at >= DATE_SUB(NOW(), INTERVAL 5 SECOND)
              AND attempt_status = 'completed'
        """, (quiz_id,))
        result = cursor.fetchone()
        updated_attempts = result['updated_attempts'] if result else 0
        
        # Check for score updates
        cursor.execute("""
            SELECT COUNT(*) as updated_scores
            FROM student_quiz_attempts 
            WHERE quiz_id = %s 
              AND (updated_at >= DATE_SUB(NOW(), INTERVAL 5 SECOND) 
                   OR completed_at >= DATE_SUB(NOW(), INTERVAL 5 SECOND))
              AND score IS NOT NULL
        """, (quiz_id,))
        result = cursor.fetchone()
        updated_scores = result['updated_scores'] if result else 0
        
        cursor.close()
        connection.close()
        
        has_updates = (new_students > 0) or (updated_attempts > 0) or (updated_scores > 0)
        
        # Update session timestamp
        session[session_key] = datetime.now().isoformat()
        
        return jsonify({
            "success": True,
            "has_updates": has_updates,
            "new_students": new_students,
            "updated_attempts": updated_attempts,
            "updated_scores": updated_scores,
            "total_students": current_count
        })
        
    except Exception as e:
        if connection:
            connection.close()
        print(f"Error checking for new students: {e}")
        return jsonify({"success": False, "message": str(e)}), 500
    
    
    

@app.route("/api/get_student_updates/<int:quiz_id>", methods=["GET"])
def get_student_updates(quiz_id):
    """Get updated student data for real-time updates"""
    if "username" not in session:
        return jsonify({"success": False, "message": "Not authenticated"}), 401
    
    connection = get_db_connection()
    if not connection:
        return jsonify({"success": False, "message": "Database connection failed"}), 500
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Get all students with their latest data
        cursor.execute("""
            SELECT 
                sqa.attempt_id,
                s.student_id,
                s.lrn,
                COALESCE(s.first_name, '') as first_name,
                COALESCE(s.last_name, '') as last_name,
                s.grade_level,
                s.section,
                sqa.attempt_status, 
                sqa.score,
                sqa.raw_score,
                sqa.total_points,
                sqa.time_taken_seconds,
                sqa.started_at,
                sqa.completed_at,
                CASE 
                    WHEN sqa.started_at >= DATE_SUB(NOW(), INTERVAL 10 SECOND) THEN 1
                    ELSE 0 
                END as is_new
            FROM student_quiz_attempts sqa
            LEFT JOIN students s ON sqa.student_id = s.student_id
            WHERE sqa.quiz_id = %s
            ORDER BY sqa.started_at DESC
        """, (quiz_id,))
        
        students = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        return jsonify({
            "success": True,
            "students": students,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        if connection:
            connection.close()
        print(f"Error getting student updates: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/student/check_registration', methods=['POST'])
def check_student_registration():
    """Check if student is registered for quiz - FIXED VERSION"""
    print("\n=== CHECKING STUDENT REGISTRATION ===")
    
    try:
        data = request.get_json()
        print(f"Request data: {data}")
        
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
        
        quiz_id = data.get('quiz_id')
        lrn = data.get('lrn', '').strip()
        section = data.get('section', '').strip()
        
        print(f"Checking: Quiz {quiz_id}, LRN: {lrn}, Section: {section}")
        
        if not quiz_id or not lrn:
            return jsonify({'success': False, 'message': 'Quiz ID and LRN required'}), 400
        
        connection = get_db_connection()
        if not connection:
            return jsonify({'success': False, 'message': 'Database error'}), 500
        
        cursor = connection.cursor(dictionary=True)
        
        # 1. Get quiz info first
        cursor.execute("""
            SELECT q.*, s.section_name 
            FROM quizzes q
            LEFT JOIN sections s ON q.section_id = s.section_id
            WHERE q.quiz_id = %s
        """, (quiz_id,))
        quiz = cursor.fetchone()
        
        if not quiz:
            cursor.close()
            connection.close()
            return jsonify({'success': False, 'message': 'Quiz not found'}), 404
        
        print(f"Quiz found: {quiz.get('quiz_title')}")
        print(f"Quiz section: {quiz.get('section_name')}")
        print(f"Quiz grade: {quiz.get('grade_level')}")
        
        # 2. Check if student exists in students table (SIMPLIFIED - just check by LRN)
        cursor.execute("""
            SELECT student_id, lrn, first_name, last_name, grade_level, section 
            FROM students 
            WHERE lrn = %s
        """, (lrn,))
        student = cursor.fetchone()
        
        print(f"Student in database: {student}")
        
        if not student:
            # Student not in database at all
            cursor.close()
            connection.close()
            return jsonify({
                'success': True,
                'registered': False,
                'message': 'Student not found in database'
            })
        
        # 3. Check if student is registered for this quiz
        cursor.execute("""
            SELECT sqa.* 
            FROM student_quiz_attempts sqa
            WHERE sqa.quiz_id = %s AND sqa.student_id = %s
        """, (quiz_id, student['student_id']))
        
        attempt = cursor.fetchone()
        print(f"Quiz attempt found: {attempt}")
        
        cursor.close()
        connection.close()
        
        if attempt:
            # Student is registered
            return jsonify({
                'success': True,
                'registered': True,
                'student_id': student['student_id'],
                'lrn': student['lrn'],
                'first_name': student['first_name'],
                'last_name': student['last_name'],
                'grade_level': student['grade_level'],
                'section': student['section'],
                'attempt_status': attempt.get('attempt_status', 'not_started'),
                'attempt_id': attempt.get('attempt_id'),
                'message': 'Student registered for quiz'
            })
        else:
            # Student exists but not registered for this quiz
            return jsonify({
                'success': True,
                'registered': False,
                'message': 'Student not registered for this quiz'
            })
        
    except Exception as e:
        print(f"ERROR in check_registration: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500



@app.route("/api/check_student_changes/<int:quiz_id>", methods=["GET"])
def check_student_changes(quiz_id):
    """Check for student changes since last check - FIXED for your schema"""
    if "username" not in session:
        return jsonify({"success": False, "message": "Not authenticated"}), 401
    
    connection = get_db_connection()
    if not connection:
        return jsonify({"success": False, "message": "Database connection failed"}), 500
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Get timestamp from request or use last 5 seconds
        last_check_seconds = request.args.get('since', 5, type=int)
        
        # Check for NEW students registered in the last X seconds
        cursor.execute("""
            SELECT COUNT(*) as new_students_count
            FROM student_quiz_attempts sqa
            WHERE sqa.quiz_id = %s 
              AND sqa.started_at >= DATE_SUB(NOW(), INTERVAL %s SECOND)
        """, (quiz_id, last_check_seconds))
        
        new_students = cursor.fetchone()
        new_students_count = new_students['new_students_count'] if new_students else 0
        
        # Check for UPDATED attempts (completions)
        cursor.execute("""
            SELECT COUNT(*) as updated_attempts_count
            FROM student_quiz_attempts sqa
            WHERE sqa.quiz_id = %s 
              AND sqa.completed_at >= DATE_SUB(NOW(), INTERVAL %s SECOND)
        """, (quiz_id, last_check_seconds))
        
        updated_attempts = cursor.fetchone()
        updated_attempts_count = updated_attempts['updated_attempts_count'] if updated_attempts else 0
        
        # Get total student count
        cursor.execute("""
            SELECT COUNT(*) as total_students
            FROM student_quiz_attempts 
            WHERE quiz_id = %s
        """, (quiz_id,))
        
        total_result = cursor.fetchone()
        total_students = total_result['total_students'] if total_result else 0
        
        cursor.close()
        connection.close()
        
        has_changes = (new_students_count > 0) or (updated_attempts_count > 0)
        
        return jsonify({
            "success": True,
            "has_changes": has_changes,
            "new_students_count": new_students_count,
            "updated_attempts_count": updated_attempts_count,
            "total_students": total_students,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        if connection:
            connection.close()
        print(f"Error checking student changes: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


# ============================================
# STUDENT QUIZ ROUTES
# ============================================

@app.route("/student/quiz/<int:quiz_id>")
def student_quiz(quiz_id):
    """Student quiz taking page"""
    return render_template("student_quiz.html")

@app.route("/api/student/get_quiz/<int:quiz_id>", methods=["GET"])
def get_student_quiz(quiz_id):
    """Get quiz data for student - UPDATED: Include current quiz status"""
    connection = get_db_connection()
    if not connection:
        return jsonify({"success": False, "message": "Database connection failed"}), 500
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Get quiz info with current status
        cursor.execute("""
            SELECT 
                q.quiz_id, 
                q.quiz_title,
                q.quiz_status,  # MAKE SURE THIS IS INCLUDED
                s.subject_name,
                sec.section_name,
                sec.grade_level,
                q.topic,
                q.duration_minutes, 
                q.total_points
            FROM quizzes q
            JOIN subjects s ON q.subject_id = s.subject_id
            JOIN sections sec ON q.section_id = sec.section_id
            WHERE q.quiz_id = %s
        """, (quiz_id,))
        quiz = cursor.fetchone()
        
        if not quiz:
            cursor.close()
            connection.close()
            return jsonify({"success": False, "message": "Quiz not found"}), 404
        
        # Get questions
        cursor.execute("""
            SELECT 
                qq.question_id, 
                qq.difficulty_level, 
                qq.question_text, 
                qq.question_type, 
                qq.points
            FROM quiz_questions qq
            WHERE qq.quiz_id = %s
            ORDER BY qq.difficulty_level, qq.question_id
        """, (quiz_id,))
        questions = cursor.fetchall()
        
        # Get choices for multiple choice questions
        for question in questions:
            if question['question_type'] == 'multiple_choice':
                cursor.execute("""
                    SELECT choice_text, choice_order
                    FROM question_choices
                    WHERE question_id = %s
                    ORDER BY choice_order
                """, (question['question_id'],))
                question['choices'] = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        # Organize questions by difficulty
        organized_questions = {
            'easy': [q for q in questions if q['difficulty_level'] == 'easy'],
            'medium': [q for q in questions if q['difficulty_level'] == 'medium'],
            'hard': [q for q in questions if q['difficulty_level'] == 'hard']
        }
        
        quiz['questions'] = organized_questions
        
        return jsonify({"success": True, "quiz": quiz})
    
    except Exception as e:
        if connection:
            connection.close()
        print(f"Error getting student quiz: {e}")
        return jsonify({"success": False, "message": str(e)}), 500
    
    
@app.route('/api/student/get_quiz/<quiz_id>')
def get_quiz_for_student(quiz_id):
    """Get quiz details for students - INCLUDES correct_answer"""
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    
    try:
        # Get quiz basic info
        cursor.execute("""
            SELECT 
                q.quiz_id,
                q.quiz_title,
                q.quiz_code,
                s.subject_name,
                sec.section_name,
                q.grade_level,
                q.duration_minutes,
                q.quiz_status,
                q.topic
            FROM quizzes q
            LEFT JOIN subjects s ON q.subject_id = s.subject_id
            LEFT JOIN sections sec ON q.section_id = sec.section_id
            WHERE q.quiz_id = %s
        """, (quiz_id,))
        quiz = cursor.fetchone()
        
        if not quiz:
            return jsonify({"success": False, "message": "Quiz not found"}), 404
        
        # Get ALL questions with correct_answer
        cursor.execute("""
            SELECT 
                question_id,
                question_type,
                difficulty_level,
                question_text,
                correct_answer,  -- This is now in your table
                points
            FROM quiz_questions 
            WHERE quiz_id = %s 
            ORDER BY question_order
        """, (quiz_id,))
        questions = cursor.fetchall()
        
        # For each question, get choices if multiple choice
        for question in questions:
            if question['question_type'] == 'multiple_choice':
                cursor.execute("""
                    SELECT 
                        choice_text, 
                        is_correct,
                        choice_order
                    FROM question_choices
                    WHERE question_id = %s
                    ORDER BY choice_order
                """, (question['question_id'],))
                question['choices'] = cursor.fetchall()
        
        # Organize by difficulty for the frontend
        questions_by_difficulty = {
            'easy': [],
            'medium': [],
            'hard': []
        }
        
        for question in questions:
            level = question['difficulty_level']
            if level in questions_by_difficulty:
                questions_by_difficulty[level].append(question)
        
        # Flatten all questions for student quiz
        all_questions = []
        for level in ['easy', 'medium', 'hard']:
            all_questions.extend(questions_by_difficulty[level])
        
        return jsonify({
            "success": True,
            "quiz": {
                "quiz_id": quiz['quiz_id'],
                "quiz_title": quiz['quiz_title'],
                "quiz_code": quiz['quiz_code'],
                "subject_name": quiz['subject_name'],
                "section_name": quiz['section_name'],
                "grade_level": quiz['grade_level'],
                "duration_minutes": quiz['duration_minutes'],
                "quiz_status": quiz['quiz_status'],
                "topic": quiz['topic'],
                "questions": all_questions,  # Flat list for student
                "questions_by_level": questions_by_difficulty  # Grouped for teacher
            }
        })
        
    except Exception as e:
        print(f"Error getting quiz: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Error loading quiz: {str(e)}"
        }), 500
        
    finally:
        cursor.close()
        connection.close()



@app.route("/api/student/register", methods=["POST"])
def student_register():
    """Register student for quiz - FIXED for your schema"""
    connection = get_db_connection()
    if not connection:
        return jsonify({"success": False, "message": "Database connection failed"}), 500
    
    try:
        data = request.json
        cursor = connection.cursor(dictionary=True)
        
        print(f"DEBUG: Registration data received: {data}")
        
        # Check if quiz exists and is active
        cursor.execute("SELECT quiz_status FROM quizzes WHERE quiz_id = %s", (data['quiz_id'],))
        quiz = cursor.fetchone()
        
        if not quiz:
            cursor.close()
            connection.close()
            return jsonify({"success": False, "message": "Quiz not found"}), 404
        
        if quiz['quiz_status'] != 'active':
            cursor.close()
            connection.close()
            return jsonify({"success": False, "message": "Quiz is not active. Please wait for the teacher to start the quiz."}), 400
        
        # Check if student already exists
        cursor.execute("SELECT student_id FROM students WHERE lrn = %s", (data['student_id'],))
        existing_student = cursor.fetchone()
        
        student_id = None
        if existing_student:
            student_id = existing_student['student_id']
            print(f"DEBUG: Student already exists with ID: {student_id}")
            
            # Update existing student information
            cursor.execute("""
                UPDATE students 
                SET first_name = %s, last_name = %s, grade_level = %s, section = %s
                WHERE student_id = %s
            """, (
                data.get('first_name', ''),
                data.get('last_name', ''),
                data['grade_level'],
                data['section'],
                student_id
            ))
            print(f"DEBUG: Updated student {student_id}")
        else:
            # Create new student WITHOUT user_id
            cursor.execute("""
                INSERT INTO students (lrn, first_name, last_name, grade_level, section)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                data['student_id'],
                data.get('first_name', ''),
                data.get('last_name', ''),
                data['grade_level'],
                data['section']
            ))
            student_id = cursor.lastrowid
            print(f"DEBUG: Created new student with ID: {student_id}")
        
        # Check if student is already registered for this quiz
        cursor.execute("""
            SELECT attempt_id, started_at FROM student_quiz_attempts 
            WHERE quiz_id = %s AND student_id = %s
        """, (data['quiz_id'], student_id))
        
        existing_attempt = cursor.fetchone()
        
        if not existing_attempt:
            # Register student for quiz with current timestamp
            cursor.execute("""
                INSERT INTO student_quiz_attempts (quiz_id, student_id, attempt_status, started_at)
                VALUES (%s, %s, 'in_progress', NOW())
            """, (data['quiz_id'], student_id))
            print(f"DEBUG: Registered student {student_id} for quiz {data['quiz_id']}")
        else:
            print(f"DEBUG: Student {student_id} already registered for quiz {data['quiz_id']}")
        
        connection.commit()
        cursor.close()
        connection.close()
        
        return jsonify({"success": True, "message": "Registration successful", "student_id": student_id})
    
    except Exception as e:
        if connection:
            connection.rollback()
            connection.close()
        print(f"Error in student registration: {e}")
        return jsonify({"success": False, "message": str(e)}), 500
    


@app.route("/api/student/submit_quiz", methods=["POST"])
def student_submit_quiz():
    """Submit student quiz answers and calculate score"""
    data = request.json
    
    connection = get_db_connection()
    if not connection:
        return jsonify({"success": False, "message": "Database connection failed"}), 500
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        quiz_id = data['quiz_id']
        student_lrn = data['student_id']
        answers = data['answers']
        time_taken = data['time_taken']
        
        # Get student_id from LRN
        cursor.execute("SELECT student_id FROM students WHERE lrn = %s", (student_lrn,))
        student_result = cursor.fetchone()
        
        if not student_result:
            cursor.close()
            connection.close()
            return jsonify({"success": False, "message": "Student not found"}), 404
        
        student_id = student_result['student_id']
        
        # Get the latest attempt
        cursor.execute("""
            SELECT attempt_id FROM student_quiz_attempts 
            WHERE quiz_id = %s AND student_id = %s 
            ORDER BY started_at DESC LIMIT 1
        """, (quiz_id, student_id))
        attempt_result = cursor.fetchone()
        
        if not attempt_result:
            cursor.close()
            connection.close()
            return jsonify({"success": False, "message": "No active quiz attempt found"}), 400
        
        attempt_id = attempt_result['attempt_id']
        
        # ========== FIXED: Get questions with correct_answer from quiz_questions ==========
        questions_query = """
            SELECT 
                question_id, 
                question_type, 
                correct_answer,  # Now from quiz_questions
                points
            FROM quiz_questions 
            WHERE quiz_id = %s
        """
        cursor.execute(questions_query, (quiz_id,))
        questions = cursor.fetchall()
        
        print(f"DEBUG: Found {len(questions)} questions for quiz {quiz_id}")
        print(f"DEBUG: First question: {questions[0] if questions else 'No questions'}")
        
        total_questions = len(questions)
        correct_count = 0
        points_earned = 0
        total_points = sum(q['points'] for q in questions)
        
        # Check each answer
        for question in questions:
            q_id = str(question['question_id'])
            student_answer = str(answers.get(q_id, '')).strip()
            correct_answer = str(question['correct_answer'] or '').strip()
            
            print(f"\nDEBUG: Question {q_id}")
            print(f"  Student answer: '{student_answer}'")
            print(f"  Correct answer: '{correct_answer}'")
            print(f"  Question type: {question['question_type']}")
            
            is_correct = False
            
            # Check answer based on question type
            if question['question_type'] == 'true_false':
                is_correct = student_answer.upper() == correct_answer.upper()
            elif question['question_type'] == 'multiple_choice':
                # For multiple choice, also check if answer matches any correct choice
                cursor.execute("""
                    SELECT choice_text FROM question_choices 
                    WHERE question_id = %s AND is_correct = 1
                """, (question['question_id'],))
                correct_choices = cursor.fetchall()
                
                for choice in correct_choices:
                    if student_answer == choice['choice_text']:
                        is_correct = True
                        break
                
                # Also check direct match with correct_answer field
                if not is_correct and student_answer == correct_answer:
                    is_correct = True
                    
            elif question['question_type'] == 'text' or question['question_type'] == 'short_answer':
                is_correct = student_answer.lower() == correct_answer.lower()
            
            print(f"  Is correct: {is_correct}")
            
            if is_correct:
                correct_count += 1
                points_earned += question['points']
            
            # Save student answer
            answer_query = """
                INSERT INTO student_answers 
                (attempt_id, question_id, answer_text, is_correct, points_earned)
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(answer_query, (
                attempt_id,
                question['question_id'],
                student_answer,
                1 if is_correct else 0,
                question['points'] if is_correct else 0
            ))
        
        # Calculate percentage score
        score = round((points_earned / total_points * 100), 2) if total_points > 0 else 0
        
        # Update quiz attempt record
        update_query = """
            UPDATE student_quiz_attempts 
            SET attempt_status = 'completed',
                score = %s,
                raw_score = %s,
                total_points = %s,
                completed_at = NOW(),
                time_taken_seconds = %s
            WHERE attempt_id = %s
        """
        cursor.execute(update_query, (
            score,
            points_earned,
            total_points,
            time_taken,
            attempt_id
        ))
        
        connection.commit()

        # Return results
        results = {
            'score': score,
            'total_questions': total_questions,
            'correct_answers': correct_count,
            'wrong_answers': total_questions - correct_count,
            'time_taken': time_taken,
            'points_earned': points_earned,
            'total_points': total_points
        }
        
        print(f"DEBUG: Final results: {results}")

        return jsonify({"success": True, "results": results})
    
    except Exception as e:
        connection.rollback()
        print("Submit quiz error:", e)
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": str(e)}), 500
    
    finally:
        try:
            cursor.close()
        except:
            pass
        connection.close()

# ============================================
# ERROR HANDLERS
# ============================================

@app.errorhandler(404)
def not_found(e):
    return jsonify({"success": False, "message": "Resource not found"}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({"success": False, "message": "Internal server error"}), 500

# ============================================
# RUN APPLICATION
# ============================================


if __name__ == "__main__":
    # Get and display local IP
    local_ip = get_local_ip()
    print("=" * 50)
    print(f"Server running on: http://{local_ip}:5000")
    print(f"Students can access at: http://{local_ip}:5000/student/quiz/[quiz_id]")
    print("=" * 50)
    
    # Run the app accessible on LAN
    app.run(debug=True, host='0.0.0.0', port=5000)
    