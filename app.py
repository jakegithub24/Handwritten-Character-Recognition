import os
import csv
import zipfile
import io
import base64
from datetime import datetime
from flask import Flask, render_template, request, redirect, session, jsonify, flash, Response, send_file, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from backend.db import get_db, init_db
from backend.auth import register_user, login_user, change_user_password, delete_user_account
from backend.predict import predict_digit, predict_digit_from_canvas, predict_digit_from_voice
from reportlab.platypus import SimpleDocTemplate, Table
from reportlab.lib import colors
import numpy as np
from PIL import Image

app = Flask(__name__)
app.config.from_object('config.Config')

# Initialize database on startup
init_db()

UPLOAD_FOLDER = app.config['UPLOAD_FOLDER']
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ------------------- CACHE PREVENTION FOR AUTHENTICATED PAGES -------------------
@app.after_request
def prevent_cache_for_authenticated_pages(response):
    """
    Prevent caching of authenticated pages to force re-authentication on logout.
    This ensures that when a user logs out, the back button won't show cached
    versions of protected pages with sensitive data.
    """
    # Check if user or admin is logged in
    is_user_authenticated = 'user_id' in session
    is_admin_authenticated = 'admin_username' in session
    
    # Only prevent caching for authenticated sessions
    if is_user_authenticated or is_admin_authenticated:
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0, private'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    
    return response

# ------------------- HOME -------------------
@app.route('/')
def home():
    return render_template("home.html")

# ------------------- USER AUTH -------------------
@app.route('/login_page')
def login_page():
    return render_template("user/login.html")

@app.route('/login', methods=['POST'])
def login():
    user = login_user(request.form['email'], request.form['password'])
    if user:
        session['user_id'] = user['id']
        session['user_name'] = user['name']
        return redirect('/dashboard')
    return render_template("user/login.html", error="Invalid Email or Password")

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            return render_template("user/register.html", message="already")
        register_user(name, email, password)
        return render_template("user/register.html", message="success")
    return render_template("user/register.html")

# ------------------- USER DASHBOARD & PREDICTIONS -------------------
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login_page')
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT id, name, email FROM users WHERE id = ?", (session['user_id'],))
    user = cursor.fetchone()
    return render_template("user/dashboard.html", user=user)

@app.route("/predict_page")
def predict_page():
    if 'user_id' not in session:
        return redirect('/login_page')
    return render_template("user/predict.html", user={'name': session.get('user_name')})

@app.route('/predict', methods=['POST'])
def predict():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    if 'image' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    file = request.files['image']
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400
    path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(path)
    digit, confidence = predict_digit(path)
    db = get_db()
    cursor = db.cursor()
    cursor.execute("INSERT INTO predictions (user_id, prediction_type, image_path, predicted_digit, confidence) VALUES (?, ?, ?, ?, ?)",
                   (session['user_id'], 'upload', path, int(digit), float(confidence)))
    db.commit()
    return jsonify({"digit": digit, "confidence": confidence, "image": path})

@app.route("/predict_canvas", methods=["POST"])
def predict_canvas():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json()
    result = predict_digit_from_canvas(data["image"])
    db = get_db()
    cursor = db.cursor()
    cursor.execute("INSERT INTO predictions (user_id, prediction_type, image_path, predicted_digit, confidence) VALUES (?, ?, ?, ?, ?)",
                   (session['user_id'], 'draw', 'canvas_image', int(result['digit']), float(result['confidence'])))
    db.commit()
    return jsonify(result)

@app.route('/predict_voice', methods=['POST'])
def predict_voice():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    if 'voice' not in request.files:
        return jsonify({"error": "No voice file"}), 400
    
    file = request.files['voice']
    
    # Ensure filename ends with .wav
    filename = file.filename
    if not filename.endswith('.wav'):
        filename = filename.split('.')[0] + '_' + str(session['user_id']) + '.wav'
    
    path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(path)
    
    print(f"[INFO] Saved voice file: {path}")
    
    digit, confidence = predict_digit_from_voice(path)
    
    db = get_db()
    cursor = db.cursor()
    cursor.execute("INSERT INTO predictions (user_id, prediction_type, image_path, predicted_digit, confidence) VALUES (?, ?, ?, ?, ?)",
                   (session['user_id'], 'voice', path, int(digit), float(confidence)))
    db.commit()
    
    return jsonify({"digit": digit, "confidence": confidence, "audio": path})

