bl_info = {
    "name": "Surface Snap Offset",
    "author": "AAADart & GPT",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "location": "3D View > Snap Popover + G / Alt G",
    "description": "Snap selected vertices to surfaces with a controllable normal offset",
    "category": "3D View",
}

import bpy
import bmesh
from mathutils import Vector
from bpy_extras import view3d_utils


addon_keymaps = []


class SSO_Settings(bpy.types.PropertyGroup):
    enabled: bpy.props.BoolProperty(
        name="Snap with Offset",
        default=False,
        description="Use surface normal offset during G move when Blender snapping is enabled"
    )

    offset: bpy.props.FloatProperty(
        name="Offset",
        default=0.005,
        unit='LENGTH',
        description="Offset along target surface normal"
    )

    wheel_step: bpy.props.FloatProperty(
        name="Wheel Step",
        default=0.001,
        unit='LENGTH',
        description="Offset change per mouse wheel step"
    )


def draw_snap_offset_settings(self, context):
    settings = context.scene.sso_settings
    layout = self.layout
    layout.separator()
    layout.prop(settings, "enabled")
    layout.prop(settings, "offset")
    layout.prop(settings, "wheel_step")


class VIEW3D_OT_surface_snap_offset_move(bpy.types.Operator):
    bl_idname = "view3d.surface_snap_offset_move"
    bl_label = "Surface Snap Offset Move"
    bl_description = "Move selected vertices with surface normal offset snapping"
    bl_options = {'REGISTER', 'UNDO'}

    force_offset: bpy.props.BoolProperty(default=False)

    def invoke(self, context, event):
        settings = context.scene.sso_settings
        tool_settings = context.scene.tool_settings

        snap_is_on = tool_settings.use_snap

        if not snap_is_on and not self.force_offset:
            bpy.ops.transform.translate('INVOKE_DEFAULT')
            return {'FINISHED'}

        if not settings.enabled and not self.force_offset:
            bpy.ops.transform.translate('INVOKE_DEFAULT')
            return {'FINISHED'}

        if context.mode != 'EDIT_MESH':
            bpy.ops.transform.translate('INVOKE_DEFAULT')
            return {'FINISHED'}

        self.obj = context.object
        self.mesh = self.obj.data
        self.settings = settings

        bm = bmesh.from_edit_mesh(self.mesh)
        self.selected_verts = [v for v in bm.verts if v.select]

        if not self.selected_verts:
            bpy.ops.transform.translate('INVOKE_DEFAULT')
            return {'FINISHED'}

        self.original_local = [v.co.copy() for v in self.selected_verts]
        self.original_world = [self.obj.matrix_world @ v.co for v in self.selected_verts]

        center = Vector((0, 0, 0))
        for p in self.original_world:
            center += p
        self.selection_center_world = center / len(self.original_world)

        self.start_mouse = (event.mouse_region_x, event.mouse_region_y)

        context.window_manager.modal_handler_add(self)
        context.workspace.status_text_set(
            "LMB Confirm | RMB/Esc Cancel | X/Y/Z Axis (Disable Offset) | Surface = Snap Offset | Empty = Free Move | Wheel Adjust Offset | G Vert/Edge Slide"
        )

        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type in {'ESC', 'RIGHTMOUSE'}:
            self.restore_original()
            context.workspace.status_text_set(None)
            return {'CANCELLED'}

        if event.type in {'LEFTMOUSE', 'RET', 'NUMPAD_ENTER'} and event.value == 'PRESS':
            context.workspace.status_text_set(None)
            return {'FINISHED'}

        if event.type == 'G' and event.value == 'PRESS':
            self.restore_original()
            context.workspace.status_text_set(None)
            try:
                bpy.ops.transform.vert_slide('INVOKE_DEFAULT')
            except Exception:
                bpy.ops.transform.translate('INVOKE_DEFAULT')
            return {'FINISHED'}

        if event.type in {'X', 'Y', 'Z'} and event.value == 'PRESS':
            self.restore_original()
            context.workspace.status_text_set(None)

            axis = (
                event.type == 'X',
                event.type == 'Y',
                event.type == 'Z'
            )

            bpy.ops.transform.translate(
                'INVOKE_DEFAULT',
                constraint_axis=axis
            )

            return {'FINISHED'}

        if event.type == 'WHEELUPMOUSE' and event.value == 'PRESS':
            self.settings.offset += self.settings.wheel_step
            self.move(context, event)
            return {'RUNNING_MODAL'}

        if event.type == 'WHEELDOWNMOUSE' and event.value == 'PRESS':
            self.settings.offset -= self.settings.wheel_step
            self.move(context, event)
            return {'RUNNING_MODAL'}

        if event.type == 'MOUSEMOVE':
            self.move(context, event)
            return {'RUNNING_MODAL'}

        return {'RUNNING_MODAL'}

    def restore_original(self):
        bm = bmesh.from_edit_mesh(self.mesh)
        selected = [v for v in bm.verts if v.select]

        for v, original in zip(selected, self.original_local):
            v.co = original

        bmesh.update_edit_mesh(self.mesh)

    def move(self, context, event):
        hit = self.raycast_visible_meshes(context, event)

        if hit is not None:
            self.snap_move(context, hit)
        else:
            self.free_move(context, event)

    def snap_move(self, context, hit):
        hit_location, hit_normal = hit
        target_position = hit_location + hit_normal.normalized() * self.settings.offset
        delta_world = target_position - self.selection_center_world

        bm = bmesh.from_edit_mesh(self.mesh)
        selected = [v for v in bm.verts if v.select]
        inv = self.obj.matrix_world.inverted()

        for v, original_world in zip(selected, self.original_world):
            v.co = inv @ (original_world + delta_world)

        bmesh.update_edit_mesh(self.mesh)

    def free_move(self, context, event):
        region = context.region
        rv3d = context.region_data

        start_location = view3d_utils.region_2d_to_location_3d(
            region,
            rv3d,
            self.start_mouse,
            self.selection_center_world
        )

        current_mouse = (event.mouse_region_x, event.mouse_region_y)

        current_location = view3d_utils.region_2d_to_location_3d(
            region,
            rv3d,
            current_mouse,
            self.selection_center_world
        )

        delta_world = current_location - start_location

        bm = bmesh.from_edit_mesh(self.mesh)
        selected = [v for v in bm.verts if v.select]
        inv = self.obj.matrix_world.inverted()

        for v, original_world in zip(selected, self.original_world):
            v.co = inv @ (original_world + delta_world)

        bmesh.update_edit_mesh(self.mesh)

    def raycast_visible_meshes(self, context, event):
        region = context.region
        rv3d = context.region_data
        depsgraph = context.evaluated_depsgraph_get()
        tool_settings = context.scene.tool_settings

        mouse = (event.mouse_region_x, event.mouse_region_y)

        ray_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, mouse)
        ray_direction = view3d_utils.region_2d_to_vector_3d(region, rv3d, mouse)

        best_distance = None
        best_hit = None

        use_snap_edit = getattr(tool_settings, "use_snap_edit", True)
        use_snap_nonedit = getattr(tool_settings, "use_snap_nonedit", True)
        use_snap_self = getattr(tool_settings, "use_snap_self", False)

        for obj in context.visible_objects:
            if obj.type != 'MESH':
                continue

            is_active = obj == self.obj

            if is_active and not (use_snap_edit or use_snap_self):
                continue

            if not is_active and not use_snap_nonedit:
                continue

            eval_obj = obj.evaluated_get(depsgraph)
            matrix = eval_obj.matrix_world
            inv_matrix = matrix.inverted()

            local_origin = inv_matrix @ ray_origin
            local_direction = inv_matrix.to_3x3() @ ray_direction
            local_direction.normalize()

            success, location, normal, face_index = eval_obj.ray_cast(
                local_origin,
                local_direction
            )

            if not success:
                continue

            world_location = matrix @ location
            world_normal = matrix.to_3x3() @ normal
            world_normal.normalize()

            distance = (world_location - ray_origin).length

            if best_distance is None or distance < best_distance:
                best_distance = distance
                best_hit = (world_location, world_normal)

        return best_hit


