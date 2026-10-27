# Escena del circuito de Halloween con acabado tipo Wobbly Life (referencias en assets/).
# Uso en Blender:
#   p = "<ruta>/blender/escena.py"; exec(open(p).read(), {"__file__": p, "__name__": "__main__"})
# Regenera la escena entera (borra todo) y escribe track.json y palette.png junto al script.
import bpy
import bmesh
import json
import math
import os
import random
from mathutils import Matrix, Vector

random.seed(31)  # 31-oct: misma escena en cada ejecución
HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in dir() else None

ROAD_W = 8.0      # ancho de calzada
KERB_W = 0.9      # piano rojo/blanco a cada lado
KERB_STRIPE = 2.0 # largo de cada franja
FILLET_R = 8.0    # radio de las curvas (línea central)
LIGHT_EVERY = 5.0 # metros entre luces de borde
EDGE = ROAD_W / 2 + KERB_W

# Esquinas del bucle, sentido horario empezando por la salida (oeste, rumbo norte).
# Todas a 90°: cada curva es una orden "left"/"right"; rectas >= 20 m por la latencia de Kev.
CORNERS = [
    (-65, -10), (-65, 40), (-30, 40), (-30, 20), (25, 20), (25, 45),
    (65, 45), (65, -40), (25, -40), (25, -10), (-10, -10), (-10, -40),
    (-40, -40), (-40, -10),
]
START = Vector((-65, 8, 0))  # en la recta oeste, mirando al norte
GATE = Vector((45, 45, 0))   # la pista cruza la puerta del castillo aquí

# Río: nace bajo el castillo, cruza la pista en y=20 y y=-10 (puentes) y cae en cascada al sur.
RIVER = [(8, -66), (8, -40), (6, -22), (4.5, -10), (3, 3), (6, 15), (7, 20), (9, 32), (7, 46), (6, 58), (6, 66)]
RIVER_W = 9.0
BRIDGES_Y = (-10, 20)

X0, X1, Y0, Y1, WH = -78, 78, -56, 56, 6.0  # murallas del recinto
CY = 72                                     # fondo del castillo


# ---------- utilidades ----------
def wipe():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.lights, bpy.data.cameras,
                 bpy.data.curves, bpy.data.images):
        for block in list(coll):
            if block.users == 0:
                coll.remove(block)
    for c in list(bpy.data.collections):
        bpy.data.collections.remove(c)


def srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hex_rgb(h):
    return tuple(int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))


def mat(name, hex_color, kind="flat"):
    # Material provisional de un color de la paleta; palettize() lo sustituye al final.
    # kind: flat (mate), glow (emisivo) o gloss (brillo: agua, cristal, pintura del coche).
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m["hex"], m["kind"] = hex_color, kind
    m.diffuse_color = (*map(srgb_to_linear, hex_rgb(hex_color)), 1)
    return m


def soft(o, width=None, subsurf=0):
    # Acabado de juguete: sombreado suave + bisel redondeado con normales endurecidas
    # (caras planas siguen planas, solo los bordes se redondean y pillan luz).
    o.data.shade_smooth()
    if width and width >= 0.02:  # en piezas diminutas el bisel no se ve y solo suma triángulos
        b = o.modifiers.new("Bevel", "BEVEL")
        b.width, b.limit_method, b.harden_normals = width, "ANGLE", True
        b.segments = 3 if width >= 0.2 else 1  # presupuesto ~250k triángulos en toda la escena
    if subsurf:
        s = o.modifiers.new("Smooth", "SUBSURF")
        s.levels = s.render_levels = subsurf
    return o


def collection(name):
    c = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(c)
    return c


def box(name, loc, size, coll, material, rot=(0, 0, 0), parent=None, bevel=True):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Diagonal((*size, 1)))
    o = mesh_obj(name, bm, coll, [material], loc, rot, parent)
    return soft(o, min(0.4, 0.2 * min(size)) if bevel else None)


def cone(name, loc, r, depth, coll, material, rot=(0, 0, 0), parent=None, r2=0.0, verts=16, bevel=True):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=verts, radius1=r, radius2=r2, depth=depth)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)  # punta en un solo vértice
    o = mesh_obj(name, bm, coll, [material], loc, rot, parent)
    return soft(o, min(0.4, 0.15 * r)) if bevel else o


def cyl(name, loc, r, depth, coll, material, rot=(0, 0, 0), verts=24, parent=None, bevel=True):
    o = cone(name, loc, r, depth, coll, material, rot, parent, r2=r, verts=verts, bevel=False)
    return soft(o, min(0.4, 0.25 * min(r, depth)) if bevel else None)


def ball(name, loc, r, coll, material, scale=(1, 1, 1), parent=None, segs=12):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=segs * 5 // 8, radius=r)
    o = soft(mesh_obj(name, bm, coll, [material], loc, parent=parent))
    o.scale = scale
    return o