# ------------------- USER HISTORY & ANALYTICS -------------------
@app.route('/history')
def history():
    if 'user_id' not in session:
        return redirect('/login_page')
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM predictions WHERE user_id = ? ORDER BY id DESC", (session['user_id'],))
    data = cursor.fetchall()
    return render_template("user/history.html", data=data)

@app.route('/delete/<int:id>')
def delete(id):
    if 'user_id' not in session:
        return redirect('/login_page')
    db = get_db()
    cursor = db.cursor()
    # Verify the prediction belongs to the current user before deleting
    cursor.execute("SELECT * FROM predictions WHERE id = ? AND user_id = ?", (id, session['user_id']))
    prediction = cursor.fetchone()
    if not prediction:
        return "Prediction not found or access denied", 404
    cursor.execute("DELETE FROM predictions WHERE id = ?", (id,))
    db.commit()
    return redirect('/history')

@app.route('/analytics')
def analytics():
    if 'user_id' not in session:
        return redirect('/login_page')
    db = get_db()
    cursor = db.cursor()
    
    # Get filter parameters
    filter_type = request.args.get('type', '')
    start_date = request.args.get('start', '')
    end_date = request.args.get('end', '')
    
    # Build base query
    base_query = "SELECT * FROM predictions WHERE user_id = ?"
    count_query = "SELECT COUNT(*) as total FROM predictions WHERE user_id = ?"
    params = [session['user_id']]
    count_params = [session['user_id']]
    
    # Add type filter
    if filter_type and filter_type != 'all':
        db_type = 'upload' if filter_type == 'image' else filter_type
        base_query += " AND prediction_type = ?"
        count_query += " AND prediction_type = ?"
        params.append(db_type)
        count_params.append(db_type)
    
    # Add date filters
    if start_date:
        base_query += " AND DATE(created_at) >= ?"
        count_query += " AND DATE(created_at) >= ?"
        params.append(start_date)
        count_params.append(start_date)
    if end_date:
        base_query += " AND DATE(created_at) <= ?"
        count_query += " AND DATE(created_at) <= ?"
        params.append(end_date)
        count_params.append(end_date)
    
    # Get total count
    cursor.execute(count_query, tuple(count_params))
    total = cursor.fetchone()['total']
    
    # Get digit statistics
    digit_query = base_query + " GROUP BY predicted_digit"
    cursor.execute(digit_query, tuple(params))
    rows = cursor.fetchall()
    digits = [str(r['predicted_digit']) for r in rows]
    counts = [r['count'] for r in rows]
    most_digit = digits[counts.index(max(counts))] if counts else 0
    accuracy = round((sum(counts)/total)*100, 2) if total>0 else 0
    
    return render_template("user/analytics.html", total=total, most_digit=most_digit, accuracy=accuracy, digits=digits, counts=counts)

@app.route('/top_predictions')
def top_predictions():
    if 'user_id' not in session:
        return redirect('/login_page')
    
    db = get_db()
    cursor = db.cursor()
    
    # Top 5 most frequent digits for this user
    cursor.execute("""
        SELECT predicted_digit, COUNT(*) as count
        FROM predictions
        WHERE user_id = ?
        GROUP BY predicted_digit
        ORDER BY count DESC
        LIMIT 5
    """, (session['user_id'],))
    top_digits = cursor.fetchall()
    
    # Top 5 highest confidence predictions
    cursor.execute("""
        SELECT id, predicted_digit, confidence, prediction_type, created_at
        FROM predictions
        WHERE user_id = ?
        ORDER BY confidence DESC
        LIMIT 5
    """, (session['user_id'],))
    top_conf = cursor.fetchall()
    
    cursor.close()
    db.close()
    
    return render_template("user/top_predictions.html",
                           top_digits=top_digits,
                           top_conf=top_conf)

# ------------------- USER PROFILE, CHANGE PASSWORD, DELETE ACCOUNT -------------------
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect('/login_page')
    db = get_db()
    cursor = db.cursor()
    # Profile page is GET only now - name cannot be edited
    cursor.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],))
    user = cursor.fetchone()
    cursor.execute("SELECT COUNT(*) as total FROM predictions WHERE user_id = ?", (session['user_id'],))
    total = cursor.fetchone()['total']
    return render_template("user/profile.html", user=user, total=total)

