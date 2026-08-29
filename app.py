import streamlit as st
from google import genai
import tempfile
import os
import requests
from fpdf import FPDF

# Konfiguracja strony
st.set_page_config(page_title="MS Budownictwo - Kalkulator SSO", layout="wide")
st.title("🏗️ MS Budownictwo Kalkulator robocizny i materiałów SSO")

# --- Funkcje do obsługi PDF ---
@st.cache_resource
def pobierz_czcionke():
    """Pobiera czcionkę obsługującą polskie znaki do generowania PDF."""
    font_path = "DejaVuSans_v2.ttf" # Zmieniona nazwa, by wymusić świeże pobranie
    if not os.path.exists(font_path):
        # Nowy, niezawodny link bezpośrednio od twórców czcionki
        url = "https://raw.githubusercontent.com/dejavu-fonts/dejavu-fonts/master/ttf/DejaVuSans.ttf"
        r = requests.get(url, allow_redirects=True)
        open(font_path, 'wb').write(r.content)
    return font_path

def generuj_pdf(tekst_raportu):
    font_path = pobierz_czcionke()
    pdf = FPDF()
    pdf.add_page()
    
    # Obsługa polskich znaków
    pdf.add_font("DejaVu", "", font_path, uni=True)
    pdf.set_font("DejaVu", size=11)
    
    # Dodawanie logo, jeśli plik istnieje
    if os.path.exists("logo.png"):
        pdf.image("logo.png", x=10, y=8, w=40)
        pdf.ln(25)
    elif os.path.exists("logo.jpg"):
        pdf.image("logo.jpg", x=10, y=8, w=40)
        pdf.ln(25)
    else:
        pdf.ln(10)
        
    # Tytuł
    pdf.set_font("DejaVu", size=16)
    pdf.cell(0, 10, txt="KOSZTORYS I HARMONOGRAM PRAC SSO", ln=True, align='C')
    pdf.ln(10)
    
    # Treść właściwa
    pdf.set_font("DejaVu", size=10)
    
    # Czyszczenie tekstu z ewentualnych znaczków Markdown, by PDF był ładny
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

# Słownik z mnożnikami regionalnymi
mnozniki_woj = {
    "Mazowieckie": 1.15, "Małopolskie": 1.08, "Pomorskie": 1.08, "Dolnośląskie": 1.06,
    "Wielkopolskie": 1.05, "Śląskie": 1.04, "Zachodniopomorskie": 1.02, "Łódzkie": 1.00,
    "Opolskie": 0.98, "Kujawsko-pomorskie": 0.95, "Lubuskie": 0.95, "Warmińsko-mazurskie": 0.92,
    "Świętokrzyskie": 0.90, "Podkarpackie": 0.90, "Podlaskie": 0.90, "Lubelskie": 0.90
}

# 2. Pasek boczny
with st.sidebar:
    st.header("Lokalizacja Inwestycji")
    wybrane_woj = st.selectbox("Wybierz województwo", list(mnozniki_woj.keys()))
    mnoznik = mnozniki_woj[wybrane_woj]
    st.info(f"Mnożnik regionalny: **{mnoznik}x**")

    st.markdown("---")
    st.header("1. Cennik Robocizny (PLN netto)")
    cena_stal = st.number_input("Robocizna: Zbrojenie (za 1 tonę)", value=1500)
    cena_beton = st.number_input("Robocizna: Wylewanie (za 1 m3)", value=120)
    cena_mur_nosne = st.number_input("Robocizna: Ściany NOŚNE (za 1 m2)", value=80)
    cena_mur_dzialowe = st.number_input("Robocizna: Ściany DZIAŁOWE (za 1 m2)", value=60)
    cena_szalunki = st.number_input("Robocizna: Szalowanie (za 1 m2)", value=70)
    cena_dach = st.number_input("Robocizna: Więźba i pokrycie (za 1 m2)", value=150)
    cena_schody = st.number_input("Robocizna: Schody żelbetowe (za komplet/piętro)", value=3000)
    cena_slupy = st.number_input("Robocizna: Słupy żelbetowe (za 1 mb)", value=150)
    marza = st.slider("Narzut / Marża wykonawcy (%)", 0, 50, 15)
    
    st.markdown("---")
    st.header("2. Cennik Materiałów (PLN netto)")
    mat_stal = st.number_input("Materiał: Stal zbrojeniowa (za 1 tonę)", value=3500)
    mat_beton = st.number_input("Materiał: Beton (za 1 m3)", value=350)
    mat_mur_nosne = st.number_input("Materiał: Bloczki NOŚNE (za 1 m2)", value=120)
    mat_mur_dzialowe = st.number_input("Materiał: Bloczki DZIAŁOWE (za 1 m2)", value=80)
    mat_szalunki = st.number_input("Materiał: Drewno/sklejka (za 1 m2)", value=50)
    mat_dach = st.number_input("Materiał: Więźba + dachówka/blacha (za 1 m2)", value=250)
    mat_schody = st.number_input("Materiał: Schody (beton/stal/szalunek za komplet)", value=2500)
    mat_slupy = st.number_input("Materiał: Słupy (beton/stal/szalunek za 1 mb)", value=120)

    st.markdown("---")
    st.header("Planowanie Czasu")
    ekipa = st.number_input("Liczba pracowników na budowie", min_value=1, value=3)

