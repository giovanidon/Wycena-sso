import streamlit as st
from google import genai
import tempfile
import os

# Konfiguracja strony
st.set_page_config(page_title="Wycena SSO - AI", layout="wide")
st.title("🏗️ Kalkulator Robocizny SSO (Stan Surowy Otwarty)")

# 1. Konfiguracja API
api_key = st.text_input("Wprowadź swój klucz API Gemini:", type="password")

# 2. Twój Cennik Robocizny (Pasek boczny)
with st.sidebar:
    st.header("Cennik Robocizny (PLN netto)")
    cena_stal = st.number_input("Zbrojenie (za 1 tonę)", value=1500)
    cena_beton = st.number_input("Betonowanie / Wylewanie (za 1 m3)", value=120)
    cena_mur = st.number_input("Murowanie ścian (za 1 m2)", value=80)
    cena_szalunki = st.number_input("Szalowanie (za 1 m2)", value=70)
    cena_dach = st.number_input("Więźba i pokrycie (za 1 m2)", value=150)
    marza = st.slider("Narzut / Marża / Ryzyko (%)", 0, 50, 15)

# 3. Wgrywanie projektów (WIELE PLIKÓW PDF) - Zmiana tutaj!
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

                # Przesłanie pliku do Google Gemini
                pdf_plik = client.files.upload(file=tmp_file_path)
                pliki_do_ai.append(pdf_plik)
            
            # Główna instrukcja (System Prompt) dla AI
            instrukcja = f"""
            Jesteś doświadczonym kosztorysantem budowlanym i inżynierem. 
            Przeanalizuj ZAŁĄCZONE PROJEKTY BUDOWLANE (PDF). Traktuj je jako jedną całość inwestycji. 
            Interesuje nas WYŁĄCZNIE Stan Surowy Otwarty (SSO).
            
            Twoim zadaniem jest znalezienie w projektach (w opisach, rzutach lub tabelach) następujących ilości zsumowanych z wszystkich plików:
            - Ton stali zbrojeniowej (szukaj zestawień stali)
            - Kubatury betonu (m3) na fundamenty, wieńce, słupy i stropy
            - Powierzchni ścian nośnych i działowych (m2)
            - Powierzchni szalunków (m2)
            - Powierzchni dachu (m2)
            
            Następnie przemnóż zsumowane ilości przez poniższe stawki robocizny wykonawcy:
            - Zbrojenie: {cena_stal} PLN / t
            - Betonowanie: {cena_beton} PLN / m3
            - Murowanie: {cena_mur} PLN / m2
            - Szalowanie: {cena_szalunki} PLN / m2
            - Dach: {cena_dach} PLN / m2
            
            Dodaj do całości {marza}% marży.
            
            Przygotuj profesjonalny raport dla wykonawcy. Wypunktuj, gdzie w projektach znalazłeś dane, przedstaw wyliczenia i podaj końcową cenę netto za robociznę SSO. 
            Jeśli jakichś danych brakuje, oszacuj je na podstawie powierzchni i norm budowlanych, ale WYRAŹNIE zaznacz, że to szacunek.
            """

            # Połączenie wszystkich plików PDF oraz instrukcji tekstowej
            zawartosc = pliki_do_ai + [instrukcja]

            # Wywołanie modelu
            odpowiedz = client.models.generate_content(
                model='gemini-3.1-pro-preview',
                contents=zawartosc
            )
            
            # Wyświetlenie wyniku
            st.success("Analiza zakończona sukcesem!")
            st.markdown("### Raport z Wyceny Robocizny SSO")
            st.write(odpowiedz.text)
            
            # Sprzątanie - usunięcie wszystkich plików tymczasowych
            for sciezka in sciezki_tymczasowe:
                os.remove(sciezka)

        except Exception as e:
            st.error(f"Wystąpił błąd podczas analizy: {e}")
elif not api_key:
    st.warning("Podaj klucz API, aby móc wygenerować wycenę.")
elif not uploaded_files:
    st.warning("Wgraj co najmniej jeden plik PDF z projektem.")
