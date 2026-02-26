import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import urllib.parse

st.set_page_config(page_title="Lékaři Brno a okolí", layout="wide")

# --- FUNKCE PRO NAČTENÍ DAT ---
@st.cache_data
def nacti_data():
    try:
        df = pd.read_csv("upraveni_lekari_brno_s_hodinami.csv", sep=";", low_memory=False)
        df.columns = df.columns.str.strip()
        df = df.reset_index(drop=True)
        
        def oprav_web(row):
            web = str(row.get('poskytovatel_web', ''))
            if web == '' or web.lower() == 'nan' or web == 'none':
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
    st.title("Vyhledávač lékařských zařízení 🩺")

    # --- FILTRY (SIDEBAR) ---
    st.sidebar.header("Filtrování")
    
    col_mesto = 'ZZ_obec' if 'ZZ_obec' in data.columns else data.columns[0]
    seznam_mest = ["Všechna"] + sorted([str(x) for x in data[col_mesto].unique() if pd.notna(x)])
    vybrane_mesto = st.sidebar.selectbox("Vyberte město:", seznam_mest)

    col_obor = 'ZZ_obor_pece_strucne' if 'ZZ_obor_pece_strucne' in data.columns else data.columns[0]
    seznam_oboru = ["Všechny"] + sorted([str(x) for x in data[col_obor].unique() if pd.notna(x)])
    vybrany_obor = st.sidebar.selectbox("Odbornost", seznam_oboru)

    df_filtered = data.copy()
    if vybrane_mesto != "Všechna":
        df_filtered = df_filtered[df_filtered[col_mesto] == vybrane_mesto]
    if vybrany_obor != "Všechny":
        df_filtered = df_filtered[df_filtered[col_obor] == vybrany_obor]

    # --- TABULKA ---
    st.subheader(f"Seznam zařízení ({len(df_filtered)})")
    st.info("💡 Kliknutím na řádek v tabulce se lékař automaticky zobrazí v detailu a na mapě níže.")
    
    vsechny_mozne_sloupce = ['ZZ_nazev', 'ZZ_obor_pece_strucne', 'ZZ_obec', 'ZZ_ulice', 'ZZ_cislo_domovni_orientacni']
    existujici_pro_tabulku = [c for c in vsechny_mozne_sloupce if c in data.columns]
    
    vystup_tabulky = st.dataframe(
        df_filtered[existujici_pro_tabulku + ['web_odkaz']], 
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            "web_odkaz": st.column_config.LinkColumn("Web / Google Search"),
            "ZZ_nazev": "Název",
            "ZZ_obor_pece_strucne": "Obor",
            "ZZ_obec": "Obec",
            "ZZ_ulice": "Ulice",
            "ZZ_cislo_domovni_orientacni":"Č.p./or.",
        }
    )

    st.markdown("---")

    # --- DETAIL A MAPA ---
    if not df_filtered.empty:
        st.subheader("Detail a navigace")
        
        vybrane_radky = vystup_tabulky.get("selection", {}).get("rows", [])
        index_pro_selectbox = 0
        if vybrane_radky:
            index_pro_selectbox = vybrane_radky[0]

        col_jmeno = 'ZZ_nazev'
        vybrany_index_v_df = st.selectbox(
            "Vyberte lékaře pro detaily:", 
            options=range(len(df_filtered)),
            index=index_pro_selectbox,
            format_func=lambda i: f"{df_filtered.iloc[i][col_jmeno]} ({df_filtered.iloc[i][col_mesto]})"
        )
        
        radek = df_filtered.iloc[vybrany_index_v_df]

        # --- ORDINAČNÍ HODINY ---
        st.write(f"### 🕒 Ordinační hodiny: {radek[col_jmeno]}")
        dni = ['Pondělí', 'Úterý', 'Středa', 'Čtvrtek', 'Pátek', 'Sobota', 'Neděle']
        cols = st.columns(7)
        
        for i, den in enumerate(dni):
            with cols[i]:
                hodnota = str(radek[den]) if den in radek else "neuvedena"
                if hodnota.lower() not in ['neuvedena', 'nan', 'x', '']:
                    st.info(f"**{den[:2]}**\n\n{hodnota}")
                else:
                    st.warning(f"**{den[:2]}**\n\nneuvedeno")

        # --- MAPA S NAVIGACÍ ---
        col_lat = 'latitude'
        col_lon = 'longitude'

        if pd.notna(radek[col_lat]) and pd.notna(radek[col_lon]):
            st.info("💡 **Tip:** Klikněte kamkoliv do mapy nebo použijte tlačítko '📍 Použít mou polohu' pro navigaci k lékaři.")
            
            # Bezpečné ošetření textů pro JavaScript
            clean_name = str(radek[col_jmeno]).replace("'", "").replace('"', "")
            clean_addr = f"{radek['ZZ_ulice']} {radek['ZZ_cislo_domovni_orientacni']}".replace("'", "").replace('"', "")

            mapa_html = f"""
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
            <style>
                #map-container {{ position: relative; width: 100%; height: 450px; }}
                #map {{ width: 100%; height: 100%; border-radius: 10px; border: 1px solid #ddd; }}
                .loc-button {{
                    position: absolute; top: 10px; right: 10px; z-index: 1000;
                    background: white; border: 2px solid rgba(0,0,0,0.2);
                    padding: 8px 12px; cursor: pointer; border-radius: 4px;
                    font-weight: bold; font-family: sans-serif; box-shadow: 0 2px 5px rgba(0,0,0,0.2);
                }}
                .loc-button:hover {{ background: #f4f4f4; }}
            </style>
            
            <div id="map-container">
                <button class="loc-button" onclick="getLocation()">📍 Použít mou polohu</button>
                <div id="map"></div>
            </div>

            <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
            <script>
                var dest = [{radek[col_lat]}, {radek[col_lon]}];
                var map = L.map('map').setView(dest, 15);
                
                L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
                    attribution: '© OpenStreetMap contributors'
                }}).addTo(map);

                // Značka lékaře
                var doctorMarker = L.marker(dest).addTo(map)
                    .bindPopup("<b>{clean_name}</b><br>{clean_addr}")
                    .openPopup();

                var routeLine = null;
                var startMarker = null;

                async function getRoute(lat, lng) {{
                    // OSRM API (profil foot = chůze)
                    // URL formát: lon,lat;lon,lat
                    var url = "https://router.project-osrm.org/route/v1/foot/" + 
                              lng + "," + lat + ";" + 
                              dest[1] + "," + dest[0] + "?overview=full&geometries=geojson";
                    
                    try {{
                        var response = await fetch(url);
                        var data = await response.json();
                        
                        if (data.routes && data.routes[0]) {{
                            var route = data.routes[0];
                            var dist = (route.distance / 1000).toFixed(2);
                            var dur = Math.round(route.duration / 60);

                            // Smazání staré trasy
                            if (routeLine) map.removeLayer(routeLine);

                            // Vykreslení nové trasy
                            routeLine = L.geoJSON(route.geometry, {{
                                style: {{ color: '#ff4b4b', weight: 5, opacity: 0.7 }}
                            }}).addTo(map);

                            // Startovní značka
                            if (!startMarker) {{
                                startMarker = L.circleMarker([lat, lng], {{ color: '#007bff', radius: 7, fillOpacity: 0.8 }}).addTo(map);
                            }} else {{
                                startMarker.setLatLng([lat, lng]);
                            }}

                            startMarker.bindPopup("<b>Váš start</b><br>Vzdálenost: " + dist + " km<br>Čas chůze: cca " + dur + " min").openPopup();
                            
                            // Zoom na celou trasu
                            map.fitBounds(routeLine.getBounds(), {{padding: [50, 50]}});
                        }}
                    }} catch (e) {{
                        console.error("Route error:", e);
                    }}
                }}

                function getLocation() {{
                    if (navigator.geolocation) {{
                        navigator.geolocation.getCurrentPosition(function(pos) {{
                            getRoute(pos.coords.latitude, pos.coords.longitude);
                        }}, function() {{
                            alert("Nelze získat polohu. Zkontrolujte oprávnění v prohlížeči.");
                        }});
                    }} else {{
                        alert("Geolokace není vaším prohlížečem podporována.");
                    }}
                }}

                map.on('click', function(e) {{
                    getRoute(e.latlng.lat, e.latlng.lng);
                }});
            </script>
            """
            components.html(mapa_html, height=470)
        else:
            st.warning("📍 Pro toto zařízení nejsou k dispozici GPS souřadnice pro zobrazení mapy.")
    else:
        st.info("Zvoleným filtrům neodpovídají žádná zařízení.")