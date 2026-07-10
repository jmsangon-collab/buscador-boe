# -*- coding: utf-8 -*-
"""Cliente del Portal de Subastas del BOE (subastas.boe.es).

Flujo:
  1. buscar(...)  -> POST al buscador avanzado, devuelve la lista de idSub
     (paginando con el token id_busqueda que genera el portal).
  2. detalle(idSub) -> GET de las pestanas ver=1 (general) y ver=3 (bienes),
     parsea las tablas th/td y normaliza importes.
"""
import re
import time
import requests
from bs4 import BeautifulSoup

BASE = "https://subastas.boe.es"
BUSCAR = f"{BASE}/subastas_ava.php"
DETALLE = f"{BASE}/detalleSubasta.php"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; subastas-boe/1.0)"}

# Subtipos de inmueble (radio dato[4]) relevantes para el proyecto.
SUBTIPOS = {
    "vivienda": "501", "local": "502", "garaje": "503", "trastero": "504",
    "nave": "505", "solar": "506", "finca_rustica": "507",
    "otros": "599", "todos_inmueble": "",
}

# Estados (radio dato[2]).
ESTADOS = {
    "cualquiera": "", "proxima": "PU", "celebrandose": "EJ",
    "suspendida": "SU", "cancelada": "CA", "concluida": "PC", "finalizada": "FS",
}


def _superficie_m2(desc):
    """Extrae superficie en m2 de la descripcion. Soporta m2/metros y hectareas."""
    if not desc:
        return None
    t = desc.lower().replace("\xba", "").replace("\xaa", "")
    # hectareas -> m2
    mh = re.search(r"([\d\.]+(?:,\d+)?)\s*(?:hect|ha\b)", t)
    if mh:
        try:
            return round(float(mh.group(1).replace(".", "").replace(",", ".")) * 10000, 1)
        except ValueError:
            pass
    # Puede haber varias cifras (util, construida, terrazas...). Nos quedamos con
    # la MAYOR plausible: la superficie principal suele ser la mas grande.
    # (Limitacion: si la superficie principal esta escrita en letra, no se capta.)
    vals = []
    for m in re.finditer(r"([\d\.]+(?:,\d+)?)\s*(?:m2|m\.?\s?2|m²|metros?\s*cuadrados?)", t):
        try:
            v = float(m.group(1).replace(".", "").replace(",", "."))
            if 5 <= v <= 5_000_000:
                vals.append(v)
        except ValueError:
            continue
    return max(vals) if vals else None


def _euros(txt):
    """'36.060,73 EUR' -> 36060.73 ; '' o 'Sin ...' -> None."""
    if not txt:
        return None
    m = re.search(r"([\d\.]+,\d{2})", txt)
    if not m:
        return None
    return float(m.group(1).replace(".", "").replace(",", "."))


class BoeClient:
    def __init__(self, pausa=0.7):
        self.s = requests.Session()
        self.s.headers.update(HEADERS)
        self.pausa = pausa

    def _get(self, url, **kw):
        r = self.s.get(url, timeout=45, **kw)
        r.encoding = "ISO-8859-15"  # el portal sirve latin-9, no utf-8
        time.sleep(self.pausa)
        return r

    def _post(self, url, data):
        r = self.s.post(url, data=data, timeout=45)
        r.encoding = "ISO-8859-15"
        time.sleep(self.pausa)
        return r

    # ---- Busqueda ---------------------------------------------------------
    def buscar(self, subtipo="", provincia="", origen="", estado="",
               max_paginas=40):
        """Devuelve lista de idSub unicos para los criterios dados."""
        data = {
            "campo[0]": "SUBASTA.ORIGEN", "dato[0]": origen,
            "campo[2]": "SUBASTA.ESTADO.CODIGO", "dato[2]": estado,
            "campo[3]": "BIEN.TIPO", "dato[3]": "I", "dato[4]": subtipo,
            "campo[8]": "BIEN.COD_PROVINCIA", "dato[8]": provincia,
            "campo[9]": "SUBASTA.POSTURA_MINIMA_MINIMA_LOTES", "dato[9]": "",
            "page_hits": "50",
            "sort_field[0]": "SUBASTA.FECHA_FIN", "sort_order[0]": "asc",
            "accion": "Buscar",
        }
        r = self._post(BUSCAR, data)
        if "es excesivo" in r.text:
            raise RuntimeError("El BOE considera la busqueda demasiado amplia; "
                               "acota mas (provincia/subtipo).")
        token = self._token(r.text)
        ids = self._ids(r.text)
        if not ids or token is None:
            return sorted(set(ids))
        # paginar
        offset = 50
        for _ in range(max_paginas):
            url = f"{BUSCAR}?accion=Buscar&id_busqueda={token}-{offset}-50"
            page = self._get(url)
            nuevos = self._ids(page.text)
            if not nuevos:
                break
            ids.extend(nuevos)
            offset += 50
        return sorted(set(ids))

    @staticmethod
    def _ids(html):
        return re.findall(r"detalleSubasta\.php\?idSub=([A-Za-z0-9\-]+)", html)

    @staticmethod
    def _token(html):
        m = re.search(r"id_busqueda=([^&\"'\s]+?)-\d+-\d+", html)
        return m.group(1) if m else None

    # ---- Detalle ----------------------------------------------------------
    def detalle(self, id_sub):
        """Combina ver=1 (general) y ver=3 (bienes) en un dict normalizado."""
        campos = {}
        for ver in (1, 3):
            r = self._get(f"{DETALLE}?idSub={id_sub}&ver={ver}")
            s = BeautifulSoup(r.text, "html.parser")
            for tr in s.find_all("tr"):
                th, td = tr.find("th"), tr.find("td")
                if th and td:
                    campos[th.get_text(" ", strip=True)] = td.get_text(" ", strip=True)
        g = lambda k: campos.get(k)
        return {
            "id_sub": id_sub,
            "url": f"{DETALLE}?idSub={id_sub}",
            "tipo_subasta": g("Tipo de subasta"),
            "descripcion": g("Descripcion") or g("Descripci\xf3n"),
            "superficie_m2": _superficie_m2(g("Descripcion") or g("Descripci\xf3n")),
            "direccion": g("Direccion") or g("Direcci\xf3n"),
            "cod_postal": g("Codigo Postal") or g("C\xf3digo Postal"),
            "localidad": g("Localidad"),
            "provincia": g("Provincia"),
            "valor_subasta": _euros(g("Valor subasta")),
            "tasacion": _euros(g("Tasacion") or g("Tasaci\xf3n")),
            "postura_minima": _euros(g("Postura minima") or g("Postura m\xednima")
                                     or g("Puja minima") or g("Puja m\xednima")),
            "deposito": _euros(g("Importe del deposito") or g("Importe del dep\xf3sito")),
            "cantidad_reclamada": _euros(g("Cantidad reclamada")),
            "anuncio_boe": g("Anuncio BOE"),
            "fecha_inicio": g("Fecha de inicio") or g("Fecha inicio"),
            "fecha_fin": g("Fecha de conclusion") or g("Fecha de conclusi\xf3n"),
            "lotes": g("Lotes"),
        }
