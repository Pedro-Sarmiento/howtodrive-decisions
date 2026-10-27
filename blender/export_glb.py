# Exporta circuito.blend a web/public/scene.glb (Draco, sin luces ni cámara).
# Uso: /Applications/Blender.app/Contents/MacOS/Blender -b blender/circuito.blend --python blender/export_glb.py
import bpy, os
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(os.path.join(HERE, "..", "web", "public", "scene.glb"))
os.makedirs(os.path.dirname(OUT), exist_ok=True)
# El .blend guarda la paleta con una ruta absoluta de otro worktree: sin esto el exportador
# no encuentra la imagen y el GLB sale con un solo material sin textura ni emisión.
for img in bpy.data.images:
    if img.name == "Palette":
        img.filepath = os.path.join(HERE, "palette.png")
        img.reload()
# Las luces de las farolas solo sirven para previsualizar en Blender.
for o in list(bpy.data.objects):
    if o.type in ("LIGHT", "CAMERA"):
        bpy.data.objects.remove(o, do_unlink=True)
bpy.ops.export_scene.gltf(
    filepath=OUT, export_format="GLB", use_selection=False,
    export_apply=True, export_yup=True,
    export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=6,
    export_image_format="AUTO", export_texcoords=True, export_normals=True,
    export_materials="EXPORT", export_lights=False, export_cameras=False, export_animations=False,
)
print("GLB", OUT, os.path.getsize(OUT), "bytes")
print("OBJETOS", sorted(o.name for o in bpy.data.objects))
