bl_info = {
    "name": "EasyTransfer",
    "author": "Weijie Tao",
    "version": (0, 1, 3),
    "blender": (4, 5, 0),
    "location": "View3D > Rightclick Menu > EasyTransfer",
    "description": "Transfer geometry between different 3D software via USDA",
    "category": "Import-Export",
}

import bpy
import os
from .ET_blender import EasyCopy, EasyPaste

addon_keymaps = []

def update_keymaps(self, context):
    """Refreshes keymaps"""
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if not kc:
        return

    km = kc.keymaps.get('3D View')
    if not km:
        km = kc.keymaps.new(name='3D View', space_type='VIEW_3D')

    target_operators = {EasyCopy.bl_idname, EasyPaste.bl_idname}
    
    for i in range(len(km.keymap_items) - 1, -1, -1):
        kmi = km.keymap_items[i]
        if kmi.idname in target_operators:
            km.keymap_items.remove(kmi)
            
    addon_keymaps.clear()

    if self.copy_key:
        kmi = km.keymap_items.new(
            EasyCopy.bl_idname, 
            self.copy_key, 
            'PRESS', 
            ctrl=self.copy_ctrl, 
            shift=self.copy_shift, 
            alt=self.copy_alt, 
            oskey=self.copy_os
        )
        addon_keymaps.append((km, kmi))
    
    if self.paste_key:
        kmi = km.keymap_items.new(
            EasyPaste.bl_idname, 
            self.paste_key, 
            'PRESS', 
            ctrl=self.paste_ctrl, 
            shift=self.paste_shift, 
            alt=self.paste_alt, 
            oskey=self.paste_os
        )
        addon_keymaps.append((km, kmi))


class EasytransferPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    # Copy Settings
    copy_key: bpy.props.StringProperty(name="Key",default='C',update=update_keymaps)
    copy_ctrl: bpy.props.BoolProperty(name="Ctrl ", default=True, update=update_keymaps)
    copy_shift: bpy.props.BoolProperty(name="Shift ", default=True, update=update_keymaps)
    copy_alt: bpy.props.BoolProperty(name="Alt ", default=False, update=update_keymaps)
    copy_os: bpy.props.BoolProperty(name="Cmd/Os ", default=False, update=update_keymaps)

    # Paste Settings
    paste_key: bpy.props.StringProperty(name="Key",default='V',update=update_keymaps)
    paste_ctrl: bpy.props.BoolProperty(name="Ctrl ", default=True, update=update_keymaps)
    paste_shift: bpy.props.BoolProperty(name="Shift ", default=True, update=update_keymaps)
    paste_alt: bpy.props.BoolProperty(name="Alt ", default=False, update=update_keymaps)
    paste_alt: bpy.props.BoolProperty(name="Alt ", default=False, update=update_keymaps)
    paste_os: bpy.props.BoolProperty(name="Cmd/Os ", default=False, update=update_keymaps)

    # Temp File Settings
    temp_path: bpy.props.StringProperty(
        name="Temp Path",
        description="Folder for temporary USD file",
        subtype='DIR_PATH',
        default=os.path.join(os.path.expanduser("~"), "Desktop")
    )
    temp_name: bpy.props.StringProperty(
        name="Temp Name",
        description="Name of temporary USD file",
        default="_temp.usd"
    )

    def draw(self, context):
        layout = self.layout
        
        main_box = layout.box()
        main_row = main_box.row(align=False)
        
        col_left = main_row.column()
        col_left.label(text="Easy Copy Shortcut", icon='COPYDOWN')
        split_copy = col_left.split(factor=0.2) 
        
        col_key_c = split_copy.column()
        col_mods_c = split_copy.column()
        
        col_key_c.prop(self, "copy_key", text="")
        row_mods_c = col_mods_c.row(align=True)
        row_mods_c.prop(self, "copy_ctrl", toggle=True)
        row_mods_c.prop(self, "copy_shift", toggle=True)
        row_mods_c.prop(self, "copy_alt", toggle=True)
        row_mods_c.prop(self, "copy_os", toggle=True)

        col_right = main_row.column()
        col_right.label(text="Easy Paste Shortcut", icon='PASTEDOWN')
        split_paste = col_right.split(factor=0.2)
        
        col_key_p = split_paste.column()
        col_mods_p = split_paste.column()
        
        col_key_p.prop(self, "paste_key", text="")
        row_mods_p = col_mods_p.row(align=True)
        row_mods_p.prop(self, "paste_ctrl", toggle=True)
        row_mods_p.prop(self, "paste_shift", toggle=True)
        row_mods_p.prop(self, "paste_alt", toggle=True)
        row_mods_p.prop(self, "paste_os", toggle=True)

        # Temp File UI
        box_temp = layout.box()
        box_temp.label(text="Temporary File Settings", icon='FILE_FOLDER')
        
        row_path = box_temp.row()
        row_path.prop(self, "temp_path")
        
        row_name = box_temp.row()
        row_name.prop(self, "temp_name")

def menu_func(self, context):
    self.layout.separator()
    self.layout.operator(EasyCopy.bl_idname, text="Easy Copy", icon='COPYDOWN')
    self.layout.operator(EasyPaste.bl_idname, text="Easy Paste", icon='PASTEDOWN')

classes = (
    EasytransferPreferences,
    EasyCopy,
    EasyPaste,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
        
    bpy.types.VIEW3D_MT_object_context_menu.append(menu_func)
    
    try:
        addon_name = __name__ 
        if addon_name in bpy.context.preferences.addons:
            prefs = bpy.context.preferences.addons[addon_name].preferences
            update_keymaps(prefs, bpy.context)
    except Exception as e:
        print(f"EasyTransfer: Failed to register keymaps on startup: {e}")


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
        
    bpy.types.VIEW3D_MT_object_context_menu.remove(menu_func)
    
    # Remove Keymaps
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()
