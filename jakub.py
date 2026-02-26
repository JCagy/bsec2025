import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import urllib.parse
import json

# --- 1. NASTAVENÍ STRÁNKY ---
st.set_page_config(page_title="Lékařský vyhledávač Brno", layout="wide")

# CSS pro vzhled (červené tlačítko a velká navigační tlačítka)
st.markdown("""
    <style>
    /* Červené tlačítko "Potřebuju pomoct" */
    div[data-testid="stColumn"]:nth-child(2) button {
        background-color: #ff4b4b !important;
        color: white !important;
        border: none !important;
        padding: 0.6rem 1.2rem !important;
        border-radius: 8px !important;
        font-weight: bold !important;
        font-size: 18px !important;
        margin-top: 25px !important;
    }
    
    /* Velká bílá navigační tlačítka s modrým rámem */
    div.nav-button-container button {
        background-color: white !important;
        color: #1e3d59 !important;
        border: 3px solid #4ebff4 !important;
        height: 100px !important;
        font-size: 22px !important;
        font-weight: bold !important;
        border-radius: 8px !important;
        transition: all 0.3s ease;
    }
    div.nav-button-container button:hover {
        background-color: #f0faff !important;
        border-color: #0096db !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. NAČTENÍ DAT ---

@st.cache_data
def nacti_data_lekaru():
    try:
        df = pd.read_csv("upraveni_lekari_brno_s_hodinami.csv", sep=";", low_memory=False)
        df.columns = df.columns.str.strip()
        def oprav_web(row):
            web = str(row.get('poskytovatel_web', ''))
            if web == '' or web.lower() in ['nan', 'none']:
                return f"https://www.google.com/search?q={urllib.parse.quote_plus(str(row['ZZ_nazev']))}"
            return web if web.startswith('http') else "https://" + web
        df['web_odkaz'] = df.apply(oprav_web, axis=1)
        return df
    except Exception as e:
        st.error(f"Chyba při načítání lékařů: {e}")
        return None

@st.cache_data
def nacti_zastavky():
    try:
        stops_df = pd.read_csv("brno_Stops.csv")
        return stops_df[['stop_name', 'latitude', 'longitude']].dropna().to_dict('records')
    except Exception as e:
        st.error(f"Chyba při načítání zastávek: {e}")
        return []

data = nacti_data_lekaru()
zastavky_json = json.dumps(nacti_zastavky())

# --- 3. DIALOGOVÁ OKNA (POPUPS) ---

@st.dialog("Naléhavá pomoc - Pohotovosti v okolí", width="large")
def nouzova_mapa():
    pohotovosti = [
        {"jmeno": "FN Brno - Bohunice", "adresa": "Jihlavská 20, Brno", "lat": 49.1747, "lon": 16.5686},
        {"jmeno": "FN u sv. Anny", "adresa": "Pekařská 53, Brno", "lat": 49.1906, "lon": 16.5986},
        {"jmeno": "Úrazová nemocnice", "adresa": "Ponávka 6, Brno", "lat": 49.1997, "lon": 16.6138},
        {"jmeno": "Dětská nemocnice", "adresa": "Černopolní 9, Brno", "lat": 49.2045, "lon": 16.6159},
    ]
    html = f"""
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <div style="display: flex; gap: 10px; height: 400px; font-family: sans-serif;">
        <div style="width:40%; overflow-y:auto; border:1px solid #ddd; padding:5px;">
            <table style="width:100%; font-size:12px; border-collapse:collapse;" id="h-table">
                <tbody id="t-body"><tr><td>Zaměřuji polohu...</td></tr></tbody>
            </table>
        </div>
        <div id="map_p" style="width:60%; border-radius:8px;"></div>
    </div>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        const hosps = {json.dumps(pohotovosti)};
        const map = L.map('map_p').setView([49.195, 16.608], 12);
        L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png').addTo(map);
        navigator.geolocation.getCurrentPosition(pos => {{
            const uL = [pos.coords.latitude, pos.coords.longitude];
            L.circleMarker(uL, {{radius:7, color:'blue'}}).addTo(map).bindPopup("Moje poloha");
            hosps.forEach(h => {{
                h.dist = Math.sqrt(Math.pow(uL[0]-h.lat,2)+Math.pow(uL[1]-h.lon,2)) * 111;
                L.marker([h.lat, h.lon]).addTo(map).bindPopup(h.jmeno);
            }});
            hosps.sort((a,b) => a.dist - b.dist);
            document.getElementById('t-body').innerHTML = hosps.map(h => 
                `<tr><td style="padding:8px; border-bottom:1px solid #eee;"><b>${{h.jmeno}}</b><br>${{h.dist.toFixed(1)}} km</td></tr>`
            ).join('');
        }});
    </script>
    """
    components.html(html, height=420)
    st.error("V případě přímého ohrožení života volejte 155.")

@st.dialog("Trasa autem k lékaři", width="large")
def dialog_auto(lat_cíl, lon_cíl, jmeno_cíl):
    clean_name = str(jmeno_cíl).replace("'", "").replace('"', "")
    html_auto = f"""
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <div id="map_auto" style="width: 100%; height: 400px; border-radius: 10px;"></div>
    <div id="info_auto" style="margin-top:10px; font-size:18px; font-weight:bold; color:#ff4b4b; font-family:sans-serif;">Získávání polohy...</div>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        const cíl = [{lat_cíl}, {lon_cíl}];
        const map = L.map('map_auto').setView(cíl, 13);
        L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png').addTo(map);
        
        navigator.geolocation.getCurrentPosition(pos => {{
            const start = [pos.coords.latitude, pos.coords.longitude];
            fetch("https://router.project-osrm.org/route/v1/driving/" + start[1] + "," + start[0] + ";" + cíl[1] + "," + cíl[0] + "?overview=full&geometries=geojson")
                .then(r => r.json()).then(data => {{
                    const route = data.routes[0];
                    L.geoJSON(route.geometry, {{style: {{color: 'red', weight: 6}}}}).addTo(map);
                    L.marker(start).addTo(map).bindPopup("Vaše poloha");
                    L.marker(cíl).addTo(map).bindPopup("{clean_name}").openPopup();
                    map.fitBounds(L.geoJSON(route.geometry).getBounds(), {{padding:[30,30]}});
                    
                    const dist = (route.distance / 1000).toFixed(1);
                    const dur = Math.round(route.duration / 60);
                    document.getElementById('info_auto').innerHTML = "🚗 Vzdálenost: " + dist + " km | ⏱️ Čas jízdy: " + dur + " min";
                }});
        }}, () => {{ document.getElementById('info_auto').innerHTML = "Chyba: Poloha nedostupná."; }});
    </script>
    """
    components.html(html_auto, height=470)

@st.dialog("Nejbližší zastávky MHD", width="large")
def dialog_mhd(lat_doc, lon_doc, jmeno_doc, zastavky_data):
    html_mhd = f"""
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <div id="map_mhd" style="width: 100%; height: 400px; border-radius: 10px;"></div>
    <div id="info_mhd" style="margin-top:15px; font-family:sans-serif; font-size:16px; border-left: 4px solid #4ebff4; padding-left: 10px;">Hledám zastávky...</div>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        const allStops = {zastavky_data};
        const docLoc = [{lat_doc}, {lon_doc}];
        function getDist(l1, o1, l2, o2) {{ return Math.sqrt(Math.pow(l1-l2, 2) + Math.pow(o1-o2, 2)); }}
        function findNearest(lat, lon) {{
            let minD = Infinity, nearest = null;
            allStops.forEach(s => {{
                let d = getDist(lat, lon, s.latitude, s.longitude);
                if (d < minD) {{ minD = d; nearest = s; }}
            }});
            return nearest;
        }}
        const map = L.map('map_mhd').setView(docLoc, 14);
        L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png').addTo(map);
        navigator.geolocation.getCurrentPosition(pos => {{
            const uLoc = [pos.coords.latitude, pos.coords.longitude];
            const s1 = findNearest(uLoc[0], uLoc[1]);
            const s2 = findNearest(docLoc[0], docLoc[1]);
            if (s1 && s2) {{
                const p1 = [s1.latitude, s1.longitude], p2 = [s2.latitude, s2.longitude];
                L.polyline([p1, p2], {{color: '#4ebff4', weight: 4, dashArray: '10, 10'}}).addTo(map);
                L.marker(p1).addTo(map).bindPopup("<b>Nástup:</b><br>" + s1.stop_name).openPopup();
                L.marker(p2).addTo(map).bindPopup("<b>Výstup:</b><br>" + s2.stop_name);
                document.getElementById('info_mhd').innerHTML = "🚏 <b>Nástup:</b> " + s1.stop_name + "<br>🏁 <b>Výstup:</b> " + s2.stop_name;
                map.fitBounds([p1, p2], {{padding: [50, 50]}});
            }}
        }});
    </script>
    """
    components.html(html_mhd, height=480)

# --- 4. HLAVNÍ APLIKACE ---

col_titul, col_tlacitko = st.columns([3, 1])
with col_titul:
    st.title("Vyhledávač lékařských zařízení 🩺")
with col_tlacitko:
    if st.button("Potřebuju pomoct", use_container_width=True):
        nouzova_mapa()

if data is not None:
    st.sidebar.header("Filtrování")
    mesto_col = 'ZZ_obec' if 'ZZ_obec' in data.columns else data.columns[0]
    vybrane_mesto = st.sidebar.selectbox("Město:", ["Všechna"] + sorted([str(x) for x in data[mesto_col].unique() if pd.notna(x)]))

    obor_col = 'ZZ_obor_pece_strucne' if 'ZZ_obor_pece_strucne' in data.columns else data.columns[0]
    vybrany_obor = st.sidebar.selectbox("Odbornost:", ["Všechny"] + sorted([str(x) for x in data[obor_col].unique() if pd.notna(x)]))

    df_f = data.copy()
    if vybrane_mesto != "Všechna": df_f = df_f[df_f[mesto_col] == vybrane_mesto]
    if vybrany_obor != "Všechny": df_f = df_f[df_f[obor_col] == vybrany_obor]

    st.subheader(f"Seznam ({len(df_f)})")
    vystup_tabulky = st.dataframe(
        df_f[['ZZ_nazev', obor_col, mesto_col, 'ZZ_ulice', 'ZZ_cislo_domovni_orientacni', 'web_odkaz']], 
        use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row",
        column_config={"web_odkaz": st.column_config.LinkColumn("Web / Google")}
    )

    if not df_f.empty:
        sel = vystup_tabulky.get("selection", {}).get("rows", [0])
        idx = sel[0] if sel else 0
        radek = df_f.iloc[idx]
        
        st.markdown("---")
        st.subheader(f"Detail: {radek['ZZ_nazev']}")
        
        # Ordinační hodiny
        cols_h = st.columns(7)
        dni = ['Pondělí', 'Úterý', 'Středa', 'Čtvrtek', 'Pátek', 'Sobota', 'Neděle']
        for i, den in enumerate(dni):
            with cols_h[i]:
                h = str(radek[den]) if den in radek else "neuvedeno"
                st.info(f"**{den[:2]}**\n\n{h}")

        # Mapa lékaře
        if pd.notna(radek['latitude']) and pd.notna(radek['longitude']):
            clean_name = str(radek['ZZ_nazev']).replace("'", "").replace('"', "")
            m_html = f"""
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
            <div id="m_map" style="width: 100%; height: 400px; border-radius: 10px; border: 1px solid #ddd;"></div>
            <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
            <script>
                var loc = [{radek['latitude']}, {radek['longitude']}];
                var map = L.map('m_map').setView(loc, 16);
                L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png').addTo(map);
                L.marker(loc).addTo(map).bindPopup("<b>{clean_name}</b>").openPopup();
            </script>
            """
            components.html(m_html, height=420)

            # Tlačítka
            st.markdown('<div class="nav-button-container">', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Pojedu autem", use_container_width=True):
                    dialog_auto(radek['latitude'], radek['longitude'], radek['ZZ_nazev'])
            with c2:
                if st.button("Pojedu MHD", use_container_width=True):
                    dialog_mhd(radek['latitude'], radek['longitude'], radek['ZZ_nazev'], zastavky_json)
            st.markdown('</div>', unsafe_allow_html=True)