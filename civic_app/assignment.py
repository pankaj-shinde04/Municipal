import math

def calculate_haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance in kilometers between two points 
    on the earth (specified in decimal degrees).
    """
    # Earth radius in kilometers
    R = 6371.0

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (math.sin(dlat / 2.0) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2.0) ** 2)
    
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    distance = R * c
    return distance

def find_nearest_department_worker(department, complaint_lat, complaint_lon):
    """
    Finds the geographically nearest worker belonging strictly to the specified department.
    - department: Department model instance
    - complaint_lat: float / Decimal latitude of issue
    - complaint_lon: float / Decimal longitude of issue
    Returns (nearest_worker_user, min_distance_km) or (None, None).
    """
    from django.contrib.auth.models import User

    if complaint_lat is None or complaint_lon is None:
        return None, None

    try:
        c_lat = float(complaint_lat)
        c_lon = float(complaint_lon)
    except (ValueError, TypeError):
        return None, None

    # Filter candidates strictly belonging to the target department with role 'worker'
    candidates = User.objects.filter(
        profile__role='worker',
        profile__department=department,
        profile__base_latitude__isnull=False,
        profile__base_longitude__isnull=False
    ).select_related('profile')

    nearest_worker = None
    min_distance = float('inf')

    for worker in candidates:
        try:
            w_lat = float(worker.profile.base_latitude)
            w_lon = float(worker.profile.base_longitude)
            dist = calculate_haversine_distance(c_lat, c_lon, w_lat, w_lon)
            if dist < min_distance:
                min_distance = dist
                nearest_worker = worker
        except (ValueError, TypeError):
            continue

    if nearest_worker:
        return nearest_worker, round(min_distance, 2)
    return None, None
