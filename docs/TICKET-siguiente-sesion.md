# Ticket — próxima sesión

Estado actual: rastreadas 5 provincias (Almería, Málaga, Cádiz, Huelva, Sevilla),
100 lotes, visor con satélite + filtros. Objetivo de esta tanda: **escalar a toda
España**, **eliminar la comparativa de gangas** para simplificar, y **añadir
filtro por CCAA**.

---

## 1. Ampliar el rastreo a TODA España

**Qué:** rastrear las 52 provincias, no solo las 5 actuales.

**Cómo:**
- `config.py`: `PROVINCIAS_OBJETIVO = list(PROVINCIAS)` (las 52). Mantener
  `SUBTIPOS = ["vivienda", "solar", "finca_rustica"]` y `ESTADOS = ["PU", "EJ"]`.
- El BOE ya se consulta por provincia+subtipo, así que no saltará el error
  "resultados excesivos". No hace falta tocar `boe.py`.

**Cuidado (cuello de botella):** el `enrich` geocodifica a **1 req/s** (límite de
Nominatim). Con toda España pueden ser **miles de lotes** → varias horas.
- `enrich` ya es **reanudable** (solo procesa `geocode_estado IS NULL`), así que
  se puede cortar y continuar.
- Lanzar `crawl` primero (rápido), luego `enrich` en segundo plano / de noche.
- Opcional: considerar un geocoder propio (CSV de callejero/CP) para no depender
  de Nominatim. **No** paralelizar Nominatim (viola su política).

**Aceptación:** `python run.py crawl` recorre las 52 provincias; la BD tiene
lotes de todas; `enrich` avanza sin errores y es reanudable.

---

## 2. Quitar la comparativa de gangas (SIMPLIFICAR)

**Qué:** eliminar toda la lógica de comparación €/m² vs mercado.

**Eliminar / limpiar:**
- `precios.py` y `data/precios_ref.csv` → borrar del pipeline (se pueden dejar
  archivados, pero `dataset.py` deja de importarlos).
- `dataset.py`: quitar `eur_m2_ref`, `ref_ambito`, `pct_mercado`, `ganga` de
  `CAMPOS` y del cálculo. Quitar `import precios` y la llamada `cargar_ref`.
- `viewer.py`: quitar del HTML/JS todo lo relativo a la comparativa:
  - Columnas de tabla: `€/m²` (`eur_m2`? ver decisión), `%merc` (`pct_mercado`).
  - Filtros: `% mercado max` (`pmerc`), interruptor `solo gangas` (`solog`).
  - Resaltado de filas `.ganga`, texto "🔥GANGA" del popup, contador de gangas
    en `#stats`, opción "% mercado (ganga primero)" del selector Ordenar.
  - Referencias a `pct_mercado`/`eur_m2_ref` en la descarga CSV.
- `run.py` (export): quitar `--solo-gangas` y las columnas/orden de ganga.
- `README.md`: quitar la sección "Detección de gangas".

**Decisión pendiente (recomendación):**
- **Mantener** `superficie_m2` y `eur_m2` **del propio lote** (precio ÷ m²): no
  son comparativa, son datos intrínsecos útiles. → mantener columna `€/m²`.
- **Quitar** solo lo que compara contra mercado (`eur_m2_ref`, `pct_mercado`,
  `ganga`). Si se prefiere limpieza total, quitar también `eur_m2`.

**Aceptación:** el visor no muestra nada de "% mercado / ganga / referencia";
`dataset.py` no importa `precios`; `run.py export` funciona sin `--solo-gangas`.

---

## 3. Añadir filtro/segmento por CCAA

**Qué:** filtrar lotes por Comunidad Autónoma.

**Cómo:**
- `provincias.py`: añadir mapa `CCAA = {cod_provincia: "Nombre CCAA"}` (o
  `CCAA_PROVINCIAS = {"Andalucía": ["04","11",...], ...}`).
- `dataset.py`: derivar `ccaa` de `provincia_cod` y añadirlo a `CAMPOS`.
- `viewer.py`: añadir filtro **CCAA**. Como son 17, mejor un **`<select>`**
  (desplegable) que un segmento; si se quiere segmento, agrupar. Poblar opciones
  con los valores únicos presentes (como ya se hace con provincia/subtipo).
  Al elegir CCAA, filtrar; opcional: encadenar para que el select de provincia
  muestre solo las de esa CCAA.

**Aceptación:** el visor tiene un filtro CCAA que acota los lotes; combina con el
resto de filtros.

---

## Archivos afectados
`config.py`, `provincias.py`, `dataset.py`, `viewer.py`, `run.py`, `README.md`.
Retirar del pipeline: `precios.py`, `data/precios_ref.csv`.

## Orden sugerido
1. CCAA (rápido, mejora navegación). 2. Quitar gangas (simplifica antes de
escalar). 3. Lanzar crawl toda España + enrich de fondo.
