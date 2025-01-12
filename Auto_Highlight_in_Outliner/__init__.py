bl_info = {
    "name": "Auto Highlight in Outliner",
    "author": "Amandeep",
    "description": "Automatically highlight selected objects in the outliner",
    "blender": (3, 5, 0),
    "version": (3, 8, 5),
    "location": "",
    "warning": "",
    "category": "Object",
}

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import bpy
from bpy.app.handlers import persistent
from .addon_update_checker import *
import rna_keymap_ui
import textwrap
from pathlib import Path
def draw_hotkeys(col,km_name):
    kc = bpy.context.window_manager.keyconfigs.user
    for kmi in [a.idname for b,a in addon_keymaps]:
        km2=kc.keymaps[km_name]
        kmi2=[]
        for a,b in km2.keymap_items.items():
            if a==kmi:
                kmi2.append(b)
        if kmi2:
            for a in kmi2:
                col.context_pointer_set("keymap", km2)
                rna_keymap_ui.draw_kmi([], kc, km2, a, col, 0)
def preferences():
    return bpy.context.preferences.addons[__package__].preferences
def savePreferences():
    config_dir=Path(bpy.utils.user_resource('SCRIPTS')).parent/"config"
    config_path=config_dir/"TA-Config.txt"
    if not os.path.isdir(config_dir):
        os.makedirs(config_dir)
    
    with open(config_path, mode='w+', newline='\n', encoding='utf-8') as file:
        for p in preferences().__annotations__.keys():
            
            file.write(f"{p}=>{type(getattr(preferences(),p,'str')).__name__}==={getattr(preferences(),p)}\n")


def loadPreferences():
    config_dir=Path(bpy.utils.user_resource('SCRIPTS')).parent/"config"
    config_path=config_dir/"TA-Config.txt"
    if not os.path.isdir(config_dir):
        os.makedirs(config_dir)
    if os.path.isfile(config_path):
        with open(config_path, mode='r', newline='\n', encoding='utf-8') as file:
            prefs = file.readlines()
            for p in reversed(prefs):
                try:
                    
                    attr = p[:p.index("=>")]
                    type = p[p.index("=>")+2:p.index("===")]
                    if type=='String':
                        type='str'
                    value = p[p.index("===")+3:]
                    value = str(value.replace("\n", ""))
                    if type=='bool':
                        setattr(preferences(), attr,eval(value))
                    else:
                        setattr(preferences(), attr,value)
                except Exception as e:
                    pass
class AHPrefs(bpy.types.AddonPreferences,AddonUpdateChecker):
    bl_idname = __package__
    expand_all_selected:bpy.props.BoolProperty(default=True,name="Keep all selected objects expanded when using 'Collapse other collections'",description='Enabling this option will expand all selected objects in the outliner. Disabling it will only expand the active object.')
    expand_bones:bpy.props.BoolProperty(default=False,name='Expand to show selected bones in Pose mode')
    ex:bpy.props.BoolProperty(name='Experimental',default=False)
    show_actual_object_for_parented_objects:bpy.props.BoolProperty(default=False,name='Show actual object for parented objects',description='When disabled, the addon will expand to show the grayed out version of children objects (the ones shown under the parent object) instead of the actual object, which may be located in another collection. Enabling this option will display the actual object from the other collection instead.')
    default_state:bpy.props.BoolProperty(default=True,name='Enable by default in all new scenes',description='This option allows you to set the starting state for new scenes. When enabled, auto highlight will be turned on by default for every new Blender scene you open.')
    collapse_fix:bpy.props.BoolProperty(default=False,name="Enable if performance is slow when using 'Collapse other collections'")
    max_objects_to_expand:bpy.props.IntProperty(default=10,min=1,max=999999,name="Objects limit")
    def draw(self, context):
        draw_update_section_for_prefs(self.layout,context)
        lines = textwrap.wrap('Ensure that both of these keymaps are set to correspond with the select button you utilize in the viewport and the outliner!',context.region.width/10 if context else 100, break_long_words=False)
        for i,l in enumerate(lines):
            self.layout.label(text=l,icon='INFO' if i==0 else 'NONE')
        draw_hotkeys(self.layout,"3D View")
        draw_hotkeys(self.layout,"Outliner")
        self.layout.prop(self,'default_state')
        self.layout.prop(self,'expand_all_selected')
        self.layout.label(text="Maximum number of objects to expand in the outliner")
        self.layout.label(text="(lower this if you are facing crashes when selecting a lot of objects)")
        self.layout.prop(self,'max_objects_to_expand')
        self.layout.prop(self,'show_actual_object_for_parented_objects')
        self.layout.prop(self,'ex',toggle=True,icon="DOWNARROW_HLT" if self.ex else "RIGHTARROW_THIN",emboss=False)
        if self.ex:
            
            self.layout.prop(self,'expand_bones')
            self.layout.prop(self,'collapse_fix')
