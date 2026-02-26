bl_info = {
    "name": "Cameras Lister（全版本兼容版）",
    "author": "Original & Gemini Update",
    "version": (1, 0, 0),
    "description": "列出相机并快速设置视图，支持分辨率实时同步。兼容 Blender 3.x/4.x/5.x。",
    "location": "快捷键: Alt + C",
    "category": "Camera"
}

import bpy
from bpy.types import Operator, PropertyGroup, Object
from bpy.props import IntProperty, StringProperty, EnumProperty, PointerProperty

# --- 核心：自动识别当前 Blender 支持的 EEVEE 名称 ---
def get_eevee_engine_id():
    """根据 Blender 版本返回正确的 EEVEE 标识符"""
    ver = bpy.app.version # 返回类似 (5, 0, 1) 的元组
    
    # 如果版本号大于等于 4.2 且 小于 5.0 (或者根据你 5.0.1 的反馈测试)
    # 逻辑：4.2 引入了 NEXT，如果 5.0.1 识别不了 NEXT，说明它已经改回去了
    if ver >= (4, 2, 0) and ver < (5, 0, 0):
        return 'BLENDER_EEVEE_NEXT'
    
    # 其他版本（3.x 或 5.0+）通常使用 BLENDER_EEVEE
    return 'BLENDER_EEVEE'

#--------------------------------------------------------------------------------------
# F E A T U R E S
#--------------------------------------------------------------------------------------

class Camera_Custom_Resolution_Settings(PropertyGroup):
    def update_res(self, context):
        SetCameraCustomResolution(context)

    Custom_Horizontal_Resolution: IntProperty(
        name="自定义水平分辨率", default=1920, min=1, update=update_res)
        
    Custom_Vertical_Resolution: IntProperty(
        name="自定义垂直分辨率", default=1080, min=1, update=update_res)

def SetCameraCustomResolution(context):
    """核心同步函数：将相机属性同步至场景渲染设置，并强制刷新UI"""
    active_obj = context.active_object
    if active_obj and active_obj.type == 'CAMERA':
        props = active_obj.camera_custom_res_props
        render = context.scene.render
        # 只有当数值不一致时才修改，避免循环触发
        if render.resolution_x != props.Custom_Horizontal_Resolution:
            render.resolution_x = props.Custom_Horizontal_Resolution
        if render.resolution_y != props.Custom_Vertical_Resolution:
            render.resolution_y = props.Custom_Vertical_Resolution
        # 关键：强制刷新所有区域，确保输出面板（Output Tab）分辨率数值实时变动
        for window in context.window_manager.windows:
            for area in window.screen.areas:
                area.tag_redraw()

# --- 基础操作符 ---

class CameraViewOff(Operator):
    bl_idname = 'cameras.camera_view_off'
    bl_label = '退出相机视图'
    def execute(self, context):
        context.space_data.region_3d.view_perspective = 'PERSP'
        return {'FINISHED'}

class AlignSelectedCameraToView(Operator):
    bl_idname = 'cameras.align_selected_to_view'
    bl_label = '将所选相机对齐到视图'
    
    @classmethod
    def poll(cls, context):
        # 只有在 3D 视图区域，并且选中了相机时，按钮才允许点击
        return context.space_data.type == 'VIEW_3D' and context.object and context.object.type == 'CAMERA'

    def execute(self, context):
        # 1. 确保目标相机是当前场景的活跃相机
        context.scene.camera = context.object
        
        try:
            # 2. 尝试执行对齐操作
            # 使用 'INVOKE_DEFAULT' 帮助 Blender 正确识别窗口上下文
            bpy.ops.view3d.camera_to_view('INVOKE_DEFAULT')
        except RuntimeError as e:
            # 3. 如果还是报错（比如已经在相机视图），静默处理，不弹出错误红框
            self.report({'INFO'}, "已在相机视图或对齐跳过")
            
        return {'FINISHED'}

