# -*- coding: utf-8 -*-
"""Genera data/visor.html: un visor autonomo (tabla + filtros + mapa) con los
datos embebidos. Se abre con doble clic en el navegador. Boton de descarga CSV
(se abre directamente en Excel) sobre la seleccion filtrada.
"""
import json
import os

import dataset

OUT = os.path.join(os.path.dirname(__file__), "data", "visor.html")


def generar():
    datos = dataset.cargar()
    html = TEMPLATE.replace("/*DATOS*/", json.dumps(datos, ensure_ascii=False))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[OK] visor -> {OUT}  ({len(datos)} lotes). Abrelo con doble clic.")


TEMPLATE = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Subastas BOE - Visor</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  :root{--bg:#0f1620;--panel:#182430;--line:#2a3a4a;--fg:#e6edf3;--mut:#8aa0b3;--acc:#3fb0ff}
  *{box-sizing:border-box}
  body{margin:0;font:14px/1.4 system-ui,Segoe UI,Roboto,sans-serif;background:var(--bg);color:var(--fg)}
  header{padding:12px 16px;background:var(--panel);border-bottom:1px solid var(--line);
    display:flex;gap:16px;align-items:baseline;flex-wrap:wrap}
  h1{font-size:16px;margin:0}
  .mut{color:var(--mut)}
  #filtros{display:flex;gap:10px;flex-wrap:wrap;padding:10px 16px;background:var(--panel);
    border-bottom:1px solid var(--line);align-items:center}
  #filtros label{display:flex;flex-direction:column;font-size:11px;color:var(--mut);gap:3px}
  input,select,button{background:var(--bg);color:var(--fg);border:1px solid var(--line);
    border-radius:6px;padding:6px 8px;font-size:13px}
  button{cursor:pointer;background:var(--acc);color:#04121f;border:0;font-weight:600}
  button.sec{background:var(--bg);color:var(--fg);border:1px solid var(--line);font-weight:400}
  #wrap{display:flex;height:calc(100vh - 118px)}
  #tabla{flex:1;overflow:auto}
  #mapa{width:42%;min-width:320px}
  table{border-collapse:collapse;width:100%;font-size:12.5px}
  th,td{padding:6px 8px;border-bottom:1px solid var(--line);text-align:left;white-space:nowrap}
  th{position:sticky;top:0;background:var(--panel);cursor:pointer;user-select:none}
  td.desc{white-space:normal;max-width:520px;min-width:380px}
  tr:hover td{background:#1d2a37}
  tr.sel td{background:#264056}
  td.fil{cursor:pointer}
  td.fil:hover{text-decoration:underline;color:var(--acc)}
  tr.ganga td{background:#1e3320}
  tr.ganga td:first-child{border-left:3px solid #4ce0a0}
  a{color:var(--acc)}
  .pill{padding:1px 6px;border-radius:10px;font-size:11px;background:#233442}
  .cerca{color:#4ce0a0;font-weight:600}
  .sw{flex-direction:row!important;align-items:center;gap:6px;color:var(--fg)!important;cursor:pointer;font-size:13px}
  .sw input{display:none}
  .sw .track{width:34px;height:18px;background:#2a3a4a;border-radius:10px;position:relative;transition:.2s;display:inline-block}
  .sw .track::after{content:"";position:absolute;top:2px;left:2px;width:14px;height:14px;background:#8aa0b3;border-radius:50%;transition:.2s}
  .sw input:checked + .track{background:#4ce0a0}
  .sw input:checked + .track::after{transform:translateX(16px);background:#04121f}
  .seg{display:inline-flex;border:1px solid var(--line);border-radius:6px;overflow:hidden}
  .seg button{border:0;border-radius:0;background:var(--bg);color:var(--mut);padding:6px 10px;font-size:12px;cursor:pointer}
  .seg button+button{border-left:1px solid var(--line)}
  .seg button.on{background:#4ce0a0;color:#04121f;font-weight:600}
</style>
</head>
<body>
<header>
  <h1>Subastas BOE</h1>
  <span class="mut" id="stats"></span>
</header>
<div id="filtros">
  <label>Texto<input id="q" placeholder="localidad, descripcion..."></label>
  <label>Precio max (EUR)<input id="pmax" type="number" step="1000" value="60000"></label>
  <label>Subtipo<select id="sub"><option value="">todos</option></select></label>
  <label>Clase<span class="seg" id="claseSeg">
    <button type="button" data-v="" class="on">Todas</button><button type="button" data-v="urbano">Urbano</button><button type="button" data-v="rural">Rural</button>
  </span></label>
  <label>Provincia<select id="prov"><option value="">todas</option></select></label>
  <label>Localidad<input id="loc" list="locs" placeholder="todas"><datalist id="locs"></datalist></label>
  <label>Estado<select id="est"><option value="">todos</option></select></label>
  <label>% mercado max<input id="pmerc" type="number" step="5" placeholder="ej: 70"></label>
  <label class="sw"><input id="solomar" type="checkbox"><span class="track"></span> &lt;500 m del mar</label>
  <label>Cierra desde<input id="fdesde" type="date"></label>
  <label>Cierra hasta<input id="fhasta" type="date"></label>
  <label>Ordenar por<select id="orden">
    <option value="fecha_fin|1">Cierre (proximo primero)</option>
    <option value="fecha_inicio|-1">Publicacion (reciente primero)</option>
    <option value="precio_ref|1">Precio (barato primero)</option>
    <option value="eur_m2|1">€/m² (barato primero)</option>
    <option value="pct_mercado|1">% mercado (ganga primero)</option>
    <option value="dist_costa_m|1">Distancia al mar</option>
  </select></label>
  <label style="flex-direction:row;align-items:center;gap:6px;color:var(--fg)">
    <input id="solog" type="checkbox" style="width:auto"> solo gangas</label>
  <label style="flex-direction:row;align-items:center;gap:6px;color:var(--fg)">
    <input id="soloc" type="checkbox" style="width:auto"> solo geolocalizados</label>
  <button id="dl">Descargar CSV (Excel)</button>
</div>
<div id="wrap">
  <div id="tabla"></div>
  <div id="mapa"></div>
</div>
<script>
const DATOS = /*DATOS*/;
const fmt = n => n==null ? "" : n.toLocaleString("es-ES",{maximumFractionDigits:0});
let sortKey="fecha_fin", sortDir=1, filtrados=[], claseVal="";

const VISTA_ESP=[[27.5,-19.0],[44.0,4.5]]; // bounds Espana (incl. Canarias)
const map = L.map('mapa').fitBounds(VISTA_ESP);
const satelite = L.tileLayer(
  'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
  {maxZoom:19, attribution:'© Esri, Maxar, Earthstar'}).addTo(map);
const callejero = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
  {maxZoom:19, attribution:'© OpenStreetMap'});
// etiquetas de calles/nombres encima del satelite
const etiquetas = L.tileLayer(
  'https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}',
  {maxZoom:19}).addTo(map);
L.control.layers({"Satélite":satelite,"Callejero":callejero},
  {"Etiquetas (satélite)":etiquetas},{position:'topright'}).addTo(map);
let capa = L.layerGroup().addTo(map);
let markers = {};

// boton "Vista general" para volver a ver toda Espana
const Home = L.Control.extend({options:{position:'topleft'},
  onAdd:function(){
    const b=L.DomUtil.create('button','','');
    b.innerHTML='🏠 Vista general';
    b.style.cssText='background:#182430;color:#e6edf3;border:1px solid #2a3a4a;'
      +'border-radius:6px;padding:6px 8px;cursor:pointer;font-size:12px';
    L.DomEvent.disableClickPropagation(b);
    b.onclick=()=>{ if(!zoomAFiltrados()) map.fitBounds(VISTA_ESP); };
    return b;}});
map.addControl(new Home());

function zoomAFiltrados(){
  const pts=filtrados.filter(d=>d.lat).map(d=>[d.lat,d.lon]);
  if(pts.length){ map.fitBounds(pts,{padding:[40,40],maxZoom:13}); return true; }
  return false;
}

function unicos(k){return [...new Set(DATOS.map(d=>d[k]).filter(Boolean))].sort();}
function llenar(sel,vals){vals.forEach(v=>{const o=document.createElement('option');o.value=v;o.textContent=v;sel.appendChild(o);});}
llenar(document.getElementById('sub'), unicos('subtipo'));
llenar(document.getElementById('prov'), unicos('provincia'));
llenar(document.getElementById('est'), unicos('estado'));
llenar(document.getElementById('locs'), unicos('localidad'));

function aplica(){
  const q=document.getElementById('q').value.toLowerCase();
  const pmax=parseFloat(document.getElementById('pmax').value)||Infinity;
  const sub=document.getElementById('sub').value;
  const clase=claseVal;
  const prov=document.getElementById('prov').value;
  const loc=document.getElementById('loc').value.trim().toLowerCase();
  const est=document.getElementById('est').value;
  const solomar=document.getElementById('solomar').checked;
  const pmerc=parseFloat(document.getElementById('pmerc').value);
  const fdesde=document.getElementById('fdesde').value;
  const fhasta=document.getElementById('fhasta').value;
  const solog=document.getElementById('solog').checked;
  const soloc=document.getElementById('soloc').checked;
  filtrados = DATOS.filter(d=>{
    if(d.precio_ref==null || d.precio_ref>pmax) return false;
    if(sub && d.subtipo!==sub) return false;
    if(clase && d.clase!==clase) return false;
    if(prov && d.provincia!==prov) return false;
    if(loc && !((d.localidad||"").toLowerCase().includes(loc))) return false;
    if(est && d.estado!==est) return false;
    if(solomar && (d.dist_costa_m==null || d.dist_costa_m>500)) return false;
    if(!isNaN(pmerc) && (d.pct_mercado==null || d.pct_mercado*100>pmerc)) return false;
    if(fdesde && (!d.fecha_fin || d.fecha_fin<fdesde)) return false;
    if(fhasta && (!d.fecha_fin || d.fecha_fin>fhasta)) return false;
    if(solog && !d.ganga) return false;
    if(soloc && d.lat==null) return false;
    if(q){const t=((d.descripcion||"")+" "+(d.localidad||"")+" "+(d.direccion||"")).toLowerCase();
      if(!t.includes(q)) return false;}
    return true;
  });
  filtrados.sort((a,b)=>{const x=a[sortKey],y=b[sortKey];
    if(x==null)return 1; if(y==null)return -1; return (x>y?1:x<y?-1:0)*sortDir;});
  render();
}

function render(){
  const cols=[["precio_ref","Precio"],["subtipo","Tipo"],["estado","Estado"],
    ["superficie_m2","m²"],["eur_m2","€/m²"],["pct_mercado","%merc"],
    ["dist_costa_m","m mar"],["localidad","Localidad"],["provincia","Provincia"],
    ["descripcion","Descripcion"],["fecha_inicio","Apertura"],["fecha_fin","Cierre"]];
  let h="<table><thead><tr>";
  cols.forEach(c=>h+=`<th data-k="${c[0]}">${c[1]}</th>`);
  h+="<th>BOE</th></tr></thead><tbody>";
  filtrados.forEach((d,i)=>{
    const cerca = d.dist_costa_m!=null && d.dist_costa_m<=500;
    const pm = d.pct_mercado==null ? "" : Math.round(d.pct_mercado*100)+"%";
    h+=`<tr data-i="${i}" class="${d.ganga?'ganga':''}">`+
      `<td>${fmt(d.precio_ref)} €</td>`+
      `<td class="fil" data-f="sub" data-v="${d.subtipo||''}"><span class="pill">${d.subtipo||""}</span></td>`+
      `<td>${d.estado||""}</td>`+
      `<td>${fmt(d.superficie_m2)}</td><td>${fmt(d.eur_m2)}</td>`+
      `<td class="${d.ganga?'cerca':''}">${pm}</td>`+
      `<td class="${cerca?'cerca':''}">${d.dist_costa_m==null?"":fmt(d.dist_costa_m)}</td>`+
      `<td class="fil" data-f="loc" data-v="${(d.localidad||'').replace(/"/g,'')}">${d.localidad||""}</td>`+
      `<td class="fil" data-f="prov" data-v="${(d.provincia||'').replace(/"/g,'')}">${d.provincia||""}</td>`+
      `<td class="desc">${(d.descripcion||"").slice(0,240)}</td>`+
      `<td>${d.fecha_inicio||""}</td><td>${d.fecha_fin||""}</td>`+
      `<td><a href="${d.url}" target="_blank">ver</a></td></tr>`;
  });
  h+="</tbody></table>";
  document.getElementById('tabla').innerHTML=h;
  document.getElementById('stats').textContent=
    `${filtrados.length} de ${DATOS.length} lotes · ${filtrados.filter(d=>d.dist_costa_m<=500).length} a <500 m del mar · ${filtrados.filter(d=>d.ganga).length} gangas`;
  document.querySelectorAll('th[data-k]').forEach(th=>th.onclick=()=>{
    const k=th.dataset.k; sortDir = (k===sortKey)? -sortDir : 1; sortKey=k; aplica();});
  function irAlPunto(tr, volar){
    const d=filtrados[tr.dataset.i];
    document.querySelectorAll('#tabla tr').forEach(r=>r.classList.remove('sel'));
    tr.classList.add('sel');
    if(d.lat){
      const m=markers[d.id_sub];
      if(volar){ map.flyTo([d.lat,d.lon],17,{duration:1.1}); }
      else { map.setView([d.lat,d.lon],15); }
      if(m) setTimeout(()=>m.openPopup(), volar?900:0);
    }
  }
  document.querySelectorAll('#tabla tr[data-i]').forEach(tr=>{
    tr.onclick=()=>irAlPunto(tr,false);
    tr.oncontextmenu=(e)=>{e.preventDefault(); irAlPunto(tr,true);};
  });
  document.querySelectorAll('#tabla td.fil').forEach(td=>td.onclick=(e)=>{
    e.stopPropagation();
    const el=document.getElementById(td.dataset.f);
    if(el){ el.value=td.dataset.v; aplica(); }
  });
  pintarMapa();
}

function pintarMapa(){
  capa.clearLayers(); markers={};
  filtrados.filter(d=>d.lat).forEach(d=>{
    const cerca=d.dist_costa_m!=null&&d.dist_costa_m<=500;
    markers[d.id_sub]=L.circleMarker([d.lat,d.lon],{radius:6,color:cerca?'#4ce0a0':'#3fb0ff',
      fillOpacity:.9,weight:2}).addTo(capa).bindPopup(
      `<b>${fmt(d.precio_ref)} €</b> · ${d.subtipo}${d.ganga?' 🔥GANGA':''}<br>${d.localidad||""} (${d.provincia||""})`+
      `<br>${d.eur_m2!=null?fmt(d.eur_m2)+" €/m²"+(d.pct_mercado!=null?" ("+Math.round(d.pct_mercado*100)+"% mercado)":"")+"<br>":""}`+
      `${d.dist_costa_m!=null?fmt(d.dist_costa_m)+" m del mar<br>":""}`+
      `${(d.descripcion||"").slice(0,120)}<br><a href="${d.url}" target="_blank">Ficha BOE</a>`);
  });
}

document.getElementById('dl').onclick=()=>{
  const cols=["id_sub","subtipo","estado","precio_ref","valor_subasta","postura_minima",
    "deposito","superficie_m2","eur_m2","eur_m2_ref","pct_mercado","ganga",
    "descripcion","direccion","localidad","provincia","dist_costa_m",
    "lat","lon","fecha_inicio","fecha_fin","anuncio_boe","url"];
  const esc=v=>'"'+String(v==null?"":v).replace(/"/g,'""')+'"';
  let csv="﻿"+cols.join(";")+"\n";
  filtrados.forEach(d=>csv+=cols.map(c=>esc(d[c])).join(";")+"\n");
  const a=document.createElement('a');
  a.href=URL.createObjectURL(new Blob([csv],{type:"text/csv"}));
  a.download="subastas_filtradas.csv"; a.click();
};

['q','pmax','sub','prov','loc','est','solomar','pmerc','fdesde','fhasta','solog','soloc'].forEach(id=>{
  const el=document.getElementById(id);
  el.addEventListener('input',aplica); el.addEventListener('change',aplica);});
document.querySelectorAll('#claseSeg button').forEach(b=>b.onclick=()=>{
  document.querySelectorAll('#claseSeg button').forEach(x=>x.classList.remove('on'));
  b.classList.add('on'); claseVal=b.dataset.v; aplica();});
document.getElementById('orden').addEventListener('change',e=>{
  const [k,dd]=e.target.value.split("|"); sortKey=k; sortDir=parseInt(dd); aplica();});
aplica();
</script>
</body>
</html>"""


if __name__ == "__main__":
    generar()
