# -*- coding: utf-8 -*-
"""Carga los lotes de la BD y los enriquece con metricas de ganga:
precio_ref, eur_m2, eur_m2_ref, pct_mercado (lote/mercado) y flag ganga.
Fuente unica compartida por el export y el visor HTML.
"""
import db
import precios

CAMPOS = ["id_sub", "subtipo", "estado", "precio_ref", "valor_subasta",
          "postura_minima", "deposito", "superficie_m2", "eur_m2",
          "eur_m2_ref", "ref_ambito", "pct_mercado", "ganga", "descripcion",
          "direccion", "localidad", "barrio", "distrito", "provincia",
          "dist_costa_m", "lat", "lon", "fecha_fin", "url"]


def cargar():
    con = db.conectar()
    ref = precios.cargar_ref()
    filas = con.execute("SELECT * FROM subastas").fetchall()
    out = []
    for r in filas:
        d = dict(r)
        d["precio_ref"] = d.get("postura_minima") or d.get("valor_subasta")
        sup = d.get("superficie_m2")
        d["eur_m2"] = round(d["precio_ref"] / sup, 1) if (d["precio_ref"] and sup) else None
        rm2, amb = precios.eur_m2_referencia(
            ref, d.get("subtipo"), d.get("barrio"), d.get("distrito"),
            d.get("municipio_geo") or d.get("localidad"))
        d["eur_m2_ref"] = rm2
        d["ref_ambito"] = amb
        d["pct_mercado"] = round(d["eur_m2"] / rm2, 3) if (d["eur_m2"] and rm2) else None
        d["ganga"] = bool(d["pct_mercado"] is not None and d["pct_mercado"] <= precios.UMBRAL_GANGA)
        out.append({k: d.get(k) for k in CAMPOS})
    return out
