# -*- coding: utf-8 -*-
"""Genera data/visor.html: un visor autonomo (tabla + filtros + mapa) con los
datos embebidos. Se abre con doble clic en el navegador. Boton de descarga CSV
(se abre directamente en Excel) sobre la seleccion filtrada.
"""
import json
import os

import dataset

OUT = os.path.join(os.path.dirname(__file__), "data", "visor.html")
# copia publicada en GitHub Pages (ver .github/workflows/pages.yml)
OUT_WEB = os.path.join(os.path.dirname(__file__), "web_publicar", "index.html")


def generar(abrir_navegador=False):
    datos = dataset.cargar()
    html = (TEMPLATE
            .replace("/*GLOSARIO*/", GLOSARIO_HTML)
            .replace("/*GUIA*/", GUIA_HTML)
            .replace("/*DATOS*/", json.dumps(datos, ensure_ascii=False)))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    for ruta in (OUT, OUT_WEB):
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(html)
    print(f"[OK] visor -> {OUT} y {OUT_WEB}  ({len(datos)} lotes).")
    if abrir_navegador:
        abrir()


def _buscar_chrome():
    """Ruta al chrome.exe en Windows, o None si no se encuentra."""
    import shutil
    cand = [
        shutil.which("chrome"),
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    ]
    for c in cand:
        if c and os.path.exists(c):
            return c
    return None


