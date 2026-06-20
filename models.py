from datetime import datetime, date
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from sqlalchemy.sql import func
from werkzeug.security import generate_password_hash, check_password_hash

# NON importiamo db qui per evitare circular import
db = SQLAlchemy()

class Struttura(db.Model):
    __tablename__ = 'strutture'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)
    indirizzo = db.Column(db.String(200))
    citta = db.Column(db.String(100))
    cap = db.Column(db.String(10))
    telefono = db.Column(db.String(30))
    email = db.Column(db.String(100))
    tipo = db.Column(db.String(50))
    num_camere = db.Column(db.Integer, default=0)
    descrizione = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=func.now())

    camere = db.relationship("Camera", back_populates="struttura", cascade="all, delete-orphan")
    prenotazioni = db.relationship("Prenotazione", back_populates="struttura")


class Camera(db.Model):
    __tablename__ = 'camere'
    id = db.Column(db.Integer, primary_key=True)
    struttura_id = db.Column(db.Integer, db.ForeignKey('strutture.id'), nullable=False)
    nome = db.Column(db.String(100), nullable=False)
    tipo = db.Column(db.String(50))
    capienza = db.Column(db.Integer, default=2)
    prezzo_base_notte = db.Column(db.Float, default=0.0)
    note = db.Column(db.Text)
    stato = db.Column(db.String(30), default='libera')
    created_at = db.Column(db.DateTime, default=func.now())

    struttura = db.relationship("Struttura", back_populates="camere")
    prenotazioni = db.relationship("Prenotazione", back_populates="camera")


class Ospite(db.Model):
    __tablename__ = 'ospiti'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    cognome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100))
    telefono = db.Column(db.String(30))
    data_nascita = db.Column(db.Date)
    luogo_nascita = db.Column(db.String(100))
    nazionalita = db.Column(db.String(50))
    sesso = db.Column(db.String(1))
    tipo_documento = db.Column(db.String(50))
    numero_documento = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=func.now())

    prenotazioni = db.relationship("Prenotazione", back_populates="ospite")


class Prenotazione(db.Model):
    __tablename__ = 'prenotazioni'
    id = db.Column(db.Integer, primary_key=True)
    struttura_id = db.Column(db.Integer, db.ForeignKey('strutture.id'), nullable=False)
    camera_id = db.Column(db.Integer, db.ForeignKey('camere.id'), nullable=False)
    ospite_id = db.Column(db.Integer, db.ForeignKey('ospiti.id'), nullable=False)

    data_arrivo = db.Column(db.Date, nullable=False)
    data_partenza = db.Column(db.Date, nullable=False)
    stato = db.Column(db.String(30), default='confermata')
    numero_adulti = db.Column(db.Integer, default=2)
    numero_bambini = db.Column(db.Integer, default=0)
    prezzo_totale = db.Column(db.Float, default=0.0)
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=func.now())

    struttura = db.relationship("Struttura", back_populates="prenotazioni")
    camera = db.relationship("Camera", back_populates="prenotazioni")
    ospite = db.relationship("Ospite", back_populates="prenotazioni")
    pagamenti = db.relationship("Pagamento", back_populates="prenotazione", cascade="all, delete-orphan")


class Pagamento(db.Model):
    __tablename__ = 'pagamenti'
    id = db.Column(db.Integer, primary_key=True)
    prenotazione_id = db.Column(db.Integer, db.ForeignKey('prenotazioni.id'), nullable=False)
    importo = db.Column(db.Float, nullable=False)
    data_pagamento = db.Column(db.DateTime, default=func.now())
    metodo = db.Column(db.String(50))
    note = db.Column(db.Text)

    prenotazione = db.relationship("Prenotazione", back_populates="pagamenti")


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    ruolo = db.Column(db.String(30), default='reception')
    created_at = db.Column(db.DateTime, default=func.now())

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class TaskPulizia(db.Model):
    __tablename__ = 'task_pulizia'
    id = db.Column(db.Integer, primary_key=True)
    camera_id = db.Column(db.Integer, db.ForeignKey('camere.id'), nullable=False)
    data = db.Column(db.Date, nullable=False)
    stato = db.Column(db.String(30), default='da_fare')
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=func.now())

    camera = db.relationship("Camera")
