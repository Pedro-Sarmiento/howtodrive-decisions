# Maqueta de bloques del circuito (referencias en assets/).
# Uso en Blender: exec(open("<ruta>/blender/blockout.py").read())
# Regenera la escena entera (borra todo lo que haya) y escribe blender/track.json.
import bpy
import bmesh
import json
import math
import os
import random
from mathutils import Matrix, Vector

random.seed(31)  # 31-oct: misma maqueta en cada ejecución
HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in dir() else None

ROAD_W = 8.0      # ancho de calzada
KERB_W = 0.9      # piano rojo/blanco a cada lado
KERB_STRIPE = 2.0 # largo de cada franja
FILLET_R = 8.0    # radio de las curvas (línea central)
LIGHT_EVERY = 5.0 # metros entre luces de borde

# Esquinas del bucle, sentido horario empezando por la salida (oeste, rumbo norte).
# Todas a 90°: cada curva es una orden "left"/"right"; rectas >= 20 m por la latencia de Kev.
CORNERS = [
    (-65, -10), (-65, 40), (-30, 40), (-30, 20), (25, 20), (25, 45),
    (65, 45), (65, -40), (25, -40), (25, -10), (-10, -10), (-10, -40),
    (-40, -40), (-40, -10),
]
START = Vector((-65, 8, 0))  # en la recta oeste, mirando al norte
GATE = Vector((45, 45, 0))   # la pista cruza la puerta del castillo aquí


# ---------- utilidades ----------
def wipe():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.lights, bpy.data.cameras, bpy.data.curves):
        for block in list(coll):
            if block.users == 0:
                coll.remove(block)


def mat(name, rgb, rough=0.8, emit=0.0, metal=0.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (*rgb, 1)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if emit:
        bsdf.inputs["Emission Color"].default_value = (*rgb, 1)
        bsdf.inputs["Emission Strength"].default_value = emit
    m.diffuse_color = (*rgb, 1)
    return m


def collection(name):
    c = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    if c.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(c)
    return c


def put(obj, coll, material, name=None, parent=None):
    for c in obj.users_collection:
        c.objects.unlink(obj)
    coll.objects.link(obj)
    obj.data.materials.append(material)
    if name:
        obj.name = name
    if parent:
        obj.parent = parent
    return obj


def box(name, loc, size, coll, material, rot=(0, 0, 0), parent=None):
    # Escala en la malla, no con transform_apply: en 5.2 también hornea la posición
    # y deja el origen en (0,0,0), lo que rompe mover/girar el objeto en three.js.
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.object
    o.data.transform(Matrix.Diagonal((*size, 1)))
    return put(o, coll, material, name, parent)


def cyl(name, loc, r, depth, coll, material, rot=(0, 0, 0), verts=24, parent=None):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth, location=loc, rotation=rot)
    return put(bpy.context.object, coll, material, name, parent)


def cone(name, loc, r, depth, coll, material, rot=(0, 0, 0), parent=None):
    bpy.ops.mesh.primitive_cone_add(radius1=r, depth=depth, location=loc, rotation=rot)
    return put(bpy.context.object, coll, material, name, parent)


def ball(name, loc, r, coll, material, scale=(1, 1, 1), parent=None):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=16, ring_count=10)
    o = put(bpy.context.object, coll, material, name, parent)
    o.scale = scale
    return o


def mesh_obj(name, bm, coll, materials):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    coll.objects.link(o)
    for m in materials:
        me.materials.append(m)
    return o


# ---------- línea central con curvas redondeadas ----------
def centerline(corners, r, step=1.0):
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


def strip(bm, pts, off_in, off_out, z=0.02, mat_of=None):
    # Cinta paralela a la línea central entre dos desplazamientos (negativo = derecha).
    n, dist, faces = len(pts), 0.0, []
    def edge(i, off):
        p = pts[i]
        t = (pts[(i + 1) % n] - pts[i - 1]).normalized()
        return bm.verts.new(p + Vector((-t.y, t.x, 0)) * off + Vector((0, 0, z)))
    rows = [(edge(i, off_in), edge(i, off_out)) for i in range(n)]
    for i in range(n):
        (a, b), (c, d) = rows[i], rows[(i + 1) % n]
        f = bm.faces.new((a, b, d, c) if off_out > off_in else (b, a, c, d))
        if mat_of:
            f.material_index = mat_of(dist)
        dist += (pts[(i + 1) % n] - pts[i]).length


