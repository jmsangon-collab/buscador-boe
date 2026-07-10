# -*- coding: utf-8 -*-
"""Precios de referencia de mercado (EUR/m2) por BARRIO / DISTRITO / MUNICIPIO
para detectar gangas. La media provincial no sirve: el precio de vivienda
depende del barrio.

Fuente: data/precios_ref.csv, que construyes UNA VEZ desde Idealista
(informes de precio por zona) y dejas fijo. No se scrapea en caliente.

Formato CSV (separador ';'):
    tipo;ambito;municipio;zona;eur_m2
  - tipo:      vivienda | suelo
  - ambito:    barrio | distrito | municipio
  - municipio: nombre del municipio (siempre)
  - zona:      nombre del barrio/distrito (vacio si ambito=municipio)
  - eur_m2:    precio medio de mercado por m2

Emparejamiento de cada subasta: se toma su barrio (reverse-geocode) y se busca
barrio -> distrito -> municipio, en ese orden.
"""
import csv
import os
import unicodedata

CSV_REF = os.path.join(os.path.dirname(__file__), "data", "precios_ref.csv")

SUBTIPO_TIPO = {"vivienda": "vivienda", "solar": "suelo", "finca_rustica": "suelo"}
UMBRAL_GANGA = 0.60  # ganga si eur_m2 del lote <= 60% del mercado de su zona


def _norm(s):
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return s.strip().lower()


def cargar_ref(path=CSV_REF):
    """Devuelve dict con claves:
       ('municipio', tipo, muni)
       ('distrito',  tipo, muni, zona)
       ('barrio',    tipo, muni, zona)
    """
    ref = {}
    if not os.path.exists(path):
        return ref
    with open(path, encoding="utf-8-sig") as f:
        for row in csv.reader(f, delimiter=";"):
            if not row or row[0].strip().startswith("#") or _norm(row[0]) == "tipo":
                continue
            try:
                tipo, ambito, muni, zona, eur = (row + [""] * 5)[:5]
                tipo, ambito = _norm(tipo), _norm(ambito)
                val = float(str(eur).replace(",", "."))
            except (ValueError, IndexError):
                continue
            if ambito == "municipio":
                ref[("municipio", tipo, _norm(muni))] = val
            elif ambito in ("distrito", "barrio"):
                ref[(ambito, tipo, _norm(muni), _norm(zona))] = val
    return ref


def eur_m2_referencia(ref, subtipo, barrio, distrito, municipio):
    """Busca barrio -> distrito -> municipio. Devuelve (valor, ambito) o (None, None)."""
    tipo = SUBTIPO_TIPO.get(subtipo, subtipo)
    m = _norm(municipio)
    v = ref.get(("barrio", tipo, m, _norm(barrio)))
    if v is not None:
        return v, "barrio"
    v = ref.get(("distrito", tipo, m, _norm(distrito)))
    if v is not None:
        return v, "distrito"
    v = ref.get(("municipio", tipo, m))
    if v is not None:
        return v, "municipio"
    return None, None
