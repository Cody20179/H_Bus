<template>
  <div style="height: 100vh;display:flex;flex-direction:column;">
    <div style="padding:10px;background:#fff;z-index:1000;">
      <button @click="exportRoute('geojson')" style="margin-right:10px;">匯出GeoJSON</button>
      <button @click="exportRoute('list')">匯出座標清單</button>
    </div>
    <div id="map" style="flex:1; width:100vw;"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

const HUALIEN_CENTER = [23.9918, 121.6169];
const mapRef = ref<any>(null);

// 一開始就要標的 marker 座標
const INIT_MARKERS: [number, number][] = [
  [23.993020, 121.603219],
  [23.992912, 121.617817],
  [23.992744, 121.619466],
  [23.991411, 121.619984],
  [23.989522, 121.619688],
  [23.988424, 121.618438],
  [23.991812, 121.616885],
  [23.991411, 121.619984],
];

// 只記錄上一個點
let lastPoint: [number, number] | null = null;

// 存所有已snap路徑段
const routeSegments = ref<[number, number][][]>([]);

onMounted(() => {
  mapRef.value = L.map('map', {
    center: HUALIEN_CENTER,
    zoom: 15,
    maxZoom: 18,
    minZoom: 12
  });
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "© OpenStreetMap"
  }).addTo(mapRef.value);

  // 一開始就把 marker 標出來
  INIT_MARKERS.forEach(([lat, lng]) => {
    L.marker([lat, lng]).addTo(mapRef.value);
  });

  mapRef.value.on('click', function(e: any) {
    handleSelectPoint(e.latlng.lat, e.latlng.lng);
  });
});

async function handleSelectPoint(lat: number, lng: number) {
  if (lastPoint === null) {
    lastPoint = [lat, lng];
    return;
  }
  const p1 = lastPoint;
  const p2: [number, number] = [lat, lng];
  lastPoint = p2;
  await snapAndDraw(p1, p2);
}

async function snapAndDraw(p1: [number, number], p2: [number, number]) {
  const routeParam = `${p1[0]},${p1[1]};${p2[0]},${p2[1]}`;
  try {
    const res = await fetch(`http://localhost:8000/snap?route=${routeParam}`);
    const data = await res.json();
    if (data.features && data.features[0].geometry.type === "LineString") {
      const snapCoords = data.features[0].geometry.coordinates.map(([lng, lat]: [number, number]) => [lat, lng]);
      L.polyline(snapCoords, {color: '#1976d2', weight: 5}).addTo(mapRef.value);
      routeSegments.value.push(snapCoords);
    }
  } catch (e) {
    const seg = [p1, p2];
    L.polyline(seg, {color: '#aaa', weight: 3, dashArray: '6 4'}).addTo(mapRef.value);
    routeSegments.value.push(seg);
  }
}

function exportRoute(format: "geojson" | "list" = "geojson") {
  if (routeSegments.value.length === 0) return;
  let path: [number, number][] = [];
  for (let i = 0; i < routeSegments.value.length; i++) {
    const seg = routeSegments.value[i];
    if (i === 0) path = seg;
    else path = path.concat(seg.slice(1));
  }
  if (format === "geojson") {
    const geojson = {
      type: "LineString",
      coordinates: path.map(([lat, lng]) => [lng, lat])
    };
    downloadFile(JSON.stringify(geojson, null, 2), "route.geojson");
  } else if (format === "list") {
    const listText = path.map(([lat, lng]) => `${lat},${lng}`).join('\n');
    downloadFile(listText, "route.txt");
  }
}

function downloadFile(content: string, filename: string) {
  const blob = new Blob([content], {type: "text/plain"});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
</script>
