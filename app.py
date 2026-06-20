from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from datetime import datetime, date
import os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# Configurazione
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'super-secret-key-cambiala-in-produzione')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///crm_ricettivo.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ====================== MODELLI ======================
from models import db, Struttura, Camera, Ospite, Prenotazione, Pagamento, User, TaskPulizia

# ====================== LOGIN ======================
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ====================== INIZIALIZZAZIONE DATABASE ======================
def init_db():
    with app.app_context():
        db.create_all()
        
        # Crea utente admin se non esiste
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', ruolo='admin')
            admin.set_password('password123')
            db.session.add(admin)
            db.session.commit()
            print("✅ Utente admin creato (admin / password123)")

# ====================== ROUTE PRINCIPALI ======================
@app.route('/')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Credenziali non valide')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# ====================== ALTRE ROUTE (placeholder) ======================
@app.route('/prenotazioni')
@login_required
def prenotazioni():
    return render_template('prenotazioni.html')

@app.route('/calendario')
@login_required
def calendario():
    return render_template('calendario.html')

@app.route('/alloggiati')
@login_required
def alloggiati():
    return render_template('alloggiati.html')

# ====================== AVVIO ======================
if __name__ == '__main__':
    with app.app_context():
        init_db()
    
    print("\n" + "="*70)
    print("🚀 CRM Strutture Ricettive AVVIATO CON SUCCESSO!")
    print("   URL: http://127.0.0.1:5000")
    print("   Admin → admin / password123")
    print("="*70 + "\n")
    
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
