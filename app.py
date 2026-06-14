import streamlit as st
import google.generativeai as genai
from datetime import datetime
import json
import pandas as pd

st.set_page_config(page_title="Mein Tracker", page_icon="🍏", layout="centered")

# KI mit Schlüssel verbinden
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# ==========================================
# NEUE DENKWEISE: Automatische Modell-Suche
# ==========================================
# Die App sucht einmalig nach Modellen, die bei dir erlaubt sind, und merkt sich das.
if "aktives_modell" not in st.session_state:
    st.session_state.aktives_modell = None
    try:
        verfuegbar = [m for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        if verfuegbar:
            # Wir versuchen zuerst ein schnelles "Flash" oder starkes "Pro" Modell zu finden
            for m in verfuegbar:
                if 'flash' in m.name.lower():
                    st.session_state.aktives_modell = m.name
                    break
            
            # Falls kein Flash da ist, suchen wir nach Pro
            if not st.session_state.aktives_modell:
                for m in verfuegbar:
                    if 'pro' in m.name.lower():
                        st.session_state.aktives_modell = m.name
                        break
            
            # Falls beides nicht da ist, nehmen wir einfach das allererste, das Text generieren kann
            if not st.session_state.aktives_modell:
                st.session_state.aktives_modell = verfuegbar[0].name
                
    except Exception as e:
        st.error(f"Fehler bei der Kontaktaufnahme mit Google: {e}")

# Wenn der Scanner absolut nichts findet, geben wir eine klare Warnung aus.
if not st.session_state.aktives_modell:
    st.error("🚨 Dein API-Key hat aktuell keine Freigabe für Google-Modelle. (Oft passiert das bei neuen Accounts im EU-Raum).")
    st.stop()

# Wir starten die KI genau mit dem Modell, das der Scanner gefunden hat
model = genai.GenerativeModel(st.session_state.aktives_modell)

# ==========================================
# Rest der Tracker-App
# ==========================================
heute = datetime.now().strftime("%Y-%m-%d")

if 'datum' not in st.session_state or st.session_state.datum != heute:
    st.session_state.datum = heute
    st.session_state.mahlzeiten = []

with st.sidebar:
    st.header("⚙️ Einstellungen")
    # Hier zeigen wir dir zur Kontrolle an, welches Modell der Scanner gefunden hat!
    st.success(f"Aktives KI-Modell:\n{st.session_state.aktives_modell.replace('models/', '')}")
    kcal_ziel = st.number_input("Dein Tagesziel (kcal):", min_value=1000, max_value=5000, value=2500, step=100)

st.title("🍏 Mein Ernährungs-Tracker")

gesamt_kcal = sum(m['kcal'] for m in st.session_state.mahlzeiten)
gesamt_protein = sum(m['protein'] for m in st.session_state.mahlzeiten)
gesamt_carbs = sum(m['carbs'] for m in st.session_state.mahlzeiten)
gesamt_fett = sum(m['fett'] for m in st.session_state.mahlzeiten)

st.subheader("📊 Deine heutige Übersicht")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Kcal", f"{gesamt_kcal} / {kcal_ziel}")
col2.metric("Protein", f"{gesamt_protein}g")
col3.metric("Carbs", f"{gesamt_carbs}g")
col4.metric("Fett", f"{gesamt_fett}g")

fortschritt = min(gesamt_kcal / kcal_ziel, 1.0)
st.progress(fortschritt)
st.divider()

st.subheader("🎙️ Was hast du gegessen?")
user_input = st.text_input("Nutze die Diktierfunktion:", placeholder="z.B. 4 Eier und 30g Sucuk")

if st.button("Hinzufügen"):
    if user_input:
        with st.spinner("KI berechnet die Nährwerte..."):
            try:
                prompt = f"""
                Du bist ein professioneller Ernährungsberater. Schätze die Nährwerte für den folgenden Input ab.
                Input: "{user_input}"
                Antworte AUSSCHLIESSLICH mit einem JSON-Objekt. Schreibe keinen Text davor oder danach.
                Schlüssel: "beschreibung" (String), "kcal" (Integer), "protein" (Integer), "carbs" (Integer), "fett" (Integer).
                """
                
                antwort = model.generate_content(prompt)
                text = antwort.text
                
                start = text.find('{')
                end = text.rfind('}') + 1
                
                if start != -1 and end != 0:
                    clean_text = text[start:end]
                    werte = json.loads(clean_text)
                    
                    jetzt = datetime.now().strftime("%H:%M")
                    werte["uhrzeit"] = jetzt
                    
                    st.session_state.mahlzeiten.append(werte)
                    st.rerun()
                else:
                    st.error("Fehler beim Auslesen der Werte.")
                
            except Exception as e:
                st.error(f"Fehler bei der Berechnung: {e}")
    else:
        st.warning("Bitte gib erst etwas ein.")

if st.session_state.mahlzeiten:
    st.divider()
    st.subheader("🍽️ Dein heutiges Essen")
    df = pd.DataFrame(st.session_state.mahlzeiten)
    df = df[['uhrzeit', 'beschreibung', 'kcal', 'protein', 'carbs', 'fett']]
    df.columns = ['Zeit', 'Mahlzeit', 'Kcal', 'Protein (g)', 'Kohlenhydrate (g)', 'Fett (g)']
    st.dataframe(df, use_container_width=True, hide_index=True)
