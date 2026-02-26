import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import urllib.parse
import json

# --- 1. NASTAVENÍ STRÁNKY ---
st.set_page_config(page_title="ŠtatlMed.net", layout="wide")

# CSS STYLY
st.markdown("""
    <style>
    /* Červené tlačítko pro pohotovost */
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
    
    /* Navigační tlačítka v detailu */
    .nav-button-container div[data-testid="stColumn"] button {
        background-color: white !important;
        color: #1e3d59 !important;
        border: 3px solid #4ebff4 !important;
        height: 100px !important;
        font-size: 22px !important;
        font-weight: bold !important;
        border-radius: 8px !important;
        transition: all 0.3s ease;
    }
    
    div.nav-button-container div[data-testid="stColumn"] button:hover {
        background-color: #f0faff !important;
        border-color: #0096db !important;
    }

    .info-box {
        background-color: #f0f2f6; 
        padding: 20px; 
        border-radius: 10px; 
        text-align: center; 
        border: 1px solid #ddd; 
        height: 100px; 
        display: flex; 
        flex-direction: column; 
        justify-content: center;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. NAČTENÍ DAT ---

@st.cache_data
def nacti_data():
    try:
        # Načtení souboru s pojišťovnami
        df = pd.read_csv("upraveni_lekari_brno_s_hodinami_zp.csv", sep=";", low_memory=False)
        df.columns = df.columns.str.strip()

        mapovani_poj = {
            "vzp": "VZP", "vozp": "VoZP", "pzp": "ČPZP", "zpmv": "ZPMV",
            "rbp": "RBP", "ozp": "OZP", "skp": "Škoda"
        }

        if 'ZP' in df.columns:
            df['ZP_raw'] = df['ZP'].fillna('').astype(str).str.lower()
            def formatuj_pojistovny(text):
                if not text or text.lower() == 'nan': return "Neuvedeno"
                seznam = [p.strip() for p in text.split(',')]
                hezky = [mapovani_poj.get(p, p.upper()) for p in seznam if p]
                return ", ".join(hezky)
            df['Smluvní pojišťovny'] = df['ZP_raw'].apply(formatuj_pojistovny)
        else:
            df['ZP_raw'] = ""
            df['Smluvní pojišťovny'] = "Neuvedeno"

        def priprav_odkaz(row):
            web = str(row.get('poskytovatel_web', ''))
            if web == '' or web.lower() in ['nan', 'none']:
                return f"https://www.google.com/search?q={urllib.parse.quote_plus(str(row['ZZ_nazev']))}"
            return web if web.startswith('http') else "https://" + web
        df['web_url'] = df.apply(priprav_odkaz, axis=1)
        
        return df, mapovani_poj
    except Exception as e:
        st.error(f"Chyba při načítání dat: {e}")
        return None, {}

@st.cache_data
def nacti_zastavky():
    try:
        stops_df = pd.read_csv("brno_Stops.csv")
        cols = ['stop_name', 'latitude', 'longitude', 'wheelchair_boarding']
        return stops_df[cols].dropna(subset=['latitude', 'longitude']).to_dict('records')
    except:
        return []

data, mapovani = nacti_data()
zastavky_json = json.dumps(nacti_zastavky())

# --- 3. DIALOGY ---

@st.dialog("Naléhavá pomoc - Pohotovosti v okolí", width="large")
def nouzova_mapa():
    pohotovosti = [
        {"jmeno": "FN Brno - Bohunice", "adresa": "Jihlavská 20, Brno", "lat": 49.1747, "lon": 16.5686},
        {"jmeno": "FN u sv. Anny", "adresa": "Pekařská 53, Brno", "lat": 49.1906, "lon": 16.5986},
        {"jmeno": "Úrazová nemocnice", "adresa": "Ponávka 6, Brno", "lat": 49.1997, "lon": 16.6138},
        {"jmeno": "Dětská nemocnice", "adresa": "Černopolní 9, Brno", "lat": 49.2045, "lon": 16.6159},
        {"jmeno": "Vojenská nemocnice", "adresa": "Zábrdovická 3, Brno", "lat": 49.2014, "lon": 16.6341},
    ]
    html = f"""
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <div style="display: flex; gap: 10px; height: 400px; font-family: sans-serif;">
        <div style="width:40%; overflow-y:auto; border:1px solid #ddd; padding:5px;">
            <table style="width:100%; font-size:12px; border-collapse:collapse;">
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
                L.marker([h.lat, h.lon]).addTo(map).bindPopup("<b>" + h.jmeno + "</b><br>" + h.adresa);
            }});
            hosps.sort((a,b) => a.dist - b.dist);
            document.getElementById('t-body').innerHTML = hosps.map(h => 
                `<tr><td style="padding:8px; border-bottom:1px solid #eee;">
                    <b>${{h.jmeno}}</b><br><small style="color:#666;">${{h.adresa}}</small><br>
                    <b style="color:#ff4b4b;">${{h.dist.toFixed(1)}} km</b>
                </td></tr>`
            ).join('');
        }});
    </script>
    """
    components.html(html, height=420)
    st.error("V případě přímého ohrožení života volejte 155.")

@st.dialog("Trasa autem", width="large")
def dialog_auto(lat, lon, jmeno):
    # Očištění textů pro JavaScript
    clean_name = str(jmeno).replace("'", "").replace('"', "")
    
    html = f"""
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <div id="map_auto" style="width: 100%; height: 400px; border-radius: 10px;"></div>
    <div id="info_auto" style="margin-top:10px; font-size:18px; font-weight:bold; color:#ff4b4b; font-family:sans-serif;">Hledám trasu...</div>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        const cíl = [{lat}, {lon}];
        const map = L.map('map_auto').setView(cíl, 13);
        L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png').addTo(map);
        
        navigator.geolocation.getCurrentPosition(pos => {{
            const start = [pos.coords.latitude, pos.coords.longitude];
            fetch("https://router.project-osrm.org/route/v1/driving/" + start[1] + "," + start[0] + ";" + cíl[1] + "," + cíl[0] + "?overview=full&geometries=geojson")
                .then(r => r.json()).then(data => {{
                    const route = data.routes[0];
                    L.geoJSON(route.geometry, {{style: {{color: 'red', weight: 6}}}}).addTo(map);
                    
                    // 2. POPISEK PRO CÍL (JMÉNO + ADRESA)
                    L.marker(cíl).addTo(map).bindPopup("<b>{clean_name}</b><br>{clean_addr}");

                    // 1. POPISEK PRO START (MOJE POLOHA)
                    L.marker(start).addTo(map).bindPopup("<b>Moje poloha</b>").openPopup();
                    
                    
                    map.fitBounds(L.geoJSON(route.geometry).getBounds(), {{padding:[50,50]}});
                    document.getElementById('info_auto').innerHTML = "🚗 " + (route.distance/1000).toFixed(1) + " km | ⏱️ " + Math.round(route.duration/60) + " min";
                }});
        }});
    </script>
    """
    components.html(html, height=470)

@st.dialog("Nejbližší zastávky MHD", width="large")
def dialog_mhd(lat_doc, lon_doc, jmeno_doc, zastavky_data):
    html_mhd = f"""
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        #mhd-layout {{ font-family: sans-serif; }}
        .legend {{ 
            display: flex; gap: 15px; font-size: 13px; margin: 10px 0; 
            padding: 10px; background: #ffffff; border-radius: 8px; border: 1px solid #ccc; 
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .leg-item {{ display: flex; align-items: center; gap: 6px; font-weight: bold; }}
        .dot {{ width: 14px; height: 14px; border-radius: 50%; border: 1px solid #000; display: inline-block; }}
        #footer-mhd {{ display: flex; justify-content: space-between; align-items: center; margin-top: 15px; }}
        #btn-dpmb {{ 
            border: 3px solid #4ebff4; background: white; color: #1e3d59; 
            padding: 10px 20px; font-weight: bold; text-decoration: none; 
            border-radius: 6px; display: none; transition: 0.2s;
        }}
        #btn-dpmb:hover {{ background: #4ebff4; color: white; }}
        .leaflet-tooltip-own {{ 
            background: white; border: 2px solid #333; font-weight: bold; 
            padding: 5px 10px; border-radius: 4px; font-size: 13px; color: #000;
        }}
    </style>
    <div id="mhd-layout">
        <div class="legend">
            <span style="margin-right:5px;">Bezbariérovost:</span>
            <div class="leg-item"><span class="dot" style="background:#28a745"></span> Ano</div>
            <div class="leg-item"><span class="dot" style="background:#dc3545"></span> Ne</div>
            <div class="leg-item"><span class="dot" style="background:#ffc107"></span> Neznámo</div>
        </div>
        <div id="map_mhd" style="width: 100%; height: 380px; border-radius: 10px; border: 2px solid #4ebff4;"></div>
        <div id="footer-mhd">
            <div id="info_mhd" style="font-size: 16px; color: #1e3d59; border-left: 4px solid #4ebff4; padding-left: 10px;">
                Hledám nejbližší spojení...
            </div>
            <a id="btn-dpmb" target="_blank">🔎 Vyhledat spoj na DPMB.cz</a>
        </div>
    </div>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        const allStops = {zastavky_data};
        const docLoc = [{lat_doc}, {lon_doc}];
        
        function getDist(l1, o1, l2, o2) {{
            return Math.sqrt(Math.pow(l1-l2, 2) + Math.pow(o1-o2, 2));
        }}

        function findNearest(lat, lon) {{
            let minD = Infinity, nearest = null;
            allStops.forEach(s => {{
                let d = getDist(lat, lon, s.latitude, s.longitude);
                if (d < minD) {{ minD = d; nearest = s; }}
            }});
            return nearest;
        }}

        // OPRAVENÁ FUNKCE PRO BARVY
        function getStopColor(val) {{
            const v = String(val); // Převedení na string pro jistotu
            if (v.startsWith('1')) return '#28a745'; // Bezbariérová
            if (v.startsWith('2')) return '#dc3545'; // Bariérová
            return '#ffc107'; // Neznámá (žlutá)
        }}

        const map = L.map('map_mhd').setView(docLoc, 15);
        L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png').addTo(map);

        // Ikona lékaře
        L.marker(docLoc, {{ icon: L.divIcon({{ html: '🩺', className: 'doc-icon', iconSize: [30, 30] }}) }}).addTo(map);

        navigator.geolocation.getCurrentPosition(pos => {{
            const uLoc = [pos.coords.latitude, pos.coords.longitude];
            const s1 = findNearest(uLoc[0], uLoc[1]); // Nástup
            const s2 = findNearest(docLoc[0], docLoc[1]); // Výstup u lékaře

            if (s1 && s2) {{
                const p1 = [s1.latitude, s1.longitude];
                const p2 = [s2.latitude, s2.longitude];

                // Čára mezi zastávkami
                L.polyline([p1, p2], {{color: '#4ebff4', weight: 4, dashArray: '8, 8', opacity: 0.6}}).addTo(map);

                // NÁSTUPNÍ BOD (s1)
                L.circleMarker(p1, {{
                    radius: 12, 
                    fillColor: getStopColor(s1.wheelchair_boarding), 
                    color: '#000', 
                    weight: 3, 
                    fillOpacity: 1
                }}).addTo(map).bindTooltip("📍 Váš nástup:<br>" + s1.stop_name, {{
                    permanent: true, 
                    direction: 'top', 
                    className: 'leaflet-tooltip-own',
                    offset: [0, -10]
                }});

                // CÍLOVÝ BOD (s2)
                L.circleMarker(p2, {{
                    radius: 12, 
                    fillColor: getStopColor(s2.wheelchair_boarding), 
                    color: '#000', 
                    weight: 3, 
                    fillOpacity: 1
                }}).addTo(map).bindTooltip("🏁 Cílová zastávka:<br>" + s2.stop_name, {{
                    permanent: true, 
                    direction: 'top', 
                    className: 'leaflet-tooltip-own',
                    offset: [0, -10]
                }});

                // Textové info
                document.getElementById('info_mhd').innerHTML = "<b>📍Odkud:</b> " + s1.stop_name + "<br><b>🏁Kam:</b> " + s2.stop_name;
                
                // Tlačítko na DPMB
                const btn = document.getElementById('btn-dpmb');
                btn.href = "https://www.dpmb.cz/spojeni?from=" + encodeURIComponent(s1.stop_name) + "&to=" + encodeURIComponent(s2.stop_name);
                btn.style.display = "block";

                // Automatické vycentrování mapy, aby bylo vidět vše
                const group = new L.featureGroup([L.marker(p1), L.marker(p2), L.marker(docLoc)]);
                map.fitBounds(group.getBounds().pad(0.2));
            }}
        }}, err => {{
            document.getElementById('info_mhd').innerHTML = "⚠️ Nepodařilo se zaměřit vaši polohu.";
        }});
    </script>
    """
    components.html(html_mhd, height=540)

# --- 4. HLAVNÍ APLIKACE ---

col_titul, col_tlacitko = st.columns([3, 1])
with col_titul:
    st.title("ŠtatlMed.net 🩺")
with col_tlacitko:
    if st.button("🏥  Valim do špitálu", use_container_width=True):
        nouzova_mapa()

if data is not None:
    # Sidebar filtry
    st.sidebar.header("Filtrování")
    mesto_col = 'ZZ_obec' if 'ZZ_obec' in data.columns else data.columns[0]
    vybrane_mesto = st.sidebar.selectbox("Město:", ["Všechna"] + sorted([str(x) for x in data[mesto_col].unique() if pd.notna(x)]))
    
    obor_col = 'ZZ_obor_pece_strucne' if 'ZZ_obor_pece_strucne' in data.columns else data.columns[0]
    vybrany_obor = st.sidebar.selectbox("Odbornost:", ["Všechny"] + sorted([str(x) for x in data[obor_col].unique() if pd.notna(x)]))
    
    vybrane_poj = st.sidebar.multiselect("Smluvní pojišťovny:", options=sorted(mapovani.values()))

    # Filtrování
    df_f = data.copy()
    if vybrane_mesto != "Všechna": df_f = df_f[df_f[mesto_col] == vybrane_mesto]
    if vybrany_obor != "Všechny": df_f = df_f[df_f[obor_col] == vybrany_obor]
    if vybrane_poj:
        inv_map = {v: k for k, v in mapovani.items()}
        vybrane_surove = [inv_map[p] for p in vybrane_poj]
        maska = df_f['ZP_raw'].apply(lambda x: any(s in x for s in vybrane_surove))
        df_f = df_f[maska]

    st.subheader(f"Seznam nalezených zařízení ({len(df_f)})")
    
    # HLAVNÍ TABULKA - POJIŠŤOVNY MÍSTO WEBU
    vystup_tabulky = st.dataframe(
        df_f[['ZZ_nazev', obor_col, mesto_col, 'ZZ_ulice', 'ZZ_cislo_domovni_orientacni', 'Smluvní pojišťovny']], 
        use_container_width=True, 
        hide_index=True, 
        on_select="rerun", 
        selection_mode="single-row",
        column_config={
            "ZZ_nazev": "Název",
            obor_col: "Obor",
            mesto_col: "Obec",
            "ZZ_ulice": "Ulice",
            "ZZ_cislo_domovni_orientacni": "Č.p./or.",
            "Smluvní pojišťovny": st.column_config.TextColumn("Pojišťovny", width="large")
        }
    )

    if not df_f.empty:
        sel = vystup_tabulky.get("selection", {}).get("rows", [0])
        idx = sel[0] if sel else 0
        radek = df_f.iloc[idx]
        
        st.markdown("---")
        st.subheader(f"Detail: {radek['ZZ_nazev']}")
        
        c1, c2 = st.columns([2, 1])
        with c1:
            st.markdown(f"""<div class="info-box">
                <small>SMLUVNÍ POJIŠŤOVNY</small><br><b>{radek['Smluvní pojišťovny']}</b>
            </div>""", unsafe_allow_html=True)
        with c2:
            st.markdown(f"""<a href="{radek['web_url']}" target="_blank" style="text-decoration:none;">
                <div style="background:#4ebff4; color:white; height:100px; border-radius:10px; display:flex; align-items:center; justify-content:center; font-weight:bold; font-size:18px;">
                    🌐 OTEVŘÍT WEB / INFO
                </div>
            </a>""", unsafe_allow_html=True)

        # Hodiny
        st.write("")
        dni = ['Pondělí', 'Úterý', 'Středa', 'Čtvrtek', 'Pátek', 'Sobota', 'Neděle']
        cols_h = st.columns(7)
        for i, den in enumerate(dni):
            with cols_h[i]:
                h = str(radek[den]) if den in radek else "---"
                st.info(f"**{den[:2]}**\n\n{h}")

        # --- MAPA V DETAILU S NÁZVEM A ADRESOU ---
        if pd.notna(radek['latitude']) and pd.notna(radek['longitude']):
            # Příprava textu adresy a jména (očištění od uvozovek pro JS)
            clean_name = str(radek['ZZ_nazev']).replace("'", "").replace('"', "")
            full_addr = f"{radek['ZZ_ulice']} {radek['ZZ_cislo_domovni_orientacni']}"
            clean_addr = str(full_addr).replace("'", "").replace('"', "")

            m_html = f"""
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
            <div id="m_map" style="width: 100%; height: 350px; border-radius: 10px; border: 1px solid #ddd;"></div>
            <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
            <script>
                var loc = [{radek['latitude']}, {radek['longitude']}];
                var map = L.map('m_map').setView(loc, 16);
                L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png').addTo(map);
                
                // PŘIDÁNÍ ADRESY DO POPUPU
                L.marker(loc).addTo(map)
                    .bindPopup("<b>{clean_name}</b><br>{clean_addr}") 
                    .openPopup();
            </script>
            """
            components.html(m_html, height=370)

            # Navigační tlačítka
            st.markdown('<div class="nav-button-container">', unsafe_allow_html=True)
            b1, b2 = st.columns(2)
            with b1:
                if st.button("🚗 Pojedu autem", use_container_width=True):
                    dialog_auto(radek['latitude'], radek['longitude'], radek['ZZ_nazev'])
            with b2:
                if st.button("🚌Pojedu MHD", use_container_width=True):
                    dialog_mhd(radek['latitude'], radek['longitude'], radek['ZZ_nazev'], zastavky_json)
            st.markdown('</div>', unsafe_allow_html=True)