def register():
    bpy.utils.register_class(SSO_Settings)
    bpy.utils.register_class(VIEW3D_OT_surface_snap_offset_move)

    bpy.types.Scene.sso_settings = bpy.props.PointerProperty(type=SSO_Settings)

    try:
        bpy.types.VIEW3D_PT_snapping.append(draw_snap_offset_settings)
    except Exception:
        print("Surface Snap Offset: could not append settings to snap popover")

    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon

    if kc:
        km = kc.keymaps.new(name='Mesh', space_type='EMPTY')

        kmi_g = km.keymap_items.new(
            "view3d.surface_snap_offset_move",
            type='G',
            value='PRESS'
        )
        kmi_g.properties.force_offset = False
        addon_keymaps.append((km, kmi_g))

        kmi_alt_g = km.keymap_items.new(
            "view3d.surface_snap_offset_move",
            type='G',
            value='PRESS',
            alt=True
        )
        kmi_alt_g.properties.force_offset = True
        addon_keymaps.append((km, kmi_alt_g))


def unregister():
    try:
        bpy.types.VIEW3D_PT_snapping.remove(draw_snap_offset_settings)
    except Exception:
        pass

    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()

    if hasattr(bpy.types.Scene, "sso_settings"):
        del bpy.types.Scene.sso_settings

    bpy.utils.unregister_class(VIEW3D_OT_surface_snap_offset_move)
    bpy.utils.unregister_class(SSO_Settings)


if __name__ == "__main__":
    register()