# ---------- escena ----------
wipe()
M = {
    "ground": mat("Ground", (0.04, 0.045, 0.03)),
    "outside": mat("Outside", (0.015, 0.02, 0.025)),
    "asphalt": mat("Asphalt", (0.05, 0.045, 0.05), rough=0.5),
    "kerb_r": mat("KerbRed", (0.75, 0.05, 0.03)),
    "kerb_w": mat("KerbWhite", (0.85, 0.85, 0.85)),
    "light": mat("EdgeLight", (1.0, 0.45, 0.08), emit=6.0),
    "stone": mat("Stone", (0.2, 0.18, 0.2)),
    "roof": mat("Roof", (0.07, 0.05, 0.1)),
    "window": mat("Window", (1.0, 0.55, 0.12), emit=5.0),
    "banner": mat("Banner", (0.06, 0.03, 0.05)),
    "pumpkin": mat("Pumpkin", (0.95, 0.38, 0.03), emit=1.5),
    "water": mat("Water", (0.02, 0.04, 0.07), rough=0.05),
    "wood": mat("DeadWood", (0.07, 0.05, 0.04)),
    "leaves": mat("AutumnLeaves", (0.6, 0.18, 0.03)),
    "car": mat("CarBody", (0.02, 0.02, 0.025), rough=0.25, metal=0.6),
    "car_glow": mat("CarGlow", (1.0, 0.4, 0.05), emit=8.0),
    "tyre": mat("Tyre", (0.01, 0.01, 0.01)),
    "glass": mat("Glass", (0.05, 0.05, 0.08), rough=0.05),
    "cloth": mat("Cloth", (0.02, 0.015, 0.02)),
    "cape_red": mat("CapeRed", (0.45, 0.02, 0.02)),
}
C = {k: collection(k) for k in ("Ground", "Track", "Castle", "Walls", "Garden", "Car", "Driver")}

# Suelo: dentro del recinto y bosque oscuro fuera
box("Outside", (0, 10, -0.2), (260, 240, 0.2), C["Ground"], M["outside"])
box("Ground", (0, 0, -0.05), (156, 112, 0.1), C["Ground"], M["ground"])

