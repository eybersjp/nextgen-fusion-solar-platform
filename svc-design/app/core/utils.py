"""Utility functions for the Design Service.

This module contains common utility functions for data processing,
validation, formatting, and other helper operations.
"""

import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union

import numpy as np
from geojson import Feature, FeatureCollection, Point, Polygon
from shapely.geometry import Point as ShapelyPoint
from shapely.geometry import Polygon as ShapelyPolygon
from shapely.geometry import shape
from shapely.ops import transform
from pyproj import Transformer


# UUID Utilities
def generate_uuid() -> uuid.UUID:
    """Generate a new UUID4.
    
    Returns:
        uuid.UUID: New UUID
    """
    return uuid.uuid4()


def is_valid_uuid(value: str) -> bool:
    """Check if string is a valid UUID.
    
    Args:
        value: String to check
        
    Returns:
        bool: True if valid UUID
    """
    try:
        uuid.UUID(value)
        return True
    except (ValueError, TypeError):
        return False


# Date/Time Utilities
def utc_now() -> datetime:
    """Get current UTC datetime.
    
    Returns:
        datetime: Current UTC datetime
    """
    return datetime.now(timezone.utc)


def to_utc(dt: datetime) -> datetime:
    """Convert datetime to UTC.
    
    Args:
        dt: Datetime to convert
        
    Returns:
        datetime: UTC datetime
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def format_datetime(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S UTC") -> str:
    """Format datetime as string.
    
    Args:
        dt: Datetime to format
        format_str: Format string
        
    Returns:
        str: Formatted datetime string
    """
    return dt.strftime(format_str)


def parse_datetime(dt_str: str) -> datetime:
    """Parse datetime string.
    
    Args:
        dt_str: Datetime string (ISO format)
        
    Returns:
        datetime: Parsed datetime
        
    Raises:
        ValueError: If datetime string is invalid
    """
    try:
        # Try parsing ISO format with timezone
        return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
    except ValueError:
        # Try parsing without timezone
        dt = datetime.fromisoformat(dt_str)
        return dt.replace(tzinfo=timezone.utc)


# String Utilities
def slugify(text: str) -> str:
    """Convert text to URL-friendly slug.
    
    Args:
        text: Text to slugify
        
    Returns:
        str: Slugified text
    """
    # Convert to lowercase and replace spaces/special chars with hyphens
    slug = re.sub(r'[^\w\s-]', '', text.lower())
    slug = re.sub(r'[-\s]+', '-', slug)
    return slug.strip('-')


def truncate_string(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate string to maximum length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        str: Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def clean_string(text: str) -> str:
    """Clean string by removing extra whitespace.
    
    Args:
        text: Text to clean
        
    Returns:
        str: Cleaned text
    """
    return re.sub(r'\s+', ' ', text.strip())


def mask_sensitive_data(text: str, mask_char: str = "*", visible_chars: int = 4) -> str:
    """Mask sensitive data in string.
    
    Args:
        text: Text to mask
        mask_char: Character to use for masking
        visible_chars: Number of characters to keep visible at end
        
    Returns:
        str: Masked text
    """
    if len(text) <= visible_chars:
        return mask_char * len(text)
    
    masked_length = len(text) - visible_chars
    return mask_char * masked_length + text[-visible_chars:]


# Numeric Utilities
def round_decimal(value: Union[float, Decimal], places: int = 2) -> Decimal:
    """Round decimal to specified places.
    
    Args:
        value: Value to round
        places: Number of decimal places
        
    Returns:
        Decimal: Rounded decimal
    """
    if isinstance(value, float):
        value = Decimal(str(value))
    elif not isinstance(value, Decimal):
        value = Decimal(value)
    
    return value.quantize(Decimal('0.' + '0' * places))


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safely divide two numbers.
    
    Args:
        numerator: Numerator
        denominator: Denominator
        default: Default value if division by zero
        
    Returns:
        float: Division result or default
    """
    if denominator == 0:
        return default
    return numerator / denominator


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp value between min and max.
    
    Args:
        value: Value to clamp
        min_val: Minimum value
        max_val: Maximum value
        
    Returns:
        float: Clamped value
    """
    return max(min_val, min(value, max_val))


def percentage(value: float, total: float, places: int = 2) -> float:
    """Calculate percentage.
    
    Args:
        value: Value
        total: Total
        places: Decimal places
        
    Returns:
        float: Percentage
    """
    if total == 0:
        return 0.0
    return round((value / total) * 100, places)


# Data Structure Utilities
def deep_merge(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge two dictionaries.
    
    Args:
        dict1: First dictionary
        dict2: Second dictionary
        
    Returns:
        Dict[str, Any]: Merged dictionary
    """
    result = dict1.copy()
    
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    
    return result


