import streamlit as st
from google import genai
import tempfile
import os
import requests
import json
import sqlite3
import time
from datetime import datetime
from fpdf import FPDF

# Konfiguracja strony
st.set_page_config(page_title="MS Budownictwo - Kalkulator SSO", layout="wide")

# --- FUNKCJE BAZY DANYCH (SQLite) ---
def init_db():
    conn = sqlite3.connect("baza_wycen.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS archiwum (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data_utworzenia TEXT,
                    nazwa_klienta TEXT,
                    wojewodztwo TEXT,
                    przedmiar TEXT,
                    harmonogram TEXT,
                    wycena TEXT
                )''')
    conn.commit()
    conn.close()

def dodaj_wycene(nazwa, woj, przedmiar, harmonogram, wycena):
    conn = sqlite3.connect("baza_wycen.db")
    c = conn.cursor()
    c.execute("PRAGMA table_info(archiwum)")
    kolumny = [kol[1] for kol in c.fetchall()]
    if "harmonogram" not in kolumny:
        c.execute("DROP TABLE archiwum")
        conn.commit()
        init_db()
        
    c.execute("INSERT INTO archiwum (data_utworzenia, nazwa_klienta, wojewodztwo, przedmiar, harmonogram, wycena) VALUES (?, ?, ?, ?, ?, ?)", 
              (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), nazwa, woj, przedmiar, harmonogram, wycena))
    conn.commit()
    conn.close()

def pobierz_wyceny(szukana_fraza=""):
    conn = sqlite3.connect("baza_wycen.db")
    c = conn.cursor()
    try:
        if szukana_fraza:
            c.execute("SELECT * FROM archiwum WHERE nazwa_klienta LIKE ? OR wojewodztwo LIKE ? ORDER BY id DESC", 
                      ('%' + szukana_fraza + '%', '%' + szukana_fraza + '%'))
        else:
            c.execute("SELECT * FROM archiwum ORDER BY id DESC")
        dane = c.fetchall()
    except sqlite3.OperationalError:
        conn.close()
        init_db()
        dane = []
    conn.close()
    return dane

def usun_wycene(id_wyceny):
    conn = sqlite3.connect("baza_wycen.db")
    c = conn.cursor()
    c.execute("DELETE FROM archiwum WHERE id = ?", (id_wyceny,))
    conn.commit()
    conn.close()

init_db()
# ------------------------------------

# --- Inicjalizacja trwałego cennika w session_state ---
if 'ceny' not in st.session_state:
    st.session_state['ceny'] = {
        'cena_stal': 1500, 'cena_beton': 120, 'cena_mur_nosne': 80,
        'cena_mur_dzialowe': 60, 'cena_szalunki': 70, 'cena_dach': 150,
        'cena_schody': 3000, 'cena_slupy': 150, 'cena_kominy': 150,
        'mat_stal': 3500, 'mat_beton': 350, 'mat_mur_nosne': 120,
        'mat_mur_dzialowe': 80, 'mat_szalunki': 50, 'mat_dach': 250,
        'mat_schody': 2500, 'mat_slupy': 120, 'mat_kominy': 300
    }

# --- Funkcja czyszcząca polskie znaki do bezpiecznego formatu PDF ---
def czysc_tekst_dla_pdf(tekst):
    polskie = {'ą': 'a', 'ć': 'c', 'ę': 'e', 'ł': 'l', 'ń': 'n', 'ó': 'o', 'ś': 's', 'ź': 'z', 'ż': 'z',
               'Ą': 'A', 'Ć': 'C', 'Ę': 'E', 'Ł': 'L', 'Ń': 'N', 'Ó': 'O', 'Ś': 'S', 'Ź': 'Z', 'Ż': 'Z'}
    for pl, en in polskie.items():
        tekst = tekst.replace(pl, en)
    return tekst

# --- Generator PDF w orientacji poziomej (Landscape) z szerokim układem tabel ---
def generuj_pdf(tekst_raportu, sciezka_logo=None, tytul="KOSZTORYS I HARMONOGRAM PRAC SSO"):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    
    pdf.set_margins(10, 10, 10)
    pdf.set_font("Helvetica", size=9)
    
    if sciezka_logo and os.path.exists(sciezka_logo):
        pdf.image(sciezka_logo, x=10, y=8, w=35)
        pdf.ln(22)
    elif os.path.exists("logo.png"):
        pdf.image("logo.png", x=10, y=8, w=35)
        pdf.ln(22)
    elif os.path.exists("logo.jpg"):
        pdf.image("logo.jpg", x=10, y=8, w=35)
        pdf.ln(22)
    else:
        pdf.ln(8)
        
    pdf.set_font("Helvetica", style="B", size=13)
    pdf.cell(0, 8, txt=czysc_tekst_dla_pdf(tytul), ln=True, align='C')
    pdf.ln(4)
    
    pdf.set_font("Helvetica", size=8)
    czysty_tekst = tekst_raportu.replace('**', '').replace('##', '').replace('#', '').replace('|', ' | ')
    
    for line in czysty_tekst.split('\n'):
        if line.strip().startswith('---') or '---' in line:
            continue
        pdf.multi_cell(0, 5, txt=czysc_tekst_dla_pdf(line))
        
    pdf_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(pdf_file.name)
    return pdf_file.name

# --- BEZPIECZNE WYWOŁANIE API Z AUTOMATYCZNYM PONAWIANIEM (RETRY) ---
def wywolaj_gemini_z_retry(client, model, contents, max_prob=3):
    for proba in range(1, max_prob + 1):
        try:
            return client.models.generate_content(model=model, contents=contents)
        except Exception as e:
            err_str = str(e)
            if "503" in err_str or "UNAVAILABLE" in err_str or "429" in err_str:
                if proba < max_prob:
                    time.sleep(3 * proba)
                    continue
            raise e
# -------------------------------------------------------------------

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
    
    if st.button("👷 Aktualizuj ceny robocizny (AI)"):
        if api_key:
            with st.spinner(f"Szukam aktualnych cen robocizny dla woj. {wybrane_woj}..."):
                try:
                    client = genai.Client(api_key=api_key)
                    prompt_ceny = f"""
                    Jesteś ekspertem budowlanym. Podaj szacunkowe, rynkowe ceny netto (w PLN) za SAMĄ ROBOCIZNĘ dla SSO dla województwa: {wybrane_woj}.
                    Odpowiedz WYŁĄCZNIE czystym formatem JSON, bez żadnego tekstu przed ani po.
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
                        "cena_kominy": 170
                    }}
                    """
                    response_ceny = wywolaj_gemini_z_retry(client, 'gemini-3.6-flash', prompt_ceny)
                    znacznik = chr(96) * 3
                    json_str = response_ceny.text.replace(znacznik + "json", "").replace(znacznik, "").strip()
                    nowe_ceny = json.loads(json_str)
                    
                    for klucz in nowe_ceny:
                        if klucz in st.session_state['ceny']:
                            st.session_state['ceny'][klucz] = nowe_ceny[klucz]
                            
                    st.success("Zaktualizowano cennik robocizny!")
                    st.rerun() 
                except Exception as e:
                    st.error(f"Nie udało się pobrać cen automatycznie. Błąd: {e}")
        else:
            st.warning("Najpierw podaj klucz API Gemini.")

    if st.button("🧱 Aktualizuj ceny materiałów (AI)"):
        if api_key:
            with st.spinner(f"Szukam aktualnych cen materiałów dla woj. {wybrane_woj}..."):
                try:
                    client = genai.Client(api_key=api_key)
                    prompt_ceny = f"""
                    Jesteś ekspertem budowlanym. Podaj szacunkowe, rynkowe ceny netto (w PLN) za SAME MATERIAŁY dla SSO dla województwa: {wybrane_woj}.
                    Odpowiedz WYŁĄCZNIE czystym formatem JSON, bez żadnego tekstu przed ani po.
                    Zwróć dokładnie taki format:
                    {{
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
                    response_ceny = wywolaj_gemini_z_retry(client, 'gemini-3.6-flash', prompt_ceny)
                    znacznik = chr(96) * 3
                    json_str = response_ceny.text.replace(znacznik + "json", "").replace(znacznik, "").strip()
                    nowe_ceny = json.loads(json_str)
                    
                    for klucz in nowe_ceny:
                        if klucz in st.session_state['ceny']:
                            st.session_state['ceny'][klucz] = nowe_ceny[klucz]
                            
                    st.success("Zaktualizowano cennik materiałów!")
                    st.rerun() 
                except Exception as e:
                    st.error(f"Nie udało się pobrać cen automatycznie. Błąd: {e}")
        else:
            st.warning("Najpierw podaj klucz API Gemini.")

    st.subheader("1. Robocizna (PLN netto)")
    st.session_state['ceny']['cena_stal'] = st.number_input("Robocizna: Zbrojenie (za 1 tonę)", value=st.session_state['ceny']['cena_stal'])
    st.session_state['ceny']['cena_beton'] = st.number_input("Robocizna: Wylewanie (za 1 m3)", value=st.session_state['ceny']['cena_beton'])
    st.session_state['ceny']['cena_mur_nosne'] = st.number_input("Robocizna: Ściany NOŚNE (za 1 m2)", value=st.session_state['ceny']['cena_mur_nosne'])
    st.session_state['ceny']['cena_mur_dzialowe'] = st.number_input("Robocizna: Ściany DZIAŁOWE (za 1 m2)", value=st.session_state['ceny']['cena_mur_dzialowe'])
    st.session_state['ceny']['cena_szalunki'] = st.number_input("Robocizna: Szalowanie (za 1 m2)", value=st.session_state['ceny']['cena_szalunki'])
    st.session_state['ceny']['cena_dach'] = st.number_input("Robocizna: Więźba i pokrycie (za 1 m2)", value=st.session_state['ceny']['cena_dach'])
    st.session_state['ceny']['cena_schody'] = st.number_input("Robocizna: Schody żelbetowe (za komplet)", value=st.session_state['ceny']['cena_schody'])
    st.session_state['ceny']['cena_slupy'] = st.number_input("Robocizna: Słupy żelbetowe (za 1 mb)", value=st.session_state['ceny']['cena_slupy'])
    st.session_state['ceny']['cena_kominy'] = st.number_input("Robocizna: Kominy systemowe (za 1 mb)", value=st.session_state['ceny']['cena_kominy'])
    
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
    st.session_state['ceny']['mat_kominy'] = st.number_input("Materiał: Kominy systemowe (za 1 mb)", value=st.session_state['ceny']['mat_kominy'])

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
nazwa_klienta = st.text_input("📇 Nazwa Klienta / Inwestycji (do zapisu w Archiwum)", value="Projekt SSO")
uploaded_files = st.file_uploader("", type=['pdf'], accept_multiple_files=True)

# GŁÓWNY PRZYCISK: WYCENA
if st.button("Generuj Kompleksową Wycenę") and uploaded_files and api_key:
    with st.spinner("Tworzenie wyceny, harmonogramu i generowanie plików PDF..."):
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
            
            c = st.session_state['ceny']
            
            instrukcja = f"""
            Jesteś doświadczonym kosztorysantem budowlanym. Przeanalizuj ZAŁĄCZONE PROJEKTY BUDOWLANE (PDF). Inwestycja: Stan Surowy Otwarty (SSO), województwo {wybrane_woj} (mnożnik regionalny: {mnoznik}).
            
            BARDZO WAŻNE - MAKSYMALNY SZCZEGÓŁOWY ROZPIS ORAZ TABELE:
            Twoja odpowiedź MUSI składać się z trzech części oddzielonych od siebie dokładnie takim znacznikiem w nowej linii:
            ===PODZIAL===
            Zatem schemat odpowiedzi to: [Część 1] -> [===PODZIAL===] -> [Część 2] -> [===PODZIAL===] -> [Część 3].
            
            ZASADA BEZWZGLĘDNA DLA PRZEDMIARU (Część 1) I WYCEN (Część 3):
            NIGDY nie sumuj elementów na jedną ogólną pozycję typu "ściany nośne ogółem". Każda kondygnacja (Parter, Piętro, Poddasze, Piwnica/Fundamenty) oraz każdy typ ściany (Nośne, Działowe) MUSI być rozpisany w osobnym wierszu tabeli! 
            Przykładowo w przedmiarze i wycenie robocizny/materiałów musisz osobno pokazać:
            - Ściany nośne - Parter (m2)
            - Ściany nośne - Piętro / Poddasze (m2)
            - Ściany działowe - Parter (m2)
            - Ściany działowe - Piętro / Poddasze (m2)
            - Fundamenty - Ławy betonowe (m3)
            - Fundamenty - Ściany fundamentowe (m2)
            - Stropy - Płyta stropowa nad parterem (m2 / m3)
            - Szalunki - osobno fundamenty, osobno stropy, osobno wieńce
            (Wszystko inne rozbijaj dokładnie w ten sam sposób – kondygnacja po kondygnacji).
            
            Wszystkie części prezentuj w formie czytelnych **tabel Markdown** (z kolumnami takimi jak: Pozycja, Element / Kondygnacja, Ilość, Jednostka, Cena jedn., Wartość netto).
            
            UWAGA DOTYCZĄCE ŚCIAN: Licząc metry kwadratowe ścian, ODLICZAJ (wybijaj) TYLKO te otwory, których powierzchnia jednostkowa wynosi POWYŻEJ 5 m2. Mniejsze całkowicie zignoruj i wlicz do pełnej ściany.

            ===PODZIAL===
            
            Część 2 (między pierwszym a drugim znacznikiem ===PODZIAL===):
            Zadanie 2 - HARMONOGRAM PRAC (DLA EKIPY - PRZEWIDZIANY НА {ekipa} PRACOWNIKÓW):
            Stwórz szczegółowy harmonogram prac (w formie tabeli) dla ekipy liczącej dokładnie {ekipa} pracowników (8h/dzień), rozpisany na poszczególne kondygnacje i etapy budowy. Podaj liczbę dni roboczych oraz łączny czas.

            ===PODZIAL===
            
            Część 3 (po drugim znaczniku ===PODZIAL=== - dla klienta):
            Zadanie 3 - ROBOCIZNA (SZCZEGÓŁOWA TABELA W ROZPISIE NA KONDYGNACJE):
            Stawki bazowe: Zbrojenie: {c['cena_stal']} PLN/t, Betonowanie: {c['cena_beton']} PLN/m3, Ściany nośne: {c['cena_mur_nosne']} PLN/m2, Ściany działowe: {c['cena_mur_dzialowe']} PLN/m2, Szalowanie: {c['cena_szalunki']} PLN/m2, Dach: {c['cena_dach']} PLN/m2, Schody żelbetowe: {c['cena_schody']} PLN/komplet, Słupy żelbetowe: {c['cena_slupy']} PLN/mb, Kominy systemowe: {c['cena_kominy']} PLN/mb.
            Przedstaw szczegółową tabelę kosztów robocizny (z uwzględnieniem parteru, piętra, poddasza osobno). Przemnóż wynik przez {mnoznik} i dolicz {marza}% marży wykonawcy.
            
            Zadanie 4 - MATERIAŁY (SZCZEGÓŁOWA TABELA W ROZPISIE NA KONDYGNACJE):
            Stawki bazowe: Stal: {c['mat_stal']} PLN/t, Beton: {c['mat_beton']} PLN/m3, Ściany nośne: {c['mat_mur_nosne']} PLN/m2, Ściany działowe: {c['mat_mur_dzialowe']} PLN/m2, Szalunki: {c['mat_szalunki']} PLN/m2, Dach: {c['mat_dach']} PLN/m2, Schody żelbetowe: {c['mat_schody']} PLN/komplet, Słupy żelbetowe: {c['mat_slupy']} PLN/mb, Kominy systemowe: {c['mat_kominy']} PLN/mb.
            Przedstaw szczegółową tabelę kosztów materiałowych (z rozbiciem na kondygnacje). Przemnóż wynik przez {mnoznik}.
            
            Zadanie 5 - TRANSZE PŁATNOŚCI:
            Podziel prace na etapy w czytelnej tabeli transz (Etap robót | Zaliczka na materiał | Robocizna | Suma transzy).
            
            Zadanie 6 - SYMULACJA SZANS AKCEPTACJI I WIDEŁKI CENOWE ROBOCIZNY:
            Oceń procentową szansę na akceptację oferty **WYŁĄCZNIE NA PODSTAWIE KWOTY ROBOCIZNY** (z marżą). Przygotuj tabelę symulacji widełek robocizny: Wariant (-5%, Bazowy, +5%, +10%, +20%) | Kwota robocizny | Szansa akceptacji (%) | Uzasadnienie rynkowe.
            """

            zawartosc = pliki_do_ai + [instrukcja]
            odpowiedz = wywolaj_gemini_z_retry(client, 'gemini-3.6-flash', zawartosc)
            pelny_tekst = odpowiedz.text
            
            if pelny_tekst.count("===PODZIAL===") >= 2:
                fragmenty = pelny_tekst.split("===PODZIAL===")
                tekst_przedmiaru = fragmenty[0].strip()
                tekst_harmonogramu = fragmenty[1].strip()
                tekst_wyceny = fragmenty[2].strip()
            else:
                tekst_przedmiaru = "UWAGA: Błąd struktury podziału.\n\n" + pelny_tekst
                tekst_harmonogramu = "Brak wygenerowanego harmonogramu."
                tekst_wyceny = pelny_tekst

            st.success("Analiza zakończona sukcesem!")
            
            dodaj_wycene(nazwa_klienta, wybrane_woj, tekst_przedmiaru, tekst_harmonogramu, tekst_wyceny)
            
            st.write("Wgląd w główny dokument (Wycena dla klienta):")
            st.write(tekst_wyceny)
            
            pdf_przedmiar_path = generuj_pdf(tekst_przedmiaru, sciezka_do_logo, tytul="ZESTAWIENIE PRZEDMIAROW - DLA EKIPY")
            pdf_harmonogram_path = generuj_pdf(tekst_harmonogramu, sciezka_do_logo, tytul=f"HARMONOGRAM PRAC ({ekipa} PRACOWNIKOW)")
            pdf_wycena_path = generuj_pdf(tekst_wyceny, sciezka_do_logo, tytul="KOSZTORYS I OFERTA - DLA KLIENTA")
            
            with open(pdf_przedmiar_path, "rb") as f_p:
                pdf_przedmiar_bytes = f_p.read()
            with open(pdf_harmonogram_path, "rb") as f_h:
                pdf_harmonogram_bytes = f_h.read()
            with open(pdf_wycena_path, "rb") as f_w:
                pdf_wycena_bytes = f_w.read()
            
            st.markdown("### 📥 Pobierz wygenerowane pliki PDF")
            
            btn_col1, btn_col2, btn_col3 = st.columns(3)
            with btn_col1:
                st.download_button(
                    label="📄 Przedmiar (dla ekipy)",
                    data=pdf_przedmiar_bytes,
                    file_name="Przedmiar_na_budowe.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            with btn_col2:
                st.download_button(
                    label="⏱️ Harmonogram (czas robót)",
                    data=pdf_harmonogram_bytes,
                    file_name="Harmonogram_prace.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            with btn_col3:
                st.download_button(
                    label="💰 Wycena (dla klienta)",
                    data=pdf_wycena_bytes,
                    file_name="Kosztorys_dla_klienta.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            
            for ai_plik in pliki_do_ai:
                try:
                    client.files.delete(name=ai_plik.name)
                except Exception:
                    pass
            
            os.remove(pdf_przedmiar_path)
            os.remove(pdf_harmonogram_path)
            os.remove(pdf_wycena_path)
            
            for sciezka in sciezki_tymczasowe:
                os.remove(sciezka)

        except Exception as e:
            st.error(f"Wystąpił błąd podczas analizy: {e}")

st.markdown("---")

# --- NOWA SEKCJA: OPTYMALIZATOR CIĘCIA STALI ---
st.header("✂️ Optymalizator Cięcia Zbrojenia")
st.write("Sztuczna inteligencja znajduje wykaz zbrojenia w projekcie, a wbudowany algorytm matematyczny dopasowuje elementy do prętów handlowych, aby zminimalizować odpady.")

dl_handlowa = st.number_input("Długość pręta handlowego w hurtowni (metry)", min_value=6.0, max_value=15.0, value=12.0, step=1.0)

if st.button("Wygeneruj Plan Cięcia (Z załączonych PDF)") and uploaded_files and api_key:
    with st.spinner("AI wyciąga tabele zbrojenia z PDF i układa matematyczny plan cięcia..."):
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
            
            prompt_rozboj = """
            Jesteś inżynierem budownictwa. Przeszukaj załączone projekty konstrukcyjne (PDF).
            Znajdź tabelę "Wykaz Zbrojenia" lub zestawienie stali.
            Zgrupuj wszystkie wypisane pręty zbrojeniowe na podstawie ich ŚREDNICY (np. fi 12, fi 16).
            Zwróć wynik WYŁĄCZNIE jako czysty JSON w poniższym formacie:
            {
              "12": [ {"dlugosc": 4.50, "sztuk": 12}, {"dlugosc": 2.10, "sztuk": 8} ],
              "16": [ {"dlugosc": 5.20, "sztuk": 4} ]
            }
            Kluczowe: Długość ("dlugosc") musi być w METRACH (jeśli projekt podaje w cm, podziel przez 100). Odpowiedz TYLKO i wyłącznie tekstem JSON.
            """
            
            zawartosc = pliki_do_ai + [prompt_rozboj]
            odpowiedz_ai = wywolaj_gemini_z_retry(client, 'gemini-3.6-flash', zawartosc)
            
            znacznik = chr(96) * 3
            json_str = odpowiedz_ai.text.replace(znacznik + "json", "").replace(znacznik, "").strip()
            
            wykaz_stali = json.loads(json_str)
            
            st.success("Pomyślnie wyciągnięto dane z projektu! Oto plan cięcia:")
            
            for srednica, elementy in wykaz_stali.items():
                st.subheader(f"Zbrojenie głównych prętów: ø {srednica} mm")
                
                plaska_lista = []
                for pozycja in elementy:
                    plaska_lista.extend([pozycja['dlugosc']] * pozycja['sztuk'])
                
                sztangi_wynik = optymalizuj_ciecie_stali(plaska_lista, dl_handlowa)
                
                st.write(f"Zapotrzebowanie na pełne pręty handlowe ({dl_handlowa}m): **{len(sztangi_wynik)} szt.** (ok. {len(sztangi_wynik) * dl_handlowa} mb)")
                
                with st.expander(f"Pokaż dokładny rozkrój prętów dla ø {srednica}"):
                    for i, sztanga in enumerate(sztangi_wynik):
                        suma_ciecia = sum(sztanga)
                        odpad = dl_handlowa - suma_ciecia
                        odcinki_tekst = " + ".join([f"{x}m" for x in sztanga])
                        st.markdown(f"**Pręt {i+1}:** Tniemy na: `{odcinki_tekst}` | Zostaje odpad: **{odpad:.2f}m**")
            
            for ai_plik in pliki_do_ai:
                try:
                    client.files.delete(name=ai_plik.name)
                except Exception:
                    pass
            
            for sciezka in sciezki_tymczasowe:
                os.remove(sciezka)
                
        except Exception as e:
            st.error(f"Nie udało się wygenerować planu cięcia. Upewnij się, że PDF zawiera wyraźną tabelę 'Wykaz Zbrojenia'. Błąd: {e}")

st.markdown("---")

# --- ARCHIWUM BAZY DANYCH Z WYSZUKIWARKĄ I POBIERANIEM 3 RODZAJÓW PDF ---
st.header("📂 Archiwum Zapisanych Wycen")
st.write("Tutaj przechowywana jest historia wygenerowanych kosztorysów. Możesz wyszukać klienta i pobrać osobno przedmiar, harmonogram lub wycenę.")

szukana_fraza = st.text_input("🔍 Szukaj w archiwum (wpisz nazwę klienta lub województwo)", value="")

dane_wycen = pobierz_wyceny(szukana_fraza)

if not dane_wycen:
    st.info("Brak wyników w archiwum dla podanej frazy.")
else:
    for w in dane_wycen:
        id_rekordu = w[0]
        data_rekordu = w[1]
        klient = w[2]
        woj = w[3]
        tekst_przedmiaru_arch = w[4]
        if len(w) >= 6:
            tekst_harmonogramu_arch = w[5]
            tekst_wyceny_arch = w[6]
        else:
            tekst_harmonogramu_arch = "Brak zapisanego harmonogramu."
            tekst_wyceny_arch = w[5]
        
        with st.expander(f"📌 {klient} | Utworzono: {data_rekordu} | Województwo: {woj}"):
            st.markdown("### 📄 Zestawienie Przedmiarów")
            st.write(tekst_przedmiaru_arch)
            
            st.markdown("### ⏱️ Harmonogram Prac")
            st.write(tekst_harmonogramu_arch)
            
            st.markdown("### 💰 Wycena i Oferta")
            st.write(tekst_wyceny_arch)
            
            st.markdown("---")
            pdf_arch_p = generuj_pdf(tekst_przedmiaru_arch, sciezka_do_logo, tytul=f"ZESTAWIENIE PRZEDMIAROW - {klient}")
            pdf_arch_h = generuj_pdf(tekst_harmonogramu_arch, sciezka_do_logo, tytul=f"HARMONOGRAM PRAC - {klient}")
            pdf_arch_w = generuj_pdf(tekst_wyceny_arch, sciezka_do_logo, tytul=f"KOSZTORYS - {klient}")
            
            with open(pdf_arch_p, "rb") as fp:
                bytes_p = fp.read()
            with open(pdf_arch_h, "rb") as fh:
                bytes_h = fh.read()
            with open(pdf_arch_w, "rb") as fw:
                bytes_w = fw.read()
                
            arch_col1, arch_col2, arch_col3, arch_col4 = st.columns(4)
            with arch_col1:
                st.download_button(
                    label="📄 Przedmiar",
                    data=bytes_p,
                    file_name=f"Przedmiar_{klient.replace(' ', '_')}.pdf",
                    mime="application/pdf",
                    key=f"pobierz_p_{id_rekordu}",
                    use_container_width=True
                )
            with arch_col2:
                st.download_button(
                    label="⏱️ Harmonogram",
                    data=bytes_h,
                    file_name=f"Harmonogram_{klient.replace(' ', '_')}.pdf",
                    mime="application/pdf",
                    key=f"pobierz_h_{id_rekordu}",
                    use_container_width=True
                )
            with arch_col3:
                st.download_button(
                    label="💰 Wycena",
                    data=bytes_w,
                    file_name=f"Wycena_{klient.replace(' ', '_')}.pdf",
                    mime="application/pdf",
                    key=f"pobierz_w_{id_rekordu}",
                    use_container_width=True
                )
            with arch_col4:
                if st.button("🗑️ Usuń", key=f"usun_{id_rekordu}", use_container_width=True):
                    usun_wycene(id_rekordu)
                    os.remove(pdf_arch_p)
                    os.remove(pdf_arch_h)
                    os.remove(pdf_arch_w)
                    st.rerun()
                    
            try:
                os.remove(pdf_arch_p)
                os.remove(pdf_arch_h)
                os.remove(pdf_arch_w)
            except Exception:
                pass
