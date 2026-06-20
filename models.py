from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
from flask_login import UserMixin

Base = declarative_base()

class Struttura(Base):
    __tablename__ = 'strutture'
    
    id = Column(Integer, primary_key=True)
    nome = Column(String(150), nullable=False)
    indirizzo = Column(String(200))
    citta = Column(String(100))
    cap = Column(String(10))
    telefono = Column(String(30))
    email = Column(String(100))
    tipo = Column(String(50))  # Hotel, B&B, Appartamento, Villa, etc.
    num_camere = Column(Integer, default=0)
    descrizione = Column(Text)
    created_at = Column(DateTime, default=func.now())
    
    camere = relationship("Camera", back_populates="struttura", cascade="all, delete-orphan")
    prenotazioni = relationship("Prenotazione", back_populates="struttura")

    def __repr__(self):
        return f"<Struttura {self.nome}>"


class Camera(Base):
    __tablename__ = 'camere'
    
    id = Column(Integer, primary_key=True)
    struttura_id = Column(Integer, ForeignKey('strutture.id'), nullable=False)
    nome = Column(String(100), nullable=False)  # es. "Camera Deluxe 101" o "Appartamento Vista Mare"
    tipo = Column(String(50))  # Singola, Doppia, Matrimoniale, Suite, Appartamento, etc.
    capienza = Column(Integer, default=2)
    prezzo_base_notte = Column(Float, default=0.0)
    note = Column(Text)
    stato = Column(String(30), default='libera')  # libera, occupata, manutenzione
    created_at = Column(DateTime, default=func.now())
    
    struttura = relationship("Struttura", back_populates="camere")
    prenotazioni = relationship("Prenotazione", back_populates="camera")

    def __repr__(self):
        return f"<Camera {self.nome}>"


class Ospite(Base):
    __tablename__ = 'ospiti'
    
    id = Column(Integer, primary_key=True)
    nome = Column(String(80), nullable=False)
    cognome = Column(String(80), nullable=False)
    email = Column(String(120))
    telefono = Column(String(30))
    documento_tipo = Column(String(30))  # Carta d'identità, Passaporto, etc.
    documento_numero = Column(String(50))
    nazionalita = Column(String(50))
    note = Column(Text)
    created_at = Column(DateTime, default=func.now())
    
    prenotazioni = relationship("Prenotazione", back_populates="ospite")

    @property
    def nome_completo(self):
        return f"{self.nome} {self.cognome}"

    def __repr__(self):
        return f"<Ospite {self.nome_completo}>"


class Prenotazione(Base):
    __tablename__ = 'prenotazioni'
    
    id = Column(Integer, primary_key=True)
    struttura_id = Column(Integer, ForeignKey('strutture.id'), nullable=False)
    camera_id = Column(Integer, ForeignKey('camere.id'), nullable=False)
    ospite_id = Column(Integer, ForeignKey('ospiti.id'), nullable=False)
    
    data_arrivo = Column(Date, nullable=False)
    data_partenza = Column(Date, nullable=False)
    num_notti = Column(Integer)
    num_persone = Column(Integer, default=1)
    
    stato = Column(String(30), default='richiesta')  # richiesta, confermata, check-in, check-out, cancellata, no-show
    prezzo_totale = Column(Float, default=0.0)
    acconto = Column(Float, default=0.0)
    
    fonte = Column(String(50))  # Booking.com, Airbnb, Sito web, Telefono, Walk-in, etc.
    note = Column(Text)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    struttura = relationship("Struttura", back_populates="prenotazioni")
    camera = relationship("Camera", back_populates="prenotazioni")
    ospite = relationship("Ospite", back_populates="prenotazioni")
    pagamenti = relationship("Pagamento", back_populates="prenotazione", cascade="all, delete-orphan")

    @property
    def saldo(self):
        totale_pagato = sum(p.importo for p in self.pagamenti if p.stato == 'completato')
        return round(self.prezzo_totale - totale_pagato, 2)

    @property
    def totale_pagato(self):
        return sum(p.importo for p in self.pagamenti if p.stato == 'completato')

    def calcola_notti(self):
        if self.data_arrivo and self.data_partenza:
            self.num_notti = (self.data_partenza - self.data_arrivo).days
        return self.num_notti or 0

    def __repr__(self):
        return f"<Prenotazione {self.id} - {self.data_arrivo}>"


class Pagamento(Base):
    __tablename__ = 'pagamenti'
    
    id = Column(Integer, primary_key=True)
    prenotazione_id = Column(Integer, ForeignKey('prenotazioni.id'), nullable=False)
    data = Column(Date, default=date.today)
    importo = Column(Float, nullable=False)
    metodo = Column(String(30))  # contanti, carta, bonifico, paypal, stripe, etc.
    stato = Column(String(20), default='completato')  # completato, pending, rimborsato
    note = Column(Text)
    transazione_id = Column(String(100))  # per pagamenti online
    created_at = Column(DateTime, default=func.now())
    
    prenotazione = relationship("Prenotazione", back_populates="pagamenti")

    def __repr__(self):
        return f"<Pagamento {self.id} - {self.importo}€>"


# ====================== NUOVI MODELLI PER FUNZIONALITÀ AVANZATE ======================

class User(Base, UserMixin):
    """Utenti per multi-utente con permessi"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    ruolo = Column(String(20), default='staff')  # admin, manager, receptionist
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    
    def __repr__(self):
        return f"<User {self.username}>"

    def check_password(self, password):
        """Semplice check (in produzione usa werkzeug.security)"""
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, password)


class TaskPulizia(Base):
    """Gestione housekeeping / pulizie"""
    __tablename__ = 'task_pulizia'
    
    id = Column(Integer, primary_key=True)
    camera_id = Column(Integer, ForeignKey('camere.id'), nullable=False)
    data = Column(Date, nullable=False)
    stato = Column(String(20), default='da_fare')  # da_fare, in_corso, completato
    note = Column(Text)
    assegnato_a = Column(String(100))  # nome del personale
    created_at = Column(DateTime, default=func.now())
    
    camera = relationship("Camera", backref="pulizie")
    
    def __repr__(self):
        return f"<Pulizia Camera {self.camera_id} - {self.data}>"
