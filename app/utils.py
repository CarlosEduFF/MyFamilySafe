import math
import secrets


def generate_invite_code() -> str:
    """6 bytes em hex = 12 chars, igual a generateInviteCode() (handler.go:262)."""
    return secrets.token_hex(6)


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distância em metros. Port de resources.go:469."""
    earth_radius = 6371000.0

    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)

    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
        * math.sin(d_lon / 2) ** 2
    )
    return earth_radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


