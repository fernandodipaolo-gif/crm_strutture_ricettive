#!/usr/bin/env python3
"""
CRM per la gestione di Strutture Ricettive
Prenotazioni, Pagamenti, Arrivi e Partenze
"""

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_mail import Mail, Message
from datetime import datetime, date, timedelta
from sqlalchemy import or_, and_, func
import os
from dotenv import load_dotenv
import json
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors

# Carica variabili d'ambiente
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///crm_ricettivo.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Flask-Mail (configura le tue credenziali in .env)
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')

mail = Mail(app)

# Importa modelli
from models import Struttura, Camera, Ospite, Prenotazione, Pagamento, Base, User, TaskPulizia

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ============================================================
# FUNZIONI DI UTILITÀ
# ============================================================

def check_disponibilita(camera_id, data_arrivo, data_partenza, exclude_prenotazione_id=None):
    """Verifica se la camera è disponibile nelle date indicate"""
    query = db.session.query(Prenotazione).filter(
        Prenotazione.camera_id == camera_id,
        Prenotazione.stato.in_(['confermata', 'check-in', 'richiesta']),
        or_(
            and_(Prenotazione.data_arrivo < data_partenza, Prenotazione.data_partenza > data_arrivo),
        )
    )
    if exclude_prenotazione_id:
        query = query.filter(Prenotazione.id != exclude_prenotazione_id)
    
    return query.count() == 0

def get_occupazione_struttura(struttura_id, data=None):
    """Calcola quante camere sono occupate in una certa data"""
    if data is None:
        data = date.today()
    
    occupate = db.session.query(Prenotazione).filter(
        Prenotazione.struttura_id == struttura_id,
        Prenotazione.stato.in_(['confermata', 'check-in']),
        Prenotazione.data_arrivo <= data,
        Prenotazione.data_partenza > data
    ).count()
    
    totale_camere = db.session.query(Camera).filter_by(struttura_id=struttura_id).count()
    return occupate, totale_camere

def get_arrivi_oggi(struttura_id=None):
    """Restituisce le prenotazioni con arrivo oggi"""
    query = db.session.query(Prenotazione).filter(
        Prenotazione.data_arrivo == date.today(),
        Prenotazione.stato.in_(['confermata', 'richiesta'])
    )
    if struttura_id:
        query = query.filter_by(struttura_id=struttura_id)
    return query.order_by(Prenotazione.data_arrivo).all()

def get_partenze_oggi(struttura_id=None):
    """Restituisce le prenotazioni con partenza oggi"""
    query = db.session.query(Prenotazione).filter(
        Prenotazione.data_partenza == date.today(),
        Prenotazione.stato.in_(['check-in', 'confermata'])
    )
    if struttura_id:
        query = query.filter_by(struttura_id=struttura_id)
    return query.order_by(Prenotazione.data_partenza).all()

def calcola_ricavi_mese(struttura_id=None, mese=None, anno=None):
    """Calcola ricavi del mese corrente (o specificato)"""
    if mese is None:
        mese = date.today().month
    if anno is None:
        anno = date.today().year
    
    primo_giorno = date(anno, mese, 1)
    if mese == 12:
        ultimo_giorno = date(anno + 1, 1, 1) - timedelta(days=1)
    else:
        ultimo_giorno = date(anno, mese + 1, 1) - timedelta(days=1)
    
    query = db.session.query(func.sum(Prenotazione.prezzo_totale)).filter(
        Prenotazione.stato.in_(['confermata', 'check-in', 'check-out']),
        Prenotazione.data_arrivo >= primo_giorno,
        Prenotazione.data_arrivo <= ultimo_giorno
    )
    if struttura_id:
        query = query.filter_by(struttura_id=struttura_id)
    
    totale = query.scalar() or 0
    return round(totale, 2)

# ============================================================
# ROUTES - DASHBOARD
# ============================================================

