from datetime import date, datetime, timedelta, timezone
import math
from typing import Optional, Tuple

_SYNODIC_MONTH = 29.530588853

def moon_phase(date_utc: date) -> int:
    """Devuelve la fase de la luna (0=nueva, 14=llena)."""
    known_new_moon = datetime(2000, 1, 6, 18, 14, tzinfo=timezone.utc)
    diff = datetime(date_utc.year, date_utc.month, date_utc.day, tzinfo=timezone.utc) - known_new_moon
    days = diff.days + (diff.seconds / 86400.0)
    lunations = days / _SYNODIC_MONTH
    frac = lunations % 1
    return round(frac * _SYNODIC_MONTH) % 30  # Wrap a 0 si llega a 30

def _julian_day(dt: datetime) -> float:
    """Convierte fecha UTC a día juliano."""
    year, month = dt.year, dt.month
    day = dt.day + (dt.hour + dt.minute / 60 + dt.second / 3600) / 24
    if month <= 2:
        year -= 1
        month += 12
    A = year // 100
    B = 2 - A + (A // 4)
    return math.floor(365.25 * (year + 4716)) + math.floor(30.6001 * (month + 1)) + day + B - 1524.5

def _normalize_angle(angle: float) -> float:
    """Normaliza ángulo a 0-360 grados."""
    return angle % 360.0

# Tabla completa 47.A para sigma_l y sigma_r (de PyMeeus/Meeus)
SIGMA_LR_TABLE = [
    [0, 0, 1, 0, 6288774.0, -20905355.0],
    [2, 0, -1, 0, 1274027.0, -3699111.0],
    [2, 0, 0, 0, 658314.0, -2955968.0],
    [0, 0, 2, 0, 213618.0, -569925.0],
    [0, 1, 0, 0, -185116.0, 48888.0],
    [0, 0, 0, 2, -114332.0, -3149.0],
    [2, 0, -2, 0, 58793.0, 246158.0],
    [2, -1, -1, 0, 57066.0, -152138.0],
    [2, 0, 1, 0, 53322.0, -170733.0],
    [2, -1, 0, 0, 45758.0, -204586.0],
    [0, 1, -1, 0, -40923.0, -129620.0],
    [1, 0, 0, 0, -34720.0, 108743.0],
    [0, 1, 1, 0, -30383.0, 104755.0],
    [2, 0, 0, -2, 15327.0, 10321.0],
    [0, 0, 1, 2, -12528.0, 0.0],
    [0, 0, 1, -2, 10980.0, 79661.0],
    [4, 0, -1, 0, 10675.0, -34782.0],
    [0, 0, 3, 0, 10034.0, -23210.0],
    [4, 0, -2, 0, 8548.0, -21636.0],
    [2, 1, -1, 0, -7888.0, 24208.0],
    [2, 1, 0, 0, -6766.0, 30824.0],
    [1, 0, -1, 0, -5163.0, -8379.0],
    [1, 1, 0, 0, 4987.0, -16675.0],
    [2, -1, 1, 0, 4036.0, -12831.0],
    [2, 0, 2, 0, 3994.0, -10445.0],
    [4, 0, 0, 0, 3861.0, -11650.0],
    [2, 0, -3, 0, 3665.0, 14403.0],
    [0, 1, -2, 0, -2689.0, -7003.0],
    [2, 0, -1, 2, -2602.0, 0.0],
    [2, -1, -2, 0, 2390.0, 10056.0],
    [1, 0, 1, 0, -2348.0, 6322.0],
    [2, -2, 0, 0, 2236.0, -9884.0],
    [0, 1, 2, 0, -2120.0, 5751.0],
    [0, 2, 0, 0, -2069.0, 0.0],
    [2, -2, -1, 0, 2048.0, -4950.0],
    [2, 0, 1, -2, -1773.0, 4130.0],
    [2, 0, 0, 2, -1595.0, 0.0],
    [4, -1, -1, 0, 1215.0, -3958.0],
    [0, 0, 2, 2, -1110.0, 0.0],
    [3, 0, -1, 0, -892.0, 3258.0],
    [2, 1, 1, 0, -810.0, 2616.0],
    [4, -1, -2, 0, 759.0, -1897.0],
    [0, 2, -1, 0, -713.0, -2117.0],
    [2, 2, -1, 0, -700.0, 2354.0],
    [2, 1, -2, 0, 691.0, 0.0],
    [2, -1, 0, -2, 596.0, 0.0],
    [4, 0, 1, 0, 549.0, -1423.0],
    [0, 0, 4, 0, 537.0, -1117.0],
    [4, -1, 0, 0, 520.0, -1571.0],
    [1, 0, -2, 0, -487.0, -1739.0],
    [2, 1, 0, -2, -399.0, 0.0],
    [0, 0, 2, -2, -381.0, -4421.0],
    [1, 1, 1, 0, 351.0, 0.0],
    [3, 0, -2, 0, -340.0, 0.0],
    [4, 0, -3, 0, 330.0, 0.0],
    [2, -1, 2, 0, 327.0, 0.0],
    [0, 2, 1, 0, -323.0, 1165.0],
    [1, 1, -1, 0, 299.0, 0.0],
    [2, 0, 3, 0, 294.0, 0.0],
    [2, 0, -1, -2, 0.0, 8752.0]
]

# Tabla completa 47.B para sigma_b (de PyMeeus/Meeus)
SIGMA_B_TABLE = [
    [0, 0, 0, 1, 5128122.0],
    [0, 0, 1, 1, 280602.0],
    [0, 0, 1, -1, 277693.0],
    [2, 0, 0, -1, 173237.0],
    [2, 0, -1, 1, 55413.0],
    [2, 0, -1, -1, 46271.0],
    [2, 0, 0, 1, 32573.0],
    [0, 0, 2, 1, 17198.0],
    [2, 0, 1, -1, 9266.0],
    [0, 0, 2, -1, 8822.0],
    [2, -1, 0, -1, 8216.0],
    [2, 0, -2, -1, 4324.0],
    [2, 0, 1, 1, 4200.0],
    [2, 1, 0, -1, -3359.0],
    [2, -1, -1, 1, 2463.0],
    [2, -1, 0, 1, 2211.0],
    [2, -1, -1, -1, 2065.0],
    [0, 1, -1, -1, -1870.0],
    [4, 0, -1, -1, 1828.0],
    [0, 1, 0, 1, -1794.0],
    [0, 0, 0, 3, -1749.0],
    [0, 1, -1, 1, -1565.0],
    [1, 0, 0, 1, -1491.0],
    [0, 1, 1, 1, -1475.0],
    [0, 1, 1, -1, -1410.0],
    [0, 1, 0, -1, -1344.0],
    [1, 0, 0, -1, -1335.0],
    [0, 0, 3, 1, 1107.0],
    [4, 0, 0, -1, 1021.0],
    [4, 0, -1, 1, 833.0],
    [0, 0, 1, -3, 777.0],
    [4, 0, -2, 1, 671.0],
    [2, 0, 0, -3, 607.0],
    [2, 0, 2, -1, 596.0],
    [2, -1, 1, -1, 491.0],
    [2, 0, -2, 1, -451.0],
    [0, 0, 3, -1, 439.0],
    [2, 0, 2, 1, 422.0],
    [2, 0, -3, -1, 421.0],
    [2, 1, -1, 1, -366.0],
    [2, 1, 0, 1, -351.0],
    [4, 0, 0, 1, 331.0],
    [2, -1, 1, 1, 315.0],
    [2, -2, 0, -1, 302.0],
    [0, 0, 1, 3, -283.0],
    [2, 1, 1, -1, -229.0],
    [1, 1, 0, -1, 223.0],
    [1, 1, 0, 1, 223.0],
    [0, 1, -2, -1, -220.0],
    [2, 1, -1, -1, -220.0],
    [1, 0, 1, 1, -185.0],
    [2, -1, -2, -1, 181.0],
    [0, 1, 2, 1, -177.0],
    [4, 0, -2, -1, 176.0],
    [4, -1, -1, -1, 166.0],
    [1, 0, 1, -1, -164.0],
    [4, 0, 1, -1, 132.0],
    [1, 0, -1, -1, -119.0],
    [4, -1, 0, -1, 115.0],
    [2, -2, 0, 1, 107.0]
]

def _periodic_terms(D, M, Mp, F, T):
    """Calcula sigma_l, sigma_r, sigma_b con tablas completas y factor E."""
    E = 1 - 0.002516 * T - 0.0000074 * T**2
    E2 = E * E
    sigma_l = 0.0
    sigma_r = 0.0
    sigma_b = 0.0

    for d_coef, m, mp, f, l, r in SIGMA_LR_TABLE:
        factor = 1.0
        if abs(m) == 1:
            factor = E
        elif abs(m) == 2:
            factor = E2
        arg = d_coef * D + m * M + mp * Mp + f * F
        sigma_l += l * math.sin(math.radians(arg)) * factor
        sigma_r += r * math.cos(math.radians(arg)) * factor

    for d_coef, m, mp, f, b in SIGMA_B_TABLE:
        factor = 1.0
        if abs(m) == 1:
            factor = E
        elif abs(m) == 2:
            factor = E2
        arg = d_coef * D + m * M + mp * Mp + f * F
        sigma_b += b * math.sin(math.radians(arg)) * factor

    sigma_l /= 1000000.0  # a grados
    sigma_r *= 0.001  # a km
    sigma_b /= 1000000.0  # a grados

    return sigma_l, sigma_r, sigma_b

def _calculate_position_and_alt(t: datetime, lat_r: float, lon: float) -> tuple[float, float]:
    """Calcula alt, h0 para un tiempo dado t (ra no usado)."""
    jd = _julian_day(t)
    T = (jd - 2451545.0) / 36525.0

    # Argumentos fundamentales (en grados)
    Lp = _normalize_angle(218.3164477 + 481267.88123421 * T - 0.0015786 * T**2 + T**3 / 538841.0 - T**4 / 65194000.0)
    D = _normalize_angle(297.8501921 + 445267.1114034 * T - 0.0018819 * T**2 + T**3 / 545868.0 - T**4 / 113065000.0)
    M = _normalize_angle(357.5291092 + 35999.0502909 * T - 0.0001536 * T**2 + T**3 / 24490000.0)  # Anomalía Sol
    Mp = _normalize_angle(134.9633964 + 477198.8675055 * T + 0.0087414 * T**2 + T**3 / 69699.0 - T**4 / 14712000.0)
    F = _normalize_angle(93.2720950 + 483202.0175238 * T - 0.0036539 * T**2 - T**3 / 3526000.0 + T**4 / 863310000.0)
    Omega = _normalize_angle(125.04452 - 1934.136261 * T + 0.0020708 * T**2 + T**3 / 450000.0)  # Para nutación

    sigma_l, sigma_r, sigma_b = _periodic_terms(D, M, Mp, F, T)

    # Longitud eclíptica (con términos seculares adicionales)
    lambda_ = Lp + sigma_l + 0.003958 * math.sin(math.radians(119.75 + 131.849 * T)) + 0.000319 * math.sin(math.radians(53.09 + 479264.290 * T)) + 0.000024 * math.sin(math.radians(313.45 + 481266.484 * T))

    # Latitud eclíptica
    beta = sigma_b - 0.000024 * math.sin(math.radians(313.45 + 481266.484 * T - 2 * F))

    # Distancia (km)
    R = 385000.529 + sigma_r

    # Paralaje
    par = math.asin(6378.14 / R)

    # Obliquidad de la eclíptica
    eps = math.radians(23.439281 - 0.0000004 * T)

    # Nutación aproximada en longitud (arcsegundos a grados)
    delta_psi = (-17.20 * math.sin(math.radians(Omega)) - 1.32 * math.sin(math.radians(2 * (Lp - F))) + 0.23 * math.sin(math.radians(2 * Lp)) + 0.21 * math.sin(math.radians(2 * Omega))) / 3600.0

    # Posición aparente
    lambda_ += delta_psi

    # Conversión a RA y Dec
    lambda_r = math.radians(lambda_)
    beta_r = math.radians(beta)
    ra = math.atan2(math.sin(lambda_r) * math.cos(eps) - math.tan(beta_r) * math.sin(eps), math.cos(lambda_r))
    dec = math.asin(math.sin(beta_r) * math.cos(eps) + math.cos(beta_r) * math.sin(eps) * math.sin(lambda_r))

    # Umbral h0 (radianes) - CORREGIDO: par - sd - ref (positivo pequeño)
    sd = 0.2725076 * par  # Semidiámetro
    ref = math.radians(0.5667)  # Refracción media
    h0 = par - sd - ref

    # GMST y HA
    gmst = (280.46061837 + 360.98564736629 * (jd - 2451545.0) + 0.000387933 * T**2 - T**3 / 38710000.0) % 360.0
    lst = math.radians((gmst + lon) % 360.0)
    ha = lst - ra
    if ha < -math.pi: ha += 2 * math.pi
    elif ha > math.pi: ha -= 2 * math.pi

    # Altitud
    alt = math.asin(math.sin(lat_r) * math.sin(dec) + math.cos(lat_r) * math.cos(dec) * math.cos(ha))

    return alt, h0

def moon_rise_set(lat: float, lon: float, date_utc: date) -> Tuple[Optional[datetime], Optional[datetime]]:
    """
    Cálculo preciso de moonrise y moonset con series completas de Meeus (precisión ~1-2 min).
    Devuelve tuplas UTC (datetime tz-aware) o None si no ocurre en ese día.
    """
    lat_r = math.radians(lat)
    rise = None
    set_ = None
    dt = datetime(date_utc.year, date_utc.month, date_utc.day, tzinfo=timezone.utc)
    prev_t = None
    prev_alt = None

    # Paso grueso para detectar intervalos de cruce
    step_grueso = 1.0
    intervalos_rise = []
    intervalos_set = []
    for i in range(int(24 / step_grueso) + 1):
        hour = i * step_grueso
        t = dt + timedelta(hours=hour)
        alt, h0 = _calculate_position_and_alt(t, lat_r, lon)
        if prev_alt is not None:
            den = alt - prev_alt
            if abs(den) < 1e-12:
                continue  # Evita división por cero en detección grueso
            if prev_alt < h0 and alt >= h0:
                intervalos_rise.append((prev_t, t, prev_alt, alt))
            elif prev_alt >= h0 and alt < h0:
                intervalos_set.append((prev_t, t, prev_alt, alt))
        prev_t = t
        prev_alt = alt

    # Función de refinamiento con bisección y guards
    def refine_event(start_t: datetime, end_t: datetime, start_alt: float, end_alt: float, is_rise: bool) -> datetime:
        for _ in range(10):  # Iteraciones para ~1 seg precisión
            mid_t = start_t + (end_t - start_t) / 2
            mid_alt, mid_h0 = _calculate_position_and_alt(mid_t, lat_r, lon)
            den = mid_alt - start_alt if is_rise else mid_alt - end_alt  # Aproximado para check
            if abs(den) < 1e-12:
                return mid_t  # Caso plano, toma medio
            if (is_rise and mid_alt < mid_h0) or (not is_rise and mid_alt >= mid_h0):
                start_t, start_alt = mid_t, mid_alt
            else:
                end_t, end_alt = mid_t, mid_alt
        return start_t + (end_t - start_t) / 2

    # Refina el primero detectado (típicamente uno por evento por día)
    if intervalos_rise and rise is None:
        start_t, end_t, start_alt, end_alt = intervalos_rise[0]
        rise = refine_event(start_t, end_t, start_alt, end_alt, True)
    if intervalos_set and set_ is None:
        start_t, end_t, start_alt, end_alt = intervalos_set[0]
        set_ = refine_event(start_t, end_t, start_alt, end_alt, False)

    # Break implícito no necesario aquí, ya que el loop grueso es corto
    return rise, set_