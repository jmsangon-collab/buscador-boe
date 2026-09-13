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
    inicio = _now()
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
                    try:
                        d = cli.detalle(id_sub)
                    except Exception as e:
                        print(f"      [!] ficha {id_sub}: {e}")
                        continue
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
    # rastreo completo: los lotes no vistos ya no estan en PU/EJ -> fuera
    if not args.provincias and not args.subtipos:
        borrados = con.execute("DELETE FROM subastas WHERE fetched_at < ?", (inicio,)).rowcount
        con.commit()
        print(f"[OK] {borrados} lotes caducados eliminados")


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


# -------------------------------------------------------------- refresh -----
def refresh(args):
    """Actualiza solo el estado de pujas (ver=5) de los lotes ya guardados.
    Ligero y rapido: 1 peticion por lote. Ideal para vigilar 'ultimas horas'."""
    con = db.conectar()
    cli = BoeClient()
    filas = con.execute("SELECT id_sub FROM subastas").fetchall()
    if args.cierran_pronto:
        # solo las que cierran en las proximas 48 h (por fecha_fin ISO)
        import datetime as _dt
        limite = (_dt.datetime.now() + _dt.timedelta(hours=48)).isoformat()
        ahora = _dt.datetime.now().isoformat()
        filas = con.execute(
            "SELECT id_sub FROM subastas WHERE fecha_fin LIKE '%ISO: %' "
            "AND substr(fecha_fin, instr(fecha_fin,'ISO: ')+5, 16) BETWEEN ? AND ?",
            (ahora[:16], limite[:16])).fetchall()
    print(f"Refrescando pujas de {len(filas)} lotes...")
    for i, f in enumerate(filas, 1):
        p = cli.pujas(f["id_sub"])
        con.execute("UPDATE subastas SET num_pujas=?, puja_maxima=? WHERE id_sub=?",
                    (p["num_pujas"], p["puja_maxima"], f["id_sub"]))
        if i % 20 == 0:
            con.commit()
            print(f"  ...{i}/{len(filas)}")
    con.commit()
    print("[OK] pujas actualizadas")


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
    if args.subtipos:
        filt &= df["subtipo"].isin(args.subtipos)

    out = df[filt].sort_values(["dist_costa_m", "precio_ref"],
                               ascending=[True, True], na_position="last")

    xlsx = "data/resultados.xlsx"
    csv = "data/resultados.csv"
    out.to_excel(xlsx, index=False)
    out.to_csv(csv, index=False, encoding="utf-8-sig")
    print(f"[OK] {len(out)} lotes -> {xlsx} y {csv}")
    if len(out):
        print(out[["precio_ref", "eur_m2", "dist_costa_m",
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

    rf = sub.add_parser("refresh", help="actualizar solo el estado de pujas (ver=5)")
    rf.add_argument("--cierran-pronto", action="store_true", help="solo las que cierran en 48 h")
    rf.set_defaults(func=refresh)

    x = sub.add_parser("export", help="exportar a Excel/CSV")
    x.add_argument("--precio-max", type=float)
    x.add_argument("--cerca-mar", action="store_true", help="solo <500 m del mar")
    x.add_argument("--subtipos", nargs="*", choices=list(SUBTIPOS))
    x.set_defaults(func=export)

    v = sub.add_parser("viewer", help="generar visor HTML (data/visor.html)")
    v.add_argument("--no-abrir", action="store_true", help="no abrir el navegador")
    v.set_defaults(func=lambda args: __import__("viewer").generar(abrir_navegador=not args.no_abrir))

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