@app.route('/')
def dashboard():
    """Dashboard principale con arrivi, partenze e KPI"""
    strutture = Struttura.query.all()
    
    # KPI globali
    arrivi_oggi = get_arrivi_oggi()
    partenze_oggi = get_partenze_oggi()
    
    # Camere totali e occupate
    totale_camere = db.session.query(Camera).count()
    occupate_oggi = db.session.query(Prenotazione).filter(
        Prenotazione.stato.in_(['confermata', 'check-in']),
        Prenotazione.data_arrivo <= date.today(),
        Prenotazione.data_partenza > date.today()
    ).count()
    
    # Ricavi mese corrente
    ricavi_mese = calcola_ricavi_mese()
    
    # Prossime prenotazioni (prossimi 7 giorni)
    prossime = db.session.query(Prenotazione).filter(
        Prenotazione.data_arrivo > date.today(),
        Prenotazione.data_arrivo <= date.today() + timedelta(days=7),
        Prenotazione.stato.in_(['confermata', 'richiesta'])
    ).order_by(Prenotazione.data_arrivo).limit(10).all()
    
    return render_template('dashboard.html',
                           strutture=strutture,
                           arrivi_oggi=arrivi_oggi,
                           partenze_oggi=partenze_oggi,
                           totale_camere=totale_camere,
                           occupate_oggi=occupate_oggi,
                           ricavi_mese=ricavi_mese,
                           prossime=prossime,
                           today=date.today())

# ============================================================
# ROUTES - STRUTTURE
# ============================================================

@app.route('/strutture')
def lista_strutture():
    strutture = Struttura.query.order_by(Struttura.nome).all()
    return render_template('strutture.html', strutture=strutture)

@app.route('/strutture/nuova', methods=['GET', 'POST'])
def nuova_struttura():
    if request.method == 'POST':
        struttura = Struttura(
            nome=request.form.get('nome'),
            indirizzo=request.form.get('indirizzo'),
            citta=request.form.get('citta'),
            cap=request.form.get('cap'),
            telefono=request.form.get('telefono'),
            email=request.form.get('email'),
            tipo=request.form.get('tipo'),
            num_camere=request.form.get('num_camere', 0, type=int),
            descrizione=request.form.get('descrizione')
        )
        db.session.add(struttura)
        db.session.commit()
        flash('Struttura creata con successo!', 'success')
        return redirect(url_for('lista_strutture'))
    
    return render_template('struttura_form.html', struttura=None)

@app.route('/strutture/<int:id>/modifica', methods=['GET', 'POST'])
def modifica_struttura(id):
    struttura = Struttura.query.get_or_404(id)
    
    if request.method == 'POST':
        struttura.nome = request.form.get('nome')
        struttura.indirizzo = request.form.get('indirizzo')
        struttura.citta = request.form.get('citta')
        struttura.cap = request.form.get('cap')
        struttura.telefono = request.form.get('telefono')
        struttura.email = request.form.get('email')
        struttura.tipo = request.form.get('tipo')
        struttura.num_camere = request.form.get('num_camere', 0, type=int)
        struttura.descrizione = request.form.get('descrizione')
        
        db.session.commit()
        flash('Struttura aggiornata con successo!', 'success')
        return redirect(url_for('lista_strutture'))
    
    return render_template('struttura_form.html', struttura=struttura)

@app.route('/strutture/<int:id>/elimina', methods=['POST'])
def elimina_struttura(id):
    struttura = Struttura.query.get_or_404(id)
    db.session.delete(struttura)
    db.session.commit()
    flash('Struttura eliminata.', 'warning')
    return redirect(url_for('lista_strutture'))

# ============================================================
# ROUTES - CAMERE
# ============================================================

@app.route('/camere')
def lista_camere():
    camere = Camera.query.join(Struttura).order_by(Struttura.nome, Camera.nome).all()
    strutture = Struttura.query.all()
    return render_template('camere.html', camere=camere, strutture=strutture)

@app.route('/camere/nuova', methods=['GET', 'POST'])
def nuova_camera():
    strutture = Struttura.query.all()
    
    if request.method == 'POST':
        camera = Camera(
            struttura_id=request.form.get('struttura_id', type=int),
            nome=request.form.get('nome'),
            tipo=request.form.get('tipo'),
            capienza=request.form.get('capienza', 2, type=int),
            prezzo_base_notte=request.form.get('prezzo_base_notte', 0, type=float),
            note=request.form.get('note'),
            stato=request.form.get('stato', 'libera')
        )
        db.session.add(camera)
        db.session.commit()
        flash('Camera/Unità creata con successo!', 'success')
        return redirect(url_for('lista_camere'))
    
    return render_template('camera_form.html', camera=None, strutture=strutture)

