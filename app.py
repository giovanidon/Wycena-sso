import streamlit as st
from google import genai
import tempfile
import os

# Konfiguracja strony
st.set_page_config(page_title="Wycena SSO - AI", layout="wide")
st.title("🏗️ Kalkulator Robocizny i Materiałów SSO")

# 1. Konfiguracja API (Pobieranie z bezpiecznego sejfu)
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = st.text_input("Wprowadź swój klucz API Gemini:", type="password")

# Słownik z mnożnikami regionalnymi (względem średniej krajowej)
mnozniki_woj = {
    "Mazowieckie": 1.15,
    "Małopolskie": 1.08,
    "Pomorskie": 1.08,
    "Dolnośląskie": 1.06,
    "Wielkopolskie": 1.05,
    "Śląskie": 1.04,
    "Zachodniopomorskie": 1.02,
    "Łódzkie": 1.00,
    "Opolskie": 0.98,
    "Kujawsko-pomorskie": 0.95,
    "Lubuskie": 0.95,
    "Warmińsko-mazurskie": 0.92,
    "Świętokrzyskie": 0.90,
    "Podkarpackie": 0.90,
    "Podlaskie": 0.90,
    "Lubelskie": 0.90
}

# 2. Pasek boczny: Cenniki, Lokalizacja i Harmonogram
with st.sidebar:
    st.header("Lokalizacja Inwestycji")
    wybrane_woj = st.selectbox("Wybierz województwo", list(mnozniki_woj.keys()))
    mnoznik = mnozniki_woj[wybrane_woj]
    st.info(f"Mnożnik regionalny: **{mnoznik}x** (względem stawek bazowych)")

    st.markdown("---")
    st.header("1. Cennik Robocizny (PLN netto)")
    cena_stal = st.number_input("Robocizna: Zbrojenie (za 1 tonę)", value=1500)
    cena_beton = st.number_input("Robocizna: Wylewanie (za 1 m3)", value=120)
    cena_mur = st.number_input("Robocizna: Murowanie (za 1 m2)", value=80)
    cena_szalunki = st.number_input("Robocizna: Szalowanie (za 1 m2)", value=70)
    cena_dach = st.number_input("Robocizna: Więźba i pokrycie (za 1 m2)", value=150)
    marza = st.slider("Narzut / Marża wykonawcy (%)", 0, 50, 15)
    
    st.markdown("---")
    st.header("2. Cennik Materiałów (PLN netto)")
    mat_stal = st.number_input("Materiał: Stal zbrojeniowa (za 1 tonę)", value=3500)
    mat_beton = st.number_input("Materiał: Beton (za 1 m3)", value=350)
    mat_mur = st.number_input("Materiał: Bloczki + zaprawa (za 1 m2)", value=120)
    mat_szalunki = st.number_input("Materiał: Drewno/sklejka (za 1 m2)", value=50)
    mat_dach = st.number_input("Materiał: Więźba + dachówka/blacha (za 1 m2)", value=250)

    st.markdown("---")
    st.header("Planowanie Czasu")
    ekipa = st.number_input("Liczba pracowników na budowie", min_value=1, value=3)

# 3. Wgrywanie projektów
uploaded_files = st.file_uploader(
    "Wgraj projekty konstrukcyjne (PDF) - możesz zaznaczyć kilka plików", 
    type=['pdf'], 
    accept_multiple_files=True
)

if st.button("Generuj Kompleksową Wycenę") and uploaded_files and api_key:
    with st.spinner("Sztuczna Inteligencja analizuje projekty i wylicza koszty..."):
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
            Jesteś doświadczonym kosztorysantem budowlanym. 
            Przeanalizuj ZAŁĄCZONE PROJEKTY BUDOWLANE (PDF). Traktuj je jako jedną inwestycję w Stanie Surowym Otwartym (SSO).
            Znajdź zapotrzebowanie na: tony stali, kubaturę betonu (m3), powierzchnię ścian (m2), powierzchnię szalunków (m2) i powierzchnię dachu (m2).
            Inwestycja znajduje się w województwie {wybrane_woj} (mnożnik regionalny: {mnoznik}).
            
            Zadanie 1 - Wycena ROBOCIZNY:
            Przemnóż ilości przez stawki bazowe robocizny: Zbrojenie: {cena_stal} PLN/t, Betonowanie: {cena_beton} PLN/m3, Murowanie: {cena_mur} PLN/m2, Szalowanie: {cena_szalunki} PLN/m2, Dach: {cena_dach} PLN/m2.
            Przemnóż wynik przez mnożnik regionalny ({mnoznik}), a następnie dodaj {marza}% marży wykonawcy.
            
            Zadanie 2 - Wycena MATERIAŁÓW:
            Przemnóż ilości przez stawki bazowe materiałów: Stal: {mat_stal} PLN/t, Beton: {mat_beton} PLN/m3, Ściany: {mat_mur} PLN/m2, Szalunki: {mat_szalunki} PLN/m2, Dach: {mat_dach} PLN/m2.
            Przemnóż koszty materiałów przez mnożnik regionalny ({mnoznik}). Podaj wyniki wyraźnie oddzielone od robocizny.
            
            Zadanie 3 - Harmonogram Prac:
            Oszacuj liczbę roboczogodzin (R-g) na podstawie norm KNR i przelicz je na dni robocze dla ekipy liczącej {ekipa} osób (8h pracy dziennie).
            
            Zadanie 4 - Szczegółowy Harmonogram Płatności (Transze):
            Rozbij całkowitą kwotę wyceny na bardzo szczegółowe transze. Podziel etapy:
            - Fundamenty: 1. Ławy, 2. Ściany, 3. Kanalizacja podposadzkowa, zasypanie, wylanie chudego betonu.
            - Płyta fundamentowa: 1. Szalowanie, 2. Zbrojenie, 3. Wylanie.
            - Stropy: 1. Szalowanie, 2. Zbrojenie, 3. Wylanie.
            - Ściany i dach podziel logicznie na etapy (mury parteru, więźba, pokrycie).
            W każdej transzy rozbij wyraźnie, jaka kwota to ZALICZKA NA MATERIAŁ, a jaka to ZAPŁATA ZA ROBOCIZNĘ po etapie.
            
            Format raportu:
            1. PODSUMOWANIE ILOŚCI Z PROJEKTU
            2. KOSZTY ROBOCIZNY (z podziałem)
            3. KOSZTY MATERIAŁÓW (z podziałem)
            4. PODSUMOWANIE CAŁKOWITE (Robocizna + Materiał)
            5. HARMONOGRAM PRAC
            6. TRANSZE PŁATNOŚCI
            """

            zawartosc = pliki_do_ai + [instrukcja]
            odpowiedz = client.models.generate_content(model='gemini-3.6-flash', contents=zawartosc)
            
            st.success("Analiza zakończona sukcesem!")
            st.write(odpowiedz.text)
            
            st.download_button(
                label="💾 Pobierz raport z wyceną (Plik tekstowy)",
                data=odpowiedz.text,
                file_name="Wycena_SSO_Robocizna_i_Material.txt",
                mime="text/plain"
            )
            
            for sciezka in sciezki_tymczasowe:
                os.remove(sciezka)

        except Exception as e:
            st.error(f"Wystąpił błąd podczas analizy: {e}")
elif not api_key:
    st.warning("Podaj klucz API, aby móc wygenerować wycenę.")
elif not uploaded_files:
    st.warning("Wgraj co najmniej jeden plik PDF z projektem.")