@app.route('/change_password', methods=['POST'])
def change_password():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    old = request.form['old_password']
    new = request.form['new_password']
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT password FROM users WHERE id = ?", (session['user_id'],))
    user = cursor.fetchone()
    if not check_password_hash(user['password'], old):
        return jsonify({"error": "Old password is incorrect"}), 400
    change_user_password(session['user_id'], new)
    return jsonify({"success": True})

@app.route('/delete_account', methods=['POST'])
def delete_account():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    # Get password from request for verification
    password = request.form.get('password') or request.get_json().get('password')
    
    if not password:
        return jsonify({"error": "Password required for account deletion"}), 400
    
    # Verify password
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT password FROM users WHERE id = ?", (session['user_id'],))
    user = cursor.fetchone()
    
    if not user or not check_password_hash(user['password'], password):
        return jsonify({"error": "Incorrect password"}), 401
    
    # Delete account if password is correct
    delete_user_account(session['user_id'])
    session.clear()
    return jsonify({"success": True})

# ------------------- DOWNLOAD ROUTES (unchanged logic, just SQLite) -------------------
@app.route('/download')
def download_page():
    if 'user_id' not in session:
        return redirect('/login_page')
    return render_template("user/download.html")

@app.route('/download/<path:filepath>')
def download_file(filepath):
    """Download a specific prediction image file"""
    if 'user_id' not in session:
        return redirect('/login_page')
    
    try:
        # Verify file exists and user owns it
        db = get_db()
        cursor = db.cursor()
        
        # Check if prediction belongs to this user
        cursor.execute(
            "SELECT * FROM predictions WHERE user_id = ? AND image_path = ?",
            (session['user_id'], filepath)
        )
        prediction = cursor.fetchone()
        
        if not prediction:
            return "File not found or access denied", 404
        
        # Check if file exists
        import os
        if not os.path.exists(filepath):
            return "File not found", 404
        
        # Send file
        return send_file(filepath, as_attachment=True)
    except Exception as e:
        return str(e), 400

@app.route('/reports')
def reports_page():
    """User reports page"""
    if 'user_id' not in session:
        return redirect('/login_page')
    
    db = get_db()
    cursor = db.cursor()
    
    # Get prediction statistics
    cursor.execute(
        "SELECT COUNT(*) as total, AVG(confidence) as avg_conf FROM predictions WHERE user_id = ?",
        (session['user_id'],)
    )
    stats = cursor.fetchone()
    total = stats[0] if stats[0] else 0
    # Confidence is already stored as percentages, just round it
    avg_confidence = round(stats[1]) if stats[1] else 0
    
    # Get top predicted digit
    cursor.execute(
        "SELECT predicted_digit, COUNT(*) as count FROM predictions WHERE user_id = ? GROUP BY predicted_digit ORDER BY count DESC LIMIT 1",
        (session['user_id'],)
    )
    top_result = cursor.fetchone()
    top_digit = top_result[0] if top_result else "N/A"
    
    # Get accuracy (using average confidence as accuracy metric)
    accuracy = round(stats[1]) if stats[1] else 0
    
    # Get predictions per type
    cursor.execute(
        "SELECT prediction_type, COUNT(*) as count FROM predictions WHERE user_id = ? GROUP BY prediction_type",
        (session['user_id'],)
    )
    type_data = cursor.fetchall()
    type_counts = dict(type_data) if type_data else {}
    
    draw_count = type_counts.get('draw', 0)
    image_count = type_counts.get('upload', 0)
    voice_count = type_counts.get('voice', 0)
    
    return render_template("user/reports.html", 
                         total=total,
                         avg_confidence=avg_confidence,
                         top_digit=top_digit,
                         accuracy=accuracy,
                         draw_count=draw_count,
                         image_count=image_count,
                         voice_count=voice_count)