new_selection=[]
prev_selection=[]      
prev_collections=set()
new_collections=set()
def enable_filter_children(area,filter_children,filter_content):
    area.spaces.active.use_filter_children=filter_children
    area.spaces.active.use_filter_object_content=filter_content
    return None
def show_active_again(active,override):
    if bpy.context.mode=='OBJECT':
        if True or not(active and active.parent and set(active.parent.users_collection)==set(active.users_collection)):
            if bpy.context.view_layer.objects.active!=active:
                bpy.context.view_layer.objects.active=active
            with bpy.context.temp_override(**override):
                bpy.ops.outliner.show_active()
        bpy.context.view_layer.objects.active=active
def collapse_outliner(override):
    if not preferences().collapse_fix:
        for i in range(15):
            with bpy.context.temp_override(**override):
                bpy.ops.outliner.show_one_level(open=False)
    else:
        with bpy.context.temp_override(**override):
            bpy.ops.outliner.expanded_toggle()
            bpy.ops.outliner.expanded_toggle()
def show_active(active_bone, active, override,area,filter_children,filter_content):

    
    if preferences().expand_all_selected:
        count=1
        if bpy.context.mode=='OBJECT':
            for a in bpy.context.selected_objects:
                count+=1
                if a!=active and not(a.parent and set(a.parent.users_collection)==set(a.users_collection)):
                    bpy.context.view_layer.objects.active=a
                    with bpy.context.temp_override(**override):
                        bpy.ops.outliner.show_active()
                if count>preferences().max_objects_to_expand:
                    break
        if preferences().expand_bones:
            if bpy.context.mode=='POSE':
                for a in bpy.context.selected_pose_bones:
                    if a!=active_bone and active:
                        bpy.context.view_layer.objects.active=a.id_data
                        a.id_data.data.bones.active=a.bone
                        with bpy.context.temp_override(**override):
                            bpy.ops.outliner.show_active()
    expanded_active=False
    if bpy.context.mode=='OBJECT':
        if active.parent and set(active.parent.users_collection)!=set(active.users_collection):
            expanded_active=True
            if bpy.context.view_layer.objects.active!=active:
                bpy.context.view_layer.objects.active=active
            with bpy.context.temp_override(**override):
                bpy.ops.outliner.show_active()
        bpy.context.view_layer.objects.active=active
    if preferences().expand_bones:
        if bpy.context.mode=='POSE' and active and active_bone:
            bpy.context.view_layer.objects.active=active_bone.id_data
            active_bone.id_data.data.bones.active=active_bone.bone
            with bpy.context.temp_override(**override):
                bpy.ops.outliner.show_active()
    
    area.spaces.active.use_filter_children=filter_children
    area.spaces.active.use_filter_object_content=filter_content
    if not expanded_active:
        bpy.app.timers.register(functools.partial(show_active_again, active, override),first_interval=0.01)
    return None