def abrir():
    """Abre el visor en Chrome (donde estas logueado en el portal). Si no hay
    Chrome, cae al navegador por defecto."""
    import subprocess
    import webbrowser
    chrome = _buscar_chrome()
    if chrome:
        subprocess.Popen([chrome, OUT])
        print(f"[OK] abriendo en Chrome: {chrome}")
    else:
        webbrowser.open(OUT)
        print("[!] Chrome no encontrado; abierto en el navegador por defecto.")


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
  a{color:var(--acc)}
  .pill{padding:1px 6px;border-radius:10px;font-size:11px;background:#233442}
  .cerca{color:#4ce0a0;font-weight:600}
  tr.oportunidad td{background:#31240f}
  tr.oportunidad td:first-child{border-left:3px solid #ffb020}
  .nopuja{color:#ffb020;font-weight:600}
  .urge{color:#ff6b6b;font-weight:600}
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
  .ayuda{background:var(--bg);color:var(--fg);border:1px solid var(--line);border-radius:6px;
    padding:6px 10px;cursor:pointer;font-size:13px;font-weight:400}
  .ayuda:hover{border-color:var(--acc);color:var(--acc)}
  .modal{position:fixed;inset:0;background:rgba(0,0,0,.6);display:none;z-index:1000;
    padding:40px 16px;overflow:auto}
  .modal.on{display:block}
  .modal .box{max-width:820px;margin:0 auto;background:var(--panel);border:1px solid var(--line);
    border-radius:10px;padding:24px 28px;box-shadow:0 20px 60px rgba(0,0,0,.5)}
  .modal h2{margin:0 0 4px;font-size:20px}
  .modal .x{float:right;background:var(--bg);border:1px solid var(--line);color:var(--fg);
    border-radius:6px;width:30px;height:30px;cursor:pointer;font-size:16px}
  .modal h3{color:var(--acc);margin:22px 0 8px;font-size:15px;border-bottom:1px solid var(--line);padding-bottom:4px}
  .modal p,.modal li{color:var(--fg);line-height:1.55}
  .modal .term{margin:0 0 9px;padding-left:0}
  .modal .term b{color:#ffd479}
  .modal .warn{background:#3a2416;border:1px solid #6b4522;border-radius:6px;padding:10px 12px;margin:10px 0}
  .modal .ok{background:#16321f;border:1px solid #2c6b45;border-radius:6px;padding:10px 12px;margin:10px 0}
  .modal .buscar{width:100%;margin:8px 0 4px;padding:8px 10px}
  .modal .oculto{display:none}
  .modal table{width:100%;border-collapse:collapse;margin:8px 0;font-size:13px}
  .modal td,.modal th{border:1px solid var(--line);padding:6px 8px;text-align:left;white-space:normal}
</style>
</head>
<body>
<header>
  <h1>Subastas BOE</h1>
  <span class="mut" id="stats"></span>
  <span style="margin-left:auto;display:flex;gap:8px">
    <button class="ayuda" onclick="abrirModal('mGloss')">📖 Glosario</button>
    <button class="ayuda" onclick="abrirModal('mGuia')">❓ Cómo funciona</button>
  </span>
</header>
<div class="modal" id="mGloss" onclick="if(event.target===this)cerrarModal('mGloss')">
  <div class="box">
    <button class="x" onclick="cerrarModal('mGloss')">✕</button>
    <h2>📖 Glosario de subastas</h2>
    <p class="mut">La jerga del mundillo, en cristiano. Busca un término:</p>
    <input class="buscar" id="glossQ" placeholder="escribe para filtrar: depósito, cargas, cesión de remate...">
    <div id="glossList">/*GLOSARIO*/</div>
  </div>
</div>
<div class="modal" id="mGuia" onclick="if(event.target===this)cerrarModal('mGuia')">
  <div class="box">
    <button class="x" onclick="cerrarModal('mGuia')">✕</button>
    <h2>❓ Cómo funciona una subasta</h2>
    <p class="mut">Requisitos, pasos, dinero necesario y preguntas frecuentes.</p>
    /*GUIA*/
  </div>
</div>
<div id="filtros">
  <label>Texto<input id="q" placeholder="localidad, descripcion..."></label>
  <label>Precio max (EUR)<input id="pmax" type="number" step="1000" value="60000"></label>
  <label>Subtipo<select id="sub"><option value="">todos</option></select></label>
  <label>Clase<span class="seg" id="claseSeg">
    <button type="button" data-v="" class="on">Todas</button><button type="button" data-v="urbano">Urbano</button><button type="button" data-v="rural">Rural</button>
  </span></label>
  <label>CCAA<select id="ccaa"><option value="">todas</option></select></label>
  <label>Provincia<select id="prov"><option value="">todas</option></select></label>
  <label>Localidad<input id="loc" list="locs" placeholder="todas"><datalist id="locs"></datalist></label>
  <label class="sw"><input id="solomar" type="checkbox"><span class="track"></span> &lt;500 m del mar</label>
  <label class="sw"><input id="sinpuj" type="checkbox"><span class="track"></span> sin pujas</label>
  <label>Cierra en &lt; (h)<input id="hmax" type="number" step="1" placeholder="ej: 24" style="width:70px"></label>
  <label>Cierra desde<input id="fdesde" type="date"></label>
  <label>Cierra hasta<input id="fhasta" type="date"></label>
  <label>Ordenar por<select id="orden">
    <option value="fecha_fin|1">Cierre (proximo primero)</option>
    <option value="horas_rest|1">Horas para cerrar (menos primero)</option>
    <option value="fecha_inicio|-1">Publicacion (reciente primero)</option>
    <option value="precio_ref|1">Precio (barato primero)</option>
    <option value="eur_m2|1">€/m² (barato primero)</option>
    <option value="dist_costa_m|1">Distancia al mar</option>
  </select></label>
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
llenar(document.getElementById('ccaa'), unicos('ccaa'));
llenar(document.getElementById('prov'), unicos('provincia'));
llenar(document.getElementById('locs'), unicos('localidad'));

// Provincias de cada CCAA, para encadenar el desplegable de provincia.
const PROV_DE_CCAA={};
DATOS.forEach(d=>{ if(d.ccaa&&d.provincia){(PROV_DE_CCAA[d.ccaa]=PROV_DE_CCAA[d.ccaa]||new Set()).add(d.provincia);} });
function refrescarProv(){
  const c=document.getElementById('ccaa').value;
  const sel=document.getElementById('prov'), prev=sel.value;
  const vals = c ? [...(PROV_DE_CCAA[c]||[])].sort() : unicos('provincia');
  sel.innerHTML='<option value="">todas</option>';
  llenar(sel, vals);
  sel.value = vals.includes(prev) ? prev : "";
}
document.getElementById('ccaa').addEventListener('change',()=>{refrescarProv();aplica();});

function aplica(){
  const q=document.getElementById('q').value.toLowerCase();
  const pmax=parseFloat(document.getElementById('pmax').value)||Infinity;
  const sub=document.getElementById('sub').value;
  const clase=claseVal;
  const ccaa=document.getElementById('ccaa').value;
  const prov=document.getElementById('prov').value;
  const loc=document.getElementById('loc').value.trim().toLowerCase();
  const solomar=document.getElementById('solomar').checked;
  const sinpuj=document.getElementById('sinpuj').checked;
  const hmax=parseFloat(document.getElementById('hmax').value);
  const fdesde=document.getElementById('fdesde').value;
  const fhasta=document.getElementById('fhasta').value;
  const soloc=document.getElementById('soloc').checked;
  const ahora=Date.now();
  DATOS.forEach(d=>{ d.horas_rest = d.fecha_fin_dt ? (new Date(d.fecha_fin_dt)-ahora)/3.6e6 : null; });
  filtrados = DATOS.filter(d=>{
    if(d.precio_ref==null || d.precio_ref>pmax) return false;
    if(sub && d.subtipo!==sub) return false;
    if(clase && d.clase!==clase) return false;
    if(ccaa && d.ccaa!==ccaa) return false;
    if(prov && d.provincia!==prov) return false;
    if(loc && !((d.localidad||"").toLowerCase().includes(loc))) return false;
    if(solomar && (d.dist_costa_m==null || d.dist_costa_m>500)) return false;
    if(sinpuj && !d.sin_pujas) return false;
    if(!isNaN(hmax) && (d.horas_rest==null || d.horas_rest<0 || d.horas_rest>hmax)) return false;
    if(fdesde && (!d.fecha_fin || d.fecha_fin<fdesde)) return false;
    if(fhasta && (!d.fecha_fin || d.fecha_fin>fhasta)) return false;
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
  const cols=[["precio_ref","Precio"],["subtipo","Tipo"],
    ["superficie_m2","m²"],["eur_m2","€/m²"],
    ["dist_costa_m","m mar"],["localidad","Localidad"],["provincia","Provincia"],
    ["descripcion","Descripcion"],["fecha_fin","Cierre"],["horas_rest","Cierra en"],
    ["num_pujas","Pujas"]];
  let h="<table><thead><tr>";
  cols.forEach(c=>h+=`<th data-k="${c[0]}">${c[1]}</th>`);
  h+="<th>BOE</th></tr></thead><tbody>";
  filtrados.forEach((d,i)=>{
    const cerca = d.dist_costa_m!=null && d.dist_costa_m<=500;
    const hr=d.horas_rest;
    const opp = d.sin_pujas && hr!=null && hr>=0 && hr<=24;
    let hrTxt="", hrCls="";
    if(hr!=null && hr>=0){
      hrTxt = hr<24 ? Math.round(hr)+" h" : Math.round(hr/24)+" d";
      hrCls = hr<=24 ? "urge" : "";
    }
    const pjTxt = d.num_pujas==null ? "?" : (d.num_pujas===0 ? "sin pujas" : d.num_pujas+" puja"+(d.num_pujas>1?"s":""));
    const pjCls = d.sin_pujas ? "nopuja" : "";
    h+=`<tr data-i="${i}" class="${opp?'oportunidad':''}">`+
      `<td>${fmt(d.precio_ref)} €</td>`+
      `<td class="fil" data-f="sub" data-v="${d.subtipo||''}"><span class="pill">${d.subtipo||""}</span></td>`+
      `<td>${fmt(d.superficie_m2)}</td><td>${fmt(d.eur_m2)}</td>`+
      `<td class="${cerca?'cerca':''}">${d.dist_costa_m==null?"":fmt(d.dist_costa_m)}</td>`+
      `<td class="fil" data-f="loc" data-v="${(d.localidad||'').replace(/"/g,'')}">${d.localidad||""}</td>`+
      `<td class="fil" data-f="prov" data-v="${(d.provincia||'').replace(/"/g,'')}">${d.provincia||""}</td>`+
      `<td class="desc">${(d.descripcion||"").slice(0,240)}</td>`+
      `<td>${d.fecha_fin||""}</td>`+
      `<td class="${hrCls}">${hrTxt}</td>`+
      `<td class="${pjCls}">${pjTxt}</td>`+
      `<td><a href="${d.url}" target="_blank">ver</a></td></tr>`;
  });
  h+="</tbody></table>";
  document.getElementById('tabla').innerHTML=h;
  document.getElementById('stats').textContent=
    `${filtrados.length} de ${DATOS.length} lotes · ${filtrados.filter(d=>d.dist_costa_m<=500).length} a <500 m del mar`;
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
      `<b>${fmt(d.precio_ref)} €</b> · ${d.subtipo}<br>${d.localidad||""} (${d.provincia||""})`+
      `<br>${d.eur_m2!=null?fmt(d.eur_m2)+" €/m²<br>":""}`+
      `${d.dist_costa_m!=null?fmt(d.dist_costa_m)+" m del mar<br>":""}`+
      `${(d.descripcion||"").slice(0,120)}<br><a href="${d.url}" target="_blank">Ficha BOE</a>`);
  });
}

document.getElementById('dl').onclick=()=>{
  const cols=["id_sub","subtipo","estado","precio_ref","valor_subasta","postura_minima",
    "deposito","superficie_m2","eur_m2",
    "descripcion","direccion","localidad","provincia","ccaa","dist_costa_m",
    "lat","lon","fecha_inicio","fecha_fin","anuncio_boe","url"];
  const esc=v=>'"'+String(v==null?"":v).replace(/"/g,'""')+'"';
  let csv="﻿"+cols.join(";")+"\n";
  filtrados.forEach(d=>csv+=cols.map(c=>esc(d[c])).join(";")+"\n");
  const a=document.createElement('a');
  a.href=URL.createObjectURL(new Blob([csv],{type:"text/csv"}));
  a.download="subastas_filtradas.csv"; a.click();
};

['q','pmax','sub','prov','loc','solomar','sinpuj','hmax','fdesde','fhasta','soloc'].forEach(id=>{
  const el=document.getElementById(id);
  el.addEventListener('input',aplica); el.addEventListener('change',aplica);});
document.querySelectorAll('#claseSeg button').forEach(b=>b.onclick=()=>{
  document.querySelectorAll('#claseSeg button').forEach(x=>x.classList.remove('on'));
  b.classList.add('on'); claseVal=b.dataset.v; aplica();});
document.getElementById('orden').addEventListener('change',e=>{
  const [k,dd]=e.target.value.split("|"); sortKey=k; sortDir=parseInt(dd); aplica();});

// ---- modales de ayuda (glosario / guia) ----
function abrirModal(id){document.getElementById(id).classList.add('on');}
function cerrarModal(id){document.getElementById(id).classList.remove('on');}
document.addEventListener('keydown',e=>{if(e.key==='Escape')
  document.querySelectorAll('.modal.on').forEach(m=>m.classList.remove('on'));});
document.getElementById('glossQ').addEventListener('input',e=>{
  const q=e.target.value.toLowerCase().trim();
  document.querySelectorAll('#glossList .term').forEach(t=>{
    t.classList.toggle('oculto', q && !t.textContent.toLowerCase().includes(q));});
});
aplica();
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Contenido de los dos modales de ayuda (glosario + guia/FAQ). Documentado a
# partir de la LEC (arts. 647-680) y la reforma LO 1/2025, de 2 de enero.
def _terminos(pares):
    return "\n".join(f'<div class="term"><b>{t}.</b> {d}</div>' for t, d in pares)


GLOSARIO_HTML = _terminos([
    ("Valor de tasación", "Precio en que se valora el inmueble (por perito o, en hipoteca, el pactado en escritura). Es el punto de partida para calcular todo lo demás."),
    ("Valor de subasta (tipo)", "Cantidad por la que el bien «sale» a subasta y sobre la que se calculan los porcentajes legales (depósito, umbrales). Suele coincidir con la tasación."),
    ("Postura / Puja", "Cada oferta económica que haces por el bien. Son sinónimos."),
    ("Puja mínima", "La cantidad más baja que el sistema admite como primera oferta válida. El portal la indica en cada subasta."),
    ("Tramos", "Escalón mínimo en que suben las pujas (p. ej. de 2.000 € en 2.000 €). No puedes ofertar cantidades intermedias, solo múltiplos del tramo."),
    ("Depósito / consignación", "Dinero que bloqueas por adelantado para poder pujar. Garantiza que, si ganas, pagarás. Se devuelve a quien no gana."),
    ("Importe del depósito", "El porcentaje del valor de subasta que hay que consignar: <b>5 %</b> en subastas de la Agencia Tributaria y notariales; <b>20 %</b> para inmuebles en ejecuciones judiciales presentadas desde el 3-abr-2025 (antes 5 %)."),
    ("Sobre cerrado", "Modalidad en que dejas una puja máxima reservada: el sistema puja por ti tramo a tramo solo lo necesario para ir ganando, sin revelar tu tope."),
    ("Adjudicación (remate)", "Acto por el que el bien se atribuye al mejor postor, una vez cerrada la subasta y aprobado el remate."),
    ("Cesión de remate", "Ceder tu posición de adjudicatario a un tercero para que el inmueble se inscriba a su nombre. En ejecución normalmente solo puede hacerlo el ejecutante (acreedor)."),
    ("Quiebra de la subasta", "Cuando el ganador no paga el resto en plazo: pierde el depósito y la subasta se resuelve a favor de los siguientes postores o se reabre."),
    ("Ejecutante", "Quien promueve la ejecución para cobrar (banco, Hacienda, particular). Es el acreedor."),
    ("Ejecutado", "Aquel contra quien se dirige la ejecución: el deudor o dueño del bien embargado."),
    ("Acreedor / Deudor", "Acreedor: quien tiene derecho a cobrar. Deudor: quien debe pagar."),
    ("Cargas", "Gravámenes que pesan sobre la finca inscritos en el Registro: hipotecas, embargos, servidumbres, usufructos…"),
    ("Cargas anteriores / preferentes", "Cargas inscritas ANTES de la que motiva la subasta. Son las peligrosas: <b>no se cancelan</b> y el comprador las hereda."),
    ("Subrogación de cargas", "Regla por la que el rematante se queda con las cargas anteriores subsistentes. Puedes acabar pagando el remate <b>y además</b> una hipoteca previa."),
    ("Certificación de dominio y cargas", "Documento del Registro con el titular actual y todas las cargas de la finca. Fuente esencial para saber qué compras."),
    ("Nota simple", "Extracto informativo (no certificado) del Registro con titularidad y cargas. Barata y muy recomendable antes de pujar."),
    ("Referencia catastral", "Código único de 20 caracteres que identifica el inmueble en el Catastro. Permite ver su superficie y ubicación."),
    ("Hipoteca", "Garantía sobre un inmueble que permite al acreedor subastarlo si no se paga la deuda garantizada."),
    ("Embargo", "Traba judicial o administrativa sobre un bien para asegurar el cobro de una deuda. Se anota en el Registro."),
    ("Usufructo", "Derecho a usar y disfrutar un bien ajeno (habitarlo, alquilarlo) sin ser su dueño."),
    ("Nuda propiedad", "Propiedad «vacía» de uso: eres dueño pero no puedes usar el bien mientras exista un usufructo. Al extinguirse este, recuperas el pleno dominio."),
    ("Pleno dominio", "Propiedad completa: nuda propiedad + usufructo en la misma persona (usar, disfrutar y disponer sin límites)."),
    ("Proindiviso / cuota", "Copropiedad: varios dueños por cuotas (p. ej. 50 %). Ojo: muchas subastas venden solo <b>una cuota</b>, no el inmueble entero."),
    ("Finca urbana vs. rústica", "Urbana: suelo o edificación en suelo urbano (viviendas, locales). Rústica: suelo agrícola/forestal o no urbanizable. Cambian usos, valor y límites."),
    ("Ocupantes / posesión", "Quien vive u ocupa el inmueble. Ganar la subasta da la propiedad, pero <b>no siempre la posesión inmediata</b>: puede haber que desalojar."),
    ("Lanzamiento / desahucio", "Procedimiento judicial para desalojar a los ocupantes y entregarte la posesión. Requiere trámite adicional y tiempo."),
    ("ITP / IVA en la adjudicación", "Impuesto que grava la compra. Según quién venda y qué se venda, tributa por ITP (particular) o por IVA + AJD (empresario). No los dos a la vez."),
    ("Testimonio del decreto de adjudicación", "Documento judicial que acredita que se te ha adjudicado el bien. Es el «título» con el que inscribes la propiedad en el Registro."),
    ("Mandamiento de cancelación de cargas", "Orden judicial al Registro para cancelar la carga que originó la ejecución y las posteriores. Es lo que «limpia» la finca (nunca de las cargas anteriores)."),
])


GUIA_HTML = r"""
<div class="warn"><b>Antes de nada — la reforma de 2025.</b> La Ley Orgánica 1/2025 cambió el régimen
de las subastas <i>judiciales</i> (por ejemplo, el depósito para inmuebles pasó del 5 % al 20 %). Se
aplica a ejecuciones cuya demanda se presentó desde el <b>3 de abril de 2025</b>; las anteriores siguen
con las reglas viejas. Las subastas de la <b>Agencia Tributaria</b> y las <b>notariales</b> mantienen el
<b>5 %</b>. Comprueba siempre las condiciones concretas de cada subasta.</div>

<h3>¿Qué requisitos hay para participar?</h3>
<p>Estar dado de alta como usuario en el <b>Portal de Subastas del BOE</b> (subastas.boe.es), lo que exige
<b>identificación electrónica</b>: certificado digital, DNI electrónico o <b>Cl@ve</b>. Después, para cada
subasta concreta hay que <b>constituir el depósito</b> por la pasarela de pago del portal; solo entonces
quedas habilitado para pujar. No es obligatorio abogado ni procurador, pero sí muy recomendable asesorarse.</p>

<h3>Pasos, de principio a fin</h3>
<ol>
  <li><b>Buscar</b> la subasta (esto es lo que hace este visor).</li>
  <li><b>Estudiar el expediente</b>: edicto, valor, cargas, situación posesoria y documentación aneja.</li>
  <li><b>Comprobar por tu cuenta</b>: nota simple en el Registro, referencia catastral, IBI y deudas de comunidad, y si está ocupado.</li>
  <li><b>Darte de alta</b> en el portal y <b>constituir el depósito</b>.</li>
  <li><b>Pujar</b> durante el plazo (las subastas del BOE duran, en general, <b>20 días naturales</b>; se prorrogan si hay pujas al final).</li>
  <li><b>Cierre</b> y envío de la mejor postura al Juzgado/Notaría.</li>
  <li><b>Aprobación del remate</b> (decreto de adjudicación) si la puja alcanza los umbrales legales.</li>
  <li><b>Pagar el resto del precio</b> en plazo.</li>
  <li>Obtener el <b>testimonio del decreto</b> y el <b>mandamiento de cancelación de cargas</b>.</li>
  <li><b>Inscribir</b> en el Registro a tu nombre y, si procede, <b>tomar posesión</b> (con lanzamiento si hay ocupantes).</li>
</ol>

<h3>💶 ¿Cuánto dinero en efectivo necesito para pujar?</h3>
<p>Necesitas <b>consignar por adelantado un porcentaje del valor de subasta</b>:</p>
<ul>
  <li><b>Agencia Tributaria y notariales: 5 %</b> del valor de subasta.</li>
  <li><b>Judicial (demanda desde el 3-abr-2025): 20 %</b> para inmuebles (mín. 1.000 €). Antes era el 5 %.</li>
</ul>
<div class="ok"><b>Ejemplo real (piso de Sevilla, subasta AT):</b> valor de subasta 204.119,28 € →
depósito para pujar = <b>10.205,96 € (5 %)</b>. Puja mínima 20.411,93 €, tramos de 2.000 €.</div>
<p>El depósito se ingresa <b>antes de pujar</b> por la pasarela del portal y queda retenido. A quien
<b>no gana</b> se le devuelve al cerrarse la subasta; al <b>ganador</b> se le imputa al precio (lo paga a cuenta).</p>

<h3>¿Qué pasa si gano? Plazo de pago y consecuencias de no pagar</h3>
<p>Debes pagar la <b>diferencia</b> entre el depósito y el precio total del remate. Tras la reforma el plazo
del mejor postor se redujo <b>de 40 a 20 días</b> desde el cierre (art. 670 LEC). Si no pagas
(<b>quiebra de la subasta</b>) <b>pierdes el depósito</b>, que se aplica a la deuda, y el bien pasa a los
siguientes postores o se reabre la subasta.</p>

<h3>¿Cómo suben las pujas? (tramos)</h3>
<p>El tramo es el escalón mínimo de subida. Con tramo de 2.000 €, sobre una postura de 80.000 € la siguiente
válida es 82.000 €. En <b>sobre cerrado</b>, el sistema sube solo un tramo por encima del rival hasta tu tope.</p>

<h3>⚠️ Riesgos clave</h3>
<ul>
  <li><b>Cargas que subsisten:</b> las anteriores/preferentes <b>NO se cancelan</b>; te subrogas en ellas. Lee la certificación de cargas.</li>
  <li><b>Ocupantes:</b> ganar da la propiedad, no siempre la posesión. Puede hacer falta un lanzamiento (coste y demora).</li>
  <li><b>Estado del inmueble:</b> normalmente <b>no es visitable</b> por dentro; compras «a ciegas».</li>
  <li><b>Deudas pendientes:</b> respondes de la comunidad del año en curso y los <b>3 años anteriores</b> (art. 9 LPH), más el IBI.</li>
</ul>

<h3>Impuestos que paga el adjudicatario</h3>
<ul>
  <li><b>ITP</b> si vende un particular (habitual): tipo autonómico, orientativamente <b>6 %–10 %</b>.</li>
  <li><b>IVA + AJD</b> si vende empresario/profesional: IVA 10 % (vivienda) o 21 % (suelo/local) + AJD 0,5 %–1,5 %.</li>
  <li>Regla práctica: <b>o ITP o IVA</b>, no ambos. Suma también inscripción registral y posibles gastos de cancelación/lanzamiento.</li>
</ul>

<h3>Judicial vs. notarial vs. Agencia Tributaria</h3>
<table>
  <tr><th>Tipo</th><th>Quién la ordena</th><th>Depósito</th><th>Título para inscribir</th></tr>
  <tr><td>Judicial</td><td>Juzgado (LEC 647-680)</td><td>20 % inmuebles (5 % antes de 2025)</td><td>Decreto de adjudicación</td></tr>
  <tr><td>Notarial</td><td>Notario</td><td>5 %</td><td>Acta notarial de adjudicación</td></tr>
  <tr><td>Agencia Tributaria</td><td>AEAT (apremio)</td><td>5 %</td><td>Certificación del acta de adjudicación</td></tr>
</table>
<p>En los tres casos se puja por el <b>mismo portal del BOE</b>, pero cambian la norma, el porcentaje y el documento final.</p>

<h3>¿Mi puja basta para que me adjudiquen? (umbrales, art. 670 LEC)</h3>
<ul>
  <li><b>≥ 70 % del valor de subasta:</b> se aprueba el remate directamente.</li>
  <li><b>&lt; 70 %:</b> el deudor tiene 10 días para presentar a un tercero que mejore (≥ 60 %, o menos si cubre toda la deuda).</li>
  <li><b>Si no hay mejora:</b> se aprueba al mejor postor si ofrece <b>≥ 50 %</b>; excepcionalmente por menos si cubre el crédito, nunca por debajo del <b>40 %</b>.</li>
</ul>
<div class="warn"><b>Vivienda habitual y adjudicación al acreedor:</b> los arts. 670 y 671 LEC exigen
umbrales reforzados (en torno al 70 %, o la deuda total si es mayor). Verifica el supuesto concreto.</div>

<p class="mut" style="margin-top:18px;font-size:12px">Información orientativa, no es asesoramiento jurídico ni fiscal.
Basado en la LEC (arts. 647-680) y la LO 1/2025, de 2 de enero. Revisa siempre las condiciones de cada subasta.</p>
"""

if __name__ == "__main__":
    generar()