def flatten_dict(data: Dict[str, Any], separator: str = ".", prefix: str = "") -> Dict[str, Any]:
    """Flatten nested dictionary.
    
    Args:
        data: Dictionary to flatten
        separator: Key separator
        prefix: Key prefix
        
    Returns:
        Dict[str, Any]: Flattened dictionary
    """
    result = {}
    
    for key, value in data.items():
        new_key = f"{prefix}{separator}{key}" if prefix else key
        
        if isinstance(value, dict):
            result.update(flatten_dict(value, separator, new_key))
        else:
            result[new_key] = value
    
    return result


def remove_none_values(data: Dict[str, Any]) -> Dict[str, Any]:
    """Remove None values from dictionary.
    
    Args:
        data: Dictionary to clean
        
    Returns:
        Dict[str, Any]: Dictionary without None values
    """
    return {k: v for k, v in data.items() if v is not None}


def pick_keys(data: Dict[str, Any], keys: List[str]) -> Dict[str, Any]:
    """Pick specific keys from dictionary.
    
    Args:
        data: Source dictionary
        keys: Keys to pick
        
    Returns:
        Dict[str, Any]: Dictionary with picked keys
    """
    return {k: data[k] for k in keys if k in data}


def omit_keys(data: Dict[str, Any], keys: List[str]) -> Dict[str, Any]:
    """Omit specific keys from dictionary.
    
    Args:
        data: Source dictionary
        keys: Keys to omit
        
    Returns:
        Dict[str, Any]: Dictionary without omitted keys
    """
    return {k: v for k, v in data.items() if k not in keys}


# Hashing Utilities
def generate_hash(data: Union[str, bytes, Dict[str, Any]], algorithm: str = "sha256") -> str:
    """Generate hash of data.
    
    Args:
        data: Data to hash
        algorithm: Hash algorithm
        
    Returns:
        str: Hash string
    """
    if isinstance(data, dict):
        data = json.dumps(data, sort_keys=True)
    
    if isinstance(data, str):
        data = data.encode('utf-8')
    
    hash_obj = hashlib.new(algorithm)
    hash_obj.update(data)
    return hash_obj.hexdigest()


def generate_checksum(data: Union[str, bytes]) -> str:
    """Generate MD5 checksum.
    
    Args:
        data: Data to checksum
        
    Returns:
        str: Checksum string
    """
    return generate_hash(data, "md5")


# Geometry Utilities
def create_point_geojson(longitude: float, latitude: float, properties: Optional[Dict] = None) -> Feature:
    """Create GeoJSON point feature.
    
    Args:
        longitude: Longitude
        latitude: Latitude
        properties: Feature properties
        
    Returns:
        Feature: GeoJSON point feature
    """
    return Feature(
        geometry=Point((longitude, latitude)),
        properties=properties or {}
    )


