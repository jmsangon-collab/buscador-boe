# -*- coding: utf-8 -*-
"""Orquestador CLI del buscador de subastas del BOE.

Uso:
    python run.py crawl     # rastrea el BOE y guarda en SQLite
    python run.py enrich    # geocodifica y calcula distancia a la costa
    python run.py export    # exporta a Excel/CSV aplicando filtros
    python run.py all       # las tres fases seguidas

Opciones utiles:
    python run.py crawl --provincias 04 29 --subtipos finca_rustica
    python run.py export --precio-max 40000 --cerca-mar
"""
import argparse
import datetime as dt

import config
import db
from boe import BoeClient, SUBTIPOS
from provincias import nombre


def _now():
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ---------------------------------------------------------------- crawl -----
def crawl(args):
    provincias = args.provincias or config.PROVINCIAS_OBJETIVO
    subtipos = args.subtipos or config.SUBTIPOS
    con = db.conectar()
    cli = BoeClient()
    total = 0
    for prov in provincias:
        for sub in subtipos:
            for estado in config.ESTADOS:
                try:
                    ids = cli.buscar(subtipo=SUBTIPOS[sub], provincia=prov, estado=estado)
                except Exception as e:
                    print(f"  [!] {nombre(prov)}/{sub}/{estado or 'prox'}: {e}")
                    continue
                if not ids:
                    continue
                print(f"  {nombre(prov):22} {sub:13} {estado or 'prox':4} -> {len(ids)} lotes")
                for i, id_sub in enumerate(ids, 1):
                    d = cli.detalle(id_sub)
                    d["subtipo"] = sub
                    d["provincia_cod"] = prov
                    d["estado"] = {"PU": "proxima_apertura", "EJ": "celebrandose"}.get(estado, estado)
                    d["fetched_at"] = _now()
                    db.upsert(con, d)
                    total += 1
                    if i % 20 == 0:
                        con.commit()
                        print(f"      ...{i}/{len(ids)}")
                con.commit()
    con.commit()
    print(f"[OK] {total} lotes guardados en {db.DB_PATH}")


# --------------------------------------------------------------- enrich -----
def enrich(args):
    from geo import geocodificar, CoastDistance
    con = db.conectar()
    filas = db.pendientes_geocode(con)
    print(f"Geocodificando {len(filas)} lotes pendientes...")
    coast = CoastDistance()
    for i, f in enumerate(filas, 1):
        g = geocodificar(f["direccion"], f["localidad"], f["provincia"], f["cod_postal"])
        if g:
            dcm = coast.metros(g["lat"], g["lon"])
            con.execute("UPDATE subastas SET lat=?, lon=?, dist_costa_m=?, barrio=?, "
                        "distrito=?, municipio_geo=?, geocode_estado='ok' WHERE id_sub=?",
                        (g["lat"], g["lon"], dcm, g["barrio"], g["distrito"],
                         g["municipio"], f["id_sub"]))
        else:
            con.execute("UPDATE subastas SET geocode_estado='no_encontrado' WHERE id_sub=?",
                        (f["id_sub"],))
        if i % 10 == 0:
            con.commit()
            print(f"  ...{i}/{len(filas)}")
    con.commit()
    print("[OK] enriquecimiento completado")


# --------------------------------------------------------------- export -----
def export(args):
    import pandas as pd
    import dataset
    df = pd.DataFrame(dataset.cargar())
    if df.empty:
        print("No hay datos. Ejecuta primero: python run.py crawl")
        return

    precio_max = args.precio_max if args.precio_max is not None else config.PRECIO_MAX
    filt = df["precio_ref"].notna() & (df["precio_ref"] <= precio_max)
    if args.cerca_mar:
        filt &= df["dist_costa_m"].notna() & (df["dist_costa_m"] <= config.DIST_COSTA_MAX_M)
    if getattr(args, "solo_gangas", False):
        filt &= df["ganga"]
    if args.subtipos:
        filt &= df["subtipo"].isin(args.subtipos)

    out = df[filt].sort_values(["ganga", "dist_costa_m", "precio_ref"],
                               ascending=[False, True, True], na_position="last")

    xlsx = "data/resultados.xlsx"
    csv = "data/resultados.csv"
    out.to_excel(xlsx, index=False)
    out.to_csv(csv, index=False, encoding="utf-8-sig")
    print(f"[OK] {len(out)} lotes -> {xlsx} y {csv}  ({int(out['ganga'].sum())} gangas)")
    if len(out):
        print(out[["precio_ref", "eur_m2", "pct_mercado", "dist_costa_m",
                   "localidad", "descripcion"]].head(15).to_string(index=False))


# ------------------------------------------------------------------ main ----
def main():
    p = argparse.ArgumentParser(description="Buscador de subastas del BOE")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("crawl", help="rastrear el BOE")
    c.add_argument("--provincias", nargs="*", help="codigos INE, ej: 04 29")
    c.add_argument("--subtipos", nargs="*", choices=list(SUBTIPOS))
    c.set_defaults(func=crawl)

    e = sub.add_parser("enrich", help="geocodificar + distancia a la costa")
    e.set_defaults(func=enrich)

    x = sub.add_parser("export", help="exportar a Excel/CSV")
    x.add_argument("--precio-max", type=float)
    x.add_argument("--cerca-mar", action="store_true", help="solo <500 m del mar")
    x.add_argument("--solo-gangas", action="store_true", help="solo lotes marcados como ganga")
    x.add_argument("--subtipos", nargs="*", choices=list(SUBTIPOS))
    x.set_defaults(func=export)

    v = sub.add_parser("viewer", help="generar visor HTML (data/visor.html)")
    v.set_defaults(func=lambda args: __import__("viewer").generar())

    a = sub.add_parser("all", help="crawl + enrich + export + viewer")
    a.add_argument("--cerca-mar", action="store_true")
    a.add_argument("--precio-max", type=float)
    a.add_argument("--provincias", nargs="*")
    a.add_argument("--subtipos", nargs="*", choices=list(SUBTIPOS))
    a.set_defaults(func=None)

    args = p.parse_args()
    if args.cmd == "all":
        crawl(args); enrich(args); export(args)
        __import__("viewer").generar()
    else:
        args.func(args)


if __name__ == "__main__":
    main()
