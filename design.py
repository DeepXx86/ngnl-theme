import numpy as np

HEIGHT = {"p": 0.753, "n": 0.816, "b": 0.784, "r": 0.782, "q": 0.829, "k": 0.696}
SOURCE_OF = {"p": "thumbnail", "n": "thumbnail", "b": "close-up",
             "q": "thumbnail", "r": "board frame", "k": "late board"}

KAPPA = 0.5523  

def _quarter_circle(radius, cy):
    return ("C", radius, cy, radius * KAPPA, cy - radius, radius, cy - radius * KAPPA)


PAWN = [
    _quarter_circle(0.172, 0.172),          
    ("L", 0.172, 0.279, 0.004),             
    ("L", 0.302, 0.316, 0.004),             
    ("L", 0.256, 0.358, 0.004),             
    ("L", 0.111, 0.389, 0.008),             
    ("C", 0.146, 0.653, 0.078, 0.441, 0.107, 0.579),  
    ("C", 0.305, 0.801, 0.204, 0.707, 0.241, 0.755),  
    ("L", 0.298, 0.990, 0.005),           
]

BISHOP = [
    ("L", 0.0285, 0.098, 0.0),    
    ("C", 0.1824, 0.240, 0.0731, 0.143, 0.1349, 0.185),
    ("C", 0.2346, 0.400, 0.2128, 0.287, 0.2375, 0.336),
    ("C", 0.1748, 0.560, 0.2384, 0.465, 0.2099, 0.513),
    ("C", 0.1225, 0.680, 0.1539, 0.600, 0.114, 0.631),
    ("C", 0.3011, 0.840, 0.1548, 0.756, 0.2679, 0.763),
    ("L", 0.304, 0.988, 0.005),
]

QUEEN = [                                  
    ("L", 0.084, 0.336, 0.0),            
    ("L", 0.272, 0.112, 0.0),            
    ("L", 0.243, 0.430, 0.0),            
    ("L", 0.450, 0.335, 0.0),            
    ("L", 0.273, 0.726, 0.008),            
    ("L", 0.356, 0.815, 0.005),            
    ("L", 0.348, 0.990, 0.005),            
]

ROOK = [
    ("L", 0.042, 0.004, 0.0),        
    ("L", 0.042, 0.070, 0.0),        
    ("L", 0.174, 0.070, 0.0),        
    ("L", 0.174, 0.004, 0.0),        
    ("L", 0.268, 0.004, 0.0),        
    ("L", 0.268, 0.259, 0.0),        
    ("L", 0.170, 0.372, 0.008),      
    ("L", 0.156, 0.626, 0.010),      
    ("L", 0.184, 0.687, 0.006),
    ("L", 0.319, 0.812, 0.006),      
    ("L", 0.321, 0.985, 0.004),         
]

KING = [
    ("L", 0.054, 0.0, 0.0),               
    ("L", 0.054, 0.086, 0.0),             
    ("L", 0.132, 0.086, 0.0),             
    ("L", 0.132, 0.158, 0.0),             
    ("L", 0.054, 0.164, 0.004),           
    ("L", 0.056, 0.198, 0.004),           
    ("L", 0.098, 0.212, 0.006),           
    ("L", 0.232, 0.222, 0.012),           
    ("C", 0.493, 0.452, 0.362, 0.224, 0.481, 0.320),  
    ("C", 0.482, 0.578, 0.497, 0.500, 0.482, 0.535),  
    ("C", 0.318, 0.780, 0.443, 0.658, 0.333, 0.698),  
    ("L", 0.351, 0.822, 0.005),      
    ("L", 0.368, 0.872, 0.005),
    ("L", 0.362, 0.960, 0.005),
    ("L", 0.300, 0.992, 0.005),
]

HALVES = {"p": PAWN, "b": BISHOP, "q": QUEEN, "r": ROOK, "k": KING}
TOP_Y = {"p": 0.0, "b": 0.0, "q": 0.0, "r": 0.005, "k": 0.0}

CROSS = {
    "b": (0.000, 0.315, 0.616, 0.404, 0.089, 0.0205, 0.0180),
    "q": (0.000, 0.460, 0.684, 0.572, 0.083, 0.0200, 0.0235),
}
EYE = (-0.190, 0.305, 0.024, 0.039, 25.0) 


def cross_path(code, tf, digits=2):
    cx, top, bottom, bar_y, bar_half, arm, bar = CROSS[code]
    corners = [
        (cx - arm, top), (cx + arm, top),
        (cx + arm, bar_y - bar), (cx + bar_half, bar_y - bar),
        (cx + bar_half, bar_y + bar), (cx + arm, bar_y + bar),
        (cx + arm, bottom), (cx - arm, bottom),
        (cx - arm, bar_y + bar), (cx - bar_half, bar_y + bar),
        (cx - bar_half, bar_y - bar), (cx - arm, bar_y - bar),
    ]
    fmt = "{:." + str(digits) + "f}"
    out = []
    for index, (x, y) in enumerate(corners):
        px, py = tf(x, y)
        out.append(("M" if index == 0 else "L") + fmt.format(px) + " " + fmt.format(py))
    return "".join(out) + "Z"


