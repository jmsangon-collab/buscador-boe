# Buscador de subastas del BOE (viviendas y terrenos)

Rastrea el [Portal de Subastas del BOE](https://subastas.boe.es), guarda los
lotes en SQLite, los geolocaliza, calcula su **distancia a la costa** y los
exporta a Excel/CSV y a un **visor HTML** con tabla, filtros y mapa.

Pensado para dos objetivos: **pisos baratos** y **terreno rústico/solar barato
cerca del mar** (para una mobile home en campo o playa).

## Instalación

```bash
pip install -r requirements.txt
```

## Uso

```bash
python run.py crawl      # 1. rastrea el BOE -> data/subastas.db
python run.py enrich     # 2. geocodifica + distancia a la costa
python run.py export     # 3. exporta a data/resultados.xlsx / .csv
python run.py viewer     # 4. genera data/visor.html (abrir con doble clic)

python run.py all        # todo lo anterior de una vez
```

### Acotar el rastreo

```bash
python run.py crawl --provincias 04 29 30 --subtipos finca_rustica solar
```

### Filtros de exportación

```bash
python run.py export --precio-max 40000 --cerca-mar --subtipos finca_rustica
```

`--cerca-mar` deja solo lotes a menos de 500 m de la costa.

## Configuración

Edita `config.py`:
- `SUBTIPOS`: vivienda / solar / finca_rustica / local / garaje / nave ...
- `PROVINCIAS_OBJETIVO`: por defecto Andalucía (`CCAA_PROVINCIAS["Andalucia"]`);
  también `COSTERAS` o `list(PROVINCIAS)` (toda España).
- `ESTADOS`: `""` (próxima apertura) y `"PU"` (celebrándose) = aún puedes pujar.
- `PRECIO_MAX`, `DIST_COSTA_MAX_M`.

## El visor HTML

`data/visor.html` es autónomo (datos embebidos). Se abre en el navegador con
doble clic. Permite filtrar por texto, precio, subtipo, clase (rural/urbano),
CCAA, provincia, localidad, estado y distancia al mar; ordenar columnas; ver los lotes en un mapa; y **descargar en
CSV** (se abre en Excel) la selección filtrada. Cada lote enlaza a su ficha
oficial del BOE.

El sistema extrae además los **m² de la descripción** del BOE y calcula el
**€/m² real del lote** (precio ÷ superficie), un dato intrínseco útil para
comparar lotes entre sí. Se muestra como columna en el visor y en el export.

## Web publicada (GitHub Pages)

El visor está publicado en <https://jmsangon-collab.github.io/subastas-boe/>.

- `.github/workflows/update.yml` se ejecuta cada día a las 03:15 UTC: rastrea
  el BOE, geocodifica, regenera el visor, guarda `data/subastas.db` y
  `web_publicar/index.html` en el repo y despliega la web. Se puede lanzar a
  mano desde la pestaña *Actions* (o `gh workflow run update`).
- `.github/workflows/pages.yml` despliega `web_publicar/` en cada push que lo
  modifique. Para publicar desde local: `python run.py all` y `git push`.
- `run.py crawl` sin acotar borra de la BD los lotes que ya no aparecen en el
  portal (subastas terminadas).

## Notas y límites

- **Distancia a la costa**: se calcula con la costa de Natural Earth 10m
  (precisión de algunos cientos de metros). Úsalo como primer cribado y
  verifica los candidatos a mano. Para más precisión, sustituye
  `data/coastline.geojson` por una costa de OSM de mayor resolución.
- **Geocodificación**: usa Nominatim (OpenStreetMap), limitado a 1 consulta/s.
  Las direcciones vagas ("paraje tal", "polígono X parcela Y") pueden no
  geolocalizarse; quedan marcadas como `no_encontrado`.
- **Cortesía y captcha**: el rastreador pausa 2 s entre peticiones. Si el
  portal detecta demasiado volumen sirve una "verificación de seguridad"
  (captcha); el rastreo se interrumpe sin purgar la BD. Espera un rato y
  reanuda con `python run.py crawl --desde <cod_provincia>`.
- Datos oficiales, pero verifica siempre la ficha del BOE antes de pujar
  (cargas, situación posesoria, tramos, depósito, fechas).

## Estructura

| Archivo | Función |
|---|---|
| `boe.py` | Cliente del portal (búsqueda + parseo de fichas) |
| `db.py` | Esquema y acceso SQLite |
| `geo.py` | Geocodificación + distancia a la costa |
| `config.py` | Qué rastrear y filtros por defecto |
| `provincias.py` | Códigos INE y provincias costeras |
| `run.py` | CLI (crawl / enrich / export / viewer / all) |
| `viewer.py` | Generador del visor HTML |
