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
        'cena_schody': 3000, 'cena_slupy': 150,
        'mat_stal': 3500, 'mat_beton': 350, 'mat_mur_nosne': 120,
        'mat_mur_dzialowe': 80, 'mat_szalunki': 50, 'mat_dach': 250,
        'mat_schody': 2500, 'mat_slupy': 120
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
    
    # Przycisk do automatycznej aktualizacji cen przez AI
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
                        "mat_stal": 3600,
                        "mat_beton": 380,
                        "mat_mur_nosne": 130,
                        "mat_mur_dzialowe": 90,
                        "mat_szalunki": 60,
                        "mat_dach": 270,
                        "mat_schody": 2600,
                        "mat_slupy": 130
                    }}
                    Wszystkie wartości muszą być liczbami całkowitymi.
                    """
                    response_ceny = client.models.generate_content(model='gemini-2.5-flash', contents=prompt_ceny)
                    
                    # Czyszczenie odpowiedzi na wypadek, gdyby AI dodało znaczniki markdown
                    json_str = response_ceny.text.replace('```json', '').replace('```', '').strip()
                    nowe_ceny = json.loads(json_str)
                    
                    # Aktualizacja stanu sesji
                    for klucz in nowe_ceny:
                        if klucz in st.session_state['ceny']:
                            st.session_state['ceny'][klucz] = nowe_ceny[klucz]
                            
                    st.success("Zaktualizowano cennik!")
                    st.rerun() # Przeładowuje stronę, aby pokazać nowe wartości
                except Exception as e:
                    st.error(f"Nie udało się pobrać cen automatycznie. Błąd: {e}")
        else:
            st.warning("Najpierw podaj klucz API Gemini, aby pobrać ceny.")

    st.subheader("1. Robocizna (PLN netto)")
    st.session_state['ceny']['cena_stal'] = st.number_input("Robocizna: Zbrojenie (za 1 tonę)", value=st.session_state['ceny']['cena_stal'])
    st.session_state['ceny']['cena_beton'] = st.number_input("Robocizna: Wylewanie (za 1 m3)", value=st.session_state['ceny']['cena_beton'])
    st.session_state['ceny']['cena_mur_nosne'] = st.number_input("Robocizna: Ściany NOŚNE (za 1 m2)", value=st.session_state['ceny']['cena_mur_nosne'])
    st.session_state['ceny']['cena_mur_dzialowe'] = st.number_input("Robocizna: Ściany DZIAŁOWE (za 1 m2)", value=st.session_state['ceny']['cena_mur_dzialowe'])
    st.session_state['ceny']['cena_szalunki'] = st.number_input("Robocizna: Szalowanie (za 1 m2)", value=st.session_state['ceny']['cena_szalunki'])
    st.session_state['ceny']['cena_dach'] = st.number_input("Robocizna: Więźba i pokrycie (za 1 m2)", value=st.session_state['ceny']['cena_dach'])
    st.session_state['ceny']['cena_schody'] = st.number_input("Robocizna: Schody żelbetowe (za komplet)", value=st.session_state['ceny']['cena_schody'])
    st.session_state['ceny']['cena_slupy'] = st.number_input("Robocizna: Słupy żelbetowe (za 1 mb)", value=st.session_state['ceny']['cena_slupy'])
    
    marza = st.slider("Narzut / Marża wykonawcy (%)", 0, 50, 15)
    
    st.subheader("2. Materiały (PLN netto)")
    st.session_state['ceny']['mat_stal'] = st.number_input("Materiał: Stal zbrojeniowa (za 1 tonę)", value=st.session_state['ceny']['mat_stal'])
    st.session_state['ceny']['mat_beton'] = st.number_input("Materiał: Beton (za 1 m3)", value=st.session_state['ceny']['mat_beton'])
    st.session_state['ceny']['mat_mur_nosne'] = st.number_input("Materiał: Bloczki NOŚNE (za 1 m2)", value=st.session_state['ceny']['mat_mur_nosne'])
    st.session_state['ceny']['mat_mur_dzialowe'] = st.number_input("Materiał: Bloczki DZIAŁOWE (za 1 m2)", value=st.session_state['ceny']['mat_mur_dzialowe'])
    st.session_state['ceny']['mat_szalunki'] = st.number_input("Materiał: Drewno/sklejka (za 1 m2)", value=st.session_state['ceny']['mat_szalunki'])
    st.session_state['ceny']['mat_dach'] = st.number_input("Materiał: Więźba + dachówka/blacha (za 1 m2)", value=st.session_state['ceny']['mat_dach'])
    st.session_state['ceny']['mat_schody'] = st.number_input("Materiał: Schody (za komplet)", value=st.session_state['ceny']['mat_schody'])
    st.session_state['ceny']['mat_slupy'] = st.number_input("Materiał: Słupy (za 1 mb)", value=st.session_state['ceny']['mat_slupy'])

    st.markdown("---")
    st.header("Planowanie Czasu")
    ekipa = st.number_input("Liczba pracowników na budowie", min_value=1, value=3)

# --- Układ nagłówka (Tytuł + wgrane Logo) ---
sciezka_do_logo = None
if wgrane_logo:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_logo:
        tmp_logo.write(wgrane_logo.getvalue())
        sciezka_do_logo = tmp_logo.name
    
    col1, col2 = st.columns([1, 6])
    with col1:
        st.image(wgrane_logo, use_container_width=True)
    with col2:
        st.title("MS Budownictwo Kalkulator robocizny i materiałów SSO")
else:
    st.title("MS Budownictwo Kalkulator robocizny i materiałów SSO")

# 3. Wgrywanie projektów
st.markdown("### Wgraj projekty konstrukcyjne (PDF)")
uploaded_files = st.file_uploader("", type=['pdf'], accept_multiple_files=True)

if st.button("Generuj Kompleksową Wycenę") and uploaded_files and api_key:
    with st.spinner("Tworzenie wyceny i generowanie pliku PDF (może to zająć do kilkunastu sekund)..."):
        try:
            client = genai.Client(api_key=api_key)
            pliki_do_ai = []
            sciezki_tymczasowe = []
            
            for file in uploaded_files:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                    tmp_file.write(file.getvalue())
                    tmp_file_path = tmp_file.name
                    sciezki_tymczasowe.append(tmp_file_path)

                pdf_plik = client.files.upload(file=tmp_file_path)
                pliki_do_ai.append(pdf_plik)
            
            # Pobranie cen z session_state do promptu
            c = st.session_state['ceny']
            
            instrukcja = f"""
            Jesteś doświadczonym kosztorysantem i analitykiem rynku budowlanego. Przeanalizuj ZAŁĄCZONE PROJEKTY BUDOWLANE (PDF). Inwestycja: Stan Surowy Otwarty (SSO), województwo {wybrane_woj} (mnożnik regionalny: {mnoznik}).
            
            UWAGA FORMATOWANIE: RAPORT TRAFI DO PLIKU PDF. Nie używaj gwiazdek (*), ani krzyżyków (#). Używaj wielkich liter dla głównych NAGŁÓWKÓW. Używaj zwykłych myślników do list.
            
            Zadanie 1 - SZCZEGÓŁOWY PRZEDMIAR:
            Znajdź zapotrzebowanie na: tony stali, beton (m3), szalunki (m2), dach (m2), schody żelbetowe (ilość kompletów/kondygnacji), słupy żelbetowe (łączna długość w mb).
            Podziel ściany osobno w rozbiciu na kondygnacje i rodzaj: nośne parter, nośne piętro, działowe parter, działowe piętro.
            
            Zadanie 2 - ROBOCIZNA:
            Stawki bazowe: Zbrojenie: {c['cena_stal']} PLN/t, Betonowanie: {c['cena_beton']} PLN/m3, Ściany nośne: {c['cena_mur_nosne']} PLN/m2, Ściany działowe: {c['cena_mur_dzialowe']} PLN/m2, Szalowanie: {c['cena_szalunki']} PLN/m2, Dach: {c['cena_dach']} PLN/m2, Schody żelbetowe: {c['cena_schody']} PLN/komplet, Słupy żelbetowe: {c['cena_slupy']} PLN/mb.
            Pokaż koszty w rozbiciu. Przemnóż wynik całości przez {mnoznik} i na koniec dodaj {marza}% marży.
            
            Zadanie 3 - MATERIAŁY:
            Stawki bazowe: Stal: {c['mat_stal']} PLN/t, Beton: {c['mat_beton']} PLN/m3, Ściany nośne: {c['mat_mur_nosne']} PLN/m2, Ściany działowe: {c['mat_mur_dzialowe']} PLN/m2, Szalunki: {c['mat_szalunki']} PLN/m2, Dach: {c['mat_dach']} PLN/m2, Schody żelbetowe: {c['mat_schody']} PLN/komplet, Słupy żelbetowe: {c['mat_slupy']} PLN/mb.
            Pokaż wyraźny podział kosztów i przemnóż je przez {mnoznik}.
            
            Zadanie 4 - HARMONOGRAM PRAC:
            Oszacuj dni robocze dla {ekipa} pracowników (8h pracy). Rozbij czas trwania wyraźnie na: fundamenty, ściany nośne (kondygnacjami), stropy, dach, słupy, schody.
            
            Zadanie 5 - TRANSZE PŁATNOŚCI:
            Podziel prace drobno na etapy (np. Ławy, Ściany fundamentowe, Strop itp.). W każdym etapie wyraźnie rozbij: ile to ZALICZKA NA MATERIAŁ, a ile ZAPŁATA ZA ROBOCIZNĘ.
            
            Zadanie 6 - SYMULACJA SZANS AKCEPTACJI I WIDEŁKI CENOWE:
            Na podstawie całkowitej wyliczonej kwoty (z marżą), oceń procentową szansę na akceptację tej oferty przez inwestora, traktując ją jako rynkowy wariant bazowy.
            Następnie stwórz zestawienie wariantów (widełki), pokazując jak zmienią się procentowe szanse na akceptację, gdy wykonawca:
            - Obniży całkowitą cenę o 5%
            - Podniesie całkowitą cenę o 5%
            - Podniesie całkowitą cenę o 10%
            - Podniesie całkowitą cenę o 20%
            Przy każdym wariancie podaj nową kwotę całkowitą, nowe szanse procentowe oraz jednozdaniowe uzasadnienie psychologiczne/rynkowe tej zmiany.
            """

            zawartosc = pliki_do_ai + [instrukcja]
            odpowiedz = client.models.generate_content(model='gemini-2.5-flash', contents=zawartosc)
            
            st.success("Analiza zakończona sukcesem!")
            st.write(odpowiedz.text)
            
            pdf_path = generuj_pdf(odpowiedz.text, sciezka_do_logo)
            
            with open(pdf_path, "rb") as pdf_file:
                pdf_bytes = pdf_file.read()
            
            st.download_button(
                label="💾 Pobierz raport z wyceną (PDF)",
                data=pdf_bytes,
                file_name="Wycena_SSO.pdf",
                mime="application/pdf"
            )
            
            os.remove(pdf_path)
            for sciezka in sciezki_tymczasowe:
                os.remove(sciezka)
            if sciezka_do_logo:
                os.remove(sciezka_do_logo)

        except Exception as e:
            st.error(f"Wystąpił błąd podczas analizy: {e}")
elif not api_key:
    st.warning("Podaj klucz API, aby móc wygenerować wycenę.")
elif not uploaded_files:
    st.warning("Wgraj co najmniej jeden plik PDF z projektem.")
