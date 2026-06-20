from treecheck_api.spatial import estimate_canopy_percent, point_hits_patch


def test_polygon_patch_uses_real_geometry_not_center_radius() -> None:
    patch = {
        "lat": 0.0,
        "lng": 0.0,
        "radius_m": 1000,
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [0.0, 0.0],
                [0.0001, 0.0],
                [0.0001, 0.0001],
                [0.0, 0.0001],
                [0.0, 0.0],
            ]],
        },
    }

    assert point_hits_patch(0.00005, 0.00005, patch)
    assert not point_hits_patch(0.001, 0.001, patch)


def test_estimate_canopy_percent_with_polygon_stays_bounded() -> None:
    polygon_patch = {
        "lat": 0.0,
        "lng": 0.0,
        "radius_m": 300,
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [-0.0002, -0.0002],
                [0.0002, -0.0002],
                [0.0002, 0.0002],
                [-0.0002, 0.0002],
                [-0.0002, -0.0002],
            ]],
        },
    }

    value = estimate_canopy_percent(0.0, 0.0, 300, [polygon_patch])

    assert 0 < value < 10