class NewCameraFromView(Operator):
    bl_idname = 'cameras.new_from_view'
    bl_label = '从视图新建相机'

    def execute(self, context):
        # 1. 如果当前已经在相机视图，先切换回透视视图，以便正确对齐新相机
        if context.space_data.region_3d.view_perspective == 'CAMERA':
            context.space_data.region_3d.view_perspective = 'PERSP'

        # 2. 创建相机数据和物体
        cam_data = bpy.data.cameras.new("Camera")
        cam_obj = bpy.data.objects.new("Camera", cam_data)
        context.collection.objects.link(cam_obj)

        # 3. 自动编号逻辑
        base_name = "Camera"
        existing_names = [o.name for o in bpy.data.objects if o.name.startswith(base_name)]
        
        # 检查重名并递增编号 (例如 Camera.001)
        suffix = 1
        new_name = base_name
        while new_name in bpy.data.objects:
            new_name = f"{base_name}.{suffix:03d}"
            suffix += 1
        cam_obj.name = new_name

        # 4. 设置为活动相机并对齐视图
        context.view_layer.objects.active = cam_obj
        context.scene.camera = cam_obj
        bpy.ops.view3d.camera_to_view()

        return {'FINISHED'}

# 修改后的引擎切换逻辑（兼容3.X-5.X)
def update_render_engine(self, context):
    target_engine = self.set_render_engine
    # 如果用户选的是 EEVEE，动态判断该用哪个 ID
    if target_engine == 'AUTO_EEVEE':
        real_id = get_eevee_engine_id()
        # 尝试切换
        try:
            context.scene.render.engine = real_id
        except:
            # 万一判断失误，强制回退到通用 ID
            context.scene.render.engine = 'BLENDER_EEVEE'
    else:
        context.scene.render.engine = target_engine
        #context.scene.render.engine = get_eevee_engine_id()
    #else:
        #context.scene.render.engine = target_engine

class SetCameraView(Operator):
    bl_idname = 'cameras.set_view'
    bl_label = '切换到相机视图'
    camera: StringProperty()
    def execute(self, context):
        cam = bpy.data.objects.get(self.camera)
        if not cam: return {'CANCELLED'}
        # 记录原始隐藏状态
        h1, h2 = cam.hide_get(), cam.hide_viewport
        cam.hide_set(False)
        cam.hide_viewport = False
        context.view_layer.objects.active = cam
        bpy.ops.view3d.object_as_camera()
        bpy.ops.view3d.view_center_camera()
        # 切换相机时同步分辨率
        SetCameraCustomResolution(context)
        cam.hide_set(h1)
        cam.hide_viewport = h2
        return {'FINISHED'}

class SelectCamera(Operator):
    bl_idname = 'cameras.select'
    bl_label = '选择相机'
    camera: StringProperty()
    def execute(self, context):
        cam = bpy.data.objects.get(self.camera)
        if cam:
            bpy.ops.object.select_all(action='DESELECT')
            cam.select_set(True)
            context.view_layer.objects.active = cam
            context.scene.camera = cam
            SetCameraCustomResolution(context)
        return {'FINISHED'}

class BindCameraToMarker(Operator):
    bl_idname = 'cameras.bind_to_marker'
    bl_label = '将相机绑定到标记'
    camera: StringProperty()
    def execute(self, context):
        tm = context.scene.timeline_markers
        curr_frame = context.scene.frame_current
        for m in [m for m in tm if m.frame == curr_frame]: tm.remove(m)
        new_marker = tm.new(self.camera, frame=curr_frame)
        new_marker.camera = bpy.data.objects.get(self.camera)
        return {'FINISHED'}

class DeleteCameraMarker(Operator):
    bl_idname = 'cameras.delete_camera_marker'
    bl_label = '删除相机标记'
    camera: StringProperty()
    def execute(self, context):
        tm = context.scene.timeline_markers
        curr_frame = context.scene.frame_current
        for m in [m for m in tm if m.frame == curr_frame and m.name == self.camera]:
            tm.remove(m)
        return {'FINISHED'}