# 3. Wgrywanie projektów
uploaded_files = st.file_uploader("Wgraj projekty konstrukcyjne (PDF)", type=['pdf'], accept_multiple_files=True)

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
            
            instrukcja = f"""
            Jesteś doświadczonym kosztorysantem i analitykiem rynku budowlanego. Przeanalizuj ZAŁĄCZONE PROJEKTY BUDOWLANE (PDF). Inwestycja: Stan Surowy Otwarty (SSO), województwo {wybrane_woj} (mnożnik regionalny: {mnoznik}).
            
            UWAGA FORMATOWANIE: RAPORT TRAFI DO PLIKU PDF. Nie używaj gwiazdek (*), ani krzyżyków (#). Używaj wielkich liter dla głównych NAGŁÓWKÓW. Używaj zwykłych myślników do list.
            
            Zadanie 1 - SZCZEGÓŁOWY PRZEDMIAR:
            Znajdź zapotrzebowanie na: tony stali, beton (m3), szalunki (m2), dach (m2), schody żelbetowe (ilość kompletów/kondygnacji), słupy żelbetowe (łączna długość w mb).
            Podziel ściany osobno w rozbiciu na kondygnacje i rodzaj: nośne parter, nośne piętro, działowe parter, działowe piętro.
            
            Zadanie 2 - ROBOCIZNA:
            Stawki bazowe: Zbrojenie: {cena_stal} PLN/t, Betonowanie: {cena_beton} PLN/m3, Ściany nośne: {cena_mur_nosne} PLN/m2, Ściany działowe: {cena_mur_dzialowe} PLN/m2, Szalowanie: {cena_szalunki} PLN/m2, Dach: {cena_dach} PLN/m2, Schody żelbetowe: {cena_schody} PLN/komplet, Słupy żelbetowe: {cena_slupy} PLN/mb.
            Pokaż koszty w rozbiciu. Przemnóż wynik całości przez {mnoznik} i na koniec dodaj {marza}% marży.
            
            Zadanie 3 - MATERIAŁY:
            Stawki bazowe: Stal: {mat_stal} PLN/t, Beton: {mat_beton} PLN/m3, Ściany nośne: {mat_mur_nosne} PLN/m2, Ściany działowe: {mat_mur_dzialowe} PLN/m2, Szalunki: {mat_szalunki} PLN/m2, Dach: {mat_dach} PLN/m2, Schody żelbetowe: {mat_schody} PLN/komplet, Słupy żelbetowe: {mat_slupy} PLN/mb.
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
            odpowiedz = client.models.generate_content(model='gemini-3.6-flash', contents=zawartosc)
            
            st.success("Analiza zakończona sukcesem!")
            st.write(odpowiedz.text)
            
            # Generowanie pliku PDF
            pdf_path = generuj_pdf(odpowiedz.text)
            
            with open(pdf_path, "rb") as pdf_file:
                pdf_bytes = pdf_file.read()
            
            st.download_button(
                label="💾 Pobierz raport z wyceną (PDF)",
                data=pdf_bytes,
                file_name="Wycena_SSO.pdf",
                mime="application/pdf"
            )
            
            # Usuwanie plików tymczasowych
            os.remove(pdf_path)
            for sciezka in sciezki_tymczasowe:
                os.remove(sciezka)

        except Exception as e:
            st.error(f"Wystąpił błąd podczas analizy: {e}")
elif not api_key:
    st.warning("Podaj klucz API, aby móc wygenerować wycenę.")
elif not uploaded_files:
    st.warning("Wgraj co najmniej jeden plik PDF z projektem.")