@app.route('/camere/<int:id>/modifica', methods=['GET', 'POST'])
def modifica_camera(id):
    camera = Camera.query.get_or_404(id)
    strutture = Struttura.query.all()
    
    if request.method == 'POST':
        camera.struttura_id = request.form.get('struttura_id', type=int)
        camera.nome = request.form.get('nome')
        camera.tipo = request.form.get('tipo')
        camera.capienza = request.form.get('capienza', 2, type=int)
        camera.prezzo_base_notte = request.form.get('prezzo_base_notte', 0, type=float)
        camera.note = request.form.get('note')
        camera.stato = request.form.get('stato', 'libera')
        
        db.session.commit()
        flash('Camera aggiornata con successo!', 'success')
        return redirect(url_for('lista_camere'))
    
    return render_template('camera_form.html', camera=camera, strutture=strutture)

@app.route('/camere/<int:id>/elimina', methods=['POST'])
def elimina_camera(id):
    camera = Camera.query.get_or_404(id)
    db.session.delete(camera)
    db.session.commit()
    flash('Camera eliminata.', 'warning')
    return redirect(url_for('lista_camere'))

# ============================================================
# ROUTES - OSPITI
# ============================================================

@app.route('/ospiti')
def lista_ospiti():
    search = request.args.get('q', '')
    if search:
        ospiti = Ospite.query.filter(
            or_(
                Ospite.nome.ilike(f'%{search}%'),
                Ospite.cognome.ilike(f'%{search}%'),
                Ospite.email.ilike(f'%{search}%'),
                Ospite.telefono.ilike(f'%{search}%')
            )
        ).order_by(Ospite.cognome, Ospite.nome).all()
    else:
        ospiti = Ospite.query.order_by(Ospite.cognome, Ospite.nome).all()
    
    return render_template('ospiti.html', ospiti=ospiti, search=search)

@app.route('/ospiti/<int:id>')
def dettaglio_ospite(id):
    ospite = Ospite.query.get_or_404(id)
    prenotazioni = Prenotazione.query.filter_by(ospite_id=id).order_by(Prenotazione.data_arrivo.desc()).all()
    return render_template('ospite_dettaglio.html', ospite=ospite, prenotazioni=prenotazioni)

# ============================================================
# ROUTES - PRENOTAZIONI
# ============================================================

@app.route('/prenotazioni')
def lista_prenotazioni():
    """Lista prenotazioni con filtri"""
    struttura_id = request.args.get('struttura_id', type=int)
    stato = request.args.get('stato', '')
    data_da = request.args.get('data_da', '')
    data_a = request.args.get('data_a', '')
    
    query = db.session.query(Prenotazione).join(Ospite).join(Camera).join(Struttura)
    
    if struttura_id:
        query = query.filter(Prenotazione.struttura_id == struttura_id)
    if stato:
        query = query.filter(Prenotazione.stato == stato)
    if data_da:
        query = query.filter(Prenotazione.data_arrivo >= datetime.strptime(data_da, '%Y-%m-%d').date())
    if data_a:
        query = query.filter(Prenotazione.data_arrivo <= datetime.strptime(data_a, '%Y-%m-%d').date())
    
    prenotazioni = query.order_by(Prenotazione.data_arrivo.desc()).all()
    strutture = Struttura.query.all()
    
    return render_template('prenotazioni.html', 
                           prenotazioni=prenotazioni, 
                           strutture=strutture,
                           filters={'struttura_id': struttura_id, 'stato': stato, 'data_da': data_da, 'data_a': data_a})