class DeleteCamera(Operator):
    bl_idname = 'cameras.delete'
    bl_label = '删除相机'
    camera: StringProperty()
    def execute(self, context):
        cam = bpy.data.objects.get(self.camera)
        if cam: bpy.data.objects.remove(cam, do_unlink=True)
        return {'FINISHED'}

#--------------------------------------------------------------------------------------
# 相机设置弹出面板
#--------------------------------------------------------------------------------------

class PanelButton_CameraSettings(Operator):
    bl_idname = "camera.settings"
    bl_label = "相机设置"
    camera: StringProperty()

    def draw(self, context):
        layout = self.layout
        cam_obj = context.active_object
        if not cam_obj or cam_obj.type != 'CAMERA': return
        
        cam_data = cam_obj.data
        layout.label(text="渲染设置", icon="RESTRICT_RENDER_OFF")
        col = layout.column(align=False)
        row = col.row()
        row.prop(cam_data, "type", text="")
        
        if cam_data.type == 'PERSP':
            row = col.row()
            row.prop(cam_data, "lens_unit", text="")
            if cam_data.lens_unit == 'MILLIMETERS':
                row.prop(cam_data, "lens", text="焦距")
            else:
                row.prop(cam_data, "angle", text="视野角")
        elif cam_data.type == 'ORTHO':
            row.prop(cam_data, "ortho_scale", text="比例")
        
        row = col.row()
        row.label(text="移位：")
        row.label(text="裁剪：")
        row = col.row()
        row.prop(cam_data, "shift_x", text="水平")
        row.prop(cam_data, "clip_start", text="开始")
        row = col.row()
        row.prop(cam_data, "shift_y", text="垂直")
        row.prop(cam_data, "clip_end", text="结束")
        
        layout.label(text="自定义分辨率：")
        row = layout.row(align=True)
        row.prop(cam_obj.camera_custom_res_props, "Custom_Horizontal_Resolution", text="水平")
        row.prop(cam_obj.camera_custom_res_props, "Custom_Vertical_Resolution", text="垂直")

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        cam = bpy.data.objects.get(self.camera)
        if cam:
            context.view_layer.objects.active = cam
            SetCameraCustomResolution(context)
        return context.window_manager.invoke_popup(self)

#--------------------------------------------------------------------------------------
# 主 UI 绘制
#--------------------------------------------------------------------------------------

def common_draw(self, layout, context):
    scene = context.scene
    tm = scene.timeline_markers
    cur_frame = scene.frame_current
    frame_markers = [marker for marker in tm if marker.frame == cur_frame]

    row = layout.row(align=False)
    row.scale_x = 1.8
    row.scale_y = 1.8
    row.operator("render.render", text="", icon="RENDER_STILL")
    row.operator("render.render", text="", icon="RENDER_ANIMATION").animation=True
    row.operator("render.view_show", text="", icon="IMAGE_DATA")
    # 渲染框逻辑
    view3d = context.space_data
    is_cam_view = (view3d.region_3d.view_perspective == 'CAMERA')
    use_border = scene.render.use_border if is_cam_view else view3d.use_render_border
    
    if use_border:
        row.alert = True
        row.operator("view3d.clear_render_border", text="", icon="BORDERMOVE")
    else:
        row.operator("view3d.render_border", text="", icon="BORDERMOVE")
            
    row.prop(scene, "set_render_engine", text=" ", expand=True)

    layout.separator()
    
    row = layout.row(align=False)
    row.scale_y = 1.2
    row.operator("cameras.new_from_view", text="根据视图添加相机", icon="ADD")
    row.operator("cameras.align_selected_to_view", text="将所选相机对齐到视图", icon="CON_CAMERASOLVER")
    
    layout.separator()
    
    box_sort = layout.box()
    row = box_sort.row(align=True)
    row.prop(scene, "sort_cameras", text=" ", expand=True)

    box_list = layout.box()
    col_list = box_list.column()
    
    all_cams = [o for o in scene.objects if o.type == 'CAMERA']
    
    if not all_cams:
        col_list.label(text="场景中没有相机", icon="ERROR")
    else:
        if scene.sort_cameras == 'alphabetically':
            all_cams.sort(key=lambda o: o.name.lower())
            for cam in all_cams:
                draw_camera_row(col_list, context, cam, frame_markers)
        else:
            for coll in bpy.data.collections:
                cams_in_coll = [o for o in coll.objects if o.type == 'CAMERA' and o.name in scene.objects]
                if cams_in_coll:
                    col_list.label(text=coll.name)
                    for cam in sorted(cams_in_coll, key=lambda o: o.name.lower()):
                        draw_camera_row(col_list, context, cam, frame_markers)

