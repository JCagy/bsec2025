from flask import Flask, render_template_string

app = Flask(__name__)

html_code = """
<!DOCTYPE html>
<html lang="cs">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard: Nejbližší Albert</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        body { margin: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; display: flex; flex-direction: column; height: 100vh; background: #f0f2f5; }
        #container { display: flex; flex: 1; overflow: hidden; flex-direction: row; }
        
        /* Levý panel - Sidebar */
        #sidebar { width: 360px; background: #f8f9fa; padding: 20px; display: flex; flex-direction: column; gap: 12px; border-right: 1px solid #d3d3d3; z-index: 1000; overflow-y: auto; }
        
        /* Mapa */
        #map { flex: 1; z-index: 1; background: #e5e3df; }

        /* Ovládací prvky */
        .search-group { display: flex; gap: 8px; margin-bottom: 5px; }
        input { flex: 1; padding: 12px; border: 1px solid #ccc; border-radius: 4px; font-size: 14px; }
        button { padding: 10px 15px; cursor: pointer; background: #005eb8; color: white; border: none; border-radius: 4px; font-weight: bold; transition: 0.2s; }
        button:hover { background: #004a91; }
        .loc-btn { background: #28a745; width: 100%; margin-bottom: 10px; }
        .loc-btn:hover { background: #218838; }

        /* Styl boxů (ArcGIS Dashboard styl) */
        .stat-box { background: white; border: 1px solid #e0e0e0; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
        .stat-box h2 { margin: 0; font-size: 13px; text-transform: uppercase; color: #666; letter-spacing: 0.5px; }
        .stat-box p { margin: 8px 0 0 0; font-size: 32px; font-weight: bold; color: #000; }
        .stat-box span { font-size: 18px; color: #444; font-weight: normal; margin-left: 4px; }
        .stat-box .sub-label { font-size: 16px; color: #005eb8; display: block; margin-top: 5px; }

        .hint { font-size: 12px; color: #888; text-align: center; margin-top: 5px; }

        /* Responzivita pro mobily */
        @media (max-width: 768px) {
            #container { flex-direction: column; }
            #sidebar { width: 100%; height: auto; border-right: none; border-bottom: 1px solid #ddd; padding: 15px; box-sizing: border-box; }
            #map { height: 300px; flex: none; flex-grow: 1; }
            .stat-box { padding: 15px; }
            .stat-box p { font-size: 26px; }
        }
    </style>
</head>
<body>

<div id="container">
    <div id="sidebar">
        <div class="search-group">
            <input type="text" id="addressInput" placeholder="Odkud vyrážíte? (ulice, Brno)">
            <button onclick="searchAddress()">Hledat</button>
        </div>
        <button class="loc-btn" onclick="getLocation()">📍 Použít mou polohu</button>
        
        <div class="stat-box">
            <h2>Nejbližší prodejna</h2>
            <p id="targetName" style="font-size: 22px;">--</p>
            <span id="targetAddr" class="sub-label">Zadejte startovní bod</span>
        </div>

        <div class="stat-box">
            <h2>Délka trasy</h2>
            <p id="distance">--<span>km</span></p>
        </div>

        <div class="stat-box">
            <h2>Doba chůze</h2>
            <p id="duration">--<span>min</span></p>
        </div>
        
        <p class="hint">Tip: Klikněte kamkoliv do mapy pro změnu startu.</p>
    </div>
    <div id="map"></div>
</div>

<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
    // 1. Seznam Albertů v Brně
    const stores = [
        { name: "Albert Tkalcovská", addr: "Tkalcovská 869/1", lat: 49.20054, lng: 16.62125 },
        { name: "Albert Vaňkovka", addr: "Ve Vaňkovce 1", lat: 49.18788, lng: 16.61278 },
        { name: "Albert Nám. Svobody", addr: "Náměstí Svobody 17", lat: 49.19456, lng: 16.60833 },
        { name: "Albert Mendlovo nám.", addr: "Mendlovo náměstí 13", lat: 49.19125, lng: 16.59424 },
        { name: "Albert Moravské nám.", addr: "Moravské náměstí 14", lat: 49.19778, lng: 16.60782 },
        { name: "Albert Campus", addr: "Netroufalky 770", lat: 49.17833, lng: 16.56528 }
    ];

    // 2. Inicializace mapy
    const map = L.map('map').setView([49.195, 16.608], 13);
    
    // Světlý podklad mapy (CartoDB Light)
    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);

    // Vykreslení prodejen na mapu
    stores.forEach(s => {
        L.circleMarker([s.lat, s.lng], { color: '#005eb8', radius: 6, fillOpacity: 0.9 }).addTo(map).bindPopup(s.name);
    });

    let routeLine, startMarker, activeTargetMarker;

    // Najde nejbližší prodejnu (vzdušnou čarou)
    function findNearestStore(lat, lng) {
        let nearest = stores[0];
        let minDist = Infinity;
        stores.forEach(store => {
            const dist = Math.sqrt(Math.pow(lat - store.lat, 2) + Math.pow(lng - store.lng, 2));
            if (dist < minDist) { minDist = dist; nearest = store; }
        });
        return nearest;
    }

    // Výpočet trasy přes OSRM
    async function calculateRoute(startLat, startLng, store) {
        // Používáme profil 'foot' pro chůzi
        const url = `https://router.project-osrm.org/route/v1/foot/${startLng},${startLat};${store.lng},${store.lat}?overview=full&geometries=geojson`;
        
        try {
            const res = await fetch(url);
            const data = await res.json();
            
            if (data.routes && data.routes[0]) {
                const route = data.routes[0];
                
                // --- Úprava času pro realističnost ---
                // OSRM je velmi optimistické, přidáváme 25 % (koeficient 1.25)
                const realMinutes = Math.round((route.duration / 60) * 1.25);
                const distanceKm = (route.distance / 1000).toFixed(1);

                // Update Sidebaru
                document.getElementById('targetName').innerText = store.name;
                document.getElementById('targetAddr').innerText = store.addr;
                document.getElementById('distance').innerHTML = `${distanceKm}<span>km</span>`;
                document.getElementById('duration').innerHTML = `${realMinutes}<span>min</span>`;
                
                // Vykreslení trasy
                if (routeLine) map.removeLayer(routeLine);
                routeLine = L.geoJSON(route.geometry, {
                    style: { color: '#e63946', weight: 6, opacity: 0.8 }
                }).addTo(map);
                
                // Zvýraznění cíle
                if (activeTargetMarker) map.removeLayer(activeTargetMarker);
                activeTargetMarker = L.circleMarker([store.lat, store.lng], {color: 'red', radius: 10, weight: 3}).addTo(map);

                map.fitBounds(routeLine.getBounds(), {padding: [50, 50]});
            }
        } catch (e) { console.error("Chyba navigace:", e); }
    }

    function setStartPoint(lat, lng) {
        const pos = [lat, lng];
        if (startMarker) startMarker.setLatLng(pos);
        else startMarker = L.marker(pos).addTo(map);
        
        const nearest = findNearestStore(lat, lng);
        calculateRoute(lat, lng, nearest);
    }

    // Vyhledávání adresy
    async function searchAddress() {
        const input = document.getElementById('addressInput').value;
        if (!input) return;
        const res = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(input + ", Brno")}`);
        const data = await res.json();
        if (data && data[0]) {
            setStartPoint(parseFloat(data[0].lat), parseFloat(data[0].lon));
        } else {
            alert("Adresa nebyla nalezena. Zkuste upřesnit název ulice.");
        }
    }

    // Moje poloha (GPS)
    function getLocation() {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(pos => {
                setStartPoint(pos.coords.latitude, pos.coords.longitude);
            }, () => alert("Nelze získat polohu. Povolte GPS v prohlížeči."));
        }
    }

    // Kliknutí do mapy
    map.on('click', e => setStartPoint(e.latlng.lat, e.latlng.lng));

    // Spuštění vyhledávání klávesou Enter
    document.getElementById('addressInput').addEventListener('keypress', function (e) {
        if (e.key === 'Enter') searchAddress();
    });
</script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(html_code)

if __name__ == '__main__':
    # Spuštění Flask serveru
    app.run(debug=True)