import functools
import time
def highlight_in_outliner():
    st=time.time()
    if bpy.context.scene.auto_highlight_in_outliner and not bpy.context.scene.auto_highlight_temp_disable:
        global new_selection,prev_selection,prev_collections,new_collections
        new_selection=set(bpy.context.selected_objects[:])
        has_parent=any([a.parent!=None for a in new_selection])
        new_selection=set([a.name for a in new_selection])
        
        active_bone=None
        if bpy.context.mode=='POSE':
            new_selection.update([a.name for a in bpy.context.selected_pose_bones])
            active_bone=bpy.context.active_pose_bone if bpy.context.active_pose_bone in bpy.context.selected_pose_bones else None
        active=bpy.context.active_object
        if bpy.context.selected_objects and active not in bpy.context.selected_objects:
            active=bpy.context.selected_objects[0]
        if new_selection!=prev_selection:
            # new_collection_set=False
            prev_selection=new_selection
            # if prev_collections!=new_collections :
            #     prev_collections=new_collections
            #     new_collection_set=True
            override = None
            for win in bpy.context.window_manager.windows:
            
                for area in win.screen.areas:
                    if 'OUTLINER' in area.type:
                        if area.spaces and area.spaces.active and area.spaces.active.display_mode in ['VIEW_LAYER','SCENES','LIBRARIES']:
                            for region in area.regions:
                                if 'WINDOW' in region.type:
                                    override = {'window':win,'area': area, 'region': region}

                                    if bpy.context.scene.collapse_other_collections and bpy.context.selected_objects[:]:
                                        if True or not preferences().show_actual_object_for_parented_objects:
                                            collapse_outliner(override)
                                            if area.spaces.active.display_mode=='LIBRARIES':
                                                with bpy.context.temp_override(**override):
                                                    bpy.ops.outliner.show_one_level(open=True)
                                    filter_children=area.spaces.active.use_filter_children
                                    filter_content=area.spaces.active.use_filter_object_content
                                    if has_parent and preferences().show_actual_object_for_parented_objects:
                                        count=1
                                        if bpy.context.mode=='OBJECT':
                                            for a in bpy.context.selected_objects:
                                                if a!=active and a.parent and set(a.parent.users_collection)==set(a.users_collection):
                                                    count+=1
                                                    bpy.context.view_layer.objects.active=a
                                                    with bpy.context.temp_override(**override):
                                                        bpy.ops.outliner.show_active()
                                                    if count>preferences().max_objects_to_expand:
                                                        break
                                        if bpy.context.mode=='OBJECT':
                                            if active and active.parent and set(active.parent.users_collection)==set(active.users_collection):
                                                if bpy.context.view_layer.objects.active!=active:
                                                    bpy.context.view_layer.objects.active=active
                                                with bpy.context.temp_override(**override):
                                                    bpy.ops.outliner.show_active()
                                        area.spaces.active.use_filter_children=False
                                        area.spaces.active.use_filter_object_content=False
                                        collapse_outliner(override)
                                        bpy.app.timers.register(functools.partial(show_active,active_bone, active, override,area,filter_children,filter_content),first_interval=0.002)
                                        
                                    else:
                                        if preferences().expand_all_selected:
                                            count=1
                                            if bpy.context.mode=='OBJECT':
                                                for a in bpy.context.selected_objects:
                                                    if a!=active:
                                                        count+=1
                                                        bpy.context.view_layer.objects.active=a
                                                        with bpy.context.temp_override(**override):
                                                            bpy.ops.outliner.show_active()
                                                            # if preferences().show_actual_object_for_parented_objects:
                                                            #     area.spaces.active.use_filter_children=False
                                                            #     area.spaces.active.use_filter_object_content=False
                                                            #     collapse_outliner(override)
                                                            #     bpy.app.timers.register(functools.partial(show_active,active_bone, active, override,area,filter_children,filter_content),first_interval=0.0002)
                                                            # else:
                                                            #     bpy.ops.outliner.show_active()
                                                        if count>preferences().max_objects_to_expand:
                                                            break
                                            if preferences().expand_bones:
                                                if bpy.context.mode=='POSE':
                                                    for a in bpy.context.selected_pose_bones:
                                                        if a!=active_bone and active:
                                                            bpy.context.view_layer.objects.active=a.id_data
                                                            a.id_data.data.bones.active=a.bone
                                                            with bpy.context.temp_override(**override):
                                                                if preferences().show_actual_object_for_parented_objects:
                                                                    area.spaces.active.use_filter_children=False
                                                                    area.spaces.active.use_filter_object_content=False
                                                                    collapse_outliner(override)
                                                                    bpy.app.timers.register(functools.partial(show_active,active_bone, active, override,area,filter_children,filter_content),first_interval=0.002)
                                                                else:
                                                                    bpy.ops.outliner.show_active()
                                                                            
                                        if bpy.context.mode=='OBJECT':
                                            if bpy.context.view_layer.objects.active!=active:
                                                bpy.context.view_layer.objects.active=active
                                            with bpy.context.temp_override(**override):
                                                bpy.ops.outliner.show_active()
                                                # if preferences().show_actual_object_for_parented_objects:
                                                #     area.spaces.active.use_filter_children=False
                                                #     area.spaces.active.use_filter_object_content=False
                                                #     collapse_outliner(override)
                                                #     bpy.app.timers.register(functools.partial(show_active,active_bone, active, override,area,filter_children,filter_content),first_interval=0.0002)
                                                # else:
                                                #     bpy.ops.outliner.show_active()
                                        if preferences().expand_bones:
                                            if bpy.context.mode=='POSE' and active and active_bone:
                                                bpy.context.view_layer.objects.active=active_bone.id_data
                                                active_bone.id_data.data.bones.active=active_bone.bone
                                                with bpy.context.temp_override(**override):
                                                    if preferences().show_actual_object_for_parented_objects:
                                                        area.spaces.active.use_filter_children=False
                                                        area.spaces.active.use_filter_object_content=False
                                                        collapse_outliner(override)
                                                        bpy.app.timers.register(functools.partial(show_active,active_bone, active, override,area,filter_children,filter_content),first_interval=0.002)
                                                    else:
                                                        bpy.ops.outliner.show_active()
                                        # area.spaces.active.use_filter_children=filter_children
                                        # area.spaces.active.use_filter_object_content=filter_content
                                    # else:
                                    #     bpy.app.timers.register(functools.partial(show_active,active_bone, active, override,area,filter_children),first_interval=0.002)
                                
                        # break
                # if override is not None:
                #     if bpy.context.scene.collapse_other_collections:
                #         bpy.ops.outliner.expanded_toggle(override)
                #         bpy.ops.outliner.expanded_toggle(override)
            # print(time.time()-st)            
    return 0.1


