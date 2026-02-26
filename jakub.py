import streamlit as st
import pandas as pd
import streamlit.components.v1 as components

# 1. Nastavení stránky
st.set_page_config(page_title="Vyhledávač lékařů JHM", layout="wide")
st.title("Vyhledávač lékařských zařízení a ambulancí 🩺")
st.markdown("Najděte si lékaře v Jihomoravském kraji a nechte se k němu navigovat.")

# 2. Načtení a příprava dat
@st.cache_data
def nacti_data():
    # Načtení souboru (ujisti se, že soubor je ve stejné složce jako skript)
    try:
        df = pd.read_csv("vysledny_spojeny_soubor.csv", sep=";", low_memory=False)
    except FileNotFoundError:
        # Pokud soubor neexistuje, vytvoříme prázdný DataFrame pro testování
        st.error("Soubor 'vysledny_spojeny_soubor.csv' nebyl nalezen!")
        return pd.DataFrame()
    
    # Vyčištění GPS souřadnic
    def zpracuj_gps(gps_text):
        try:
            if pd.isna(gps_text) or gps_text == "": return None, None
            # Odstranění písmen a rozdělení
            ciste = str(gps_text).replace('N', '').replace('E', '').replace(' ', '').split(',')
            return float(ciste[0]), float(ciste[1])
        except:
            return None, None

    # Vytvoříme nové sloupce lat a lon
    coords = df['ZZ_GPS'].apply(zpracuj_gps)
    df['lat'] = [x[0] for x in coords]
    df['lon'] = [x[1] for x in coords]
    
    # Vyplníme prázdné hodnoty
    df['ZZ_obor_pece'] = df['ZZ_obor_pece'].fillna('Neuvedeno')
    df['Obec'] = df['Obec'].fillna('Neuvedeno')
    df['NazevCely'] = df['NazevCely'].fillna('Neznámý název')
    
    return df

data = nacti_data()

if not data.empty:
    # 3. BOČNÍ PANEL
    st.sidebar.header("Možnosti filtrování")

    seznam_oboru = ["Všechny"] + sorted(list(data['ZZ_obor_pece'].unique()))
    seznam_obci = ["Všechny"] + sorted(list(data['Obec'].unique()))

    vybrana_obec = st.sidebar.selectbox("Město / Obec", seznam_obci)
    vybrany_obor = st.sidebar.selectbox("Téma odbornosti", seznam_oboru)

    # 4. FILTROVÁNÍ DAT
    vyfiltrovana_data = data.copy()
    if vybrana_obec != "Všechny":
        vyfiltrovana_data = vyfiltrovana_data[vyfiltrovana_data['Obec'] == vybrana_obec]
    if vybrany_obor != "Všechny":
        vyfiltrovana_data = vyfiltrovana_data[vyfiltrovana_data['ZZ_obor_pece'] == vybrany_obor]

    # 5. ZOBRAZENÍ TABULKY
    st.subheader(f"Nalezená zařízení ({len(vyfiltrovana_data)})")
    cols_to_show = ['NazevCely', 'ZZ_obor_pece', 'Obec', 'Ulice', 'poskytovatel_telefon']
    st.dataframe(vyfiltrovana_data[cols_to_show], use_container_width=True)

    st.markdown("---")

    # 6. VÝBĚR CÍLE PRO MAPU
    st.subheader("Navigace k vybranému zařízení 🗺️")

    if not vyfiltrovana_data.empty:
        vyfiltrovana_data['Vyberove_jmeno'] = vyfiltrovana_data['NazevCely'] + " (" + vyfiltrovana_data['Ulice'].astype(str) + ")"
        vybrany_lekar_jmeno = st.selectbox("Vyberte zařízení pro navigaci:", vyfiltrovana_data['Vyberove_jmeno'])
        
        cile = vyfiltrovana_data[vyfiltrovana_data['Vyberove_jmeno'] == vybrany_lekar_jmeno].iloc[0]
        
        cilova_lat = cile['lat']
        cilova_lon = cile['lon']
        nazev_cile = cile['NazevCely'].replace("'", "") # Odstranění uvozovek pro JS
        adresa_cile = f"{cile['Ulice']}, {cile['Obec']}".replace("'", "")

        if pd.isna(cilova_lat) or pd.isna(cilova_lon):
            st.warning(f"Zařízení '{nazev_cile}' nemá GPS souřadnice.")
        else:
            # 7. VYKRESLENÍ MAPY
            mapa_html = """
            <!DOCTYPE html>
            <html>
            <head>
                <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
                <style>
                    body { margin: 0; font-family: sans-serif; }
                    #container { display: flex; height: 100vh; flex-direction: row; }
                    #sidebar { width: 300px; background: white; padding: 15px; border-right: 1px solid #ddd; z-index: 1000; }
                    #map { flex: 1; }
                    .stat-box { border: 1px solid #eee; padding: 10px; margin-bottom: 10px; }
                    .stat-box h2 { font-size: 12px; color: #666; margin: 0; }
                    .stat-box p { font-size: 20px; font-weight: bold; margin: 5px 0 0 0; }
                </style>
            </head>
            <body>
            <div id="container">
                <div id="sidebar">
                    <div class="stat-box"><h2>Délka trasy</h2><p id="distance">-- km</p></div>
                    <div class="stat-box"><h2>Doba chůze</h2><p id="duration">-- min</p></div>
                    <div class="stat-box"><h2>Cíl</h2><p style="font-size: 14px;">__NAZEV__</p></div>
                    <p style="font-size: 12px; color: #888;">Klikněte do mapy pro start trasy.</p>
                </div>
                <div id="map"></div>
            </div>

            <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
            <script>
                const destination = [__LAT__, __LON__];
                const map = L.map('map').setView(destination, 15);

                L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png').addTo(map);
                L.marker(destination).addTo(map).bindPopup("__NAZEV__").openPopup();

                let routeLine, startMarker;

                async function getRoute(start) {
                    const url = `https://router.project-osrm.org/route/v1/foot/${start[1]},${start[0]};${destination[1]},${destination[0]}?overview=full&geometries=geojson`;
                    const res = await fetch(url);
                    const data = await res.json();
                    if (data.routes && data.routes[0]) {
                        const r = data.routes[0];
                        document.getElementById('distance').innerText = (r.distance/1000).toFixed(1) + ' km';
                        document.getElementById('duration').innerText = Math.round(r.duration/60) + ' min';
                        if (routeLine) map.removeLayer(routeLine);
                        routeLine = L.geoJSON(r.geometry, {style: {color: '#e63946', weight: 5}}).addTo(map);
                    }
                }

                map.on('click', function(e) {
                    if (startMarker) startMarker.setLatLng(e.latlng);
                    else startMarker = L.circleMarker(e.latlng, {color: '#007bff'}).addTo(map);
                    getRoute([e.latlng.lat, e.latlng.lng]);
                });
            </script>
            </body>
            </html>
            """
            # Oprava: placeholderů
            mapa_html = mapa_html.replace("__LAT__", str(cilova_lat))
            mapa_html = mapa_html.replace("__LON__", str(cilova_lon))
            mapa_html = mapa_html.replace("__NAZEV__", nazev_cile)
            
            components.html(mapa_html, height=600)
    else:
        st.info("Žádné výsledky.")