@app.route('/download_csv')
def download_csv():
    """Download all user predictions as CSV"""
    if 'user_id' not in session:
        return redirect('/login_page')
    
    db = get_db()
    cursor = db.cursor()
    
    # Get all predictions for user
    cursor.execute(
        "SELECT id, predicted_digit, confidence, prediction_type, created_at FROM predictions WHERE user_id = ? ORDER BY created_at DESC",
        (session['user_id'],)
    )
    predictions = cursor.fetchall()
    
    # Create CSV
    output = io.StringIO()
    output.write("ID,Digit,Confidence,Type,Date\n")
    for pred in predictions:
        output.write(f"{pred[0]},{pred[1]},{pred[2]:.2f},{pred[3]},{pred[4]}\n")
    
    # Return as download
    output.seek(0)
    return Response(output.getvalue(), mimetype="text/csv", 
                   headers={"Content-Disposition": "attachment;filename=predictions.csv"})

@app.route('/download_filtered', methods=['POST'])
def download_filtered():
    """Download predictions filtered by date range as CSV"""
    if 'user_id' not in session:
        return redirect('/login_page')
    
    start_date = request.form.get('start')
    end_date = request.form.get('end')
    
    db = get_db()
    cursor = db.cursor()
    
    # Get filtered predictions
    cursor.execute(
        "SELECT id, predicted_digit, confidence, prediction_type, created_at FROM predictions WHERE user_id = ? AND DATE(created_at) BETWEEN ? AND ? ORDER BY created_at DESC",
        (session['user_id'], start_date, end_date)
    )
    predictions = cursor.fetchall()
    
    # Create CSV
    output = io.StringIO()
    output.write(f"Predictions from {start_date} to {end_date}\n")
    output.write("ID,Digit,Confidence,Type,Date\n")
    for pred in predictions:
        output.write(f"{pred[0]},{pred[1]},{pred[2]:.2f},{pred[3]},{pred[4]}\n")
    
    output.seek(0)
    return Response(output.getvalue(), mimetype="text/csv",
                   headers={"Content-Disposition": f"attachment;filename=predictions_{start_date}_to_{end_date}.csv"})

@app.route('/download_filtered_type', methods=['POST'])
def download_filtered_type():
    """Download predictions filtered by type and/or digit as CSV"""
    if 'user_id' not in session:
        return redirect('/login_page')
    
    pred_type = request.form.get('type')
    digit = request.form.get('digit')
    
    db = get_db()
    cursor = db.cursor()
    
    # Build query
    if pred_type == 'all' and not digit:
        query = "SELECT id, predicted_digit, confidence, prediction_type, created_at FROM predictions WHERE user_id = ? ORDER BY created_at DESC"
        params = (session['user_id'],)
    elif pred_type != 'all' and digit:
        # Map 'image' to 'upload' for database
        db_type = 'upload' if pred_type == 'image' else pred_type
        query = "SELECT id, predicted_digit, confidence, prediction_type, created_at FROM predictions WHERE user_id = ? AND prediction_type = ? AND predicted_digit = ? ORDER BY created_at DESC"
        params = (session['user_id'], db_type, int(digit))
    elif pred_type != 'all':
        db_type = 'upload' if pred_type == 'image' else pred_type
        query = "SELECT id, predicted_digit, confidence, prediction_type, created_at FROM predictions WHERE user_id = ? AND prediction_type = ? ORDER BY created_at DESC"
        params = (session['user_id'], db_type)
    else:
        query = "SELECT id, predicted_digit, confidence, prediction_type, created_at FROM predictions WHERE user_id = ? AND predicted_digit = ? ORDER BY created_at DESC"
        params = (session['user_id'], int(digit))
    
    cursor.execute(query, params)
    predictions = cursor.fetchall()
    
    # Create CSV
    output = io.StringIO()
    output.write(f"Filtered Predictions - Type: {pred_type}, Digit: {digit if digit else 'All'}\n")
    output.write("ID,Digit,Confidence,Type,Date\n")
    for pred in predictions:
        output.write(f"{pred[0]},{pred[1]},{pred[2]:.2f},{pred[3]},{pred[4]}\n")
    
    output.seek(0)
    filename = f"predictions_filtered_{pred_type}_{digit}.csv" if digit else f"predictions_filtered_{pred_type}.csv"
    return Response(output.getvalue(), mimetype="text/csv",
                   headers={"Content-Disposition": f"attachment;filename={filename}"})

