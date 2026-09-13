# -*- coding: utf-8 -*-
"""Que buscar en el BOE. Edita esto para cambiar el alcance del rastreo."""
from provincias import COSTERAS, PROVINCIAS

# Subtipos de inmueble a rastrear (clave de boe.SUBTIPOS).
SUBTIPOS = ["vivienda", "solar", "finca_rustica"]

# Provincias a rastrear. Toda Espana (las 52). Para acotar, pon COSTERAS
# (solo las de mar) o una lista de codigos INE, ej: ["04", "29"].
PROVINCIAS_OBJETIVO = list(PROVINCIAS)

# Estados de subasta a incluir. "PU" (proxima apertura) y "EJ" (celebrandose)
# son las que aun puedes pujar.
ESTADOS = ["PU", "EJ"]

# ---- Filtros de exportacion ----------------------------------------------
PRECIO_MAX = 60000        # euros: descarta lo caro (valor_subasta o postura)
DIST_COSTA_MAX_M = 500    # metros a la costa para el filtro "cerca del mar"
