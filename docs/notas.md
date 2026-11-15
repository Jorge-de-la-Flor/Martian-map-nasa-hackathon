# notas importantes para desarollo

## Limitaciones

Una limitación que quiero hacer explícita: validar que el elipsoide tenga dimensiones marcianas no demuestra por sí solo que el producto respete la convención planetográfica/planetocéntrica correcta. Esa comprobación necesita los metadatos originales y debe formar parte de la preparación científica del producto. (src/geospatial/raster.py)

Importante: uncertain_distance_m y hazard_exposure_distance_m son métricas basadas en el umbral de exposición 0.5 aplicado a la media de los valores de los extremos de cada segmento. No representan una medición física exacta de riesgo ni una distancia certificada dentro de un polígono científico. (src/services/metrics.py)

## Hay cuatro decisiones científicas que debemos respetar

- Primero: MOLA no puede ser nuestro único DEM para planificar caminatas. Sus productos MEGDR tienen resoluciones de 4, 16, 32, 64 y 128 píxeles por grado. Incluso el de 128 píxeles por grado representa aproximadamente 463 metros por píxel en el ecuador marciano. Nos sirve como contexto topográfico global, no como navegación de detalle. Además, desde el 25 de agosto de 2026, el archivo mantenido está en el bundle PDS4.

- Segundo: CTX y HiRISE sí pueden proporcionar terreno de mayor detalle, pero no de forma uniforme. Los DTM estéreo de CTX tienen un espaciado de aproximadamente 20 metros; HiRISE puede producir DTM con espaciado de 1–2 metros, aunque no todas sus imágenes estéreo se procesan como modelos de elevación.

- Tercero: no podemos asumir que todos los productos tienen el mismo sistema de coordenadas. Marte utiliza convenciones planetocéntricas y planetográficas, además de distintas direcciones de longitud. Debemos interpretar los metadatos originales antes de transformar y alinear las capas.

- Cuarto: THEMIS requiere tratamiento especial. Sus productos estándar pueden estar en coordenadas de cámara y no en una proyección geográfica. Para integrarlos espacialmente debemos seleccionar productos proyectados y leer sus parámetros de mapa.

> Hay también una buena noticia para la elección de región: el catálogo de HiRISE contiene DTM de ambas candidatas, Gale y Jezero. Por tanto, la existencia de DTM por sí sola no decide cuál conviene; tendremos que contrastar la cobertura real de los productos que vayamos a utilizar.

## notas improtantes para las categorias de datos

1. La documentación de USGS indica que los CTX DTM tienen espaciado de 20 m, mientras que el mosaico global CTX de Murray Lab tiene aproximadamente 5 m por píxel. Son productos diferentes: el mosaico óptico no sustituye al DTM.

2. Para THEMIS existe un mosaico global de infrarrojo de unos 100 m por píxel, distribuido como Cloud Optimized GeoTIFF, con convención planetocéntrica y longitud positiva al este.

3. Y MOLA tiene productos globales de hasta 128 píxeles por grado, aproximadamente 460 m por píxel en el ecuador; lo usaremos como contexto regional, no como sustituto de un DTM local de navegación.

## Implementación backend

```bash
src/
├── api/
│   └── routes/
│       ├── health.py
│       └── mission.py
├── core/
│   └── config.py
├── geospatial/
│   ├── catalog.py
│   ├── raster.py
│   └── terrain.py
├── models/
│   └── mission.py
├── services/
│   ├── astar.py
│   ├── cost.py
│   ├── metrics.py
│   └── planner.py
└── main.py

tests/
├── conftest.py
├── test_api.py
├── test_astar.py
├── test_planner.py  # pruebas criticas en este módulo
└── test_terrain.py
```
