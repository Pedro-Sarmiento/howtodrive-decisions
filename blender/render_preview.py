import bpy, math, os
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
from mathutils import Vector
s=bpy.context.scene
s.render.engine='CYCLES'
s.cycles.samples=12
s.render.resolution_x=1080
s.render.resolution_y=1080
s.render.resolution_percentage=100
for im in bpy.data.images:
 if im.name=='Palette':
  im.filepath=os.path.join(ROOT,'blender/palette.png')
  im.reload()
cam=bpy.data.objects.new('VideoCamera',bpy.data.cameras.new('VideoCamera'))
s.collection.objects.link(cam)
cam.location=(130,-160,150)
cam.rotation_euler=(Vector((0,15,0))-cam.location).to_track_quat('-Z','Y').to_euler()
cam.data.type='ORTHO'
cam.data.ortho_scale=215
s.camera=cam
s.render.filepath=os.path.join(ROOT,'docs/media/halloween-circuit.png')
bpy.ops.render.render(write_still=True)
