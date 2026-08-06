"""
Server-rendered SVG packing visualizer.

Pure Python, no charting library, no JS — every coordinate below is
computed by hand from the recommendation's `plan` (a list of
{sku, name, position, dims} dicts, same shape the API returns). That
makes this ~150 lines you can walk an interviewer through line by line,
instead of a black-box dependency.

Two projections are generated:
  - `render_isometric_svg`: the classic 2:1 "game tile" isometric
    projection — shows all 3 dimensions at once. Each cuboid's top,
    right and left faces get progressively darker shading to fake
    lighting without any actual 3D rendering.
  - `render_orthographic_svg`: flat top/front/side 2D projections
    (just drop one axis) — less pretty, but lets you read exact
    overlaps and gaps at a glance, which the isometric view can hide.
"""

import colorsys
import hashlib
import math

ISO_COS30 = math.cos(math.radians(30))
ISO_SIN30 = math.sin(math.radians(30))


def _color_for_sku(sku: str) -> tuple[float, float, float]:
    """Deterministic pastel RGB (0-255 floats) per SKU, so the same
    product always renders the same color across a session."""
    digest = hashlib.md5(sku.encode()).hexdigest()
    hue = (int(digest[:8], 16) % 360) / 360.0
    r, g, b = colorsys.hls_to_rgb(hue, 0.68, 0.55)
    return (r * 255, g * 255, b * 255)


def _shade(rgb: tuple[float, float, float], factor: float) -> str:
    r, g, b = (max(0, min(255, c * factor)) for c in rgb)
    return f"rgb({r:.0f},{g:.0f},{b:.0f})"


def _iso_project(x: float, y: float, z: float, scale: float) -> tuple[float, float]:
    px = (x - y) * ISO_COS30 * scale
    py = (x + y) * ISO_SIN30 * scale - z * scale
    return px, py


def _iso_polygon(points: list[tuple[float, float]], fill: str, stroke: str = "#00000030") -> str:
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    return f'<polygon points="{pts}" fill="{fill}" stroke="{stroke}" stroke-width="0.6" />'


def render_isometric_svg(container_dims: tuple[int, int, int], plan: list[dict],
                          scale: float = 0.45) -> str:
    """
    `container_dims` = (length, width, height) in mm.
    `plan` = list of {"sku", "name", "position": [x,y,z], "dims": [l,w,h]}.
    """
    L, W, H = container_dims

    # Project the container's 8 corners first, purely to size the canvas.
    corners = [_iso_project(x, y, z, scale)
               for x in (0, L) for y in (0, W) for z in (0, H)]
    xs = [c[0] for c in corners]
    ys = [c[1] for c in corners]
    margin = 20
    min_x, max_x = min(xs) - margin, max(xs) + margin
    min_y, max_y = min(ys) - margin, max(ys) + margin
    svg_w, svg_h = max_x - min_x, max_y - min_y

    def p(x, y, z):
        px, py = _iso_project(x, y, z, scale)
        return (px - min_x, py - min_y)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_w:.0f} {svg_h:.0f}" '
        f'width="100%" height="auto" font-family="ui-monospace, monospace">'
    ]

    # Container wireframe: draw the 3 back edges + the 9 edges that
    # outline the visible top/right/left faces.
    edges = [
        ((0, 0, 0), (L, 0, 0)), ((0, 0, 0), (0, W, 0)), ((0, 0, 0), (0, 0, H)),
        ((L, 0, 0), (L, W, 0)), ((L, 0, 0), (L, 0, H)),
        ((0, W, 0), (L, W, 0)), ((0, W, 0), (0, W, H)),
        ((0, 0, H), (L, 0, H)), ((0, 0, H), (0, W, H)),
        ((L, W, 0), (L, W, H)), ((L, 0, H), (L, W, H)), ((0, W, H), (L, W, H)),
    ]
    for (x1, y1, z1), (x2, y2, z2) in edges:
        ax, ay = p(x1, y1, z1)
        bx, by = p(x2, y2, z2)
        parts.append(f'<line x1="{ax:.1f}" y1="{ay:.1f}" x2="{bx:.1f}" y2="{by:.1f}" '
                      f'stroke="#94a3b8" stroke-width="1" stroke-dasharray="3,2" />')

    # Painter's algorithm: draw items farthest-from-camera first so
    # nearer ones correctly occlude them. See module docstring.
    ordered = sorted(plan, key=lambda item: sum(item["position"]))

    for item in ordered:
        x, y, z = item["position"]
        l, w, h = item["dims"]
        rgb = _color_for_sku(item["sku"])

        top = [p(x, y, z + h), p(x + l, y, z + h), p(x + l, y + w, z + h), p(x, y + w, z + h)]
        right = [p(x + l, y, z), p(x + l, y + w, z), p(x + l, y + w, z + h), p(x + l, y, z + h)]
        left = [p(x, y + w, z), p(x + l, y + w, z), p(x + l, y + w, z + h), p(x, y + w, z + h)]

        parts.append(_iso_polygon(top, _shade(rgb, 1.05)))
        parts.append(_iso_polygon(right, _shade(rgb, 0.80)))
        parts.append(_iso_polygon(left, _shade(rgb, 0.60)))

    parts.append("</svg>")
    return "\n".join(parts)


_AXIS_VIEWS = {
    # view_name: (axis1_index, axis2_index, axis1_len_index, axis2_len_index, label)
    "top": (0, 1, 0, 1, "Top view (X × Y)"),
    "front": (0, 2, 0, 2, "Front view (X × Z)"),
    "side": (1, 2, 1, 2, "Side view (Y × Z)"),
}


def render_orthographic_svg(container_dims: tuple[int, int, int], plan: list[dict],
                             view: str, scale: float = 0.5) -> str:
    """Flat 2D projection dropping one axis. `view` is 'top', 'front', or 'side'."""
    ai, aj, li, lj = _AXIS_VIEWS[view][:4]
    dims_by_axis = {0: container_dims[0], 1: container_dims[1], 2: container_dims[2]}
    width = dims_by_axis[ai] * scale
    height = dims_by_axis[aj] * scale
    margin = 10

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width + 2 * margin:.0f} {height + 2 * margin:.0f}" '
        f'width="100%" height="auto" font-family="ui-monospace, monospace">',
        f'<rect x="{margin}" y="{margin}" width="{width:.1f}" height="{height:.1f}" '
        f'fill="none" stroke="#94a3b8" stroke-width="1.5" />',
    ]

    for item in plan:
        pos = item["position"]
        dims = item["dims"]
        rgb = _color_for_sku(item["sku"])
        rx = margin + pos[ai] * scale
        ry = margin + pos[aj] * scale
        rw = dims[li] * scale
        rh = dims[lj] * scale
        parts.append(
            f'<rect x="{rx:.1f}" y="{ry:.1f}" width="{rw:.1f}" height="{rh:.1f}" '
            f'fill="{_shade(rgb, 0.9)}" stroke="#00000040" stroke-width="0.6" />'
        )

    parts.append("</svg>")
    return "\n".join(parts)
