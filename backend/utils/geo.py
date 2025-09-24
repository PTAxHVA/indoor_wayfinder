import math
from typing import List, Tuple

Point = Tuple[float, float]


def signed_turn_angle_screen(
    p1: Tuple[float, float], p2: Tuple[float, float], p3: Tuple[float, float]
) -> float:
    """
    Góc rẽ tại p2 theo hệ toạ độ màn hình (x tăng sang phải, y tăng xuống).
    > 0  : quay theo chiều kim đồng hồ (CW) => rẽ phải
    < 0  : quay ngược chiều kim đồng hồ (CCW) => rẽ trái
    Trả về độ trong khoảng (-180, 180].
    """
    theta1 = math.atan2(p2[1] - p1[1], p2[0] - p1[0])  # dy, dx
    theta2 = math.atan2(p3[1] - p2[1], p3[0] - p2[0])
    d = math.degrees(theta2 - theta1)
    while d <= -180.0:
        d += 360.0
    while d > 180.0:
        d -= 360.0
    return d


def polyline_length(poly: List[Point]) -> float:
    if not poly or len(poly) < 2:
        return 0.0
    total = 0.0
    for i in range(1, len(poly)):
        x1, y1 = poly[i - 1]
        x2, y2 = poly[i]
        total += math.hypot(x2 - x1, y2 - y1)
    return total


def angle_signed(p1: Point, p2: Point, p3: Point) -> float:
    """
    Góc rẽ tại p2: >0 là rẽ trái, <0 là rẽ phải, tính theo độ (-180..180)
    """
    vx1, vy1 = (p2[0] - p1[0], p2[1] - p1[1])
    vx2, vy2 = (p3[0] - p2[0], p3[1] - p2[1])
    dot = vx1 * vx2 + vy1 * vy2
    det = vx1 * vy2 - vy1 * vx2
    ang = math.degrees(math.atan2(det, dot))
    return ang


def merge_polylines(polys: List[List[Point]]) -> List[Point]:
    """Ghép nhiều polyline theo thứ tự cạnh. Loại bỏ điểm trùng đầu-cuối giữa các đoạn."""
    if not polys:
        return []
    out = list(polys[0])
    for poly in polys[1:]:
        if not poly:
            continue
        # tránh lặp điểm đầu
        start_idx = 1 if out and poly and out[-1] == poly[0] else 0
        out.extend(poly[start_idx:])
    return out


def initial_heading_text(p0: tuple[float, float], p1: tuple[float, float]) -> str:
    """
    Trả về câu mô tả hướng ban đầu dựa trên vector p0->p1 theo hệ toạ độ màn hình (y tăng xuống).
    Ưu tiên 4 hướng chính: trái->phải, phải->trái, trên->xuống, dưới->lên.
    """
    dx = p1[0] - p0[0]
    dy = p1[1] - p0[1]
    if abs(dx) >= abs(dy):
        # thiên về ngang
        if dx > 0:
            return "từ trái sang phải"
        elif dx < 0:
            return "từ phải sang trái"
        else:
            # dx == 0 (hiếm), fallback theo dy
            if dy > 0:
                return "từ trên xuống"
            elif dy < 0:
                return "từ dưới lên"
            else:
                return "đứng yên"
    else:
        # thiên về dọc
        if dy > 0:
            return "từ trên xuống"
        elif dy < 0:
            return "từ dưới lên"
        else:
            # dy == 0 (hiếm), fallback theo dx
            if dx > 0:
                return "từ trái sang phải"
            elif dx < 0:
                return "từ phải sang trái"
            else:
                return "đứng yên"


def dist(a: Point, b: Point) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def almost_same(a: Point, b: Point, tol: float = 1.5) -> bool:
    return dist(a, b) <= tol


def orient_polyline_to_uv(poly: List[Point], u_pos: Point, v_pos: Point) -> List[Point]:
    """
    Đảm bảo polyline chạy từ gần u_pos -> gần v_pos.
    Nếu điểm đầu của polyline gần v_pos hơn u_pos thì đảo ngược.
    """
    if not poly:
        return poly
    d0_u = dist(poly[0], u_pos)
    dN_u = dist(poly[-1], u_pos)
    # nếu đầu poly không sát u mà đuôi poly lại sát u -> đảo
    if dN_u + 1e-6 < d0_u:
        return list(reversed(poly))
    return poly


def merge_polys_with_tol(polys: List[List[Point]], tol: float = 1.5) -> List[Point]:
    """
    Ghép nhiều polyline đã được định hướng. Dùng dung sai để nối mượt.
    Nếu điểm cuối poly trước không trùng (theo tol) với điểm đầu poly sau, ta nối thẳng 1 đoạn ngắn.
    """
    out: List[Point] = []
    for poly in polys:
        if not poly:
            continue
        if not out:
            out.extend(poly)
            continue
        # nếu out[-1] gần poly[0] -> bỏ điểm đầu trùng để tránh lặp
        if almost_same(out[-1], poly[0], tol):
            out.extend(poly[1:])
        else:
            # thử đảo nếu cần (trong trường hợp upstream chưa orient chuẩn)
            if almost_same(out[-1], poly[-1], tol):
                out.extend(list(reversed(poly))[1:])
            else:
                # không khớp 2 đầu -> chèn "cầu nối" nhỏ (để không bị ngắt)
                out.append(poly[0])
                out.extend(poly[1:])
    return out


def dedupe_polyline(poly: List[Point], tol: float = 1.0) -> List[Point]:
    """
    Loại bỏ các điểm trùng/siêu gần nhau (<= tol px) để tránh jitter.
    """
    if not poly:
        return []
    out = [poly[0]]
    for p in poly[1:]:
        if dist(out[-1], p) > tol:
            out.append(p)
    return out


def heading_angle_from_polyline(poly: List[Point], min_dist: float = 25.0) -> float:
    """
    Tính heading ban đầu theo hệ toạ độ màn hình (y tăng xuống).
    Đi từ điểm đầu, cộng dồn đến khi tổng quãng >= min_dist để chống jitter.
    Trả về góc (độ): 0°=phải, +90°=xuống, ±180°=trái, -90°=lên.
    """
    if not poly or len(poly) < 2:
        return 0.0
    p0 = poly[0]
    acc = 0.0
    last = p0
    dx_sum, dy_sum = 0.0, 0.0
    for i in range(1, len(poly)):
        p = poly[i]
        dx = p[0] - last[0]
        dy = p[1] - last[1]
        seg = math.hypot(dx, dy)
        if seg <= 1e-6:
            continue
        dx_sum += dx
        dy_sum += dy
        acc += seg
        last = p
        if acc >= min_dist:
            break
    # nếu vẫn < min_dist (tuyến quá ngắn), dùng vector tổng hiện có
    ang = math.degrees(math.atan2(dy_sum, dx_sum))
    # chuẩn hóa (-180, 180]
    while ang <= -180.0:
        ang += 360.0
    while ang > 180.0:
        ang -= 360.0
    return ang


def initial_heading_text_from_angle(angle_deg: float) -> str:
    """
    Quy 4 hướng chính từ góc. Ngưỡng ±45° quanh trục.
      -45..+45  => trái -> phải
      +45..+135 => trên -> xuống
      -135..-45 => dưới -> lên
      còn lại   => phải -> trái
    """
    a = angle_deg
    if -45.0 <= a <= 45.0:
        return "từ trái sang phải"
    elif 45.0 < a <= 135.0:
        return "từ trên xuống"
    elif -135.0 <= a < -45.0:
        return "từ dưới lên"
    else:
        return "từ phải sang trái"