@app.route('/prenotazioni/nuova', methods=['GET', 'POST'])
def nuova_prenotazione():
    strutture = Struttura.query.all()
    camere = Camera.query.all()
    ospiti = Ospite.query.order_by(Ospite.cognome).all()
    
    if request.method == 'POST':
        struttura_id = request.form.get('struttura_id', type=int)
        camera_id = request.form.get('camera_id', type=int)
        data_arrivo = datetime.strptime(request.form.get('data_arrivo'), '%Y-%m-%d').date()
        data_partenza = datetime.strptime(request.form.get('data_partenza'), '%Y-%m-%d').date()
        
        # Verifica disponibilità
        if not check_disponibilita(camera_id, data_arrivo, data_partenza):
            flash('Attenzione: la camera non è disponibile nelle date selezionate!', 'danger')
            return render_template('prenotazione_form.html', 
                                   strutture=strutture, camere=camere, ospiti=ospiti,
                                   form_data=request.form)
        
        # Ospite: nuovo o esistente
        ospite_id = request.form.get('ospite_id', type=int)
        if not ospite_id:
            # Crea nuovo ospite
            ospite = Ospite(
                nome=request.form.get('nome_ospite'),
                cognome=request.form.get('cognome_ospite'),
                email=request.form.get('email_ospite'),
                telefono=request.form.get('telefono_ospite'),
                documento_tipo=request.form.get('documento_tipo'),
                documento_numero=request.form.get('documento_numero'),
                nazionalita=request.form.get('nazionalita')
            )
            db.session.add(ospite)
            db.session.flush()  # per ottenere l'id
            ospite_id = ospite.id
        
        # Crea prenotazione
        prenotazione = Prenotazione(
            struttura_id=struttura_id,
            camera_id=camera_id,
            ospite_id=ospite_id,
            data_arrivo=data_arrivo,
            data_partenza=data_partenza,
            num_persone=request.form.get('num_persone', 1, type=int),
            stato=request.form.get('stato', 'confermata'),
            prezzo_totale=request.form.get('prezzo_totale', 0, type=float),
            acconto=request.form.get('acconto', 0, type=float),
            fonte=request.form.get('fonte'),
            note=request.form.get('note')
        )
        prenotazione.calcola_notti()
        
        db.session.add(prenotazione)
        db.session.commit()
        
        flash('Prenotazione creata con successo!', 'success')
        return redirect(url_for('lista_prenotazioni'))
    
    return render_template('prenotazione_form.html', 
                           strutture=strutture, camere=camere, ospiti=ospiti,
                           form_data=None)

@app.route('/prenotazioni/<int:id>')
def dettaglio_prenotazione(id):
    prenotazione = Prenotazione.query.get_or_404(id)
    pagamenti = Pagamento.query.filter_by(prenotazione_id=id).order_by(Pagamento.data.desc()).all()
    return render_template('prenotazione_dettaglio.html', 
                           prenotazione=prenotazione, 
                           pagamenti=pagamenti)

@app.route('/prenotazioni/<int:id>/modifica', methods=['GET', 'POST'])
def modifica_prenotazione(id):
    prenotazione = Prenotazione.query.get_or_404(id)
    strutture = Struttura.query.all()
    camere = Camera.query.filter_by(struttura_id=prenotazione.struttura_id).all()
    
    if request.method == 'POST':
        data_arrivo = datetime.strptime(request.form.get('data_arrivo'), '%Y-%m-%d').date()
        data_partenza = datetime.strptime(request.form.get('data_partenza'), '%Y-%m-%d').date()
        camera_id = request.form.get('camera_id', type=int)
        
        # Verifica disponibilità (escludendo questa prenotazione)
        if not check_disponibilita(camera_id, data_arrivo, data_partenza, exclude_prenotazione_id=id):
            flash('La camera non è disponibile nelle nuove date!', 'danger')
            return redirect(url_for('modifica_prenotazione', id=id))
        
        prenotazione.struttura_id = request.form.get('struttura_id', type=int)
        prenotazione.camera_id = camera_id
        prenotazione.data_arrivo = data_arrivo
        prenotazione.data_partenza = data_partenza
        prenotazione.num_persone = request.form.get('num_persone', 1, type=int)
        prenotazione.stato = request.form.get('stato')
        prenotazione.prezzo_totale = request.form.get('prezzo_totale', 0, type=float)
        prenotazione.acconto = request.form.get('acconto', 0, type=float)
        prenotazione.fonte = request.form.get('fonte')
        prenotazione.note = request.form.get('note')
        prenotazione.calcola_notti()
        
        db.session.commit()
        flash('Prenotazione aggiornata!', 'success')
        return redirect(url_for('dettaglio_prenotazione', id=id))
    
    return render_template('prenotazione_form.html', 
                           prenotazione=prenotazione,
                           strutture=strutture, 
                           camere=camere)

