// ===================== DATOS REALES (Curiosity en Gale) =====================
// REMS: temperatura del aire ~0 °C (máx) a ~-70 °C (mín) por día
// REMS: presión diaria ~685 a ~780 Pa
// RAD: dosis equivalente promedio en superficie ~0.67 mSv/día
export const GALE_ENVIRONMENT = {
  airTempMaxC: 0,
  airTempMinC: -70,
  pressureMinPa: 685,
  pressureMaxPa: 780,
  radiationMsvPerDay: 0.67,
};

export const RADIATION_MSV_PER_HOUR = GALE_ENVIRONMENT.radiationMsvPerDay / 24;

// Temperatura aproximada según la hora local (ciclo simple: más calor ~14:00)
export function airTempAt(localHour: number): number {
  const { airTempMaxC, airTempMinC } = GALE_ENVIRONMENT;
  const mid = (airTempMaxC + airTempMinC) / 2;
  const amplitude = (airTempMaxC - airTempMinC) / 2;
  return mid + amplitude * Math.cos((2 * Math.PI * (localHour - 14)) / 24);
}

// ===================== MODELO SIMULADO DEL TRAJE (SUPUESTOS) =====================
// Valores de ejemplo para la demo. Acordar con el equipo.

// Cuánto más rápido se gasta el O2 según el peso del equipo (23 kg -> x1.46)
export function o2Multiplier(loadKg: number): number {
  return 1 + loadKg / 50;
}

// Ritmo cardíaco estimado caminando con carga
export function heartRateBpm(loadKg: number, jitter = 0): number {
  return Math.round(85 + loadKg * 1.5 + jitter);
}

// Batería: 10 %/h base + 6 %/h extra si hace mucho frío (calefacción)
export function batteryDrainPerHour(airTempC: number): number {
  return 10 + (airTempC < -40 ? 6 : 0);
}

// Estado de cada métrica: verde / amarillo / rojo
export type Level = "ok" | "warn" | "danger";

export function levelFromPercent(pct: number): Level {
  if (pct <= 15) return "danger";
  if (pct <= 30) return "warn";
  return "ok";
}

export function levelFromHeartRate(bpm: number): Level {
  if (bpm >= 150) return "danger";
  if (bpm >= 125) return "warn";
  return "ok";
}

export function levelFromAirTemp(c: number): Level {
  if (c <= -55) return "danger";
  if (c <= -30) return "warn";
  return "ok";
}