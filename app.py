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

# Dodano argument "tytul", aby pliki miały osobne nagłówki
def generuj_pdf(tekst_raportu, sciezka_logo=None, tytul="KOSZTORYS I HARMONOGRAM PRAC SSO"):
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
    pdf.cell(0, 10, txt=tytul, ln=True, align='C')
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
                    
                    znacznik = chr(96) * 3
                    json_str = response_ceny.text.replace(znacznik + "json", "").replace(znacznik, "").strip()
                    nowe_ceny = json.loads(json_str)
                    
                    for klucz in nowe_ceny:
                        if klucz in st.session_state['ceny']:
                            st.session_state['ceny'][klucz] = nowe_ceny[klucz]
                            
                    st.success("Zaktualizowano cennik!")
                    st.rerun() 
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
uploaded_files = st.file_uploader("", type=['pdf'], accept_multiple_files=True)

# GŁÓWNY PRZYCISK: WYCENA
if st.button("Generuj Kompleksową Wycenę") and uploaded_files and api_key:
    with st.spinner("Tworzenie wyceny i generowanie plików PDF..."):
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
            Jesteś doświadczonym kosztorysantem i analitykiem rynku budowlanego. Przeanalizuj ZAŁĄCZONE PROJEKTY BUDOWLANE (PDF). Inwestycja: Stan Surowy Otwarty (SSO), województwo {wybrane_woj} (mnożnik regionalny: {mnoznik}).
            
            BARDZO WAŻNE - PODZIAŁ DOKUMENTU:
            Twoja odpowiedź MUSI składać się z dwóch części oddzielonych od siebie dokładnie takim znacznikiem w nowej linii:
            ===PODZIAL===
            Zatem schemat odpowiedzi to: [Odpowiedź na Zadanie 1] -> [===PODZIAL===] -> [Odpowiedź na Zadania 2 do 6].
            
            Część 1 (przed znacznikiem ===PODZIAL===):
            Zadanie 1 - ZESTAWIENIE PRZEDMIARÓW (CZYSTA LISTA DO WYDRUKU NA BUDOWĘ):
            Stwórz czystą listę wszystkich odczytanych z projektu ilości (bez podawania żadnych cen). Musi ona zawierać minimum:
            - Fundamenty (metry bieżące lub sześcienne)
            - Ściany nośne parter (m2)
            - Ściany nośne poddasze/piętro (m2)
            - Ściany działowe (m2)
            - Stropy (m2 lub m3)
            - Dach (m2)
            - Stal zbrojeniowa (tony)
            - Beton (m3)
            - Szalunki (m2)
            - Schody żelbetowe (sztuki / komplety)
            - Słupy żelbetowe (mb)
            - Kominy systemowe (mb)
            UWAGA DOTYCZĄCE ŚCIAN: Licząc metry kwadratowe ścian, ODLICZAJ (wybijaj) TYLKO te otwory, których powierzchnia wynosi POWYŻEJ 5 m2. Mniejsze całkowicie zignoruj i wlicz do pełnej ściany.

            ===PODZIAL===
            
            Część 2 (po znaczniku ===PODZIAL=== - dla klienta):
            Zadanie 2 - ROBOCIZNA:
            Stawki bazowe: Zbrojenie: {c['cena_stal']} PLN/t, Betonowanie: {c['cena_beton']} PLN/m3, Ściany nośne: {c['cena_mur_nosne']} PLN/m2, Ściany działowe: {c['cena_mur_dzialowe']} PLN/m2, Szalowanie: {c['cena_szalunki']} PLN/m2, Dach: {c['cena_dach']} PLN/m2, Schody żelbetowe: {c['cena_schody']} PLN/komplet, Słupy żelbetowe: {c['cena_slupy']} PLN/mb, Kominy systemowe: {c['cena_kominy']} PLN/mb.
            Pokaż koszty w rozbiciu. Przemnóż wynik całości przez {mnoznik} i na koniec dodaj {marza}% marży.
            
            Zadanie 3 - MATERIAŁY:
            Stawki bazowe: Stal: {c['mat_stal']} PLN/t, Beton: {c['mat_beton']} PLN/m3, Ściany nośne: {c['mat_mur_nosne']} PLN/m2, Ściany działowe: {c['mat_mur_dzialowe']} PLN/m2, Szalunki: {c['mat_szalunki']} PLN/m2, Dach: {c['mat_dach']} PLN/m2, Schody żelbetowe: {c['mat_schody']} PLN/komplet, Słupy żelbetowe: {c['mat_slupy']} PLN/mb, Kominy systemowe: {c['mat_kominy']} PLN/mb.
            Pokaż podział kosztów i przemnóż je przez {mnoznik}.
            
            Zadanie 4 - HARMONOGRAM PRAC:
            Oszacuj dni robocze dla {ekipa} pracowników (8h pracy). Rozbij czas trwania na elementy (fundamenty, stropy itp.).
            
            Zadanie 5 - TRANSZE PŁATNOŚCI:
            Podziel prace na etapy. W każdym etapie wyraźnie rozbij: ile to ZALICZKA NA MATERIAŁ, a ile ZAPŁATA ZA ROBOCIZNĘ.
            
            Zadanie 6 - SYMULACJA SZANS AKCEPTACJI I WIDEŁKI CENOWE:
            Oceń procentową szansę na akceptację tej oferty. Zrób symulację: -5%, +5%, +10%, +20% z uzasadnieniem.
            """

            zawartosc = pliki_do_ai + [instrukcja]
            odpowiedz = client.models.generate_content(model='gemini-2.5-flash', contents=zawartosc)
            pelny_tekst = odpowiedz.text
            
            if "===PODZIAL===" in pelny_tekst:
                fragmenty = pelny_tekst.split("===PODZIAL===")
                tekst_przedmiaru = fragmenty[0].strip()
                tekst_wyceny = fragmenty[1].strip()
            else:
                tekst_przedmiaru = "UWAGA: Brak podziału dokumentu.\n\n" + pelny_tekst
                tekst_wyceny = pelny_tekst

            st.success("Analiza zakończona sukcesem!")
            st.write("Wgląd w główny dokument (Wycena):")
            st.write(tekst_wyceny)
            
            pdf_przedmiar_path = generuj_pdf(tekst_przedmiaru, sciezka_do_logo, tytul="ZESTAWIENIE PRZEDMIAROW - DLA EKIPY")
            pdf_wycena_path = generuj_pdf(tekst_wyceny, sciezka_do_logo, tytul="KOSZTORYS I HARMONOGRAM PRAC SSO")
            
            with open(pdf_przedmiar_path, "rb") as f_p:
                pdf_przedmiar_bytes = f_p.read()
                
            with open(pdf_wycena_path, "rb") as f_w:
                pdf_wycena_bytes = f_w.read()
            
            st.markdown("### 📥 Pobierz wygenerowane pliki PDF")
            
            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                st.download_button(
                    label="📄 Pobierz PRZEDMIAR (dla ekipy)",
                    data=pdf_przedmiar_bytes,
                    file_name="Przedmiar_na_budowe.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            with btn_col2:
                st.download_button(
                    label="💰 Pobierz WYCENĘ (dla klienta)",
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
    with st.spinner("AI wyciąga tabele zbrojenia z PDF i układa matematyczny plan cięcia (może potrwać kilkanaście sekund)..."):
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
            odpowiedz_ai = client.models.generate_content(model='gemini-2.5-flash', contents=zawartosc)
            
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