@app.route('/prenotazioni/<int:id>/stato', methods=['POST'])
def cambia_stato_prenotazione(id):
    """Cambia stato prenotazione (check-in, check-out, etc.)"""
    prenotazione = Prenotazione.query.get_or_404(id)
    nuovo_stato = request.form.get('stato')
    
    if nuovo_stato in ['richiesta', 'confermata', 'check-in', 'check-out', 'cancellata', 'no-show']:
        prenotazione.stato = nuovo_stato
        
        # Aggiorna stato camera se necessario
        if nuovo_stato == 'check-in':
            prenotazione.camera.stato = 'occupata'
        elif nuovo_stato == 'check-out':
            prenotazione.camera.stato = 'libera'
        
        db.session.commit()
        flash(f'Stato aggiornato a: {nuovo_stato}', 'success')
    
    return redirect(request.referrer or url_for('dettaglio_prenotazione', id=id))

@app.route('/prenotazioni/<int:id>/elimina', methods=['POST'])
def elimina_prenotazione(id):
    prenotazione = Prenotazione.query.get_or_404(id)
    db.session.delete(prenotazione)
    db.session.commit()
    flash('Prenotazione eliminata.', 'warning')
    return redirect(url_for('lista_prenotazioni'))

# ============================================================
# ROUTES - PAGAMENTI
# ============================================================

@app.route('/prenotazioni/<int:prenotazione_id>/pagamento/nuovo', methods=['POST'])
def aggiungi_pagamento(prenotazione_id):
    prenotazione = Prenotazione.query.get_or_404(prenotazione_id)
    
    pagamento = Pagamento(
        prenotazione_id=prenotazione_id,
        data=datetime.strptime(request.form.get('data'), '%Y-%m-%d').date() if request.form.get('data') else date.today(),
        importo=request.form.get('importo', 0, type=float),
        metodo=request.form.get('metodo'),
        stato=request.form.get('stato', 'completato'),
        note=request.form.get('note'),
        transazione_id=request.form.get('transazione_id')
    )
    
    db.session.add(pagamento)
    db.session.commit()
    
    flash('Pagamento registrato con successo!', 'success')
    return redirect(url_for('dettaglio_prenotazione', id=prenotazione_id))

@app.route('/pagamenti/<int:id>/elimina', methods=['POST'])
def elimina_pagamento(id):
    pagamento = Pagamento.query.get_or_404(id)
    prenotazione_id = pagamento.prenotazione_id
    db.session.delete(pagamento)
    db.session.commit()
    flash('Pagamento eliminato.', 'warning')
    return redirect(url_for('dettaglio_prenotazione', id=prenotazione_id))

# ============================================================
# ROUTES - API per form dinamici (es. camere per struttura)
# ============================================================

@app.route('/api/camere/<int:struttura_id>')
def api_camere_struttura(struttura_id):
    """API per ottenere le camere di una struttura (usata da JS)"""
    camere = Camera.query.filter_by(struttura_id=struttura_id).all()
    return jsonify([{
        'id': c.id,
        'nome': c.nome,
        'tipo': c.tipo,
        'prezzo_base_notte': c.prezzo_base_notte,
        'capienza': c.capienza
    } for c in camere])

# ============================================================
# ROUTES - REPORT E ESPORTAZIONE
# ============================================================

@app.route('/report')
def report():
    """Pagina reportistica semplice"""
    strutture = Struttura.query.all()
    
    # Ricavi per struttura questo mese
    ricavi_per_struttura = []
    for s in strutture:
        ricavo = calcola_ricavi_mese(s.id)
        ricavi_per_struttura.append({'nome': s.nome, 'ricavo': ricavo})
    
    # Prenotazioni per stato
    stati_count = db.session.query(
        Prenotazione.stato, func.count(Prenotazione.id)
    ).group_by(Prenotazione.stato).all()
    
    return render_template('report.html', 
                           ricavi_per_struttura=ricavi_per_struttura,
                           stati_count=stati_count,
                           today=date.today())

