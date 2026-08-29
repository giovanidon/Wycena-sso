import streamlit as st
from google import genai
import tempfile
import os
import requests
import json
from fpdf import FPDF

# Konfiguracja strony
st.set_page_config(page_title="MS Budownictwo - Kalkulator SSO", layout="wide")

# --- Inicjalizacja domyślnych cen w pamięci aplikacji (session_state) ---
if 'ceny' not in st.session_state:
    st.session_state['ceny'] = {
        'cena_stal': 1500, 'cena_beton': 120, 'cena_mur_nosne': 80,
        'cena_mur_dzialowe': 60, 'cena_szalunki': 70, 'cena_dach': 150,
        'cena_schody': 3000, 'cena_slupy': 150, 'cena_kominy': 150,
        'mat_stal': 3500, 'mat_beton': 350, 'mat_mur_nosne': 120,
        'mat_mur_dzialowe': 80, 'mat_szalunki': 50, 'mat_dach': 250,
        'mat_schody': 2500, 'mat_slupy': 120, 'mat_kominy': 300
    }

# --- Funkcje do obsługi PDF ---
@st.cache_resource
def pobierz_czcionke():
    font_path = "DejaVuSans_v2.ttf"
    if not os.path.exists(font_path):
        url = "https://raw.githubusercontent.com/dejavu-fonts/dejavu-fonts/master/ttf/DejaVuSans.ttf"
        r = requests.get(url, allow_redirects=True)
        open(font_path, 'wb').write(r.content)
    return font_path

def generuj_pdf(tekst_raportu, sciezka_logo=None):
    font_path = pobierz_czcionke()
    pdf = FPDF()
    pdf.add_page()
    
    pdf.add_font("DejaVu", "", font_path, uni=True)
    pdf.set_font("DejaVu", size=11)
    
    if sciezka_logo and os.path.exists(sciezka_logo):
        pdf.image(sciezka_logo, x=10, y=8, w=40)
        pdf.ln(25)
    elif os.path.exists("logo.png"):
        pdf.image("logo.png", x=10, y=8, w=40)
        pdf.ln(25)
    elif os.path.exists("logo.jpg"):
        pdf.image("logo.jpg", x=10, y=8, w=40)
        pdf.ln(25)
    else:
        pdf.ln(10)
        
    pdf.set_font("DejaVu", size=16)
    pdf.cell(0, 10, txt="KOSZTORYS I HARMONOGRAM PRAC SSO", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("DejaVu", size=10)
    czysty_tekst = tekst_raportu.replace('**', '').replace('##', '').replace('#', '')
    
    for line in czysty_tekst.split('\n'):
        pdf.multi_cell(0, 6, txt=line)
        
    pdf_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(pdf_file.name)
    return pdf_file.name
# ------------------------------

# --- ALGORYTM OPTYMALIZACJI CIĘCIA (Matematyka w Pythonie) ---
def optymalizuj_ciecie_stali(lista_elementow, dlugosc_handlowa=12.0):
    lista_elementow.sort(reverse=True)
    sztangi = [] 
    for element in lista_elementow:
        if element > dlugosc_handlowa:
            continue
        zapakowano = False
        for sztanga in sztangi:
            if sum(sztanga) + element <= dlugosc_handlowa:
                sztanga.append(element)
                zapakowano = True
                break
        if not zapakowano:
            sztangi.append([element])
    return sztangi
# -----------------------------------------------------------

# 1. Konfiguracja API
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = st.text_input("Wprowadź swój klucz API Gemini:", type="password")

mnozniki_woj = {
    "Mazowieckie": 1.15, "Małopolskie": 1.08, "Pomorskie": 1.08, "Dolnośląskie": 1.06,
    "Wielkopolskie": 1.05, "Śląskie": 1.04, "Zachodniopomorskie": 1.02, "Łódzkie": 1.00,
    "Opolskie": 0.98, "Kujawsko-pomorskie": 0.95, "Lubuskie": 0.95, "Warmińsko-mazurskie": 0.92,
    "Świętokrzyskie": 0.90, "Podkarpackie": 0.90, "Podlaskie": 0.90, "Lubelskie": 0.90
}

# 2. Pasek boczny
with st.sidebar:
    st.header("Opcje Wizualne")
    wgrane_logo = st.file_uploader("Wgraj logo firmy (PNG/JPG)", type=['png', 'jpg', 'jpeg'])
    
    st.markdown("---")
    st.header("Lokalizacja Inwestycji")
    wybrane_woj = st.selectbox("Wybierz województwo", list(mnozniki_woj.keys()))
    mnoznik = mnozniki_woj[wybrane_woj]
    st.info(f"Mnożnik regionalny: **{mnoznik}x**")
    
    st.markdown("---")
    st.header("Cennik Budowlany")
    
    if st.button("🤖 Aktualizuj ceny rynkowe (AI)"):
        if api_key:
            with st.spinner(f"Szukam aktualnych cen rynkowych dla woj. {wybrane_woj}..."):
                try:
                    client = genai.Client(api_key=api_key)
                    prompt_ceny = f"""
                    Jesteś ekspertem budowlanym. Podaj szacunkowe, rynkowe ceny netto (w PLN) za robociznę i materiały dla SSO dla województwa: {wybrane_woj}.
                    Odpowiedz WYŁĄCZNIE czystym formatem JSON, bez żadnego tekstu przed ani po. Żadnych znaczników ```json.
                    Zwróć dokładnie taki format:
                    {{
                        "cena_stal": 1600,
                        "cena_beton": 140,
                        "cena_mur_nosne": 90,
                        "cena_mur_dzialowe": 65,
                        "cena_szalunki": 80,
                        "cena_dach": 160,
                        "cena_schody": 3200,
                        "cena_slupy": 160,
                        "cena_kominy": 170,
                        "mat_stal": 3600,
                        "mat_beton": 380,
                        "mat_mur_nosne": 130,
                        "mat_mur_dzialowe": 90,
                        "mat_szalunki": 60,
                        "mat_dach": 270,
                        "mat_schody": 2600,
                        "mat_slupy": 130,
                        "mat_kominy": 320
                    }}
                    """
                    response_ceny = client.models.generate_content(model='gemini-2.5-flash', contents=prompt_ceny)
                    
                    json_str = response_ceny.text.replace('
                    
