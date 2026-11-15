# TODO

1. revisar el data/catalog.json, la sección de _comment, ya que ahí explico el null de la clave `region` 
2. Atención a un detalle del estado: aunque tengamos un algoritmo A* implementado, el estado de misión seguirá siendo awaiting_data mientras no exista un DEM registrado y una región seleccionada. No confundiremos el motor disponible con una misión científica lista. (src/api/routes/mission.py)