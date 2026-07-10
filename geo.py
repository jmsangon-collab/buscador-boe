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


# --------------------------------------------------------------------------
def geocodificar(direccion, localidad, provincia, cod_postal=None):
    """Devuelve dict(lat, lon, barrio, distrito, municipio) o None.
    Una sola llamada (addressdetails=1). Respeta el limite de 1 req/s."""
    partes = [p for p in (direccion, cod_postal, localidad, provincia) if p and p != "No consta"]
    if not partes:
        return None
    q = ", ".join(partes) + ", Espana"
    try:
        r = requests.get(NOMINATIM, headers=UA, timeout=30, params={
            "q": q, "format": "jsonv2", "limit": 1, "countrycodes": "es",
            "addressdetails": 1})
        time.sleep(1.1)
        data = r.json()
        if not data:
            return None
        a = data[0].get("address", {})
        return {
            "lat": float(data[0]["lat"]), "lon": float(data[0]["lon"]),
            "barrio": a.get("neighbourhood") or a.get("suburb") or a.get("quarter"),
            "distrito": a.get("city_district") or a.get("district") or a.get("borough"),
            "municipio": (a.get("city") or a.get("town") or a.get("village")
                          or a.get("municipality") or localidad),
        }
    except Exception:
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
