
import bpy

bl_info = {
    "name": "菌菌阻尼追踪器",
    "author": "除菌菌菌Well",
    "version": (1, 3),
    "blender": (3, 6, 0),
    "location": "视图3D > 工具架 > 菌菌阻尼追踪器",
    "description": "为选中的骨骼生成阻尼追踪约束并控制参数",
    "category": "绑定",
}


class GenerateDampingTrack(bpy.types.Operator):
    """为选中的骨骼生成阻尼追踪约束"""
    bl_idname = "rig.generate_damping_track"
    bl_label = "生成阻尼追踪"

    def execute(self, context):
        armature = context.active_object
        if armature.type != 'ARMATURE':
            self.report({'ERROR'}, "活动对象不是骨骼对象。")
            return {'CANCELLED'}

        # 获取选中的骨骼，并按它们在世界空间中的Z轴坐标排序
        selected_bones = [bone for bone in armature.pose.bones if bone.bone.select]
        selected_bones.sort(key=lambda bone: bone.head[2])

        # 解锁选中骨骼的位置和旋转锁定属性
        for bone in selected_bones:
            bone.lock_location = [False, False, False]
            bone.lock_rotation = [False, False, False]

        for i in range(len(selected_bones) - 1):
            constraint = selected_bones[i + 1].constraints.new(type='DAMPED_TRACK')
            constraint.target = armature
            constraint.subtarget = selected_bones[i].name
            constraint.influence = 0.5  # 设置默认影响力为 0.5
            constraint.track_axis = 'TRACK_Y'  # 默认追踪轴

        return {'FINISHED'}


class ControlDampingTrackParams(bpy.types.Operator):
    """控制选中骨骼的阻尼追踪参数"""
    bl_idname = "rig.control_damping_track_params"
    bl_label = "控制阻尼追踪参数"

    influence: bpy.props.FloatProperty(name="影响力", default=0.5, min=0.0, max=1.0)
    track_axis: bpy.props.EnumProperty(
        name="追踪轴",
        items=[
            ('TRACK_X', "X轴", ""),
            ('TRACK_Y', "Y轴", ""),
            ('TRACK_Z', "Z轴", ""),
            ('TRACK_NEGATIVE_X', "-X轴", ""),
            ('TRACK_NEGATIVE_Y', "-Y轴", ""),
            ('TRACK_NEGATIVE_Z', "-Z轴", ""),
        ],
        default='TRACK_Y'
    )

    def execute(self, context):
        armature = context.active_object
        if armature.type != 'ARMATURE':
            self.report({'ERROR'}, "活动对象不是骨骼对象。")
            return {'CANCELLED'}

        bones = [bone for bone in armature.pose.bones if bone.bone.select]
        for bone in bones:
            for constraint in bone.constraints:
                if constraint.type == 'DAMPED_TRACK':
                    constraint.influence = self.influence
                    constraint.track_axis = self.track_axis

        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)


class ClearDampingTrack(bpy.types.Operator):
    """清除选中骨骼的阻尼追踪约束"""
    bl_idname = "rig.clear_damping_track"
    bl_label = "清除阻尼追踪"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        armature = context.active_object
        if armature.type != 'ARMATURE':
            self.report({'ERROR'}, "活动对象不是骨骼对象。")
            return {'CANCELLED'}
        
        cleared_count = 0
        bones = [bone for bone in armature.pose.bones if bone.bone.select]
        
        for bone in bones:
            for i in range(len(bone.constraints)-1, -1, -1):
                if bone.constraints[i].type == 'DAMPED_TRACK':
                    bone.constraints.remove(bone.constraints[i])
                    cleared_count += 1
        
        if cleared_count > 0:
            self.report({'INFO'}, f"已清除 {cleared_count} 个阻尼追踪约束")
        else:
            self.report({'WARNING'}, "选中的骨骼上没有阻尼追踪约束")
        
        return {'FINISHED'}