class AH_OT_Click_Bypass(bpy.types.Operator):
    bl_idname = "ah.clickbypass"
    bl_label = "Select in Outliner"
    bl_description = "Used to detect clicks in outliner to temporarily disable auto hightlight while you are in outliner."
    bl_options = {"REGISTER", "UNDO"}

    def invoke(self, context,event):
        context.scene.auto_highlight_temp_disable=True
        return {'PASS_THROUGH'}
class AH_OT_Click_Bypass_View3d(bpy.types.Operator):
    bl_idname = "ah.clickbypassview"
    bl_label = "Select in Viewport"
    bl_description = "Used to detect clicks in viewport to reenable auto hightlight after it was temporarily disabled when you clicked in outliner."
    bl_options = {"REGISTER", "UNDO"}

    def invoke(self, context,event):
        context.scene.auto_highlight_temp_disable=False
        return {'PASS_THROUGH'}
classes = (AHPrefs,AH_OT_Click_Bypass,AH_OT_Click_Bypass_View3d
)

icon_collection={}
addon_keymaps = []

def drawIntoOutliner(self, context):
    layout= self.layout
    layout.separator(factor=1)
    layout.prop(context.scene,'auto_highlight_in_outliner')
    if context.scene.auto_highlight_in_outliner:
        layout.prop(context.scene,'collapse_other_collections')
        if context.scene.collapse_other_collections and preferences().collapse_fix:
            layout.label(text='Make sure you collapse all',icon='ERROR') 
            layout.label(text='collections once using SHIFT+A')
            layout.label(text='before using this.Press again if')
            layout.label(text='collections expand instead of collapsing!')
    draw_update_section_for_panel(layout,context)
