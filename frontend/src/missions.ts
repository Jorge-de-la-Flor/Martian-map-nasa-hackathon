export interface Coordinate {
  longitude: number;
  latitude: number;
}

export interface Mission {
  id: string;
  name: string;
  objective: string;
  science: string;
  target: Coordinate & { label: string };
  roverDrop: Coordinate & { label: string }; // donde el rover presurizado deja al astronauta
  equipment: Array<{ item: string; massKg: number }>;
  evaMaxHours: number; // tiempo máximo de caminata (oxígeno)
  difficulty: "Low" | "Medium" | "High";
  photo: { src: string; caption: string; credit: string }; 
}

// Base del astronauta: sitio de aterrizaje de Curiosity
export const HABITAT: Coordinate & { label: string } = {
  label: "Habitat · Bradbury Landing",
  longitude: 137.4416,
  latitude: -4.5895,
};

export const MISSIONS: Mission[] = [
  {
    id: "boxwork",
    name: "Boxwork ridges survey",
    objective: "Collect samples from a boxwork ridge and from the sandy hollow next to it.",
    science:
      "Boxwork ridges formed where ancient groundwater left minerals in rock fractures. " +
      "Curiosity found clay minerals in a ridge and carbonates in a hollow.",
    // Waypoint real de Curiosity (NASA/JPL-Caltech), sol 4711: cresta "Nevado Sajama"
    target: { label: "Nevado Sajama · boxwork ridge (sol 4711)", longitude: 137.3810041, latitude: -4.80800755 },
    roverDrop: { label: "Rover drop-off", longitude: 137.388, latitude: -4.814 },
    equipment: [
      { item: "Sampling kit", massKg: 8 },
      { item: "Hand drill", massKg: 12 },
      { item: "Stereo camera", massKg: 3 },
    ],
    evaMaxHours: 6,
    difficulty: "High",
        photo: {
      src: "/missions/boxwork.jpg",
      caption: "Curiosity's Mastcam view of a curb-like boxwork ridge on Mount Sharp (PIA26558).",
      credit: "NASA/JPL-Caltech/MSSS",
    },
  },
  {
    id: "nazca",
    name: "Crystal block inspection",
    objective: "Photograph and sample the 'discs and needles' crystal block at the Nazca drill site.",
    science:
      "Crystal-shaped lumps in the sulfate layer of Mount Sharp record how water dried out on Mars.",
    // Posición de Curiosity en el sol 5045 (mapa de ubicación de la NASA)
    target: { label: "Nazca drill site (sol 5045)", longitude: 137.3876111, latitude: -4.8246694 },
    roverDrop: { label: "Rover drop-off", longitude: 137.382, latitude: -4.818 },
    equipment: [
      { item: "Sampling kit", massKg: 8 },
      { item: "Macro camera", massKg: 2 },
    ],
    evaMaxHours: 6,
    difficulty: "Medium",
        photo: {
      src: "/missions/nazca.jpg",
      caption: "Curiosity's MAHLI close-up of disc-shaped crystal forms on the 'Nazca' drill target (sol 5048).",
      credit: "NASA/JPL-Caltech/MSSS",
    },
  },
  ];

// Zona de estudio = área con datos de elevación (DEM USGS de 1 m, Mount Sharp).
// Estos valores son el respaldo; al iniciar se actualizan con /api/mission/coverage.
export const STUDY_ZONE = {
  label: "Gale DEM coverage · 1 m (Mount Sharp)",
  west: 137.37846,
  east: 137.39014,
  south: -4.8272,
  north: -4.80531,
};

export function isInsideZone(longitude: number, latitude: number): boolean {
  return (
    longitude >= STUDY_ZONE.west &&
    longitude <= STUDY_ZONE.east &&
    latitude >= STUDY_ZONE.south &&
    latitude <= STUDY_ZONE.north
  );
}