class SetCustomDecreasingInfluence(bpy.types.Operator):
    """自定义设置阻尼追踪影响系数递减范围"""
    bl_idname = "rig.set_custom_decreasing_influence"
    bl_label = "设置自定义递减影响"
    bl_options = {'REGISTER', 'UNDO'}

    start_influence: bpy.props.FloatProperty(
        name="起始影响",
        description="最高骨骼的影响系数",
        default=0.8,
        min=0.0,
        max=1.0,
        step=0.1,
        precision=2
    )
    
    end_influence: bpy.props.FloatProperty(
        name="结束影响",
        description="最低骨骼的影响系数",
        default=0.4,
        min=0.0,
        max=1.0,
        step=0.1,
        precision=2
    )

    def execute(self, context):
        armature = context.active_object
        if armature.type != 'ARMATURE':
            self.report({'ERROR'}, "活动对象不是骨骼对象。")
            return {'CANCELLED'}
        
        # 获取选中的骨骼并按Z轴排序（从高到低）
        selected_bones = [bone for bone in armature.pose.bones if bone.bone.select]
        if not selected_bones:
            self.report({'WARNING'}, "没有选中的骨骼")
            return {'CANCELLED'}
        
        selected_bones.sort(key=lambda bone: bone.head[2], reverse=True)
        
        # 只考虑有约束的骨骼（跳过最高位置的骨骼）
        constrained_bones = selected_bones[1:]
        if not constrained_bones:
            self.report({'WARNING'}, "选中的骨骼中没有约束")
            return {'CANCELLED'}
        
        # 计算影响系数递减值
        num_constraints = len(constrained_bones)
        start = min(1.0, max(0.0, self.start_influence))
        end = min(1.0, max(0.0, self.end_influence))
        step = (start - end) / max(1, (num_constraints - 1))
        
        # 设置递减影响系数（四舍五入到两位小数）
        for i, bone in enumerate(constrained_bones):
            influence = round(start - i * step, 2)
            # 确保影响系数在0.0-1.0之间
            influence = max(0.0, min(1.0, influence))
            
            # 只更新阻尼追踪约束
            for constraint in bone.constraints:
                if constraint.type == 'DAMPED_TRACK':
                    constraint.influence = influence
        
        self.report({'INFO'}, f"成功设置 {num_constraints} 个骨骼的影响系数从 {start} 到 {end}")
        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)


class HairPhysicsPanel(bpy.types.Panel):
    """在3D视图工具架中创建一个面板"""
    bl_label = "菌菌阻尼追踪器"
    bl_idname = "VIEW3D_PT_hair_physics"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "菌菌阻尼追踪器"

    def draw(self, context):
        layout = self.layout
        
        # 红色警告区域
        warning_box = layout.box()
        warning_box.alert = True
        row_warning = warning_box.row()
        row_warning.alignment = 'CENTER'
        row_warning.label(text="注意设置追踪时需要保持A形Pose，否则概率错位", icon='ERROR')
        
        # 主面板标题
        box = layout.box()
        row = box.row()
        row.alignment = 'CENTER'
        row.label(text="菌菌阻尼追踪器", icon='CONSTRAINT_BONE')

        layout.separator()

        button_box = layout.box()
        button_box.alignment = 'CENTER'
        
        # 第一行按钮
        row_buttons = button_box.row(align=True)
        row_buttons.operator("rig.generate_damping_track", icon='CONSTRAINT_BONE')
        row_buttons.operator("rig.set_custom_decreasing_influence", icon='SORT_DESC')
        
        # 第二行按钮
        row_buttons = button_box.row(align=True)
        row_buttons.operator("rig.control_damping_track_params", icon='PREFERENCES')
        row_buttons.operator("rig.clear_damping_track", icon='TRASH')
        
        # 按钮标签
        button_box.label(text="生成追踪      设置递减影响")
        button_box.label(text="控制参数      清除追踪")
        
        # 黄色温馨提示区域 - 放在按钮下方
        tip_box = layout.box()
        tip_box.alert = True  # 使用警告样式（黄色背景）
        tip_box.alert = False  # 覆盖为黄色（在Blender中，alert=True是红色，False是黄色）
        row_tip = tip_box.row()
        row_tip.alignment = 'CENTER'
        row_tip.label(text="温馨提示：本插件支持固定影响系数和递减影响系数，选择一个即可", icon='INFO')

        layout.separator()
        layout.alignment = 'CENTER'
        layout.label(text="除菌菌菌Well制作")


def register():
    bpy.utils.register_class(GenerateDampingTrack)
    bpy.utils.register_class(ControlDampingTrackParams)
    bpy.utils.register_class(ClearDampingTrack)
    bpy.utils.register_class(SetCustomDecreasingInfluence)
    bpy.utils.register_class(HairPhysicsPanel)


def unregister():
    bpy.utils.unregister_class(GenerateDampingTrack)
    bpy.utils.unregister_class(ControlDampingTrackParams)
    bpy.utils.unregister_class(ClearDampingTrack)
    bpy.utils.unregister_class(SetCustomDecreasingInfluence)
    bpy.utils.unregister_class(HairPhysicsPanel)


if __name__ == "__main__":
    register()
