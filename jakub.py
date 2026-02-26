import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import urllib.parse

st.set_page_config(page_title="Lékaři Brno", layout="wide")

# FUNKCE PRO NAČTENÍ DAT
@st.cache_data
def nacti_data():
    try:
        df = pd.read_csv("upraveni_lekari_brno_s_hodinami.csv", sep=";", low_memory=False)
        df.columns = df.columns.str.strip()
        df.index = range(1, len(df) + 1)
        
        def oprav_web(row):
            web = str(row.get('poskytovatel_web', ''))
            if web == '' or web.lower() == 'nan' or web == 'None':
                jmeno = urllib.parse.quote_plus(str(row['ZZ_nazev']))
                return f"https://www.google.com/search?q={jmeno}"
            if not web.startswith('http'):
                return "https://" + web
            return web

        if 'ZZ_nazev' in df.columns:
            df['web_odkaz'] = df.apply(oprav_web, axis=1)
        else:
            df['web_odkaz'] = ""
            
        return df
    except Exception as e:
        st.error(f"❌ Chyba při načítání dat: {e}")
        return None

data = nacti_data()

if data is not None:
    st.title("Vyhledávač lékařských zařízení Brno 🩺")

    # --- FILTRY ---
    st.sidebar.header("Filtrování")
    col_obor = 'ZZ_obor_pece_strucne' if 'ZZ_obor_pece_strucne' in data.columns else data.columns[0]
    
    seznam_oboru = ["Všechny"] + sorted(list(data[col_obor].astype(str).unique()))
    vybrany_obor = st.sidebar.selectbox("Odbornost", seznam_oboru)

    df_filtered = data.copy()
    if vybrany_obor != "Všechny":
        df_filtered = df_filtered[df_filtered[col_obor] == vybrany_obor]

    # --- TABULKA ---
    st.subheader(f"Seznam zařízení ({len(df_filtered)})")
    vsechny_mozne_sloupce = ['ZZ_nazev', 'ZZ_obor_pece_strucne', 'ZZ_obec', 'ZZ_ulice', 'ZZ_cislo_domovni_orientacni']
    existujici_pro_tabulku = [c for c in vsechny_mozne_sloupce if c in data.columns]
    
    st.dataframe(
        df_filtered[existujici_pro_tabulku + ['web_odkaz']], 
        use_container_width=True,
        column_config={
            "web_odkaz": st.column_config.LinkColumn("Web / Google Search"),
            "ZZ_nazev": "Název",
            "ZZ_obor_pece_strucne": "Obor",
            "ZZ_obec": "Obec",
            "ZZ_ulice": "Ulice",
            "ZZ_cislo_domovni_orientacni":"Číslo popisné/orientační",
        }
    )

    st.markdown("---")

    # --- DETAIL A MAPA ---
    if not df_filtered.empty:
        st.subheader("Detail a navigace")
        
        col_jmeno = 'ZZ_nazev' if 'ZZ_nazev' in data.columns else data.columns[0]
        vyber_text = df_filtered[col_jmeno].astype(str) + " (" + df_filtered.index.astype(str) + ")"
        vybrany_label = st.selectbox("Vyberte lékaře pro detaily:", vyber_text)
        
        idx = int(vybrany_label.split("(")[-1].replace(")", ""))
        radek = df_filtered.loc[idx]

        # --- ORDINAČNÍ HODINY ---
        st.write("### 🕒 Ordinační hodiny")
        dni = ['Pondělí', 'Úterý', 'Středa', 'Čtvrtek', 'Pátek', 'Sobota', 'Neděle']
        cols = st.columns(7)
        
        for i, den in enumerate(dni):
            with cols[i]:
                hodnota = str(radek[den]) if den in radek else "neuvedena"
                if hodnota.lower() not in ['neuvedena', 'nan', 'x', '']:
                    st.info(f"**{den[:2]}**\n\n{hodnota}")
                else:
                    st.warning(f"**{den[:2]}**\n\nneuvedeno")

        # --- MAPA S NAVIGACÍ A GEOLOKACÍ ---
        col_lat = 'latitude' if 'latitude' in data.columns else None
        col_lon = 'longitude' if 'longitude' in data.columns else None

        if col_lat and pd.notna(radek[col_lat]):
            st.info("💡 **Tip:** Klikněte do mapy nebo použijte tlačítko pro zaměření vaší polohy a výpočet trasy.")
            
            ciste_jmeno = str(radek[col_jmeno]).replace('"', '').replace("'", "")
            
            mapa_html = f"""
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
            <style>
                #map-container {{ position: relative; width: 100%; height: 450px; }}
                #map {{ width: 100%; height: 100%; border-radius: 10px; }}
                #loc-button {{
                    position: absolute; top: 10px; right: 10px; z-index: 1000;
                    background: white; border: 2px solid rgba(0,0,0,0.2);
                    padding: 8px 12px; cursor: pointer; border-radius: 4px;
                    font-weight: bold; font-family: sans-serif; box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                #loc-button:hover {{ background: #f4f4f4; }}
            </style>
            
            <div id="map-container">
                <button id="loc-button" onclick="getLocation()">📍 Použít mou polohu</button>
                <div id="map"></div>
            </div>

            <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
            <script>
                var dest = [{radek[col_lat]}, {radek[col_lon]}];
                var map = L.map('map').setView(dest, 15);
                
                L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
                    attribution: '© OpenStreetMap'
                }}).addTo(map);

                var doctorMarker = L.marker(dest).addTo(map)
                    .bindPopup("<b>{ciste_jmeno}</b><br>Cíl cesty")
                    .openPopup();
            </script>
            """
            components.html(mapa_html, height=470)