# Pista
pts, turns = centerline(CORNERS, FILLET_R)
bm = bmesh.new()
strip(bm, pts, -ROAD_W / 2, ROAD_W / 2)
mesh_obj("Road", bm, C["Track"], [M["asphalt"]])
bm = bmesh.new()
stripe = lambda d: int(d // KERB_STRIPE) % 2
strip(bm, pts, ROAD_W / 2, ROAD_W / 2 + KERB_W, 0.04, stripe)
strip(bm, pts, -ROAD_W / 2, -ROAD_W / 2 - KERB_W, 0.04, stripe)
mesh_obj("Kerbs", bm, C["Track"], [M["kerb_r"], M["kerb_w"]])

bm, dist = bmesh.new(), 0.0
for i, p in enumerate(pts):
    t = (pts[(i + 1) % len(pts)] - pts[i - 1]).normalized()
    nrm = Vector((-t.y, t.x, 0))
    if dist >= LIGHT_EVERY or i == 0:
        dist = 0.0
        for side in (-1, 1):
            q = p + nrm * side * (ROAD_W / 2 + KERB_W + 0.5) + Vector((0, 0, 0.15))
            bmesh.ops.create_cube(bm, size=0.3, matrix=Matrix.Translation(q))
    dist += (pts[(i + 1) % len(pts)] - p).length
mesh_obj("EdgeLights", bm, C["Track"], [M["light"]])

box("StartLine", START + Vector((0, -3, 0.05)), (ROAD_W, 0.8, 0.02), C["Track"], M["kerb_w"])

# Línea central para el juego: puntos (x, y) en metros de Blender y giros por esquina
if HERE:
    with open(os.path.join(HERE, "track.json"), "w") as f:
        json.dump({"road_width": ROAD_W, "start": [START.x, START.y], "start_heading_deg": 90,
                   "turns": turns, "points": [[round(p.x, 3), round(p.y, 3)] for p in pts]}, f)

# Murallas del recinto con torres, almenas, antorchas y calabazas
X0, X1, Y0, Y1, WH = -78, 78, -56, 56, 6.0
for name, loc, size in [
    ("Wall_S", (0, Y0, WH / 2), (X1 - X0, 2.5, WH)),
    ("Wall_W", (X0, 0, WH / 2), (2.5, Y1 - Y0, WH)),
    ("Wall_E", (X1, 0, WH / 2), (2.5, Y1 - Y0, WH)),
    ("Wall_N", (0, Y1, WH / 2), (X1 - X0, 2.5, WH)),
]:
    box(name, loc, size, C["Walls"], M["stone"])
for k, (tx, ty) in enumerate([(X0, Y0), (X1, Y0), (X0, Y1), (X1, Y1), (X0, 0), (X1, 0),
                              (-40, Y0), (0, Y0), (40, Y0)]):
    cyl(f"WallTower_{k}", (tx, ty, 5), 3.2, 10, C["Walls"], M["stone"])
    cone(f"WallTowerRoof_{k}", (tx, ty, 13), 3.9, 6, C["Walls"], M["roof"])
for k in range(24):  # calabazas sobre la muralla sur, mirando a la pista
    ball("WallPumpkin", (X0 + 6 + k * 6.3, Y0 + 1.5, WH + 0.5), 0.7, C["Walls"], M["pumpkin"], (1, 1, 0.8))

# Castillo al norte: la pista pasa bajo la puerta en GATE
CY = 72
box("CastleBody", (25, CY, 11), (90, 22, 22), C["Castle"], M["stone"])
box("Keep", (35, CY + 4, 22), (24, 14, 22), C["Castle"], M["stone"])
for k, tx in enumerate((-15, 5, 20, 50, 65)):
    h = 26 + (k % 2) * 8
    cyl(f"CastleTower_{k}", (tx, CY - 9, h / 2), 4, h, C["Castle"], M["stone"])
    cone(f"CastleTowerRoof_{k}", (tx, CY - 9, h + 5), 4.8, 10, C["Castle"], M["roof"])
    for w in range(3):
        box(f"CastleWindow_{k}{w}", (tx, CY - 13.05, 8 + w * 7), (1.2, 0.2, 2.2), C["Castle"], M["window"])
gx, gy = GATE.x, GATE.y
for side in (-1, 1):  # torreones de la puerta, a los lados de la pista
    cyl(f"GateTower_{side}", (gx + side * 9, gy, 8), 3.6, 16, C["Castle"], M["stone"])
    cone(f"GateTowerRoof_{side}", (gx + side * 9, gy, 20), 4.4, 8, C["Castle"], M["roof"])
    box(f"GateWall_{side}", (gx + side * 7, gy + 5, 6), (5, 12, 12), C["Castle"], M["stone"])
    box(f"Banner_{side}", (gx + side * 9, gy - 3.7, 8), (2.4, 0.15, 5), C["Castle"], M["banner"])
box("GateArch", (gx, gy, 11), (18, 6, 6), C["Castle"], M["stone"])
box("GateGlow", (gx, gy - 3.05, 8.2), (8, 0.1, 0.6), C["Castle"], M["window"])
box("GateLink", (gx, gy + 9, 8), (18, 8, 16), C["Castle"], M["stone"])

# Foso en el hueco sur entre las dos rectas interiores
box("Moat", (7.5, -35, -0.3), (15, 38, 0.2), C["Garden"], M["water"])
for side, x in (("W", -1.2), ("E", 16.2)):
    box(f"MoatParapet_{side}", (x, -35, 0.5), (0.8, 38, 1.0), C["Garden"], M["stone"])

# Jardín central: rotonda con la calabaza gigante
cyl("Roundabout", (-2, 5, 0.15), 9, 0.3, C["Garden"], M["stone"], verts=48)
ball("GiantPumpkin", (-2, 5, 3.2), 4, C["Garden"], M["pumpkin"], (1, 1, 0.8))
cyl("GiantPumpkinStem", (-2, 5, 6.6), 0.5, 1.6, C["Garden"], M["wood"])

# Árboles otoñales y árboles secos en las zonas libres
for k, (x, y) in enumerate([(-52, 28), (-50, -30), (-25, -25), (40, 5), (52, -25), (45, 30),
                            (-55, 50), (5, 32), (-20, 30), (35, -50), (-60, -50), (60, 25)]):
    cyl(f"Trunk_{k}", (x, y, 1.5), 0.35, 3, C["Garden"], M["wood"], verts=8)
    if k % 3:
        ball(f"Crown_{k}", (x, y, 4.2), 2.6, C["Garden"], M["leaves"])
    else:
        cone(f"DeadTop_{k}", (x, y, 5), 0.3, 4, C["Garden"], M["wood"])
for k in range(30):  # calabazas sueltas fuera de la pista
    x, y = random.uniform(-72, 72), random.uniform(-50, 50)
    if min((Vector((x, y, 0)) - p).length for p in pts[::4]) > ROAD_W / 2 + 3:
        ball(f"Pumpkin_{k}", (x, y, 0.45), 0.6, C["Garden"], M["pumpkin"], (1, 1, 0.75))

# ---------- coche (roadster negro) ----------
car = bpy.data.objects.new("Car", None)  # vacío padre: three.js mueve y gira este nodo
C["Car"].objects.link(car)
car.location = START
car.rotation_euler = (0, 0, 0)  # rumbo +Y (norte)
cc = C["Car"]
box("CarBody", (0, 0, 0.55), (1.95, 4.5, 0.6), cc, M["car"], parent=car)
box("CarNose", (0, 1.75, 0.8), (1.85, 1.2, 0.3), cc, M["car"], rot=(math.radians(-12), 0, 0), parent=car)
box("CarDeck", (0, -1.5, 0.95), (1.8, 1.4, 0.25), cc, M["car"], parent=car)
box("CarSpoiler", (0, -2.15, 1.3), (1.9, 0.35, 0.08), cc, M["car"], parent=car)
box("CarWindshield", (0, 0.65, 1.1), (1.6, 0.08, 0.5), cc, M["glass"], rot=(math.radians(-35), 0, 0), parent=car)
for side in (-1, 1):
    box(f"CarSeat_{side}", (side * 0.45, -0.45, 0.95), (0.55, 0.5, 0.7), cc, M["cloth"], parent=car)
    box(f"CarHeadlight_{side}", (side * 0.65, 2.27, 0.75), (0.45, 0.06, 0.1), cc, M["car_glow"], parent=car)
    box(f"CarSideGlow_{side}", (side * 0.99, 0, 0.32), (0.04, 3.6, 0.05), cc, M["car_glow"], parent=car)
    for end, y in (("F", 1.45), ("R", -1.4)):
        cyl(f"Wheel_{end}{side}", (side * 0.92, y, 0.36), 0.36, 0.32, cc, M["tyre"],
            rot=(0, math.radians(90), 0), parent=car)

# ---------- conductora: cabeza de calabaza con sombrero de bruja ----------
dc = C["Driver"]
drv = bpy.data.objects.new("Driver", None)
dc.objects.link(drv)
drv.parent = car
drv.location = (-0.45, -0.4, 0)  # asiento izquierdo
box("DriverTorso", (0, 0, 1.45), (0.5, 0.32, 0.65), dc, M["cloth"], parent=drv)
box("DriverCape", (0, -0.2, 1.4), (0.7, 0.08, 0.8), dc, M["cape_red"], parent=drv)
for side in (-1, 1):
    box(f"DriverArm_{side}", (side * 0.22, 0.35, 1.45), (0.12, 0.6, 0.12), dc, M["cloth"],
        rot=(math.radians(-20), 0, 0), parent=drv)
cyl("SteeringWheel", (0, 0.65, 1.35), 0.18, 0.04, dc, M["tyre"], rot=(math.radians(70), 0, 0), parent=drv)
ball("DriverHead", (0, 0, 2.0), 0.3, dc, M["pumpkin"], (1, 1, 0.85), parent=drv)
box("DriverFace", (0, 0.27, 2.0), (0.3, 0.05, 0.12), dc, M["window"], parent=drv)
cyl("HatBrim", (0, 0, 2.25), 0.5, 0.03, dc, M["cloth"], parent=drv)
cone("HatTop", (0, -0.05, 2.6), 0.25, 0.7, dc, M["cloth"], rot=(math.radians(-15), 0, 0), parent=drv)

# ---------- luz de luna, cielo y cámara de persecución ----------
bpy.ops.object.light_add(type="SUN", rotation=(math.radians(55), 0, math.radians(200)))
bpy.context.object.data.energy = 1.2
bpy.context.object.data.color = (0.6, 0.65, 1.0)
world = bpy.context.scene.world or bpy.data.worlds.new("World")
bpy.context.scene.world = world
world.use_nodes = True
bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
bg.inputs["Color"].default_value = (0.03, 0.02, 0.07, 1)

bpy.ops.object.camera_add(location=(0, -10, 6), rotation=(math.radians(73), 0, 0))
cam = bpy.context.object
cam.name = "ChaseCam"
cam.parent = car
bpy.context.scene.camera = cam
print("ok", len(bpy.data.objects), "objetos,", len(pts), "puntos de pista, giros:", turns)
