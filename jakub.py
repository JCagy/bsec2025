import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import urllib.parse
import json

# --- 1. NASTAVENÍ STRÁNKY ---
st.set_page_config(page_title="Lékařský vyhledávač", layout="wide")

# CSS pro červené tlačítko a vzhled
st.markdown("""
    <style>
    div[data-testid="stColumn"]:nth-child(2) button {
        background-color: #ff4b4b !important;
        color: white !important;
        border: none !important;
        padding: 0.6rem 1.2rem !important;
        border-radius: 8px !important;
        font-weight: bold !important;
        font-size: 18px !important;
        margin-top: 25px !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    div[data-testid="stColumn"]:nth-child(2) button:hover {
        background-color: #d33333 !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. DIALOGOVÉ OKNO (POPUP) ---
@st.dialog("Naléhavá pomoc - Pohotovosti v okolí", width="large")
def nouzova_mapa():
    # Definice míst s adresami
    pohotovosti = [
        {"jmeno": "FN Brno - Bohunice", "adresa": "Jihlavská 20, Brno", "lat": 49.1747, "lon": 16.5686},
        {"jmeno": "FN u sv. Anny", "adresa": "Pekařská 53, Brno", "lat": 49.1906, "lon": 16.5986},
        {"jmeno": "Úrazová nemocnice", "adresa": "Ponávka 6, Brno", "lat": 49.1997, "lon": 16.6138},
        {"jmeno": "Dětská nemocnice", "adresa": "Černopolní 9, Brno", "lat": 49.2045, "lon": 16.6159},
    ]

    # HTML kód obsahující tabulku i mapu
    dashboard_html = f"""
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        #popup-layout {{ display: flex; gap: 15px; font-family: sans-serif; height: 450px; }}
        #list-container {{ width: 40%; overflow-y: auto; background: #f9f9f9; padding: 10px; border-radius: 8px; border: 1px solid #ddd; }}
        #map-container {{ width: 60%; position: relative; border-radius: 8px; overflow: hidden; border: 1px solid #ddd; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
        th {{ text-align: left; background: #eee; padding: 8px; position: sticky; top: 0; }}
        td {{ padding: 8px; border-bottom: 1px solid #eee; }}
        .dist-val {{ font-weight: bold; color: #ff4b4b; }}
        .user-loc-dot {{ background: #007bff; border: 2px solid white; border-radius: 50%; box-shadow: 0 0 5px rgba(0,0,0,0.5); }}
    </style>

    <div id="popup-layout">
        <div id="list-container">
            <table id="hosp-table">
                <thead>
                    <tr><th>Nemocnice / Adresa</th><th>Vzdálenost</th></tr>
                </thead>
                <tbody id="table-body">
                    <tr><td colspan="2">Zaměřování polohy...</td></tr>
                </tbody>
            </table>
        </div>
        <div id="map-container">
            <div id="map_p" style="width: 100%; height: 100%;"></div>
        </div>
    </div>

    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        const hospitals = {json.dumps(pohotovosti)};
        const map = L.map('map_p').setView([49.195, 16.608], 12);
        L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png').addTo(map);

        let userMarker;

        // Výpočet vzdálenosti (Haversine formula)
        function getDistance(lat1, lon1, lat2, lon2) {{
            const R = 6371;
            const dLat = (lat2-lat1) * Math.PI / 180;
            const dLon = (lon2-lon1) * Math.PI / 180;
            const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
                      Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * 
                      Math.sin(dLon/2) * Math.sin(dLon/2);
            return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
        }}

        function updateUI(userLat, userLon) {{
            // Přidat vzdálenost ke každému záznamu
            hospitals.forEach(h => {{
                h.distance = getDistance(userLat, userLon, h.lat, h.lon);
            }});

            // Seřadit vzestupně
            hospitals.sort((a, b) => a.distance - b.distance);

            // Aktualizace tabulky
            const tbody = document.getElementById('table-body');
            tbody.innerHTML = '';
            hospitals.forEach(h => {{
                tbody.innerHTML += `<tr>
                    <td><b>${{h.jmeno}}</b><br><small>${{h.adresa}}</small></td>
                    <td class="dist-val">${{h.distance.toFixed(1)}} km</td>
                </tr>`;
            }});

            // Moje poloha na mapě
            if (userMarker) map.removeLayer(userMarker);
            userMarker = L.circleMarker([userLat, userLon], {{
                radius: 8, color: 'white', weight: 2, fillColor: '#007bff', fillOpacity: 1
            }}).addTo(map).bindPopup("<b>Vaše aktuální poloha</b>").openPopup();

            // Nemocnice na mapě
            hospitals.forEach(h => {{
                L.marker([h.lat, h.lon]).addTo(map)
                 .bindPopup(`<b>${{h.jmeno}}</b><br>${{h.adresa}}`);
            }});
        }}

        // Získat polohu
        navigator.geolocation.getCurrentPosition(
            pos => {{
                const lat = pos.coords.latitude;
                const lon = pos.coords.longitude;
                map.setView([lat, lon], 13);
                updateUI(lat, lon);
            }},
            err => {{
                document.getElementById('table-body').innerHTML = '<tr><td colspan="2">Nepodařilo se zaměřit polohu.</td></tr>';
                // I bez polohy vykreslit nemocnice
                hospitals.forEach(h => {{
                    L.marker([h.lat, h.lon]).addTo(map).bindPopup(h.jmeno);
                }});
            }}
        );
    </script>
    """
    components.html(dashboard_html, height=470)
    st.error("V případě přímého ohrožení života volejte 155.")

# --- 3. FUNKCE PRO NAČTENÍ DAT (Hlavní tabulka) ---
@st.cache_data
def nacti_data():
    try:
        df = pd.read_csv("upraveni_lekari_brno_s_hodinami.csv", sep=";", low_memory=False)
        df.columns = df.columns.str.strip()
        df = df.reset_index(drop=True)
        def oprav_web(row):
            web = str(row.get('poskytovatel_web', ''))
            if web == '' or web.lower() in ['nan', 'none']:
                return f"https://www.google.com/search?q={urllib.parse.quote_plus(str(row['ZZ_nazev']))}"
            return web if web.startswith('http') else "https://" + web
        df['web_odkaz'] = df.apply(oprav_web, axis=1)
        return df
    except Exception as e:
        st.error(f"Chyba dat: {e}")
        return None

data = nacti_data()

# --- 4. HLAVA ---
col_titul, col_tlacitko = st.columns([3, 1])
with col_titul:
    st.title("Vyhledávač lékařských zařízení 🩺")
with col_tlacitko:
    if st.button("Potřebuju pomoct", use_container_width=True):
        nouzova_mapa()

# --- 5. FILTRY A ZBYTEK APLIKACE ---
if data is not None:
    st.sidebar.header("Filtrování")
    
    mesto_col = 'ZZ_obec' if 'ZZ_obec' in data.columns else data.columns[0]
    seznam_mest = ["Všechna"] + sorted([str(x) for x in data[mesto_col].unique() if pd.notna(x)])
    vybrane_mesto = st.sidebar.selectbox("Vyberte město:", seznam_mest)

    obor_col = 'ZZ_obor_pece_strucne' if 'ZZ_obor_pece_strucne' in data.columns else data.columns[0]
    seznam_oboru = ["Všechny"] + sorted([str(x) for x in data[obor_col].unique() if pd.notna(x)])
    vybrany_obor = st.sidebar.selectbox("Odbornost", seznam_oboru)

    df_f = data.copy()
    if vybrane_mesto != "Všechna": df_f = df_f[df_f[mesto_col] == vybrane_mesto]
    if vybrany_obor != "Všechny": df_f = df_f[df_f[obor_col] == vybrany_obor]

    st.subheader(f"Seznam zařízení ({len(df_f)})")
    
    vystup_tabulky = st.dataframe(
        df_f[['ZZ_nazev', obor_col, mesto_col, 'ZZ_ulice', 'ZZ_cislo_domovni_orientacni', 'web_odkaz']], 
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        column_config={"web_odkaz": st.column_config.LinkColumn("Web / Google")}
    )

    st.markdown("---")

    # Detail pod tabulkou (zjednodušeno pro přehlednost kompletního kódu)
    if not df_f.empty:
        sel = vystup_tabulky.get("selection", {}).get("rows", [0])
        idx = sel[0] if sel else 0
        radek = df_f.iloc[idx]
        st.subheader(f"Detail: {radek['ZZ_nazev']}")
        
        # Ordinační hodiny
        cols = st.columns(7)
        dni = ['Pondělí', 'Úterý', 'Středa', 'Čtvrtek', 'Pátek', 'Sobota', 'Neděle']
        for i, den in enumerate(dni):
            with cols[i]:
                h = str(radek[den]) if den in radek else "neuvedeno"
                st.info(f"**{den[:2]}**\n\n{h}")

        # Hlavní mapa pod detailem
        # --- HLAVNÍ MAPA POD DETAILEM ---
        if pd.notna(radek['latitude']) and pd.notna(radek['longitude']):
            st.info("💡 **Navigace:** Klikněte do mapy nebo použijte tlačítko pro výpočet trasy k tomuto lékaři.")
            
            # Ošetření textů pro JavaScript
            clean_name = str(radek['ZZ_nazev']).replace("'", "").replace('"', "")
            
            m_main_html = f"""
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
            <style>
                #map-wrapper {{ position: relative; width: 100%; height: 450px; }}
                #main_map {{ width: 100%; height: 100%; border-radius: 10px; border: 1px solid #ddd; }}
                .gps-button {{
                    position: absolute; top: 10px; right: 10px; z-index: 1000;
                    background: white; border: 2px solid rgba(0,0,0,0.2);
                    padding: 8px 12px; cursor: pointer; border-radius: 4px;
                    font-weight: bold; font-family: sans-serif; box-shadow: 0 2px 5px rgba(0,0,0,0.2);
                }}
                .gps-button:hover {{ background: #f4f4f4; }}
            </style>
            
            <div id="map-wrapper">
                <button class="gps-button" onclick="locateMe()">📍 Použít mou polohu</button>
                <div id="main_map"></div>
            </div>

            <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
            <script>
                var doctorLoc = [{radek['latitude']}, {radek['longitude']}];
                var map = L.map('main_map').setView(doctorLoc, 15);
                
                L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
                    attribution: '© OpenStreetMap'
                }}).addTo(map);

                // Cíl (Lékař)
                var markerDoc = L.marker(doctorLoc).addTo(map)
                    .bindPopup("<b>{clean_name}</b><br>Cíl navigace")
                    .openPopup();

                var routeLine = null;
                var userMarker = null;

                async function calculateRoute(lat, lng) {{
                    // OSRM API pro chůzi
                    var url = "https://router.project-osrm.org/route/v1/foot/" + 
                              lng + "," + lat + ";" + 
                              doctorLoc[1] + "," + doctorLoc[0] + "?overview=full&geometries=geojson";
                    
                    try {{
                        var response = await fetch(url);
                        var data = await response.json();
                        
                        if (data.routes && data.routes[0]) {{
                            var route = data.routes[0];
                            var dist = (route.distance / 1000).toFixed(2);
                            var dur = Math.round(route.duration / 60);

                            if (routeLine) map.removeLayer(routeLine);
                            routeLine = L.geoJSON(route.geometry, {{
                                style: {{ color: '#ff4b4b', weight: 6, opacity: 0.7 }}
                            }}).addTo(map);

                            if (!userMarker) {{
                                userMarker = L.circleMarker([lat, lng], {{ color: '#007bff', radius: 8, fillOpacity: 0.9 }}).addTo(map);
                            }} else {{
                                userMarker.setLatLng([lat, lng]);
                            }}

                            userMarker.bindPopup("<b>Váš start</b><br>Vzdálenost: " + dist + " km<br>Čas: " + dur + " min").openPopup();
                            map.fitBounds(routeLine.getBounds(), {{padding: [50, 50]}});
                        }}
                    }} catch (e) {{ console.error(e); }}
                }}

                function locateMe() {{
                    navigator.geolocation.getCurrentPosition(function(pos) {{
                        calculateRoute(pos.coords.latitude, pos.coords.longitude);
                    }}, function() {{ alert("Nelze získat polohu."); }});
                }}

                map.on('click', function(e) {{
                    calculateRoute(e.latlng.lat, e.latlng.lng);
                }});
            </script>
            """
            components.html(m_main_html, height=470)