def draw_camera_row(layout, context, cam, frame_markers):
    row = layout.row(align=True)
    is_viewing = (context.space_data.region_3d.view_perspective == 'CAMERA' and context.space_data.camera == cam)
    
    row.operator("cameras.select", text="", icon="RESTRICT_SELECT_OFF").camera = cam.name
    if is_viewing:
        row.operator("cameras.camera_view_off", text=cam.name, icon="CHECKBOX_HLT")
    else:
        row.operator("cameras.set_view", text=cam.name, icon="CHECKBOX_DEHLT").camera = cam.name
        
    has_marker = any(m.camera == cam for m in frame_markers)
    row.operator("cameras.delete_camera_marker" if has_marker else "cameras.bind_to_marker", 
                 text="", icon="MARKER_HLT" if has_marker else "MARKER").camera = cam.name
        
    row.operator("cameras.delete", text="", icon="PANEL_CLOSE").camera = cam.name
    row.separator()
    row.operator("camera.settings", text="", icon="TRIA_RIGHT").camera = cam.name

class VIEW3D_PT_FloatingPanel(Operator):
    bl_idname = "cameras.lister"
    bl_label = "相机列表"
    def draw(self, context):
        common_draw(self, self.layout, context)
    def invoke(self, context, event):
        return context.window_manager.invoke_popup(self, width=320)
    def execute(self, context):
        return {'FINISHED'}

#--------------------------------------------------------------------------------------
# R E G I S T R Y
#--------------------------------------------------------------------------------------

classes = (
    Camera_Custom_Resolution_Settings,
    CameraViewOff,
    AlignSelectedCameraToView,
    NewCameraFromView,
    SetCameraView,
    SelectCamera,
    BindCameraToMarker,
    DeleteCameraMarker,
    DeleteCamera,
    PanelButton_CameraSettings,
    VIEW3D_PT_FloatingPanel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    Object.camera_custom_res_props = PointerProperty(type=Camera_Custom_Resolution_Settings)
    
    # 兼容性修改：使用 AUTO_EEVEE 作为内部标识符
    bpy.types.Scene.set_render_engine = EnumProperty(
        items=[('AUTO_EEVEE', "EEVEE", ""), ('CYCLES', "CYCLES ", "")],
        name="渲染引擎", 
        default='AUTO_EEVEE', 
        update=update_render_engine)
        
    bpy.types.Scene.sort_cameras = EnumProperty(
        items=[("alphabetically", "按字母", ""), ("by_collections", "按集合", "")],
        name="相机排序", default="alphabetically")

    wm = bpy.context.window_manager
    if wm.keyconfigs.addon:
        km = wm.keyconfigs.addon.keymaps.new(name='Object Mode', space_type='EMPTY')
        km.keymap_items.new(VIEW3D_PT_FloatingPanel.bl_idname, 'C', 'PRESS', alt=True)

def unregister():
    wm = bpy.context.window_manager
    if wm.keyconfigs.addon:
        km = wm.keyconfigs.addon.keymaps.get('Object Mode')
        if km:
            for kmi in km.keymap_items:
                if kmi.idname == VIEW3D_PT_FloatingPanel.bl_idname:
                    km.keymap_items.remove(kmi)
    del Object.camera_custom_res_props
    del bpy.types.Scene.set_render_engine
    del bpy.types.Scene.sort_cameras
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