def eye_path(tf, digits=2):
    cx, cy, rx, ry, tilt = EYE
    angle = np.radians(tilt)
    cosine, sine = np.cos(angle), np.sin(angle)

    def rotate(point):
        x, y = point
        return (cx + x * cosine - y * sine, cy + x * sine + y * cosine)

    nodes = [rotate((0, -ry)), rotate((rx, 0)), rotate((0, ry)), rotate((-rx, 0))]
    handles = [
        (rotate((rx * 0.72, -ry * 0.78)), rotate((rx, -ry * 0.36))),
        (rotate((rx, ry * 0.36)), rotate((rx * 0.72, ry * 0.78))),
        (rotate((-rx * 0.72, ry * 0.78)), rotate((-rx, ry * 0.36))),
        (rotate((-rx, -ry * 0.36)), rotate((-rx * 0.72, -ry * 0.78))),
    ]
    fmt = "{:." + str(digits) + "f}"
    def p(point):
        px, py = tf(*point)
        return fmt.format(px) + " " + fmt.format(py)
    parts = ["M" + p(nodes[0])]
    for index in range(4):
        c1, c2 = handles[index]
        parts.append("C" + p(c1) + " " + p(c2) + " " + p(nodes[(index + 1) % 4]))
    return "".join(parts) + "Z"

def _mirror(segments, start):
    points = [start] + [(s[1], s[2]) for s in segments]
    out = []
    for index in range(len(segments) - 1, -1, -1):
        seg = segments[index]
        target = points[index]
        if seg[0] == "L":
            out.append(("L", -target[0], target[1], seg[3]))
        else:
            out.append(("C", -target[0], target[1], -seg[5], seg[6], -seg[3], seg[4]))
    return out


def outline(code):
    half = HALVES[code]
    start = (0.0, TOP_Y[code])
    base_y = half[-1][2]
    segments = list(half)
    segments.append(("L", -half[-1][1], base_y, 0.005))     
    segments.extend(_mirror(half, start))                   
    return start, segments


def _corner_trim(prev_point, corner, next_point, radius):
    into = corner - prev_point
    out_of = next_point - corner
    len_in, len_out = float(np.hypot(*into)), float(np.hypot(*out_of))
    if len_in == 0 or len_out == 0 or radius <= 0:
        return 0.0
    cosine = float(np.clip(np.dot(into / len_in, out_of / len_out), -1.0, 1.0))
    turn = float(np.arccos(cosine))
    if turn < 1e-6:
        return 0.0
    half_angle = (np.pi - turn) / 2
    trim = radius / np.tan(half_angle) if half_angle > 1e-6 else radius
    return float(min(abs(trim), len_in * 0.48, len_out * 0.48))


def path_data(code, tf, digits=2):
    start, segments = outline(code)
    nodes = [np.array(tf(*start))]
    kinds = []
    for seg in segments:
        nodes.append(np.array(tf(seg[1], seg[2])))
        if seg[0] == "L":
            kinds.append(("L", seg[3]))
        else:
            kinds.append(("C", np.array(tf(seg[3], seg[4])), np.array(tf(seg[5], seg[6]))))
    nodes = nodes[:-1]                     
    count = len(nodes)

    scale = abs(tf(1.0, 0.0)[0] - tf(0.0, 0.0)[0])
    trims = [0.0] * count
    for i in range(count):
        before, after = kinds[i - 1], kinds[i]
        if before[0] != "L" or after[0] != "L" or after[1] <= 0:
            continue
        trims[i] = _corner_trim(nodes[i - 1], nodes[i], nodes[(i + 1) % count],
                                after[1] * scale)

    fmt = "{:." + str(digits) + "f}"
    def p(point):
        return fmt.format(point[0]) + " " + fmt.format(point[1])

    def entry(i):
        if trims[i] <= 0:
            return nodes[i]
        step = nodes[i] - nodes[i - 1]
        return nodes[i] - step / np.hypot(*step) * trims[i]

    def exit_(i):
        if trims[i] <= 0:
            return nodes[i]
        step = nodes[(i + 1) % count] - nodes[i]
        return nodes[i] + step / np.hypot(*step) * trims[i]

    parts = ["M" + p(entry(0))]
    for i in range(count):
        if trims[i] > 0:
            here = nodes[i]
            c1 = here + (entry(i) - here) * (1 - KAPPA)
            c2 = here + (exit_(i) - here) * (1 - KAPPA)
            parts.append("C" + p(c1) + " " + p(c2) + " " + p(exit_(i)))
        kind = kinds[i]
        nxt = (i + 1) % count
        if kind[0] == "C":
            parts.append("C" + p(kind[1]) + " " + p(kind[2]) + " " + p(entry(nxt)))
        else:
            parts.append("L" + p(entry(nxt)))
    parts.append("Z")
    return "".join(parts)