@app.route('/download/canvas_image/<int:prediction_id>')
def download_canvas_image(prediction_id):
    """Download a canvas prediction as an image"""
    if 'user_id' not in session:
        return redirect('/login_page')
    
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Get prediction
        cursor.execute(
            "SELECT * FROM predictions WHERE id = ? AND user_id = ? AND prediction_type = 'draw'",
            (prediction_id, session['user_id'])
        )
        prediction = cursor.fetchone()
        
        if not prediction:
            return "Canvas image not found", 404
        
        # Create a simple image file with the prediction info
        from PIL import Image, ImageDraw
        
        # Create placeholder image with prediction info
        img = Image.new('RGB', (400, 300), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        
        text = f"Digit Prediction: {prediction['predicted_digit']}\nConfidence: {prediction['confidence']}%\nDate: {prediction['created_at']}"
        draw.text((50, 50), text, fill=(0, 0, 0))
        
        # Save to bytes
        img_io = io.BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)
        
        return send_file(img_io, mimetype='image/png',
                        as_attachment=True, download_name=f'canvas_prediction_{prediction_id}.png')
    
    except Exception as e:
        return str(e), 400

@app.route('/download_images')
def download_images():
    """Download all user's prediction images as ZIP"""
    if 'user_id' not in session:
        return redirect('/login_page')
    
    db = get_db()
    cursor = db.cursor()
    
    # Get all predictions for user
    cursor.execute(
        "SELECT image_path FROM predictions WHERE user_id = ?",
        (session['user_id'],)
    )
    predictions = cursor.fetchall()
    
    if not predictions:
        return "No predictions found", 404
    
    # Create ZIP file
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for pred in predictions:
            image_path = pred[0]
            if os.path.exists(image_path):
                # Get just the filename for the zip
                filename = os.path.basename(image_path)
                zf.write(image_path, arcname=filename)
    
    memory_file.seek(0)
    return send_file(memory_file, mimetype='application/zip',
                    as_attachment=True, download_name='predictions_images.zip')

@app.route('/download_report')
def download_report():
    """Download user report as PDF"""
    if 'user_id' not in session:
        return redirect('/login_page')
    
    db = get_db()
    cursor = db.cursor()
    
    # Get user info
    cursor.execute("SELECT name, email FROM users WHERE id = ?", (session['user_id'],))
    user = cursor.fetchone()
    
    # Get prediction statistics
    cursor.execute(
        "SELECT COUNT(*) as total, AVG(confidence) as avg_conf FROM predictions WHERE user_id = ?",
        (session['user_id'],)
    )
    stats = cursor.fetchone()
    
    # Get predictions by digit
    cursor.execute(
        "SELECT predicted_digit, COUNT(*) as count FROM predictions WHERE user_id = ? GROUP BY predicted_digit ORDER BY predicted_digit",
        (session['user_id'],)
    )
    digit_stats = cursor.fetchall()
    
    # Get predictions by type
    cursor.execute(
        "SELECT prediction_type, COUNT(*) as count FROM predictions WHERE user_id = ? GROUP BY prediction_type",
        (session['user_id'],)
    )
    type_stats = cursor.fetchall()
    
    # Create PDF report
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, title="Prediction Report", pagesize=(600, 800))
    elements = []
    
    # Title
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import Paragraph, Spacer, PageBreak
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(name='CustomTitle', parent=styles['Heading1'], fontSize=24, textColor=colors.HexColor('#22c55e'), alignment=1)
    
    elements.append(Paragraph("Digit Recognition Report", title_style))
    elements.append(Spacer(1, 12))
    
    # User info
    elements.append(Paragraph(f"<b>User:</b> {user[0]}", styles['Normal']))
    elements.append(Paragraph(f"<b>Email:</b> {user[1]}", styles['Normal']))
    elements.append(Spacer(1, 12))
    
    # Statistics
    elements.append(Paragraph(f"<b>Total Predictions:</b> {stats[0]}", styles['Normal']))
    elements.append(Paragraph(f"<b>Average Confidence:</b> {stats[1]:.2f}%" if stats[1] else "N/A", styles['Normal']))
    elements.append(Spacer(1, 12))
    
    # Digit breakdown table
    elements.append(Paragraph("<b>Predictions by Digit</b>", styles['Heading2']))
    digit_data = [['Digit', 'Count']] + [[str(d[0]), str(d[1])] for d in digit_stats]
    digit_table = Table(digit_data)
    digit_table.setStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#22c55e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey)
    ])
    elements.append(digit_table)
    elements.append(Spacer(1, 12))
    
    # Type breakdown table
    elements.append(Paragraph("<b>Predictions by Type</b>", styles['Heading2']))
    type_data = [['Type', 'Count']] + [[d[0], str(d[1])] for d in type_stats]
    type_table = Table(type_data)
    type_table.setStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#22c55e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey)
    ])
    elements.append(type_table)
    
    # Build PDF
    doc.build(elements)
    pdf_buffer.seek(0)
    
    return send_file(pdf_buffer, mimetype='application/pdf',
                    as_attachment=True, download_name='prediction_report.pdf')

