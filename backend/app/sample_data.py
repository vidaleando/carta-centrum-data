"""Static sample GeoJSON, served by the legacy ?source=sample endpoint and in demo mode."""

SAMPLE_FEATURE_COLLECTION = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {
                "name": "Sample Point 1",
                "description": "This is a sample point",
                "category": "point",
            },
            "geometry": {"type": "Point", "coordinates": [-74.0060, 40.7128]},  # New York
        },
        {
            "type": "Feature",
            "properties": {
                "name": "Sample Point 2",
                "description": "Another sample point",
                "category": "point",
            },
            "geometry": {"type": "Point", "coordinates": [-0.1276, 51.5074]},  # London
        },
        {
            "type": "Feature",
            "properties": {
                "name": "Sample Point 3",
                "description": "Third sample point",
                "category": "point",
            },
            "geometry": {"type": "Point", "coordinates": [139.6917, 35.6895]},  # Tokyo
        },
        {
            "type": "Feature",
            "properties": {
                "name": "Sample Polygon",
                "description": "A sample polygon area",
                "category": "polygon",
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [2.3522, 48.8566],  # Paris area
                    [2.3622, 48.8566],
                    [2.3622, 48.8666],
                    [2.3522, 48.8666],
                    [2.3522, 48.8566],
                ]],
            },
        },
    ],
}
