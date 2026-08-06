from api.visualizer import _color_for_sku, render_isometric_svg, render_orthographic_svg

PLAN = [
    {"sku": "MUG-001", "name": "Mug", "position": [0, 0, 0], "dims": [110, 90, 95]},
    {"sku": "BOOK-001", "name": "Book", "position": [110, 0, 0], "dims": [198, 129, 20]},
]
CONTAINER_DIMS = (350, 250, 200)


def test_isometric_svg_contains_one_svg_root():
    svg = render_isometric_svg(CONTAINER_DIMS, PLAN)
    assert svg.count("<svg") == 1
    assert svg.strip().endswith("</svg>")


def test_isometric_svg_draws_three_faces_per_item():
    svg = render_isometric_svg(CONTAINER_DIMS, PLAN)
    # top, right, left face polygon per item = 3 * len(PLAN)
    assert svg.count("<polygon") == 3 * len(PLAN)


def test_isometric_svg_handles_empty_plan():
    svg = render_isometric_svg(CONTAINER_DIMS, [])
    assert "<svg" in svg
    assert svg.count("<polygon") == 0


def test_color_for_sku_is_deterministic():
    assert _color_for_sku("MUG-001") == _color_for_sku("MUG-001")


def test_color_for_sku_differs_across_skus():
    # Not a mathematical guarantee (hash collisions are possible) but
    # true for our real catalogue skus, and a useful smoke check.
    assert _color_for_sku("MUG-001") != _color_for_sku("BOOK-001")


def test_orthographic_svg_draws_one_rect_per_item_plus_container_outline():
    svg = render_orthographic_svg(CONTAINER_DIMS, PLAN, "top")
    assert svg.count("<rect") == len(PLAN) + 1  # +1 for the container outline


def test_orthographic_svg_supports_all_three_views():
    for view in ("top", "front", "side"):
        svg = render_orthographic_svg(CONTAINER_DIMS, PLAN, view)
        assert "<svg" in svg


def test_orthographic_svg_empty_plan_still_draws_container():
    svg = render_orthographic_svg(CONTAINER_DIMS, [], "top")
    assert svg.count("<rect") == 1