@app.route('/export/prenotazioni')
def export_prenotazioni():
    """Esporta prenotazioni in Excel (richiede pandas + openpyxl)"""
    try:
        import pandas as pd
        from io import BytesIO
        from flask import send_file
        
        prenotazioni = db.session.query(
            Prenotazione.id,
            Struttura.nome.label('struttura'),
            Camera.nome.label('camera'),
            Ospite.nome_completo.label('ospite'),  # property non funziona bene in query
            Prenotazione.data_arrivo,
            Prenotazione.data_partenza,
            Prenotazione.num_notti,
            Prenotazione.num_persone,
            Prenotazione.stato,
            Prenotazione.prezzo_totale,
            Prenotazione.acconto,
            Prenotazione.fonte
        ).join(Struttura).join(Camera).join(Ospite).all()
        
        # Converti in lista dict
        data = []
        for p in prenotazioni:
            ospite = Ospite.query.get(p.ospite) if hasattr(p, 'ospite') else None  # fix
            # Semplifichiamo
            data.append({
                'ID': p.id,
                'Struttura': p.struttura,
                'Camera': p.camera,
                'Ospite': f"{p.nome} {p.cognome}" if hasattr(p, 'nome') else 'N/A',
                'Arrivo': p.data_arrivo,
                'Partenza': p.data_partenza,
                'Notti': p.num_notti,
                'Persone': p.num_persone,
                'Stato': p.stato,
                'Prezzo Totale': p.prezzo_totale,
                'Acconto': p.acconto,
                'Fonte': p.fonte
            })
        
        df = pd.DataFrame(data)
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Prenotazioni')
        
        output.seek(0)
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'prenotazioni_{date.today().strftime("%Y%m%d")}.xlsx'
        )
    except Exception as e:
        flash(f'Errore durante l\'esportazione: {str(e)}', 'danger')
        return redirect(url_for('report'))

# ============================================================
# INIZIALIZZAZIONE DB E DATI DEMO
# ============================================================

def init_db():
    """Crea tabelle e dati demo se il DB è vuoto"""
    db.create_all()
    
    # Se non ci sono strutture, crea dati demo
    if Struttura.query.count() == 0:
        print("Creazione dati demo...")
        
        # Struttura demo
        struttura = Struttura(
            nome="B&B Il Glicine",
            indirizzo="Via Roma 45",
            citta="Firenze",
            cap="50123",
            telefono="+39 055 123456",
            email="info@ilglicine.it",
            tipo="B&B",
            num_camere=5,
            descrizione="Accogliente B&B nel centro storico di Firenze"
        )
        db.session.add(struttura)
        db.session.flush()
        
        # Camere
        camere_data = [
            ("Camera Rosa", "Doppia", 2, 95.0),
            ("Camera Glicine", "Matrimoniale", 2, 110.0),
            ("Suite Torre", "Suite", 3, 150.0),
            ("Camera Azzurra", "Singola", 1, 70.0),
            ("Appartamento Terrazza", "Appartamento", 4, 180.0),
        ]
        
        for nome, tipo, capienza, prezzo in camere_data:
            camera = Camera(
                struttura_id=struttura.id,
                nome=nome,
                tipo=tipo,
                capienza=capienza,
                prezzo_base_notte=prezzo,
                stato='libera'
            )
            db.session.add(camera)
        
        db.session.flush()
        
        # Ospite demo
        ospite = Ospite(
            nome="Mario",
            cognome="Rossi",
            email="mario.rossi@email.it",
            telefono="+39 333 1234567",
            documento_tipo="Carta d'identità",
            documento_numero="AB1234567",
            nazionalita="Italia"
        )
        db.session.add(ospite)
        db.session.flush()
        
        # Prenotazione demo
        arrivo = date.today() + timedelta(days=2)
        partenza = arrivo + timedelta(days=3)
        
        pren = Prenotazione(
            struttura_id=struttura.id,
            camera_id=1,  # Camera Rosa
            ospite_id=ospite.id,
            data_arrivo=arrivo,
            data_partenza=partenza,
            num_notti=3,
            num_persone=2,
            stato='confermata',
            prezzo_totale=285.0,
            acconto=100.0,
            fonte="Sito web",
            note="Arrivo previsto dopo le 15:00"
        )
        db.session.add(pren)
        db.session.flush()
        
        # Pagamento demo
        pag = Pagamento(
            prenotazione_id=pren.id,
            data=date.today(),
            importo=100.0,
            metodo="bonifico",
            stato="completato",
            note="Acconto via bonifico"
        )
        db.session.add(pag)
        
        db.session.commit()
        print("Dati demo creati con successo!")

# ============================================================
# MAIN
# ============================================================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()      # Crea le tabelle nel database
        init_db()            # Crea dati demo + utente admin
    
    print("\n" + "="*60)
    print("🚀 CRM Ricettivo avviato con successo!")
    print("   URL: http://127.0.0.1:5000")
    print("="*60 + "\n")
    
    # Per Render.com
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
# Per deploy su Render / Production (Gunicorn)
# Questo permette di usare `gunicorn app:app`
