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
- `PROVINCIAS_OBJETIVO`: por defecto solo las costeras (`provincias.COSTERAS`).
- `ESTADOS`: `""` (próxima apertura) y `"PU"` (celebrándose) = aún puedes pujar.
- `PRECIO_MAX`, `DIST_COSTA_MAX_M`.

## El visor HTML

`data/visor.html` es autónomo (datos embebidos). Se abre en el navegador con
doble clic. Permite filtrar por texto, precio, subtipo, provincia, estado y
distancia al mar; ordenar columnas; ver los lotes en un mapa; y **descargar en
CSV** (se abre en Excel) la selección filtrada. Cada lote enlaza a su ficha
oficial del BOE.

## Detección de gangas (€/m² vs mercado)

El sistema extrae los **m² de la descripción** del BOE, calcula el **€/m² real
del lote** y lo compara con el precio de mercado de su **zona** para marcar
gangas (`ganga = €/m² lote ≤ 60% del mercado`, ajustable en `precios.py`).

La referencia se toma **por barrio → distrito → municipio** (nunca provincial:
no sirve). Cada subasta se asigna a su barrio mediante *reverse-geocoding* de
sus coordenadas.

Los precios de mercado se cargan una sola vez desde `data/precios_ref.csv`:

```
tipo;ambito;municipio;zona;eur_m2
vivienda;barrio;Malaga;Pedregalejo;3200
vivienda;distrito;Almeria;Centro;1900
vivienda;municipio;Roquetas de Mar;;1600
```

Rellénalo **una vez** con datos de Idealista (sus
[informes de precio por zona](https://www.idealista.com/sala-de-prensa/informes-precio-vivienda/))
y déjalo fijo. **No se scrapea Idealista** (sus términos lo prohíben y tiene
anti-bot): es un dataset preprocesado que tú aportas. La comparación es fiable
para **vivienda**; para suelo rústico la referencia es débil.

Exportar solo gangas:

```bash
python run.py export --solo-gangas
```

En el visor: filtro **% mercado max** y casilla **solo gangas** (fila resaltada).

## Notas y límites

- **Distancia a la costa**: se calcula con la costa de Natural Earth 10m
  (precisión de algunos cientos de metros). Úsalo como primer cribado y
  verifica los candidatos a mano. Para más precisión, sustituye
  `data/coastline.geojson` por una costa de OSM de mayor resolución.
- **Geocodificación**: usa Nominatim (OpenStreetMap), limitado a 1 consulta/s.
  Las direcciones vagas ("paraje tal", "polígono X parcela Y") pueden no
  geolocalizarse; quedan marcadas como `no_encontrado`.
- **Cortesía**: el rastreador pausa entre peticiones. No abuses del portal.
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
