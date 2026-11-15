# Martian data sources

This document separates scientific products by measurement type and
intended use.

A source being listed here does not mean that its data are already
downloaded, prepared, or integrated into the application.

## Topographic

### CTX stereo Digital Terrain Models

- Mission: Mars Reconnaissance Orbiter.
- Instrument: Context Camera (CTX).
- Product: stereo-derived Digital Terrain Models.
- Typical post spacing: 20 metres.
- Intended use: local terrain elevation and slope analysis.
- Source:
  https://stac.astrogeology.usgs.gov/docs/data/mars/ctxdtms/

Coverage is local and must be confirmed for the selected study region.

### HiRISE Digital Terrain Models

- Mission: Mars Reconnaissance Orbiter.
- Instrument: High Resolution Imaging Science Experiment.
- Intended use: detailed local topography where a suitable stereo DTM exists.
- Source:
  https://www.uahirise.org/

An optical HiRISE image is not automatically a digital terrain model.

### MOLA MEGDR

- Mission: Mars Global Surveyor.
- Instrument: Mars Orbiter Laser Altimeter.
- Product: gridded planetary topography.
- Available resolutions include 4, 16, 32, 64, and 128 pixels per degree.
- Intended use: global and regional context.
- Source:
  https://pds-geosciences.wustl.edu/missions/mgs/megdr.html

The highest-resolution global product is approximately 460 metres per
pixel at the equator. It is not suitable as the only terrain model for
detailed human route planning.

## Optical

### CTX Global Mosaic

- Mission: Mars Reconnaissance Orbiter.
- Instrument: CTX.
- Product: global optical mosaic.
- Approximate image scale: 5 metres per pixel.
- Intended use: surface morphology and regional visual context.
- Source:
  https://murray-lab.caltech.edu/CTX/

The global mosaic consists of tiled products. Download only the local
tiles needed for the selected region.

This product is imagery, not a DEM.

### HiRISE images

- Mission: Mars Reconnaissance Orbiter.
- Instrument: HiRISE.
- Intended use: detailed optical inspection of local surface features.
- Source:
  https://www.uahirise.org/

## Thermal and infrared

### THEMIS controlled infrared mosaics

- Mission: Mars Odyssey.
- Instrument: Thermal Emission Imaging System.
- Product: controlled infrared mosaics.
- Approximate resolution: 100 metres per pixel.
- Format: Cloud Optimized GeoTIFF.
- Intended use: thermal and geological context.
- Source:
  https://registry.opendata.aws/nasa-usgs-themis-mosaics/

The controlled mosaics use simple cylindrical projection, planetocentric
latitude, and positive-east longitude.

Product band, processing level, calibration, and physical units must be
checked before quantitative interpretation.

## Optional additional categories

### Spectral: CRISM

- Mission: Mars Reconnaissance Orbiter.
- Instrument: Compact Reconnaissance Imaging Spectrometer for Mars.
- Intended use: mineralogical and compositional context.
- Source:
  https://pds.nasa.gov/ds-view/pds/viewContext.jsp?identifier=urn%3Anasa%3Apds%3Acontext%3Ainstrument%3Acrism.mro

CRISM products are multiband spectral cubes. They require product-specific
interpretation and are not ordinary single-band thermal or optical images.

### Radiation: RAD

- Mission: Mars Science Laboratory.
- Rover: Curiosity.
- Instrument: Radiation Assessment Detector.
- Intended use: surface radiation observations over time.
- Source:
  https://science.nasa.gov/mission/msl-curiosity/science-instruments/

RAD measurements are rover observations, not a continuous orbital
radiation raster across Gale Crater.

### Atmospheric: MEDA

- Mission: Mars 2020.
- Rover: Perseverance.
- Instrument: Mars Environmental Dynamics Analyzer.
- Intended use: surface weather and atmospheric observations in Jezero.
- Source:
  https://science.nasa.gov/mission/mars-2020-perseverance/science-instruments/

MEDA measures wind, temperature, humidity, and dust-related properties.
These observations must retain their location and acquisition time.

### Chemical

Potential sources include Curiosity instruments such as APXS, ChemCam,
CheMin, and SAM.

Source:
https://science.nasa.gov/mission/msl-curiosity/science-instruments/

These are local measurements and should be represented as observations
or points of interest, not as continuous chemical maps unless a separate,
validated interpolation product is available.

## Data preparation requirements

Before a raster is used by the route planner:

1. Confirm the original product and processing level.
2. Read the original planetary coordinate convention.
3. Confirm planetocentric or planetographic latitude.
4. Confirm longitude direction and domain.
5. Confirm the Mars datum and ellipsoid.
6. Convert to a projected Mars CRS suitable for the selected region.
7. Confirm horizontal units are metres.
8. Preserve original NoData semantics.
9. Document physical units and scale factors.
10. Align hazard, uncertainty, and blocked layers exactly to the route DEM.

Do not assume that a CRS labelled with a generic longitude/latitude name
is an Earth CRS or that two planetary rasters can be overlaid without
checking their reference systems.
