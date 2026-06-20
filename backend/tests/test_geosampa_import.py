from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[2] / "tools"))

from geosampa_import import canopy_patch_from_feature, green_area_from_shape_record, tree_point_from_feature, write_canopy_sqlite
from treecheck_api.data_repository import canopy_patches_from_sqlite


def test_tree_point_from_geosampa_point_feature() -> None:
    feature = {
        "type": "Feature",
        "id": "arvore.1",
        "properties": {"nome_popular": "Ipe"},
        "geometry": {"type": "Point", "coordinates": [-46.65, -23.56]},
    }

    tree = tree_point_from_feature(feature)

    assert tree == {
        "lat": -23.56,
        "lng": -46.65,
        "species": "Ipe",
        "source_id": "arvore.1",
    }


def test_canopy_patch_from_polygon_feature() -> None:
    feature = {
        "type": "Feature",
        "properties": {"objectid": 7},
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [-46.6500, -23.5600],
                [-46.6490, -23.5600],
                [-46.6490, -23.5590],
                [-46.6500, -23.5590],
                [-46.6500, -23.5600],
            ]],
        },
    }

    patch = canopy_patch_from_feature(feature)

    assert patch is not None
    assert patch["source_id"] == 7
    assert patch["radius_m"] > 8


def test_green_area_from_shape_record() -> None:
    class Shape:
        bbox = [328170.0, 7393841.0, 328220.0, 7393915.0]
        parts = [0]
        points = [
            (328170.0, 7393841.0),
            (328220.0, 7393841.0),
            (328220.0, 7393915.0),
            (328170.0, 7393915.0),
            (328170.0, 7393841.0),
        ]

    class Transformer:
        def transform(self, x: float, y: float) -> tuple[float, float]:
            return -46.65 + (x - 328170.0) / 100000, -23.56 + (y - 7393841.0) / 100000

    area = green_area_from_shape_record(
        {
            "index": 1,
            "shape": Shape(),
            "transformer": Transformer(),
            "properties": {"categoria": "PC", "nome": "CELSO DELMANTO", "cd_identif": 30752},
        },
    )

    assert area is not None
    assert area["name"] == "PC CELSO DELMANTO"
    assert area["source_id"] == 30752


def test_write_canopy_sqlite_returns_indexed_polygons(tmp_path) -> None:
    db_path = tmp_path / "canopy.sqlite"
    patch = {
        "lat": -23.56,
        "lng": -46.65,
        "radius_m": 20,
        "source_id": 7,
        "bounds": (-46.6502, -23.5602, -46.6498, -23.5598),
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [-46.6502, -23.5602],
                [-46.6498, -23.5602],
                [-46.6498, -23.5598],
                [-46.6502, -23.5598],
                [-46.6502, -23.5602],
            ]],
        },
    }

    write_canopy_sqlite(db_path, [patch])

    patches = canopy_patches_from_sqlite(db_path, -23.56, -46.65, 50)
    assert len(patches) == 1
    assert patches[0]["source_id"] == "7"
    assert patches[0]["geometry"]["type"] == "Polygon"