def enabled(self,context):
    self.ah_state_set=True
    if self.auto_highlight_in_outliner:
        if not bpy.app.timers.is_registered(highlight_in_outliner):
                bpy.app.timers.register(highlight_in_outliner,persistent=True)
    else:
        if bpy.app.timers.is_registered(highlight_in_outliner):
            bpy.app.timers.unregister(highlight_in_outliner)
def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)
    
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    kmaps = [('ah.clickbypassview','LEFTMOUSE','')
    ]
    # select_mouse=bpy.context.window_manager.keyconfigs.active.preferences.select_mouse
    # outliner_select=bpy.context.window_manager.keyconfigs.active.keymaps.get('Outliner').keymap_items['outliner.item_activate'].type
    km = kc.keymaps.new(name="3D View", space_type="VIEW_3D")
    if kc:
        kmi = km.keymap_items.new(
            "ah.clickbypassview",
            type=f'LEFTMOUSE',
            value="PRESS",any=True
        )
        addon_keymaps.append((km, kmi))
    km = kc.keymaps.new(name='Outliner', space_type='OUTLINER')
    if kc:
        kmi = km.keymap_items.new(
            "ah.clickbypass",
            type='LEFTMOUSE',
            value="PRESS",any=True

        )
        addon_keymaps.append((km, kmi))
    bpy.types.OUTLINER_PT_filter.append(drawIntoOutliner)
    bpy.types.Scene.auto_highlight_in_outliner= bpy.props.BoolProperty(default=True,name="Auto Highlight",update=enabled)
    bpy.types.Scene.collapse_other_collections= bpy.props.BoolProperty(default=True,name="Collapse Other Collections")
    bpy.types.Scene.auto_highlight_temp_disable=bpy.props.BoolProperty(default=False,name="Auto Highlight Temp Disable")
    bpy.types.Scene.ah_state_set=bpy.props.BoolProperty(default=False,name="Auto Highlight State Set")
    bpy.app.handlers.load_post.append(start_ah)
    addon_update_checker.register("c3b0a36c72810a6b1837b8e0e4c0e55c")
    loadPreferences()
    # bpy.app.handlers.load_pre.append(stop_modal)
from bpy.app.handlers import persistent
@persistent
def start_ah(scene):
    if bpy.context.scene.ah_state_set:
        for scene in bpy.data.scenes:
            scene.auto_highlight_in_outliner=scene.auto_highlight_in_outliner
    else:
        for scene in bpy.data.scenes:
            scene.auto_highlight_in_outliner=preferences().default_state
    

def unregister():
    savePreferences()
    if bpy.app.timers.is_registered(highlight_in_outliner):
            bpy.app.timers.unregister(highlight_in_outliner)
    from bpy.utils import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)
    for (km, kmi) in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()
    bpy.types.OUTLINER_PT_filter.remove(drawIntoOutliner)
    
    try:
        bpy.app.handlers.load_post.remove(start_ah)
    except Exception:
        pass
    addon_update_checker.unregister()
    # bpy.app.handlers.load_pre.clear()
if __name__ == "__main__":
    register()

