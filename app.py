import streamlit as st
import google.generativeai as genai
import tempfile
import os

# Konfiguracja strony
st.set_page_config(page_title="Wycena SSO - AI", layout="wide")
st.title("🏗️ Kalkulator Robocizny SSO (Stan Surowy Otwarty)")

# 1. Konfiguracja API
api_key = st.text_input("Wprowadź swój klucz API Gemini:", type="password")
if api_key:
    genai.configure(api_key=api_key)

# 2. Twój Cennik Robocizny (Pasek boczny)
with st.sidebar:
    st.header("Cennik Robocizny (PLN netto)")
    cena_stal = st.number_input("Zbrojenie (za 1 tonę)", value=1500)
    cena_beton = st.number_input("Betonowanie / Wylewanie (za 1 m3)", value=120)
    cena_mur = st.number_input("Murowanie ścian (za 1 m2)", value=80)
    cena_szalunki = st.number_input("Szalowanie (za 1 m2)", value=70)
    cena_dach = st.number_input("Więźba i pokrycie (za 1 m2)", value=150)
    marza = st.slider("Narzut / Marża / Ryzyko (%)", 0, 50, 15)

# 3. Wgrywanie projektu (PDF)
uploaded_file = st.file_uploader("Wgraj projekt konstrukcyjny / architektoniczny (PDF)", type=['pdf'])

if st.button("Generuj Wycenę Robocizny") and uploaded_file and api_key:
    with st.spinner("Sztuczna Inteligencja analizuje projekt konstrukcyjny... To może potrwać kilkanaście sekund."):
        try:
            # Zapisanie pliku PDF do pliku tymczasowego (wymagane przez API)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_file_path = tmp_file.name

            # Przesłanie pliku do Google Gemini
            pdf_plik = genai.upload_file(tmp_file_path, mime_type="application/pdf")
            
            # Główna instrukcja (System Prompt) dla AI
            instrukcja = f"""
            Jesteś doświadczonym kosztorysantem budowlanym i inżynierem. 
            Przeanalizuj załączony projekt budowlany (PDF). Interesuje nas WYŁĄCZNIE Stan Surowy Otwarty (SSO).
            
            Twoim zadaniem jest znalezienie w projekcie (w opisach, rzutach lub tabelach) następujących ilości:
            - Ton stali zbrojeniowej (szukaj zestawień stali)
            - Kubatury betonu (m3) na fundamenty, wieńce, słupy i stropy
            - Powierzchni ścian nośnych i działowych (m2)
            - Powierzchni szalunków (m2)
            - Powierzchni dachu (m2)
            
            Następnie przemnóż znalezione ilości przez poniższe stawki robocizny wykonawcy:
            - Zbrojenie: {cena_stal} PLN / t
            - Betonowanie: {cena_beton} PLN / m3
            - Murowanie: {cena_mur} PLN / m2
            - Szalowanie: {cena_szalunki} PLN / m2
            - Dach: {cena_dach} PLN / m2
            
            Dodaj do całości {marza}% marży.
            
            Przygotuj profesjonalny raport dla wykonawcy. Wypunktuj, gdzie w projekcie znalazłeś dane (aby wykonawca mógł to zweryfikować), przedstaw wyliczenia i podaj końcową cenę netto za robociznę SSO. 
            Jeśli jakichś danych brakuje w PDF (np. nie ma zestawienia stali), oszacuj je na podstawie powierzchni i norm budowlanych, ale WYRAŹNIE zaznacz, że to szacunek.
            """

            # Wywołanie modelu
            model = genai.GenerativeModel('gemini-1.5-pro')
            odpowiedz = model.generate_content([pdf_plik, instrukcja])
            
            # Wyświetlenie wyniku
            st.success("Analiza zakończona sukcesem!")
            st.markdown("### Raport z Wyceny Robocizny SSO")
            st.write(odpowiedz.text)
            
            # Sprzątanie
            os.remove(tmp_file_path)

        except Exception as e:
            st.error(f"Wystąpił błąd podczas analizy: {e}")
elif not api_key:
    st.warning("Podaj klucz API, aby móc wygenerować wycenę.")
