# -*- coding: utf-8 -*-
"""Enriquecimiento geografico:
  - geocodificar(): direccion -> (lat, lon) via Nominatim (OpenStreetMap).
  - CoastDistance: distancia en metros de un punto a la linea de costa.

La costa se toma de Natural Earth 10m (se descarga una vez a data/).
Precision ~ algunos cientos de metros: suficiente como PRIMER filtro
"a menos de 500 m del mar", pero conviene verificar los candidatos a mano.
Para mas precision, sustituye data/coastline.geojson por una costa OSM.
"""
import os
import re
import time
import requests

DATA = os.path.join(os.path.dirname(__file__), "data")
COAST_GEOJSON = os.path.join(DATA, "coastline.geojson")
COAST_URL = ("https://raw.githubusercontent.com/nvkelso/natural-earth-vector/"
             "master/geojson/ne_10m_coastline.geojson")
NOMINATIM = "https://nominatim.openstreetmap.org/search"
UA = {"User-Agent": "subastas-boe/1.0 (uso personal)"}

# bbox de Espana (incluye Canarias): lon_min, lat_min, lon_max, lat_max
ESPANA_BBOX = (-19.0, 27.0, 5.0, 44.5)
CRS_METROS = "EPSG:25830"  # ETRS89 / UTM 30N (metros)


# Abreviaturas de tipo de via -> forma que Nominatim entiende.
_VIA_ABREV = [
    (r"^\s*CL\b", "Calle"), (r"^\s*C/\s*", "Calle "), (r"^\s*C\.\s*", "Calle "),
    (r"^\s*CR\b", "Carretera"), (r"^\s*CTRA\b", "Carretera"),
    (r"^\s*AV(?:DA)?\b", "Avenida"), (r"^\s*PZ(?:A)?\b", "Plaza"),
    (r"^\s*P[ºo]\s*", "Paseo "), (r"^\s*PS\b", "Paseo"), (r"^\s*PSJE\b", "Pasaje"),
    (r"^\s*CJON\b", "Callejon"), (r"^\s*GTA\b", "Glorieta"),
    (r"^\s*URB\b", "Urbanizacion"), (r"^\s*RD\b", "Ronda"),
    (r"^\s*CMNO?\b", "Camino"), (r"^\s*TRV\b", "Travesia"), (r"^\s*BO\b", "Barrio"),
]


def limpiar_direccion(d):
    """Reduce una direccion registral ('CALLE GRANADA Nº 38 ESCALERA E PLANTA 1
    PUERTA 2') a 'Calle GRANADA 38', que es lo que Nominatim sabe geocodificar.
    Expande la abreviatura de via, quita el marcador de numero y corta el ruido
    (escalera/planta/puerta/bloque...) tras el primer numero de portal."""
    if not d:
        return None
    t = re.sub(r"\s+", " ", d).strip()
    for pat, rep in _VIA_ABREV:
        nuevo = re.sub(pat, rep, t, count=1, flags=re.IGNORECASE)
        if nuevo != t:
            t = nuevo
            break
    # "Nº 38" / "N°38" / "N�13" / "num. 38" -> "38"
    t = re.sub(r"\bN[ºo°\.º�]*\s*(?=\d)", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\bn[uú]m\.?\s*(?=\d)", "", t, flags=re.IGNORECASE)
    # conservar 'via nombre <primer numero de portal>' y tirar el resto
    m = re.search(r"^(.*?\d{1,4})\b", t)
    if m:
        t = m.group(1)
    t = re.sub(r"\s+", " ", t).strip(" ,.-")
    return t or None


def _pedir(q):
    """Una consulta a Nominatim (respeta 1 req/s). Devuelve el primer resultado o None."""
    try:
        r = requests.get(NOMINATIM, headers=UA, timeout=30, params={
            "q": q, "format": "jsonv2", "limit": 1, "countrycodes": "es",
            "addressdetails": 1})
        time.sleep(1.1)
        data = r.json()
        return data[0] if data else None
    except Exception:
        return None


# --------------------------------------------------------------------------
def geocodificar(direccion, localidad, provincia, cod_postal=None):
    """Devuelve dict(lat, lon, barrio, distrito, municipio, precision) o None.
    Intenta primero la direccion completa (limpia); si falla, cae a nivel de
    municipio para que el lote aparezca al menos en el pueblo. precision =
    'exacta' | 'municipio' | 'provincia'."""
    loc = None if (not localidad or localidad == "No consta") else localidad
    prov = None if (not provincia or provincia == "No consta") else provincia
    dir_limpia = limpiar_direccion(direccion)

    intentos = []
    if dir_limpia:
        intentos.append(("exacta", ", ".join(p for p in (dir_limpia, cod_postal, loc, prov) if p) + ", Espana"))
    # plan B: solo municipio (o CP) para no perder el lote
    if loc or cod_postal:
        intentos.append(("municipio", ", ".join(p for p in (loc, cod_postal, prov) if p) + ", Espana"))
    # plan C: capital de provincia, para que el lote aparezca siempre en el mapa
    if prov:
        intentos.append(("provincia", f"{prov}, Espana"))

    for precision, q in intentos:
        d = _pedir(q)
        if not d:
            continue
        a = d.get("address", {})
        return {
            "lat": float(d["lat"]), "lon": float(d["lon"]),
            "barrio": a.get("neighbourhood") or a.get("suburb") or a.get("quarter"),
            "distrito": a.get("city_district") or a.get("district") or a.get("borough"),
            "municipio": (a.get("city") or a.get("town") or a.get("village")
                          or a.get("municipality") or localidad),
            "precision": precision,
        }
    return None


# --------------------------------------------------------------------------
class CoastDistance:
    """Calcula distancia a la costa reproyectando a UTM (metros)."""

    def __init__(self):
        import geopandas as gpd
        from shapely.geometry import box
        if not os.path.exists(COAST_GEOJSON):
            self._descargar()
        gdf = gpd.read_file(COAST_GEOJSON)
        recorte = box(*ESPANA_BBOX)
        gdf = gdf[gdf.intersects(recorte)].clip(recorte)
        gdf = gdf.to_crs(CRS_METROS)
        self.costa = gdf.union_all()
        from pyproj import Transformer
        self._tf = Transformer.from_crs("EPSG:4326", CRS_METROS, always_xy=True)

    @staticmethod
    def _descargar():
        print("Descargando linea de costa (una sola vez)...")
        r = requests.get(COAST_URL, timeout=120)
        r.raise_for_status()
        os.makedirs(DATA, exist_ok=True)
        with open(COAST_GEOJSON, "wb") as f:
            f.write(r.content)

    def metros(self, lat, lon):
        from shapely.geometry import Point
        x, y = self._tf.transform(lon, lat)
        return float(Point(x, y).distance(self.costa))