# ------------------- ADMIN ROUTES (with hashed password) -------------------
@app.route('/admin')
def admin_login():
    return render_template("admin/admin_login.html", error=None)

@app.route('/admin_login', methods=['POST'])
def admin_login_post():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM admin WHERE username = ?", (request.form['username'],))
    admin = cursor.fetchone()
    if admin and check_password_hash(admin['password'], request.form['password']):
        session['admin'] = True
        session['admin_username'] = admin['username']
        return redirect('/admin_dashboard')
    return render_template("admin/admin_login.html", error="Invalid Credentials")

@app.route('/admin/change_password', methods=['POST'])
def admin_change_password():
    if 'admin_username' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    old = request.form['old_password']
    new = request.form['new_password']
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT password FROM admin WHERE username = ?", (session['admin_username'],))
    admin = cursor.fetchone()
    if not check_password_hash(admin['password'], old):
        return jsonify({"error": "Old password incorrect"}), 400
    hashed_new = generate_password_hash(new)
    cursor.execute("UPDATE admin SET password = ? WHERE username = ?", (hashed_new, session['admin_username']))
    db.commit()
    return jsonify({"success": True})

@app.route('/admin_logout')
def admin_logout():
    session.pop('admin_username', None)
    session.pop('admin', None)
    return redirect('/admin')


# ------------------- ADMIN DASHBOARD & MANAGEMENT -------------------

@app.route("/admin_dashboard")
def admin_dashboard():
    if 'admin_username' not in session:
        return redirect('/admin')

    db = get_db()
    cursor = db.cursor()

    # Users
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()

    # Predictions with user name
    cursor.execute("""
        SELECT p.*, u.name AS user_name
        FROM predictions p
        JOIN users u ON p.user_id = u.id
        ORDER BY p.id ASC
    """)
    predictions = cursor.fetchall()

    # Totals
    total_users = len(users)
    total_predictions = len(predictions)

    # Most predicted digit
    cursor.execute("""
        SELECT predicted_digit, COUNT(*) as count
        FROM predictions
        GROUP BY predicted_digit
        ORDER BY count DESC LIMIT 1
    """)
    res = cursor.fetchone()
    most_digit = res['predicted_digit'] if res else 0

    # Highest confidence
    cursor.execute("SELECT MAX(confidence) as max_conf FROM predictions")
    res2 = cursor.fetchone()
    highest_pred = res2['max_conf'] if res2 and res2['max_conf'] else 0

    # Graph data
    cursor.execute("""
        SELECT predicted_digit, COUNT(*) as count
        FROM predictions
        GROUP BY predicted_digit
        ORDER BY predicted_digit ASC
    """)
    data = cursor.fetchall()
    digits = [str(d['predicted_digit']) for d in data]
    counts = [d['count'] for d in data]

    cursor.close()
    db.close()

    # ✅ IMPORTANT: comma after template name!
    return render_template("admin/admin_dashboard.html",
                           users=users,
                           predictions=predictions,
                           total_users=total_users,
                           total_predictions=total_predictions,
                           most_digit=most_digit,
                           highest_pred=highest_pred,
                           digits=digits,
                           counts=counts)


# --- Additional Admin Routes for Sidebar Navigation ---
@app.route('/admin/users')
def admin_users():
    if 'admin_username' not in session:
        return redirect('/admin')
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    return render_template("admin/users.html", users=users)

