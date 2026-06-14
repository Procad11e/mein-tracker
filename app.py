import streamlit as st
import google.generativeai as genai
from datetime import datetime
import json
import pandas as pd
import os

# 1. Modernes Handy-Design & Styling
st.set_page_config(page_title="MacroTracker AI", page_icon="🍏", layout="centered")

# CSS für ein schöneres App-Feeling auf dem Smartphone
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric {
        background-color: white;
        padding: 15px;
        border-radius: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        text-align: center;
    }
    div[data-testid="stMetricValue"] { font-size: 20px !important; font-weight: bold; }
    div[data-testid="stMetricLabel"] { font-size: 12px !important; color: #6c757d; }
    .stButton>button {
        width: 100%;
        border-radius: 10px;
        font-weight: bold;
    }
    div.stProgress > div > div > div > div { background-color: #2ec4b6; }
    </style>
""", unsafe_allow_html=True)

# 2. KI mit Schlüssel verbinden
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# Automatische Modell-Suche (beibehalten, weil es funktionierte)
if "aktives_modell" not in st.session_state:
    st.session_state.aktives_modell = None
    try:
        verfuegbar = [m for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        if verfuegbar:
            for m in verfuegbar:
                if 'flash' in m.name.lower():
                    st.session_state.aktives_modell = m.name
                    break
            if not st.session_state.aktives_modell:
                for m in verfuegbar:
                    if 'pro' in m.name.lower():
                        st.session_state.aktives_modell = m.name
                        break
            if not st.session_state.aktives_modell:
                st.session_state.aktives_modell = verfuegbar[0].name
    except Exception as e:
        st.error(f"Fehler bei der Modellsuche: {e}")

if not st.session_state.aktives_modell:
    st.error("🚨 Kein KI-Modell verfügbar.")
    st.stop()

model = genai.GenerativeModel(st.session_state.aktives_modell)

# 3. Dauerhafter Speicher (Datei auf dem Server)
DATEI_PFAD = "tracker_daten.json"

def daten_laden():
    if os.path.exists(DATEI_PFAD):
        try:
            with open(DATEI_PFAD, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {"datum": datetime.now().strftime("%Y-%m-%d"), "mahlzeiten": []}
    return {"datum": datetime.now().strftime("%Y-%m-%d"), "mahlzeiten": []}

def daten_speichern(daten):
    with open(DATEI_PFAD, "w", encoding="utf-8") as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)

# Daten beim Start aus der Datei laden
gespeicherte_daten = daten_laden()
heute = datetime.now().strftime("%Y-%m-%d")

# Automatischer Tages-Reset: Wenn ein neuer Tag anbricht, lösche die alten Mahlzeiten
if gespeicherte_daten.get("datum") != heute:
    gespeicherte_daten = {"datum": heute, "mahlzeiten": []}
    daten_speichern(gespeicherte_daten)

st.session_state.mahlzeiten = gespeicherte_daten["mahlzeiten"]

# 4. Seitenleiste für Einstellungen & Löschen
with st.sidebar:
    st.header("⚙️ Einstellungen")
    kcal_ziel = st.number_input("Dein Tagesziel (kcal):", min_value=1000, max_value=5000, value=2500, step=100)
    
    st.divider()
    st.subheader("🗑️ Daten verwalten")
    # Neuer Löschen-Button in der Seitenleiste
    if st.button("🔴 Heutige Liste löschen", type="secondary"):
        st.session_state.mahlzeiten = []
        daten_speichern({"datum": heute, "mahlzeiten": []})
        st.toast("Alle Mahlzeiten gelöscht!", icon="🗑️")
        st.rerun()

# 5. Haupt-Ansicht / Dashboard
st.title("🍏 MacroTracker AI")
st.caption("Einfach sprechen oder tippen – die KI trackt für dich.")

# Werte berechnen
gesamt_kcal = sum(m['kcal'] for m in st.session_state.mahlzeiten)
gesamt_protein = sum(m['protein'] for m in st.session_state.mahlzeiten)
gesamt_carbs = sum(m['carbs'] for m in st.session_state.mahlzeiten)
gesamt_fett = sum(m['fett'] for m in st.session_state.mahlzeiten)

# Schicke Kacheln (Nebeneinander auf dem Handy)
col1, col2, col3, col4 = st.columns(4)
col1.metric("Kcal", f"{gesamt_kcal}/{kcal_ziel}")
col2.metric("Protein", f"{gesamt_protein}g")
col3.metric("Carbs", f"{gesamt_carbs}g")
col4.metric("Fett", f"{gesamt_fett}g")

# Fortschrittsbalken
fortschritt = min(gesamt_kcal / kcal_ziel, 1.0)
st.progress(fortschritt)
st.divider()

# 6. Eingabebereich
st.subheader("🎙️ Was hast du gegessen?")
user_input = st.text_input("Nutze das Mikrofon auf der Tastatur:", placeholder="z.B. 1 Packung Aldi Sucuk und 3 Rewe Eier")

if st.button("🚀 Hinzufügen", type="primary"):
    if user_input:
        with st.spinner("Nährwerte werden ermittelt..."):
            try:
                # DEUTSCHE PROMPTING-ANWEISUNG: Die KI lernt deutsche Produkte kennen
                prompt = f"""
                Du bist ein deutscher Ernährungsberater und Experte für Produkte aus deutschen Supermärkten (Aldi, Lidl, Rewe, Penny, Edeka).
                Schätze die Nährwerte für folgenden Input so präzise wie möglich ab. Beziehe typische deutsche Eigenmarken (z.B. Milbona, Gut&Günstig, Ja!, K-Classic) mit ein, falls erwähnt.
                Input: "{user_input}"
                
                Antworte AUSSCHLIESSLICH mit einem JSON-Objekt. Schreibe KEINEN Text davor oder danach (kein ```json).
                Schlüssel: "beschreibung" (String, kurze deutsche Zusammenfassung), "kcal" (Integer), "protein" (Integer), "carbs" (Integer), "fett" (Integer).
                """
                
                antwort = model.generate_content(prompt)
                text = antwort.text
                
                start = text.find('{')
                end = text.rfind('}') + 1
                
                if start != -1 and end != 0:
                    clean_text = text[start:end]
                    werte = json.loads(clean_text)
                    
                    # Uhrzeit stempeln
                    werte["uhrzeit"] = datetime.now().strftime("%H:%M")
                    
                    # Im Session State UND dauerhaft in der Datei speichern
                    st.session_state.mahlzeiten.append(werte)
                    daten_speichern({"datum": heute, "mahlzeiten": st.session_state.mahlzeiten})
                    
                    st.toast("Erfolgreich eingetragen!", icon="✅")
                    st.rerun()
                else:
                    st.error("Fehler beim Lesen der Nährwerte. Bitte genauer eingeben.")
                
            except Exception as e:
                st.error(f"Fehler: {e}")
    else:
        st.warning("Bitte gib erst etwas ein.")

# 7. Die heutige Liste (Responsive Tabelle)
if st.session_state.mahlzeiten:
    st.divider()
    st.subheader("🍽️ Dein heutiges Essen")
    df = pd.DataFrame(st.session_state.mahlzeiten)
    df = df[['uhrzeit', 'beschreibung', 'kcal', 'protein', 'carbs', 'fett']]
    df.columns = ['Zeit', 'Mahlzeit', 'Kcal', 'Prot (g)', 'Carb (g)', 'Fett (g)']
    st.dataframe(df, use_container_width=True, hide_index=True)
