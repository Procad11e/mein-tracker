import streamlit as st
import google.generativeai as genai
from datetime import datetime
import json
import pandas as pd

# 1. Seiten-Design einstellen
st.set_page_config(page_title="Mein Tracker", page_icon="🍏", layout="centered")

# 2. KI (Gemini) vorbereiten
# Der Key wird später sicher in Streamlit hinterlegt
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
# Wir nutzen Flash, weil es super schnell ist, und zwingen es, JSON auszugeben
model = genai.GenerativeModel('gemini-1.5-flash', generation_config={"response_mime_type": "application/json"})

# 3. Speicher (Session State) für den täglichen Reset vorbereiten
heute = datetime.now().strftime("%Y-%m-%d")

if 'datum' not in st.session_state or st.session_state.datum != heute:
    st.session_state.datum = heute
    st.session_state.mahlzeiten = []

# 4. Seitenleiste für die Einstellungen (Kcal-Ziel)
with st.sidebar:
    st.header("⚙️ Einstellungen")
    kcal_ziel = st.number_input("Dein Tagesziel (kcal):", min_value=1000, max_value=5000, value=2500, step=100)
    st.write("Jeden Tag um 00:00 Uhr setzt sich die Anzeige automatisch zurück.")

# 5. Haupt-Ansicht
st.title("🍏 Mein Ernährungs-Tracker")

# Bisherige Werte zusammenrechnen
gesamt_kcal = sum(m['kcal'] for m in st.session_state.mahlzeiten)
gesamt_protein = sum(m['protein'] for m in st.session_state.mahlzeiten)
gesamt_carbs = sum(m['carbs'] for m in st.session_state.mahlzeiten)
gesamt_fett = sum(m['fett'] for m in st.session_state.mahlzeiten)

# Übersichtsbereich (oben)
st.subheader("📊 Deine heutige Übersicht")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Kcal", f"{gesamt_kcal} / {kcal_ziel}")
col2.metric("Protein", f"{gesamt_protein}g")
col3.metric("Carbs", f"{gesamt_carbs}g")
col4.metric("Fett", f"{gesamt_fett}g")

# Fortschrittsbalken für Kalorien
fortschritt = min(gesamt_kcal / kcal_ziel, 1.0)
st.progress(fortschritt)

st.divider()

# 6. Eingabebereich
st.subheader("🎙️ Was hast du gegessen?")
user_input = st.text_input("Nutze die Diktierfunktion auf der Tastatur:", placeholder="z.B. 4 Eier und 30g Sucuk vom Türken")

if st.button("Hinzufügen"):
    if user_input:
        with st.spinner("KI berechnet die Nährwerte..."):
            try:
                # KI Prompt (Anweisung an mich/Gemini)
                prompt = f"""
                Du bist ein professioneller Ernährungsberater. Schätze die Nährwerte für den folgenden Input so gut wie möglich ab.
                Input: "{user_input}"
                Antworte EXAKT mit einem JSON-Objekt, das diese Schlüssel hat (Werte müssen reine Zahlen sein):
                "beschreibung" (String, kurze Zusammenfassung was gegessen wurde), "kcal" (Integer), "protein" (Integer), "carbs" (Integer), "fett" (Integer).
                """
                
                # KI fragen
                antwort = model.generate_content(prompt)
                werte = json.loads(antwort.text)
                
                # Uhrzeit hinzufügen
                jetzt = datetime.now().strftime("%H:%M")
                werte["uhrzeit"] = jetzt
                
                # In der Liste speichern
                st.session_state.mahlzeiten.append(werte)
                st.rerun() # Seite neu laden, um die neuen Zahlen oben anzuzeigen
                
            except Exception as e:
                st.error("Da ist etwas schiefgelaufen. Bitte versuche es nochmal.")
    else:
        st.warning("Bitte gib erst etwas ein.")

# 7. Liste der heutigen Mahlzeiten anzeigen
if st.session_state.mahlzeiten:
    st.divider()
    st.subheader("🍽️ Dein heutiges Essen")
    
    # Tabelle schön formatieren
    df = pd.DataFrame(st.session_state.mahlzeiten)
    df = df[['uhrzeit', 'beschreibung', 'kcal', 'protein', 'carbs', 'fett']]
    df.columns = ['Zeit', 'Mahlzeit', 'Kcal', 'Protein (g)', 'Kohlenhydrate (g)', 'Fett (g)']
    st.dataframe(df, use_container_width=True, hide_index=True)
