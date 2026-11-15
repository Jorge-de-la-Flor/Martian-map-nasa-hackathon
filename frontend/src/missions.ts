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
  equipment: Array<{ item: string; massKg: number }>;
  evaMaxHours: number; // tiempo máximo de caminata (oxígeno)
  difficulty: "Low" | "Medium" | "High";
  photo: { src: string; caption: string; credit: string; source?: string };
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
    target: { label: "Boxwork region, Mount Sharp (approx.)", longitude: 137.39, latitude: -4.8 },
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
      source: "https://science.nasa.gov/photojournal/curiosity-views-a-fractured-boxwork-pattern-up-close/",
    },
  },
  {
    id: "nazca",
    name: "Crystal block inspection",
    objective: "Photograph and sample the 'discs and needles' crystal block at the Nazca drill site.",
    science:
      "Crystal-shaped lumps in the sulfate layer of Mount Sharp record how water dried out on Mars.",
    target: { label: "Nazca drill site, Mount Sharp", longitude: 137.3876, latitude: -4.8247 },
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