def create_polygon_geojson(coordinates: List[List[float]], properties: Optional[Dict] = None) -> Feature:
    """Create GeoJSON polygon feature.
    
    Args:
        coordinates: Polygon coordinates
        properties: Feature properties
        
    Returns:
        Feature: GeoJSON polygon feature
    """
    return Feature(
        geometry=Polygon([coordinates]),
        properties=properties or {}
    )


def transform_coordinates(coordinates: List[List[float]], from_crs: str, to_crs: str) -> List[List[float]]:
    """Transform coordinates between CRS.
    
    Args:
        coordinates: Coordinates to transform
        from_crs: Source CRS
        to_crs: Target CRS
        
    Returns:
        List[List[float]]: Transformed coordinates
    """
    transformer = Transformer.from_crs(from_crs, to_crs, always_xy=True)
    
    transformed = []
    for coord in coordinates:
        x, y = transformer.transform(coord[0], coord[1])
        transformed.append([x, y])
    
    return transformed


def calculate_polygon_area(coordinates: List[List[float]]) -> float:
    """Calculate polygon area in square meters.
    
    Args:
        coordinates: Polygon coordinates (longitude, latitude)
        
    Returns:
        float: Area in square meters
    """
    # Create Shapely polygon
    polygon = ShapelyPolygon(coordinates)
    
    # Transform to appropriate projected CRS for area calculation
    # Using Web Mercator (EPSG:3857) as approximation
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
    projected_polygon = transform(transformer.transform, polygon)
    
    return projected_polygon.area


def calculate_distance(point1: List[float], point2: List[float]) -> float:
    """Calculate distance between two points in meters.
    
    Args:
        point1: First point [longitude, latitude]
        point2: Second point [longitude, latitude]
        
    Returns:
        float: Distance in meters
    """
    # Create Shapely points
    p1 = ShapelyPoint(point1)
    p2 = ShapelyPoint(point2)
    
    # Transform to Web Mercator for distance calculation
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
    p1_proj = transform(transformer.transform, p1)
    p2_proj = transform(transformer.transform, p2)
    
    return p1_proj.distance(p2_proj)


def is_point_in_polygon(point: List[float], polygon_coords: List[List[float]]) -> bool:
    """Check if point is inside polygon.
    
    Args:
        point: Point coordinates [longitude, latitude]
        polygon_coords: Polygon coordinates
        
    Returns:
        bool: True if point is inside polygon
    """
    point_geom = ShapelyPoint(point)
    polygon_geom = ShapelyPolygon(polygon_coords)
    
    return polygon_geom.contains(point_geom)


# Solar Calculation Utilities
def calculate_solar_azimuth(latitude: float, day_of_year: int, hour: float) -> float:
    """Calculate solar azimuth angle.
    
    Args:
        latitude: Latitude in degrees
        day_of_year: Day of year (1-365)
        hour: Hour of day (0-24)
        
    Returns:
        float: Solar azimuth angle in degrees
    """
    # Simplified solar position calculation
    lat_rad = np.radians(latitude)
    
    # Solar declination
    declination = 23.45 * np.sin(np.radians(360 * (284 + day_of_year) / 365))
    decl_rad = np.radians(declination)
    
    # Hour angle
    hour_angle = 15 * (hour - 12)
    hour_rad = np.radians(hour_angle)
    
    # Solar elevation
    elevation = np.arcsin(
        np.sin(decl_rad) * np.sin(lat_rad) +
        np.cos(decl_rad) * np.cos(lat_rad) * np.cos(hour_rad)
    )
    
    # Solar azimuth
    azimuth = np.arctan2(
        np.sin(hour_rad),
        np.cos(hour_rad) * np.sin(lat_rad) - np.tan(decl_rad) * np.cos(lat_rad)
    )
    
    return np.degrees(azimuth)