def torus(name, loc, R, r, coll, material, rot=(0, 0, 0), parent=None, seg=24, sides=8):
    bm = bmesh.new()
    rings = [[bm.verts.new(((R + r * math.cos(b)) * math.cos(a), (R + r * math.cos(b)) * math.sin(a), r * math.sin(b)))
              for b in (2 * math.pi * j / sides for j in range(sides))]
             for a in (2 * math.pi * i / seg for i in range(seg))]
    for i in range(seg):
        for j in range(sides):
            r0, r1 = rings[i], rings[(i + 1) % seg]
            bm.faces.new((r0[j], r1[j], r1[(j + 1) % sides], r0[(j + 1) % sides]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return soft(mesh_obj(name, bm, coll, [material], loc, rot, parent))


def add_light(name, kind, loc=(0, 0, 0), rot=(0, 0, 0)):
    L = bpy.data.objects.new(name, bpy.data.lights.new(name, kind))
    L.location, L.rotation_euler = loc, rot
    C["Lights"].objects.link(L)
    return L


def mesh_obj(name, bm, coll, materials, loc=(0, 0, 0), rot=(0, 0, 0), parent=None):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    coll.objects.link(o)
    for m in materials:
        me.materials.append(m)
    o.location, o.rotation_euler, o.parent = loc, rot, parent
    return o


def prism(name, outline, depth, loc, coll, material, rot=(0, 0, 0), parent=None, scale=1.0):
    # Silueta (x, z) extruida en Y: ojos y boca tallados, murciélagos, emblemas.
    bm = bmesh.new()
    front = [bm.verts.new((x * scale, -depth / 2, z * scale)) for x, z in outline]
    back = [bm.verts.new((x * scale, depth / 2, z * scale)) for x, z in outline]
    bm.faces.new(front)
    bm.faces.new(back[::-1])
    n = len(outline)
    for i in range(n):
        bm.faces.new((front[i], back[i], back[(i + 1) % n], front[(i + 1) % n]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    return mesh_obj(name, bm, coll, [material], loc, rot, parent)


def limb(name, p0, p1, r, coll, material, parent=None):
    # Cilindro de p0 a p1 (brazos, ramas, soportes).
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    o = cyl(name, (p0 + p1) / 2, r, d.length, coll, material, verts=12, parent=parent)
    o.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    return o


def carve(target, cutter):
    # Booleano de resta; las caras del corte heredan el material del cortador (p. ej. luz).
    for c in cutter.users_collection:
        c.objects.unlink(cutter)
    C["Cutters"].objects.link(cutter)
    cutter.display_type, cutter.hide_render = "WIRE", True
    m = target.modifiers.new("Carve", "BOOLEAN")
    m.operation, m.solver, m.object = "DIFFERENCE", "EXACT", cutter
    m.material_mode = "TRANSFER"
    return cutter


# ---------- líneas centrales ----------
def centerline(corners, r, step=1.0):
    # Bucle cerrado con esquinas redondeadas (arcos de radio r).
    pts = [Vector((x, y, 0)) for x, y in corners]
    n = len(pts)
    arcs = []  # (inicio, fin, centro, giro con signo) por esquina
    for i in range(n):
        a, p, b = pts[i - 1], pts[i], pts[(i + 1) % n]
        d1, d2 = (p - a).normalized(), (b - p).normalized()
        turn = math.atan2(d1.x * d2.y - d1.y * d2.x, d1.dot(d2))  # >0 izquierda
        t = r * math.tan(abs(turn) / 2)
        s = p - d1 * t
        left = Vector((-d1.y, d1.x, 0))
        arcs.append((s, p + d2 * t, s + left * r * math.copysign(1, turn), turn))
    out = []
    for i in range(n):
        s, e, c, turn = arcs[i]
        k = max(2, int(abs(turn) * r / step))
        a0 = math.atan2(s.y - c.y, s.x - c.x)
        out += [c + Vector((math.cos(a0 + turn * j / k), math.sin(a0 + turn * j / k), 0)) * r for j in range(k)]
        nxt = arcs[(i + 1) % n][0]
        k = max(1, int((nxt - e).length / step))
        out += [e.lerp(nxt, j / k) for j in range(k)]
    return out, [("left" if a[3] > 0 else "right") for a in arcs]


def catmull(ctrl, step=1.0):
    # Curva abierta suave que pasa por todos los puntos de control (río).
    P = [Vector((x, y, 0)) for x, y in ctrl]
    P = [2 * P[0] - P[1]] + P + [2 * P[-1] - P[-2]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        k = max(2, int((p2 - p1).length / step))
        for j in range(k):
            t = j / k
            out.append(0.5 * (2 * p1 + (p2 - p0) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                              + (3 * p1 - p0 - 3 * p2 + p3) * t ** 3))
    return out + [P[-2]]


def normal_at(pts, i, closed=True):
    n = len(pts)
    a = pts[(i + 1) % n] if closed else pts[min(i + 1, n - 1)]
    b = pts[i - 1] if closed else pts[max(i - 1, 0)]
    t = (a - b).normalized()
    return Vector((-t.y, t.x, 0))


def ribbon(bm, pts, off_in, off_out, z=0.02, closed=True, mat_of=None):
    # Cinta plana paralela a la línea central (negativo = derecha), con normales hacia arriba
    # (three.js no pinta la cara trasera).
    n, dist = len(pts), 0.0
    rows = []
    for i in range(n):
        nr = normal_at(pts, i, closed)
        rows.append([bm.verts.new(pts[i] + nr * off + Vector((0, 0, z))) for off in (off_in, off_out)])
    for i in range(n if closed else n - 1):
        (a, b), (c, d) = rows[i], rows[(i + 1) % n]
        f = bm.faces.new((a, b, d, c))
        f.normal_update()
        if f.normal.z < 0:
            f.normal_flip()
        if mat_of:
            f.material_index = mat_of(dist)
        dist += (pts[(i + 1) % n] - pts[i]).length


def ribbon_solid(bm, pts, half, z0, z1):
    # Volumen cerrado a lo largo de una curva abierta: cortador del cauce del río.
    rows = []
    for i, p in enumerate(pts):
        nr = normal_at(pts, i, closed=False) * half
        rows.append([bm.verts.new(p + v) for v in (nr + Vector((0, 0, z0)), -nr + Vector((0, 0, z0)),
                                                   -nr + Vector((0, 0, z1)), nr + Vector((0, 0, z1)))])
    for r0, r1 in zip(rows, rows[1:]):
        for k in range(4):
            bm.faces.new((r0[k], r0[(k + 1) % 4], r1[(k + 1) % 4], r1[k]))
    bm.faces.new(rows[0])
    bm.faces.new(rows[-1][::-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])


def nearest(pts, x, y):
    q = Vector((x, y, 0))
    return min((p - q).length for p in pts)


# ---------- piezas del kit ----------
BAT = [(0.0, 0.18), (0.08, 0.32), (0.13, 0.16), (0.35, 0.26), (0.62, 0.34), (1.0, 0.2), (0.86, 0.05),
       (0.78, -0.12), (0.62, -0.05), (0.5, -0.2), (0.36, -0.08), (0.2, -0.22), (0.08, -0.12), (0.0, -0.3)]
BAT = BAT + [(-x, z) for x, z in reversed(BAT[1:-1])]
EYE = [(-0.15, -0.1), (0.15, -0.1), (0.04, 0.15)]
MOUTH = [(-0.55, 0.05), (-0.38, -0.05), (-0.25, 0.08), (-0.1, -0.04), (0.05, 0.08), (0.2, -0.04),
         (0.35, 0.08), (0.55, 0.05), (0.35, -0.22), (0.0, -0.3), (-0.35, -0.22)]


def pumpkin(name, loc, r, coll, carved=False, face=0.0, parent=None, squash=0.8):
    # Calabaza con gajos; carved=True talla ojos y boca que brillan por dentro.
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=24 if carved else 16, v_segments=12 if carved else 10, radius=r)
    for v in bm.verts:
        k = 1 - 0.09 * (1 - math.cos(8 * math.atan2(v.co.y, v.co.x))) / 2
        v.co.x, v.co.y, v.co.z = v.co.x * k, v.co.y * k, v.co.z * squash
    o = soft(mesh_obj(name, bm, coll, [M["pumpkin"]], loc, (0, 0, face), parent))
    stem = name.split("__")[0] + "__stem" if "__" in name else name + "Stem"
    cone(stem, (loc[0], loc[1], loc[2] + r * squash + 0.12 * r), 0.13 * r, 0.4 * r, coll, M["stem"],
         parent=parent, r2=0.07 * r, verts=6, bevel=False)
    if carved:
        for side in (-1, 1):
            eye = [(side * x, z) for x, z in EYE]
            carve(o, prism("Cut", eye, r, (side * 0.33 * r, 0.75 * r, 0.18 * r), C["Cutters"], M["window"],
                           parent=o, scale=r))
        carve(o, prism("Cut", MOUTH, r, (0, 0.75 * r, -0.2 * r), C["Cutters"], M["window"], parent=o, scale=r))
    return o


def tower(name, x, y, r, h, coll, roof=True, windows=2):
    cyl(name, (x, y, h / 2), r, h, coll, M["stone"])
    cyl(name + "Corbel", (x, y, h + 0.3), r + 0.4, 0.6, coll, M["stone"])
    n = max(6, int(2 * math.pi * (r + 0.2) / 1.5))
    for k in range(n):
        a = 2 * math.pi * k / n
        box(name + "Merlon", (x + math.cos(a) * (r + 0.1), y + math.sin(a) * (r + 0.1), h + 1.1),
            (0.8, 0.8, 1.0), coll, M["stone"], rot=(0, 0, a))
    if roof:
        cone(name + "Roof", (x, y, h + 0.6 + r * 1.3), r + 0.9, r * 2.6, coll, M["roof"])
        cone(name + "Finial", (x, y, h + 0.6 + r * 2.6 + 0.5), 0.15, 1.2, coll, M["gold"], verts=8)
    for k in range(windows):
        a = random.uniform(0, 2 * math.pi)
        box(name + "Window", (x + math.cos(a) * r, y + math.sin(a) * r, h * (0.45 + 0.3 * k)),
            (0.3, 0.55, 1.1), coll, M["window"], rot=(0, 0, a))


def merlons(p0, p1, z, coll, thick=1.0, every=2.0):
    p0, p1 = Vector((*p0, 0)), Vector((*p1, 0))
    d = p1 - p0
    rz = math.atan2(d.y, d.x)
    n = max(1, int(d.length / every))
    for k in range(n):
        p = p0 + d * (k + 0.5) / n
        box("Merlon", (p.x, p.y, z + 0.5), (1.0, thick, 1.0), coll, M["stone"], rot=(0, 0, rz))


def arch_window(x, y, z, coll, w=1.2, h=2.0):
    box("Window", (x, y, z), (w, 0.3, h), coll, M["window"])
    cyl("WindowTop", (x, y, z + h / 2), w / 2, 0.3, coll, M["window"], rot=(math.pi / 2, 0, 0), verts=16)


def lantern(x, y, coll):
    box("LanternBase", (x, y, 0.15), (0.4, 0.4, 0.3), coll, M["iron"])
    cyl("LanternPost", (x, y, 1.6), 0.08, 3.0, coll, M["iron"], verts=8)
    box("Lantern", (x, y, 3.3), (0.4, 0.4, 0.5), coll, M["lamp"])
    cone("LanternCap", (x, y, 3.7), 0.36, 0.32, coll, M["iron"], rot=(0, 0, math.pi / 4), verts=4)
    L = add_light("LanternLight", "POINT", (x, y, 3.0))
    L.data.energy, L.data.color, L.data.shadow_soft_size = 120, (1.0, 0.6, 0.25), 0.3


def torch(p, n, z, coll):
    q = p + n * 0.45
    limb("TorchBracket", (p.x, p.y, z), (q.x, q.y, z + 0.25), 0.05, coll, M["iron"])
    cone("TorchCup", (q.x, q.y, z + 0.3), 0.14, 0.2, coll, M["iron"], rot=(math.pi, 0, 0), verts=8)
    cone("TorchFlame", (q.x, q.y, z + 0.6), 0.14, 0.45, coll, M["flame"], verts=8)


def banner(p, n, z, coll):
    rz = math.atan2(n.y, n.x) - math.pi / 2
    q = p + n * 0.1
    box("Banner", (q.x, q.y, z), (1.8, 0.08, 3.0), coll, M["banner"], rot=(0, 0, rz))
    q = q + n * 0.06
    prism("BannerBat", BAT, 0.04, (q.x, q.y, z + 0.4), coll, M["flame"], rot=(0, 0, rz), scale=0.7)


def tomb(x, y, rz, coll):
    if random.random() < 0.3:
        box("TombCross", (x, y, 0.65), (0.22, 0.22, 1.3), coll, M["stone"], rot=(0, 0, rz))
        box("TombCrossArm", (x, y, 0.9), (0.8, 0.2, 0.2), coll, M["stone"], rot=(0, 0, rz))
    else:
        box("Tomb", (x, y, 0.4), (0.75, 0.28, 0.8), coll, M["stone"], rot=(0, 0, rz))
        cyl("TombTop", (x, y, 0.8), 0.375, 0.28, coll, M["stone"], rot=(math.pi / 2, 0, rz), verts=16)


def fence(p0, p1, coll):
    p0, p1 = Vector((*p0, 0)), Vector((*p1, 0))
    d = p1 - p0
    rz = math.atan2(d.y, d.x)
    n = max(1, int(d.length / 1.2))
    for k in range(n + 1):
        p = p0 + d * k / n
        box("FencePost", (p.x, p.y, 0.7), (0.08, 0.08, 1.4), coll, M["iron"], rot=(0, 0, rz))
        cone("FenceSpear", (p.x, p.y, 1.5), 0.08, 0.22, coll, M["iron"], verts=4)
    m = (p0 + p1) / 2
    for z in (0.45, 1.2):
        box("FenceRail", (m.x, m.y, z), (d.length, 0.05, 0.06), coll, M["iron"], rot=(0, 0, rz))


def autumn_tree(x, y, s, coll):
    cone("Trunk", (x, y, 1.5 * s), 0.35 * s, 3 * s, coll, M["wood"], r2=0.2 * s, verts=10)
    for k in range(3):
        a = k * 2.1 + random.random()
        ball("Crown", (x + math.cos(a) * 0.9 * s, y + math.sin(a) * 0.9 * s, (3.6 + k * 0.6) * s),
             random.uniform(1.4, 1.9) * s, coll, random.choice((M["leaves"], M["leaves2"])))


def dead_tree(x, y, s, coll):
    cone("DeadTrunk", (x, y, 2 * s), 0.35 * s, 4 * s, coll, M["wood"], r2=0.1 * s, verts=8)
    for k in range(4):
        a, z = random.uniform(0, 2 * math.pi), random.uniform(2.0, 3.4) * s
        tip = (x + math.cos(a) * 1.6 * s, y + math.sin(a) * 1.6 * s, z + 1.0 * s)
        limb("Branch", (x, y, z), tip, 0.08 * s, coll, M["wood"])


def pine(x, y, s, z0, coll):
    cyl("PineTrunk", (x, y, z0 + 0.8 * s), 0.3 * s, 1.6 * s, coll, M["wood"], verts=6, bevel=False)
    cone("PineLow", (x, y, z0 + 3.0 * s), 2.4 * s, 3.6 * s, coll, M["pine"], verts=8, bevel=False)
    cone("PineHigh", (x, y, z0 + 5.2 * s), 1.7 * s, 3.0 * s, coll, M["pine"], verts=8, bevel=False)


def bush(x, y, s, coll):
    for k in range(3):
        a = k * 2.1
        ball("Bush", (x + math.cos(a) * 0.5 * s, y + math.sin(a) * 0.5 * s, 0.5 * s), random.uniform(0.6, 0.9) * s,
             coll, random.choice((M["grass_d"], M["grass_l"])))


def rock(x, y, s, coll, z=0.0):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=1, radius=s)
    for v in bm.verts:
        v.co += Vector([random.uniform(-0.2, 0.2) * s for _ in range(3)])
        v.co.z *= 0.6
    return mesh_obj("Rock", bm, coll, [M["stone_dark"]], (x, y, z), (0, 0, random.uniform(0, math.pi)))


def loft(name, stations, coll, material, parent=None):
    # Carrocería: secciones redondeadas a lo largo de Y, suavizadas con subdivisión.
    bm = bmesh.new()
    rings = []
    for y, w, zb, zt in stations:
        h = zt - zb
        sec = [(-0.8 * w, zb), (0.8 * w, zb), (w, zb + 0.3 * h), (w, zb + 0.65 * h),
               (0.75 * w, zt), (-0.75 * w, zt), (-w, zb + 0.65 * h), (-w, zb + 0.3 * h)]
        rings.append([bm.verts.new((x, y, z)) for x, z in sec])
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(8):
            bm.faces.new((r0[k], r0[(k + 1) % 8], r1[(k + 1) % 8], r1[k]))
    bm.faces.new(rings[0])
    bm.faces.new(rings[-1][::-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return soft(mesh_obj(name, bm, coll, [material], parent=parent), subsurf=2)


def witch_hat(name, loc, base_r, h, bend, coll, material, parent=None):
    # Cono de bruja con la punta doblada hacia atrás.
    bm, seg, N = bmesh.new(), 16, 10
    rings = []
    for k in range(N):
        t = k / N
        r = base_r * (1 - t) ** 0.8
        c = Vector((0, -bend * t ** 2.5, h * t))
        rings.append([bm.verts.new(c + Vector((math.cos(a) * r, math.sin(a) * r, 0)))
                      for a in (2 * math.pi * s / seg for s in range(seg))])
    tip = bm.verts.new((0, -bend * 1.15, h * 0.97))
    for r0, r1 in zip(rings, rings[1:]):
        for s in range(seg):
            bm.faces.new((r0[s], r0[(s + 1) % seg], r1[(s + 1) % seg], r1[s]))
    for s in range(seg):
        bm.faces.new((rings[-1][s], rings[-1][(s + 1) % seg], tip))
    bm.faces.new(rings[0][::-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return soft(mesh_obj(name, bm, coll, [material], loc, parent=parent), subsurf=1)


def cape(name, loc, coll, parent=None):
    # Capa abierta por delante: negra por fuera, roja por dentro (solidify con material_offset).
    bm, cols, rows = bmesh.new(), 10, 5
    grid = []
    for i in range(rows + 1):
        t = i / rows
        r = 0.3 + 0.2 * t
        grid.append([bm.verts.new((math.cos(a) * r, math.sin(a) * r * 0.9, -0.8 * t))
                     for a in (-math.pi / 2 - 1.5 + 3.0 * j / cols for j in range(cols + 1))])
    for r0, r1 in zip(grid, grid[1:]):
        for j in range(cols):
            bm.faces.new((r0[j], r0[j + 1], r1[j + 1], r1[j]))
    o = soft(mesh_obj(name, bm, coll, [M["cloth"], M["cape_red"]], loc, parent=parent))
    s = o.modifiers.new("Thick", "SOLIDIFY")
    s.thickness, s.material_offset = 0.04, 1
    return o


# ---------- dispersión sin pisar pista, río ni zonas ocupadas ----------
taken = []


def free(x, y, r):
    if not (X0 + 3 + r < x < X1 - 3 - r and Y0 + 3 + r < y < Y1 - 3 - r):
        return False
    if nearest(TRACK_S, x, y) < EDGE + 1.2 + r or nearest(RIVER_S, x, y) < RIVER_W / 2 + 1.5 + r:
        return False
    return all(math.hypot(x - cx, y - cy) > cr + r for cx, cy, cr in taken)


def spot(r, tries=300):
    for _ in range(tries):
        x, y = random.uniform(X0, X1), random.uniform(Y0, Y1)
        if free(x, y, r):
            taken.append((x, y, r))
            return x, y
    return None


def palettize(cell=4, cols=8):
    # Una textura-paleta (cols x cols casillas de `cell` px) y tres materiales para toda la
    # escena: Palette (mate), PaletteGlow (emisivo) y PaletteGloss (brillo). Cada cara apunta
    # su UV al centro de la casilla de su color: glTF exporta 3 materiales y un PNG diminuto.
    colors = sorted({m["hex"] for m in bpy.data.materials if "hex" in m})
    assert len(colors) <= cols * cols, f"paleta llena: {len(colors)} colores"
    size = cell * cols
    img = bpy.data.images.new("Palette", size, size)
    px = [0.0] * (size * size * 4)
    for k, h in enumerate(colors):
        cx, cy = k % cols, k // cols
        for y in range(cy * cell, (cy + 1) * cell):
            for x in range(cx * cell, (cx + 1) * cell):
                px[(y * size + x) * 4:(y * size + x) * 4 + 4] = (*hex_rgb(h), 1)
    img.pixels = px
    if HERE:
        img.filepath_raw = os.path.join(HERE, "palette.png")
        img.file_format = "PNG"
        img.save()
    uv_of = {h: ((k % cols + 0.5) / cols, (k // cols + 0.5) / cols) for k, h in enumerate(colors)}

    def palette_mat(name, kind):
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image, tex.interpolation = img, "Closest"
        nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
        bsdf.inputs["Roughness"].default_value = 0.2 if kind == "gloss" else 0.9
        bsdf.inputs["Metallic"].default_value = 0.0
        if kind == "glow":
            nt.links.new(tex.outputs["Color"], bsdf.inputs["Emission Color"])
            bsdf.inputs["Emission Strength"].default_value = 4.0
        return m

    kinds = ("flat", "glow", "gloss")
    slots = [palette_mat(n, k) for n, k in zip(("Palette", "PaletteGlow", "PaletteGloss"), kinds)]
    for o in bpy.data.objects:
        if o.type != "MESH" or not o.data.materials:
            continue
        me, old = o.data, list(o.data.materials)
        uv = me.uv_layers.active or me.uv_layers.new(name="UVMap")
        for poly in me.polygons:
            m = old[min(poly.material_index, len(old) - 1)]
            u, v = uv_of[m["hex"]]
            for li in poly.loop_indices:
                uv.data[li].uv = (u, v)
            poly.material_index = kinds.index(m["kind"])
        me.materials.clear()
        for s in slots:
            me.materials.append(s)
    for m in list(bpy.data.materials):
        if "hex" in m:
            bpy.data.materials.remove(m)


def finalize():
    # 1) Aplica modificadores (biseles, booleanos, subdivisión, solidify) y borra cortadores.
    bpy.ops.object.select_all(action="DESELECT")
    cutters = set(C["Cutters"].objects)
    meshes = [o for o in bpy.data.objects if o.type == "MESH" and o not in cutters]
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.convert(target="MESH")
    for o in cutters:
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.data.collections.remove(C["Cutters"])
    # 2) Paleta única.
    palettize()
    # 3) Une mallas: lo estático por colección; coche y conductora por prefijo "Grupo__pieza"
    #    (ruedas, cabeza y sombrero quedan sueltos para animarlos en three.js).
    groups = {}
    for o in bpy.data.objects:
        if o.type != "MESH":
            continue
        key = o.name.split("__")[0] if "__" in o.name else o.users_collection[0].name
        groups.setdefault(key, []).append(o)
    for key, objs in groups.items():
        bpy.ops.object.select_all(action="DESELECT")
        for o in objs:
            o.select_set(True)
        bpy.context.view_layer.objects.active = objs[0]
        if len(objs) > 1:
            bpy.ops.object.join()
        objs[0].name = objs[0].data.name = key


# ---------- materiales: paleta Halloween pastel saturada (hex sRGB) ----------
wipe()
M = {
    "ground": mat("Ground", "#4E7A4C"), "grass_l": mat("GrassLight", "#66955A"),
    "grass_d": mat("GrassDark", "#3B6141"), "dirt": mat("Dirt", "#7A5A43"),
    "bank": mat("Bank", "#5B5068"), "cliff": mat("Cliff", "#6A6079"), "outside": mat("Outside", "#26343A"),
    "asphalt": mat("Asphalt", "#4B4459"), "kerb_r": mat("KerbRed", "#E2553F"), "kerb_w": mat("KerbWhite", "#F1ECE2"),
    "light": mat("EdgeLight", "#FFB04A", "glow"), "lamp": mat("Lamp", "#FFD27A", "glow"),
    "flame": mat("Flame", "#FF8A3D", "glow"), "window": mat("Window", "#FFC766", "glow"),
    "stone": mat("Stone", "#9089A0"), "stone_dark": mat("StoneDark", "#6E6880"), "roof": mat("Roof", "#5E4391"),
    "banner": mat("Banner", "#3E2A5C"), "shadow": mat("Shadow", "#1E1A26"), "gold": mat("Gold", "#E8B04A"),
    "pumpkin": mat("Pumpkin", "#F2862E"), "stem": mat("Stem", "#5E7A3A"),
    "water": mat("Water", "#3D7FA6", "gloss"), "foam": mat("Foam", "#CFE6F2"),
    "wood": mat("Wood", "#6E4C3B"), "leaves": mat("Leaves", "#E57A3C"), "leaves2": mat("Leaves2", "#C9513A"),
    "pine": mat("Pine", "#2E5048"), "mountain": mat("Mountain", "#2C2645"), "moon": mat("Moon", "#F3EBC8", "glow"),
    "car": mat("CarPaint", "#34303F", "gloss"), "car_glow": mat("CarGlow", "#FF9640", "glow"),
    "tyre": mat("Tyre", "#2A2733"), "rim": mat("Rim", "#57516B"), "glass": mat("Glass", "#4C5E7E", "gloss"),
    "cloth": mat("Cloth", "#45395A"), "cape_red": mat("CapeRed", "#C9413F"), "leather": mat("Leather", "#5A3B2E"),
    "iron": mat("Iron", "#2A2733"),
}
C = {k: collection(k) for k in ("Ground", "Outside", "Track", "Castle", "Walls", "Garden", "Props", "Sky",
                                "Car", "Driver", "Lights", "Cutters")}

# ---------- meseta, río y cascada ----------
pts, turns = centerline(CORNERS, FILLET_R)
river = catmull(RIVER, 1.0)
TRACK_S, RIVER_S = pts[::2], river[::2]

rock_base = box("PlateauRock", (0, 15, -3.4), (168, 152, 5.6), C["Ground"], M["cliff"])
grass_top = box("PlateauGrass", (0, 15, -0.3), (168.4, 152.4, 0.6), C["Ground"], M["ground"])
bm = bmesh.new()
ribbon_solid(bm, river, RIVER_W / 2 + 1.0, -2.2, 1.0)
cut = carve(rock_base, mesh_obj("RiverCut", bm, C["Cutters"], [M["bank"]]))
carve(grass_top, cut)
bm = bmesh.new()
ribbon(bm, [p for p in river if p.y > -61.2], -(RIVER_W / 2 + 1.0), RIVER_W / 2 + 1.0, z=-1.0, closed=False)
mesh_obj("River", bm, C["Garden"], [M["water"]])
rx0 = river[0].x
box("Waterfall", (rx0, -61.3, -3.6), (RIVER_W + 2, 0.5, 5.2), C["Garden"], M["foam"])
cyl("Pool", (rx0, -68, -6.1), 8, 0.2, C["Garden"], M["water"], verts=32)
for k in range(7):
    ball("Foam", (rx0 + random.uniform(-4, 4), -62.5 - random.uniform(0, 2), -5.8), random.uniform(0.7, 1.3),
         C["Garden"], M["foam"], (1, 1, 0.6))
for i in range(0, len(river), 7):  # rocas en las orillas
    p, nr = river[i], normal_at(river, i, closed=False)
    q = p + nr * (RIVER_W / 2 + 1.3) * random.choice((-1, 1))
    if -60 < q.y < 60 and nearest(TRACK_S, q.x, q.y) > EDGE + 3:
        rock(q.x, q.y, random.uniform(0.6, 1.1), C["Garden"], z=0.1)

# ---------- pista ----------
bm = bmesh.new()
ribbon(bm, pts, -ROAD_W / 2, ROAD_W / 2)
mesh_obj("Road", bm, C["Track"], [M["asphalt"]])
bm = bmesh.new()
stripe = lambda d: int(d // KERB_STRIPE) % 2
ribbon(bm, pts, ROAD_W / 2, EDGE, 0.04, mat_of=stripe)
ribbon(bm, pts, -EDGE, -ROAD_W / 2, 0.04, mat_of=stripe)
mesh_obj("Kerbs", bm, C["Track"], [M["kerb_r"], M["kerb_w"]])
bm = bmesh.new()
ribbon(bm, pts, EDGE, EDGE + 2.4, 0.012)
ribbon(bm, pts, -EDGE - 2.4, -EDGE, 0.012)
mesh_obj("Verges", bm, C["Track"], [M["grass_d"]])

bm, dist = bmesh.new(), 0.0
for i, p in enumerate(pts):
    if dist >= LIGHT_EVERY or i == 0:
        dist = 0.0
        for side in (-1, 1):
            q = p + normal_at(pts, i) * side * (EDGE + 0.5) + Vector((0, 0, 0.15))
            bmesh.ops.create_cube(bm, size=0.3, matrix=Matrix.Translation(q))
    dist += (pts[(i + 1) % len(pts)] - p).length
mesh_obj("EdgeLights", bm, C["Track"], [M["light"]])

for k in range(8):  # línea de salida a cuadros
    for row in range(2):
        box("StartCheck", (START.x - ROAD_W / 2 + 0.5 + k, START.y - 3 + row, 0.05), (1, 1, 0.04), C["Track"],
            M["kerb_w"] if (k + row) % 2 else M["tyre"], bevel=False)

dist = 0.0
for i, p in enumerate(pts):  # farolas a lo largo de la pista, alternando lados
    dist += (pts[i] - pts[i - 1]).length
    if dist >= 24:
        dist = 0.0
        q = p + normal_at(pts, i) * (EDGE + 3.4) * (1 if i % 2 else -1)
        if nearest(RIVER_S, q.x, q.y) > RIVER_W / 2 + 2.5 and (q - GATE).length > 15 and (q - START).length > 6:
            lantern(q.x, q.y, C["Props"])

# Línea central para el juego: puntos (x, y) en metros de Blender y giros por esquina
if HERE:
    with open(os.path.join(HERE, "track.json"), "w") as f:
        json.dump({"road_width": ROAD_W, "start": [START.x, START.y], "start_heading_deg": 90,
                   "turns": turns, "points": [[round(p.x, 3), round(p.y, 3)] for p in pts]}, f)

# ---------- puentes: la pista cruza el río ----------
for by in BRIDGES_Y:
    bx = min(river, key=lambda p: abs(p.y - by)).x
    span = RIVER_W + 7
    deck = box("BridgeDeck", (bx, by, -0.52), (span, 14.6, 1.0), C["Garden"], M["stone"])
    arch = cyl("BridgeArch", (bx, by, -1.95), 3.8, 18, C["Cutters"], M["stone_dark"], rot=(math.pi / 2, 0, 0), verts=32)
    arch.scale = (1, 0.45, 1)  # arco rebajado
    carve(deck, arch)
    for s in (-1, 1):
        box("BridgeParapet", (bx, by + s * 6.9, 0.45), (span, 0.55, 0.9), C["Garden"], M["stone"])
        for e in (-1, 1):
            box("BridgePillar", (bx + e * span / 2, by + s * 6.9, 0.7), (0.9, 0.9, 1.4), C["Garden"], M["stone"])
            lantern(bx + e * (span / 2 + 1.2), by + s * 6.9, C["Props"])

# ---------- murallas ----------
WALLS = {"S": ((X0, Y0), (X1, Y0), Vector((0, 1, 0))), "N": ((X0, Y1), (X1, Y1), Vector((0, -1, 0))),
         "W": ((X0, Y0), (X0, Y1), Vector((1, 0, 0))), "E": ((X1, Y0), (X1, Y1), Vector((-1, 0, 0)))}
TOWERS = [(X0, Y0), (X1, Y0), (X0, Y1), (X1, Y1), (X0, 0), (X1, 0), (-40, Y0), (0, Y0), (40, Y0)]
river_x_s = min(river, key=lambda p: abs(p.y - Y0)).x
river_x_n = min(river, key=lambda p: abs(p.y - Y1)).x
for key, (a, b, nrm) in WALLS.items():
    mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    size = (abs(b[0] - a[0]) or 2.5, abs(b[1] - a[1]) or 2.5, WH)
    w = box(f"Wall_{key}", (*mid, WH / 2), size, C["Walls"], M["stone"])
    if key in "SN":  # paso del río bajo la muralla
        rx = river_x_s if key == "S" else river_x_n
        carve(w, box("WallCut", (rx, mid[1], 0.6), (RIVER_W + 2, 5, 3.6), C["Cutters"], M["stone_dark"], bevel=False))
    merlons(a, b, WH, C["Walls"], thick=2.5)
    L = (Vector((*b, 0)) - Vector((*a, 0))).length
    for k in range(1, int(L / 16)):
        p = Vector((*a, 0)).lerp(Vector((*b, 0)), k * 16 / L) + nrm * 1.25
        if min(math.hypot(p.x - tx, p.y - ty) for tx, ty in TOWERS) < 6 or (key in "SN" and abs(p.x - rx) < 8):
            continue
        if k % 2:
            torch(p, nrm, 4.0, C["Walls"])
        else:
            banner(p, nrm, 3.4, C["Walls"])
for k, (tx, ty) in enumerate(TOWERS):
    tower(f"WallTower{k}", tx, ty, 3.4, 9 if k > 3 else 12, C["Walls"], roof=k < 4)
for k in range(13):  # calabazas talladas al pie de la muralla sur, mirando a la pista
    x = X0 + 8 + k * 12
    if abs(x - river_x_s) > 8:
        pumpkin("WallPumpkin", (x, Y0 + 2.4, 0.5), 0.7, C["Walls"], carved=True)

# ---------- castillo ----------
for name, (cx, cy), (w, d, h) in [("CastleHall", (25, 72), (90, 22, 18)), ("CastleKeep", (35, 74), (26, 14, 30)),
                                  ("CastleWing", (-8, 70), (20, 14, 24))]:
    box(name, (cx, cy, h / 2), (w, d, h), C["Castle"], M["stone"])
    yf = cy - d / 2
    merlons((cx - w / 2, yf + 0.5), (cx + w / 2, yf + 0.5), h, C["Castle"])
    merlons((cx - w / 2 + 0.5, yf), (cx - w / 2 + 0.5, cy + d / 2), h, C["Castle"])
    merlons((cx + w / 2 - 0.5, yf), (cx + w / 2 - 0.5, cy + d / 2), h, C["Castle"])
CASTLE_TOWERS = [(-20, 61, 4.2, 28), (-6, 62, 3.6, 34), (18, 61, 4.0, 30), (56, 61, 4.4, 36), (70, 61, 4.2, 26)]
for k, (tx, ty, r, h) in enumerate(CASTLE_TOWERS):
    tower(f"CastleTower{k}", tx, ty, r, h, C["Castle"], windows=3)
for k, (sx, sy) in enumerate([(22, 67), (48, 67), (22, 81), (48, 81)]):
    tower(f"KeepSpire{k}", sx, sy, 1.6, 36, C["Castle"], windows=1)
for z in (5.5, 11.5):
    for x in range(-16, 67, 5):
        if min(abs(x - t[0]) for t in CASTLE_TOWERS) > 5.5 and not (z < 8 and abs(x - river_x_n) < 7):
            arch_window(x, 60.85, z, C["Castle"])
for z in (20, 26):
    for x in range(26, 45, 4):
        arch_window(x, 66.85, z, C["Castle"])
box("WaterGate", (river_x_n, 60.9, 1.5), (9, 0.4, 3.0), C["Castle"], M["shadow"])
cyl("WaterGateTop", (river_x_n, 60.9, 3.0), 4.5, 0.4, C["Castle"], M["shadow"], rot=(math.pi / 2, 0, 0), verts=32)

# Puerta: arco real por el que pasa la pista
gx, gy = GATE.x, GATE.y
gate = box("GateArch", (gx, gy, 9), (24, 6, 18), C["Castle"], M["stone"])
carve(gate, box("GateCut", (gx, gy, 3.0), (13, 8, 7), C["Cutters"], M["stone_dark"], bevel=False))
carve(gate, cyl("GateCutTop", (gx, gy, 6.5), 6.5, 8, C["Cutters"], M["stone_dark"], rot=(math.pi / 2, 0, 0), verts=32))
merlons((gx - 12, gy - 2.5), (gx + 12, gy - 2.5), 18, C["Castle"])
merlons((gx - 12, gy + 2.5), (gx + 12, gy + 2.5), 18, C["Castle"])
for s in (-1, 1):
    tower(f"GateTower{s}", gx + s * 13.5, gy, 4.2, 24, C["Castle"], windows=2)
    box(f"GateWall{s}", (gx + s * 13.5, (gy + 3 + Y1) / 2, WH / 2), (2.5, Y1 - gy - 3, WH), C["Castle"], M["stone"])
    banner(Vector((gx + s * 13.5, gy - 4.2, 0)), Vector((0, -1, 0)), 12, C["Castle"])
    torch(Vector((gx + s * 8, gy - 3, 0)), Vector((0, -1, 0)), 6.0, C["Castle"])
    torch(Vector((gx + s * 8, gy + 3, 0)), Vector((0, 1, 0)), 6.0, C["Castle"])
    pumpkin("GatePumpkin", (gx + s * 9.5, gy - 6.5, 0.9), 1.1, C["Castle"], carved=True, face=math.pi)
taken += [(gx, gy, 16)]

# ---------- jardín ----------
gc = C["Garden"]
# Rotonda con la calabaza gigante
RB = (-25, 2)
cyl("RoundaboutRing", (*RB, 0.17), 9, 0.35, gc, M["stone"], verts=48)
cyl("RoundaboutLawn", (*RB, 0.22), 8, 0.45, gc, M["grass_l"], verts=48)
pumpkin("GiantPumpkin", (*RB, 3.3), 3.6, gc, carved=True, face=math.pi)
for k in range(10):
    a = 2 * math.pi * k / 10
    pumpkin("RingPumpkin", (RB[0] + math.cos(a) * 6.5, RB[1] + math.sin(a) * 6.5, 0.85), 0.55, gc,
            carved=k % 3 == 0, face=a + math.pi / 2)
taken.append((*RB, 9.5))

# Cementerio vallado con cripta
G0, G1 = (-54, 3), (-40, 29)
fence(G0, (G1[0], G0[1]), gc)
fence((G1[0], G0[1]), (G1[0], 13), gc)
fence((G1[0], 18), G1, gc)
fence(G1, (G0[0], G1[1]), gc)
fence((G0[0], G1[1]), G0, gc)
for x in range(-52, -41, 3):
    for y in range(6, 23, 4):
        if random.random() > 0.25:
            tomb(x + random.uniform(-0.4, 0.4), y + random.uniform(-0.4, 0.4), random.uniform(-0.25, 0.25), gc)
box("Crypt", (-47, 26, 1.8), (5, 3.5, 3.6), gc, M["stone_dark"])
cone("CryptRoof", (-47, 26, 4.4), 3.6, 1.8, gc, M["roof"], rot=(0, 0, math.pi / 4), verts=4)
box("CryptDoor", (-47, 24.2, 1.2), (1.4, 0.1, 2.2), gc, M["shadow"])
dead_tree(-51, 26, 1.0, gc)
dead_tree(-43, 8, 0.9, gc)
taken.append((-47, 16, 15))

# Relleno: manchas de suelo, montículos, árboles, arbustos, rocas y calabazas
for _ in range(30):
    x, y = random.uniform(X0 + 4, X1 - 4), random.uniform(Y0 + 4, Y1 - 4)
    if free(x, y, 2):
        cyl("Patch", (x, y, 0.01), random.uniform(2, 4), 0.04, gc,
            random.choice((M["dirt"], M["grass_l"], M["grass_d"])), verts=12)
for _ in range(10):
    s = spot(4)
    if s:
        ball("Mound", (*s, 0), random.uniform(3, 4.5), gc, M["grass_l"], (1, 1, 0.22))
trees = [s for s in (spot(3) for _ in range(20)) if s]
for x, y in trees:
    autumn_tree(x, y, random.uniform(0.85, 1.2), gc)
for _ in range(8):
    s = spot(2)
    if s:
        dead_tree(*s, random.uniform(0.8, 1.1), gc)
for _ in range(30):
    s = spot(1.3)
    if s:
        bush(*s, random.uniform(0.8, 1.2), gc)
for _ in range(16):
    s = spot(1)
    if s:
        rock(*s, random.uniform(0.5, 1.0), gc)
for _ in range(14):
    s = spot(1.5)
    if s:
        for k in range(random.randint(2, 3)):
            r = random.uniform(0.45, 0.8)
            pumpkin("Pumpkin", (s[0] + random.uniform(-1, 1), s[1] + random.uniform(-1, 1), r * 0.75), r, gc,
                    carved=k == 0 and random.random() < 0.5, face=random.uniform(0, 2 * math.pi))
for i in range(0, len(pts), len(pts) // 10):  # calabazas talladas junto a la pista, mirando a ella
    side = 1 if (i // 10) % 2 else -1
    nr = normal_at(pts, i) * side
    q = pts[i] + nr * (EDGE + 2.8)
    if nearest(RIVER_S, q.x, q.y) > RIVER_W / 2 + 2 and (q - GATE).length > 15:
        to_road = -nr
        pumpkin("TrackPumpkin", (q.x, q.y, 0.6), 0.75, gc, carved=True,
                face=math.atan2(to_road.y, to_road.x) - math.pi / 2)

# Hojas caídas bajo los árboles: una sola malla de cuadraditos naranjas
bm = bmesh.new()
for x, y in trees:
    for _ in range(30):
        a, d = random.uniform(0, 2 * math.pi), random.uniform(0.5, 4.5)
        c = Vector((x + math.cos(a) * d, y + math.sin(a) * d, 0.03))
        if nearest(TRACK_S, c.x, c.y) < ROAD_W / 2 + 0.5:
            continue
        rz = random.uniform(0, math.pi)
        quad = [bm.verts.new(c + Matrix.Rotation(rz, 3, "Z") @ Vector(v)) for v in
                ((-0.18, -0.12, 0), (0.18, -0.12, 0), (0.18, 0.12, 0), (-0.18, 0.12, 0))]
        bm.faces.new(quad).material_index = random.randint(0, 1)
mesh_obj("FallenLeaves", bm, gc, [M["leaves"], M["leaves2"]])

# ---------- entorno: bosque bajo la meseta, montañas, luna y murciélagos ----------
oc = C["Outside"]
box("OutsideGround", (0, 15, -6.3), (600, 600, 0.2), oc, M["outside"], bevel=False)
n = 0
while n < 160:
    x, y = random.uniform(-190, 190), random.uniform(-170, 210)
    if abs(x) < 92 and -69 < y < 99:
        continue
    pine(x, y, random.uniform(1.2, 2.2), -6.2, oc)
    n += 1
for k in range(18):  # sierra lejana, baja y facetada; la niebla de three.js la difumina
    a = 2 * math.pi * k / 18 + random.uniform(-0.1, 0.1)
    h = random.uniform(28, 55)
    cone("Mountain", (math.cos(a) * 360, 15 + math.sin(a) * 360, -6 + h / 2), random.uniform(55, 85), h, oc,
         M["mountain"], verts=9, bevel=False)
ball("Moon", (90, 320, 140), 22, C["Sky"], M["moon"], segs=24)
for k in range(16):
    prism("Bat", BAT, 0.06, (random.uniform(-20, 80), random.uniform(48, 92), random.uniform(22, 40)), C["Sky"],
          M["iron"], rot=(random.uniform(-0.4, 0.4), 0, random.uniform(0, 2 * math.pi)), scale=random.uniform(1.2, 2.0))

# ---------- coche: roadster negro de juguete (vacío padre "Car" que mueve three.js) ----------
car = bpy.data.objects.new("Car", None)
C["Car"].objects.link(car)
car.location = START  # rumbo +Y (norte)
cc = C["Car"]
loft("CarBody__shell", [(2.15, 0.8, 0.42, 0.66), (1.9, 1.0, 0.32, 0.84), (1.1, 1.05, 0.28, 1.0),
                        (0.5, 1.05, 0.28, 1.04), (0.3, 1.05, 0.28, 0.86), (-0.85, 1.05, 0.28, 0.86),
                        (-1.1, 1.05, 0.28, 1.1), (-1.85, 1.0, 0.32, 1.06), (-2.15, 0.88, 0.45, 0.92)],
     cc, M["car"], parent=car)
box("CarBody__tub", (0, -0.3, 0.86), (1.6, 1.3, 0.1), cc, M["cloth"], parent=car)
for s in (-1, 1):
    ball("CarBody__fender", (s * 0.97, 1.3, 0.78), 0.55, cc, M["car"], (0.35, 1.1, 0.55), parent=car, segs=16)
    ball("CarBody__fenderR", (s * 0.97, -1.3, 0.8), 0.55, cc, M["car"], (0.38, 1.15, 0.6), parent=car, segs=16)
    box("CarBody__vent", (s * 0.35, 1.25, 0.99), (0.35, 0.6, 0.05), cc, M["tyre"], rot=(math.radians(-6), 0, 0), parent=car)
    # faros rasgados siguiendo la curva del morro y tomas en V hacia el murciélago
    box("CarBody__headlight", (s * 0.56, 2.0, 0.78), (0.55, 0.1, 0.09), cc, M["car_glow"],
        rot=(0, s * 0.12, -s * 0.35), parent=car)
    limb("CarBody__intake", (s * 0.86, 1.94, 0.66), (s * 0.5, 2.1, 0.34), 0.03, cc, M["car_glow"], parent=car)
    limb("CarBody__intakeLow", (s * 0.5, 2.1, 0.34), (s * 0.18, 2.13, 0.34), 0.03, cc, M["car_glow"], parent=car)
    box("CarBody__sideglow", (s * 1.02, 0, 0.38), (0.05, 3.0, 0.06), cc, M["car_glow"], parent=car)
    box("CarBody__taillight", (s * 0.55, -2.13, 0.8), (0.5, 0.06, 0.1), cc, M["car_glow"], parent=car)
    limb("CarBody__mirrorArm", (s * 0.9, 0.5, 0.98), (s * 1.12, 0.45, 1.1), 0.03, cc, M["car"], parent=car)
    box("CarBody__mirror", (s * 1.15, 0.45, 1.12), (0.22, 0.1, 0.14), cc, M["car"], parent=car)
    box("CarBody__seat", (s * 0.45, -0.45, 0.98), (0.6, 0.55, 0.2), cc, M["cloth"], parent=car)
    box("CarBody__seatBack", (s * 0.45, -0.72, 1.3), (0.6, 0.15, 0.7), cc, M["cloth"],
        rot=(math.radians(-10), 0, 0), parent=car)
    box("CarBody__spoilerPost", (s * 0.7, -1.9, 1.3), (0.12, 0.2, 0.35), cc, M["car"], parent=car)
    for e, y in (("F", 1.3), ("R", -1.3)):
        wn = f"Wheel{e}{'L' if s < 0 else 'R'}"  # grupo suelto: three.js lo hace girar
        cyl(f"{wn}__tyre", (s * 0.97, y, 0.46), 0.46, 0.38, cc, M["tyre"], rot=(0, math.pi / 2, 0), parent=car)
        cyl(f"{wn}__rim", (s * 0.99, y, 0.46), 0.29, 0.4, cc, M["rim"], rot=(0, math.pi / 2, 0), parent=car)
        cyl(f"{wn}__brake", (s * 1.0, y, 0.46), 0.13, 0.41, cc, M["car_glow"], rot=(0, math.pi / 2, 0), parent=car)
box("CarBody__spoiler", (0, -1.95, 1.5), (2.0, 0.45, 0.1), cc, M["car"], parent=car)
box("CarBody__windshield", (0, 0.55, 1.2), (1.6, 0.06, 0.38), cc, M["glass"], rot=(math.radians(-40), 0, 0), parent=car)
prism("CarBody__bat", BAT, 0.05, (0, 2.15, 0.55), cc, M["car_glow"], parent=car, scale=0.28)
torus("SteeringWheel__ring", (-0.45, 0.25, 1.32), 0.22, 0.035, cc, M["tyre"], rot=(math.radians(65), 0, 0), parent=car)
limb("SteeringWheel__column", (-0.45, 0.25, 1.32), (-0.45, 0.6, 1.0), 0.04, cc, M["tyre"], parent=car)

# ---------- conductora: calabaza tallada, sombrero torcido, capa y manoplas ----------
dc = C["Driver"]
drv = bpy.data.objects.new("Driver", None)
dc.objects.link(drv)
drv.parent = car
drv.location = (-0.45, -0.4, 0)  # asiento izquierdo
ball("DriverBody__bean", (0, 0, 1.38), 0.3, dc, M["cloth"], (1, 0.85, 1.3), parent=drv, segs=16)
for s in (-1, 1):
    limb("DriverBody__arm", (s * 0.27, 0.02, 1.6), (s * 0.18, 0.6, 1.4), 0.085, dc, M["cloth"], parent=drv)
    ball("DriverBody__mitten", (s * 0.18, 0.62, 1.4), 0.11, dc, M["leather"], parent=drv, segs=16)
cape("DriverBody__cape", (0, 0, 1.78), dc, parent=drv)
prism("DriverBody__collar", [(-0.45, 0), (0.45, 0), (0.6, 0.45), (0.25, 0.2), (0, 0.35), (-0.25, 0.2), (-0.6, 0.45)],
      0.05, (0, -0.24, 1.72), dc, M["cape_red"], rot=(math.radians(-15), 0, 0), parent=drv)
pumpkin("DriverHead__pumpkin", (0, 0, 2.1), 0.44, dc, carved=True, parent=drv)
cyl("DriverHat__brim", (0, 0, 2.42), 0.72, 0.06, dc, M["cloth"], parent=drv)
cyl("DriverHat__band", (0, 0, 2.52), 0.335, 0.13, dc, M["roof"], parent=drv)
box("DriverHat__buckle", (0, 0.33, 2.52), (0.16, 0.04, 0.12), dc, M["gold"], parent=drv)
witch_hat("DriverHat__cone", (0, -0.03, 2.45), 0.32, 1.1, 0.35, dc, M["cloth"], parent=drv)

# ---------- luz de luna, cielo y cámara de persecución ----------
sun = add_light("Moonlight", "SUN", rot=(math.radians(50), 0, math.radians(200)))
sun.data.energy, sun.data.color, sun.data.angle = 2.0, (0.72, 0.78, 1.0), math.radians(8)
world = bpy.context.scene.world or bpy.data.worlds.new("World")
bpy.context.scene.world = world
world.use_nodes = True
bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
bg.inputs["Color"].default_value = (0.05, 0.045, 0.11, 1)
bg.inputs["Strength"].default_value = 1.5

cam = bpy.data.objects.new("ChaseCam", bpy.data.cameras.new("ChaseCam"))
C["Car"].objects.link(cam)
cam.location, cam.rotation_euler, cam.parent = (0, -10, 6), (math.radians(73), 0, 0), car
bpy.context.scene.camera = cam

finalize()
print("ok", len(bpy.data.objects), "objetos,", len(pts), "puntos de pista, giros:", turns)