@app.route('/admin/analytics')
def admin_analytics():
    if 'admin_username' not in session:
        return redirect('/admin')
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT COUNT(*) as total_users FROM users")
    total_users = cursor.fetchone()['total_users']
    cursor.execute("SELECT COUNT(*) as total_predictions FROM predictions")
    total_predictions = cursor.fetchone()['total_predictions']
    cursor.execute("SELECT predicted_digit, COUNT(*) as count FROM predictions GROUP BY predicted_digit ORDER BY count DESC LIMIT 1")
    res = cursor.fetchone()
    most_digit = res['predicted_digit'] if res else 0
    cursor.execute("SELECT MAX(confidence) as max_conf FROM predictions")
    res2 = cursor.fetchone()
    highest_conf = res2['max_conf'] if res2 and res2['max_conf'] else 0
    cursor.execute("SELECT predicted_digit, COUNT(*) as count FROM predictions GROUP BY predicted_digit ORDER BY predicted_digit ASC")
    data = cursor.fetchall()
    digits = [str(d['predicted_digit']) for d in data]
    counts = [d['count'] for d in data]
    return render_template("admin/admin_analytics.html", total_users=total_users, total_predictions=total_predictions, most_digit=most_digit, highest_conf=highest_conf, digits=digits, counts=counts)

@app.route('/admin/reports')
def admin_reports():
    if 'admin_username' not in session:
        return redirect('/admin')
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT p.*, u.name AS user_name FROM predictions p
        LEFT JOIN users u ON p.user_id = u.id
        ORDER BY p.id DESC
    """)
    predictions = []
    for row in cursor.fetchall():
        r = dict(row)
        if 'created_at' in r and r['created_at']:
            if not isinstance(r['created_at'], str):
                r['created_at'] = str(r['created_at'])
        predictions.append(r)
    return render_template("admin/admin_reports.html", predictions=predictions)

@app.route('/admin/predictions')
def admin_predictions():
    if 'admin_username' not in session:
        return redirect('/admin')
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT p.*, u.name AS user_name FROM predictions p
        LEFT JOIN users u ON p.user_id = u.id
        ORDER BY p.id ASC
    """)
    predictions = []
    for row in cursor.fetchall():
        # Ensure created_at is a string for template
        r = dict(row)
        if 'created_at' in r and r['created_at']:
            # If already string, leave as is
            if not isinstance(r['created_at'], str):
                r['created_at'] = str(r['created_at'])
        predictions.append(r)
    return render_template("admin/admin_predictions.html", predictions=predictions)

@app.route('/admin/settings', methods=['GET', 'POST'])
def admin_settings():
    if 'admin_username' not in session:
        return redirect('/admin')
    
    message = None
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('password')
        
        # Verify current password
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT password FROM admin WHERE username = ?", (session['admin_username'],))
        admin = cursor.fetchone()
        
        if not admin or not check_password_hash(admin['password'], current_password):
            message = "Current password is incorrect"
        elif new_password:
            # Update password
            hashed_new = generate_password_hash(new_password)
            cursor.execute("UPDATE admin SET password = ? WHERE username = ?", (hashed_new, session['admin_username']))
            db.commit()
            message = "Password updated successfully"
        else:
            message = "Please enter a new password"
    
    # Dummy admin object for template rendering
    admin = type('Admin', (), {'username': 'admin'})()
    return render_template("admin/admin_settings.html", admin=admin, message=message)

@app.route('/admin/view_user/<int:user_id>')
def view_user(user_id):
    if 'admin_username' not in session:
        return redirect('/admin')
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    cursor.execute("SELECT * FROM predictions WHERE user_id = ?", (user_id,))
    predictions = cursor.fetchall()
    return render_template("admin/view_user.html", user=user, predictions=predictions)

@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
def delete_user_by_admin(user_id):
    """Admin endpoint to delete a user and all their predictions"""
    if 'admin_username' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Delete all predictions for this user first
        cursor.execute("DELETE FROM predictions WHERE user_id = ?", (user_id,))
        
        # Delete the user
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        db.commit()
        
        return jsonify({"success": True, "message": "User deleted successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# ------------------- LOGOUT -------------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)