def calculate_solar_elevation(latitude: float, day_of_year: int, hour: float) -> float:
    """Calculate solar elevation angle.
    
    Args:
        latitude: Latitude in degrees
        day_of_year: Day of year (1-365)
        hour: Hour of day (0-24)
        
    Returns:
        float: Solar elevation angle in degrees
    """
    lat_rad = np.radians(latitude)
    
    # Solar declination
    declination = 23.45 * np.sin(np.radians(360 * (284 + day_of_year) / 365))
    decl_rad = np.radians(declination)
    
    # Hour angle
    hour_angle = 15 * (hour - 12)
    hour_rad = np.radians(hour_angle)
    
    # Solar elevation
    elevation = np.arcsin(
        np.sin(decl_rad) * np.sin(lat_rad) +
        np.cos(decl_rad) * np.cos(lat_rad) * np.cos(hour_rad)
    )
    
    return np.degrees(elevation)


def calculate_optimal_tilt(latitude: float) -> float:
    """Calculate optimal tilt angle for solar panels.
    
    Args:
        latitude: Latitude in degrees
        
    Returns:
        float: Optimal tilt angle in degrees
    """
    # Simple rule: tilt = latitude for maximum annual energy
    return abs(latitude)


def calculate_panel_spacing(panel_height: float, tilt_angle: float, latitude: float) -> float:
    """Calculate minimum spacing between panel rows to avoid shading.
    
    Args:
        panel_height: Panel height in meters
        tilt_angle: Panel tilt angle in degrees
        latitude: Site latitude in degrees
        
    Returns:
        float: Minimum spacing in meters
    """
    # Calculate shadow length at winter solstice (worst case)
    winter_elevation = calculate_solar_elevation(latitude, 355, 12)  # Dec 21, noon
    
    if winter_elevation <= 0:
        return float('inf')  # No sun, infinite spacing needed
    
    # Shadow length from tilted panel
    panel_projection = panel_height * np.cos(np.radians(tilt_angle))
    shadow_length = panel_projection / np.tan(np.radians(winter_elevation))
    
    # Add safety factor
    return shadow_length * 1.2


# Validation Utilities
def validate_email(email: str) -> bool:
    """Validate email address format.
    
    Args:
        email: Email address
        
    Returns:
        bool: True if valid email
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_phone(phone: str) -> bool:
    """Validate phone number format.
    
    Args:
        phone: Phone number
        
    Returns:
        bool: True if valid phone
    """
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', phone)
    
    # Check if it's a reasonable length (7-15 digits)
    return 7 <= len(digits) <= 15


def validate_coordinates(longitude: float, latitude: float) -> bool:
    """Validate geographic coordinates.
    
    Args:
        longitude: Longitude
        latitude: Latitude
        
    Returns:
        bool: True if valid coordinates
    """
    return -180 <= longitude <= 180 and -90 <= latitude <= 90


def validate_positive_number(value: Union[int, float]) -> bool:
    """Validate positive number.
    
    Args:
        value: Number to validate
        
    Returns:
        bool: True if positive
    """
    try:
        return float(value) > 0
    except (ValueError, TypeError):
        return False


# File Utilities
def get_file_extension(filename: str) -> str:
    """Get file extension.
    
    Args:
        filename: Filename
        
    Returns:
        str: File extension (without dot)
    """
    return filename.split('.')[-1].lower() if '.' in filename else ''


def is_image_file(filename: str) -> bool:
    """Check if file is an image.
    
    Args:
        filename: Filename
        
    Returns:
        bool: True if image file
    """
    image_extensions = {'jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg', 'webp'}
    return get_file_extension(filename) in image_extensions


def is_document_file(filename: str) -> bool:
    """Check if file is a document.
    
    Args:
        filename: Filename
        
    Returns:
        bool: True if document file
    """
    doc_extensions = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'csv'}
    return get_file_extension(filename) in doc_extensions


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        str: Formatted size string
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size = float(size_bytes)
    
    while size >= 1024.0 and i < len(size_names) - 1:
        size /= 1024.0
        i += 1
    
    return f"{size:.1f} {size_names[i]}"