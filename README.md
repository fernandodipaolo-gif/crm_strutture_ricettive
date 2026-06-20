# CRM per Strutture Ricettive

Sistema completo per la gestione di prenotazioni, pagamenti, arrivi e partenze per hotel, B&B, appartamenti e strutture ricettive.

## Caratteristiche principali

- **Dashboard** con arrivi e partenze del giorno, occupazione e ricavi
- **Gestione Strutture** (multi-proprietà supportata)
- **Gestione Camere/Unità** con prezzi base
- **Prenotazioni** complete con verifica disponibilità automatica
- **Gestione Ospiti** con storico
- **Pagamenti** multipli per prenotazione (acconti + saldi)
- **Check-in / Check-out** rapidi con aggiornamento stato camera
- **Filtri e ricerca** avanzati
- **Report** base + esportazione Excel
- Interfaccia moderna responsive (Bootstrap 5)

## Installazione (su tuo computer)

1. Assicurati di avere Python 3.10+ installato

2. Clona o scarica questa cartella

3. Crea un ambiente virtuale ed installa le dipendenze:
```bash
python -m venv venv
source venv/bin/activate          # su Linux/Mac
# venv\Scripts\activate           # su Windows

pip install -r requirements.txt
```

4. Avvia l'applicazione:
```bash
python app.py
```

5. Apri il browser su: **http://127.0.0.1:5000**

I dati demo verranno creati automaticamente al primo avvio (B&B Il Glicine + 1 prenotazione di esempio).

## Struttura Database

- **strutture**: le tue proprietà ricettive
- **camere**: unità abitative collegate alle strutture
- **ospiti**: anagrafica clienti
- **prenotazioni**: core del sistema con date, stato, prezzi
- **pagamenti**: storico incassi collegati alle prenotazioni

## Personalizzazione

- Modifica `app.config['SECRET_KEY']` in produzione
- Per usare PostgreSQL/MySQL cambia `SQLALCHEMY_DATABASE_URI` in `.env` o direttamente in `app.py`
- Aggiungi autenticazione utenti con Flask-Login se necessario

## Prossimi sviluppi suggeriti

- Calendario visivo interattivo (FullCalendar)
- Integrazione con channel manager (Booking.com, Airbnb)
- Fatturazione automatica / invio email
- Statistiche avanzate con grafici (Chart.js)
- App mobile o PWA

Sviluppato con ❤️ per semplificare la vita degli albergatori e gestori di strutture ricettive.
