# Mount Sharp boxwork data

The study area is around two sites investigated by Curiosity in Gale crater in 2025.
Valle de la Luna is in the Monte Grande hollow and Nevado Sajama is on an adjacent ridge.
The site catalog gives published rover waypoints close to the targets. Use the pins to
locate the workspaces. Surveyed drill-hole coordinates would require another source.

## Sources and credits

| Resource | Use and attribution |
| --- | --- |
| [Curiosity location map](https://science.nasa.gov/mission/msl-curiosity/location-map/) and [public waypoint data](https://mars.nasa.gov/mmgis-maps/MSL/Layers/json/MSL_waypoints.json) | Source of the positions, sols, and rover motion counter identifiers in [the site catalog](../data/mount-sharp-boxwork-sites.json). Credit NASA/JPL-Caltech. |
| [Valle de la Luna](https://science.nasa.gov/blog/curiosity-blog-sols-4689-4694-drill-in-the-boxwork-unit/), [Nevado Sajama](https://science.nasa.gov/blog/curiosity-blog-sols-4716-4722-drilling-success-at-nevado-sajama/) and [JPL's sample results](https://www.jpl.nasa.gov/news/nasas-curiosity-rover-sees-martian-spiderwebs-up-close/) | Site descriptions and reported mineral identifications for the specific samples. Credit NASA/JPL-Caltech. |
| [Mars MSL Gale Merged DEM 1m, v3](https://astrogeology.usgs.gov/search/map/mars_msl_gale_merged_dem_1m) | Calef III and Parker (2016), NASA/JPL and USGS Astrogeology. Astropedia asks for author credit and lists no use constraints. The script reads the USGS download mirror. |

For any Curiosity images added to the interface, use the product's credit line
and follow the [JPL image use policy](https://www.jpl.nasa.gov/jpl-image-use-policy/).

## Prepare the elevation grid

From the repository root, using the existing Python environment:

```bash
uv run python scripts/prepare_boxwork_dem.py
```

The script requests a window of the source raster around both waypoints, with a
150-cell margin. It preserves the native grid and CRS and reports the count of valid
cells and the elevation at each waypoint. Use `--source /path/to/source.tif` to read
from a local copy. Generated TIFFs are ignored by Git.

After starting the backend, inspect the generated grid at
`/api/mission/raster?path=mount-sharp-boxwork-dem.tif`.
The initial extraction produced a 303 × 311 cell grid in `ESRI:103885` with
94,233 valid elevation cells.

The map coordinates use east-positive longitude and planetocentric latitude on Mars.
The output cell spacing is 1 m. Parts of the source DEM were filled with coarser
data, so check which elevation product contributed to the corridor before using it
to judge small ridges or surface obstacles. The waypoint samples are DEM values
at the rover positions and should be interpreted at that scale.

Codex assisted with source research, scripting, and documentation for this data preparation.
