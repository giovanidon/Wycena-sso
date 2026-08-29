import streamlit as st
from google import genai
import tempfile
import os

# Konfiguracja strony
st.set_page_config(page_title="Wycena SSO - AI", layout="wide")
st.title("🏗️ Kalkulator Robocizny SSO (Stan Surowy Otwarty)")

# 1. Konfiguracja API (Pobieranie z bezpiecznego sejfu)
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = st.text_input("Wprowadź swój klucz API Gemini:", type="password")

# 2. Cennik Robocizny i Harmonogram (Pasek boczny)
with st.sidebar:
    st.header("Cennik Robocizny (PLN netto)")
    cena_stal = st.number_input("Zbrojenie (za 1 tonę)", value=1500)
    cena_beton = st.number_input("Betonowanie / Wylewanie (za 1 m3)", value=120)
    cena_mur = st.number_input("Murowanie ścian (za 1 m2)", value=80)
    cena_szalunki = st.number_input("Szalowanie (za 1 m2)", value=70)
    cena_dach = st.number_input("Więźba i pokrycie (za 1 m2)", value=150)
    marza = st.slider("Narzut / Marża / Ryzyko (%)", 0, 50, 15)
    
    st.markdown("---")
    st.header("Planowanie Czasu")
    ekipa = st.number_input("Liczba pracowników na budowie", min_value=1, value=3)

# 3. Wgrywanie projektów
uploaded_files = st.file_uploader(
    "Wgraj projekty konstrukcyjne (PDF) - możesz zaznaczyć kilka plików", 
    type=['pdf'], 
    accept_multiple_files=True
)

if st.button("Generuj Wycenę Robocizny") and uploaded_files and api_key:
    with st.spinner("Sztuczna Inteligencja analizuje projekty... To może potrwać dłuższą chwilę."):
        try:
            client = genai.Client(api_key=api_key)
            pliki_do_ai = []
            sciezki_tymczasowe = []
            
            # Przetwarzanie każdego wgranego pliku
            for file in uploaded_files:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                    tmp_file.write(file.getvalue())
                    tmp_file_path = tmp_file.name
                    sciezki_tymczasowe.append(tmp_file_path)

                # Przesłanie pliku do AI
                pdf_plik = client.files.upload(file=tmp_file_path)
                pliki_do_ai.append(pdf_plik)
            
            # Instrukcja główna
            instrukcja = f"""
            Jesteś doświadczonym kosztorysantem budowlanym i inżynierem. 
            Przeanalizuj ZAŁĄCZONE PROJEKTY BUDOWLANE (PDF). Traktuj je jako jedną całość inwestycji. 
            Interesuje nas WYŁĄCZNIE Stan Surowy Otwarty (SSO).
            
            Zadanie 1 - Ilości i Koszty:
            Znajdź w projektach: tony stali zbrojeniowej, kubaturę betonu (m3), powierzchnię ścian (m2), powierzchnię szalunków (m2) i powierzchnię dachu (m2).
            Przemnóż je przez stawki: Zbrojenie: {cena_stal} PLN/t, Betonowanie: {cena_beton} PLN/m3, Murowanie: {cena_mur} PLN/m2, Szalowanie: {cena_szalunki} PLN/m2, Dach: {cena_dach} PLN/m2.
            Dodaj do całości {marza}% marży.
            
            Zadanie 2 - Harmonogram:
            Na podstawie znalezionych ilości, oszacuj łączną liczbę roboczogodzin (R-g) potrzebnych na wykonanie SSO, bazując na standardowych normach budowlanych (KNR). 
            Na budowie będzie pracować stała ekipa licząca {ekipa} osób (przyjmij 8-godzinny dzień pracy).
            Przelicz łączną liczbę roboczogodzin na szacowaną liczbę dni roboczych potrzebnych na realizację całej inwestycji przez tę konkretną ekipę.
            
            Przygotuj profesjonalny raport dla wykonawcy z wyraźnym podziałem na sekcję wyceny oraz nową sekcję szacunkowego harmonogramu prac. Jeśli jakichś danych brakuje, oszacuj je i wyraźnie zaznacz w raporcie, że to szacunek.
            """

            zawartosc = pliki_do_ai + [instrukcja]
            
            # Wywołanie modelu
            odpowiedz = client.models.generate_content(model='gemini-3.6-flash', contents=zawartosc)
            
            # Wyświetlenie wyniku na ekranie
            st.success("Analiza zakończona sukcesem!")
            st.write(odpowiedz.text)
            
            # PRZYCISK DO POBIERANIA - nowa funkcja
            st.download_button(
                label="💾 Pobierz raport z wyceną (Plik tekstowy)",
                data=odpowiedz.text,
                file_name="Wycena_SSO.txt",
                mime="text/plain"
            )
            
            # Usuwanie plików tymczasowych
            for sciezka in sciezki_tymczasowe:
                os.remove(sciezka)

        except Exception as e:
            st.error(f"Wystąpił błąd podczas analizy: {e}")
elif not api_key:
    st.warning("Podaj klucz API, aby móc wygenerować wycenę.")
elif not uploaded_files:
    st.warning("Wgraj co najmniej jeden plik PDF z projektem.")
    
