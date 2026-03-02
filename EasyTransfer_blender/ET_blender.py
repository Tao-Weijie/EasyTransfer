import bpy
import os
import time

def GetTempPath(context):
    try:
        file_path = context.window_manager.clipboard.strip().strip('"')
        if os.path.exists(file_path) and os.path.isfile(file_path):
             return file_path
    except:
        pass
        
    return None

def SetTempPath():
    addon_name = __package__
    prefs = bpy.context.preferences.addons[addon_name].preferences
    temp_dir = prefs.temp_path if prefs.temp_path else os.path.join(os.path.expanduser("~"), "Desktop")
    temp_name = prefs.temp_name if prefs.temp_name else "_temp.usd"
    return os.path.join(temp_dir, temp_name)

def RenameColorAttributes():
    selected_objs = bpy.context.selected_objects
    
    if not selected_objs:
        return

    for obj in selected_objs:
        if obj.type == 'MESH':
            mesh = obj.data
            
            if mesh.color_attributes:
                first_color_attr = mesh.color_attributes[0]
                first_color_attr.name = "displayColor"

class EasyCopy(bpy.types.Operator):
    """Copy selected meshes to clipboard as USD"""
    bl_idname = "object.easy_copy_usd"
    bl_label = "Copy to Clipboard (USD)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        """Copies selected objects to USDA format."""
        
        # 1. Check Selection
        if not context.selected_objects:
            self.report({'WARNING'}, "No objects selected.")
            return {'CANCELLED'}

        # 2. Rename Color Attributes to USD Standard
        RenameColorAttributes()

        # 3. Export to USD
        try:
            file_path = SetTempPath()
            start_time = time.time()

            bpy.ops.wm.usd_export(
                filepath=file_path,
                selected_objects_only=True,
                root_prim_path="",
                merge_parent_xform=True,
                author_blender_name=False,
                evaluation_mode='VIEWPORT',
                convert_world_material=False,
                export_subdivision='BEST_MATCH',
                export_custom_properties=True
            )
                
            elapsed_time = time.time() - start_time
            self.report({'INFO'}, f"Copied objects to {file_path} in {elapsed_time:.4f} seconds")
            
            context.window_manager.clipboard = file_path
            
        except Exception as e:
            self.report({'ERROR'}, f"Error exporting USD: {e}")
            return {'CANCELLED'}
            
        return {'FINISHED'}

class EasyPaste(bpy.types.Operator):
    """Paste USDA from Clipboard"""
    bl_idname = "object.easy_paste_usd"
    bl_label = "Paste from Clipboard (USD)"
    bl_options = {'REGISTER', 'UNDO'}
        
    def execute(self, context):
        """Imports USD from clipboard path."""
        try:
            file_path = GetTempPath(context)
            
            if not file_path:
                self.report({'ERROR'}, "Clipboard does not contain a valid file path.")
                return {'CANCELLED'}

            bpy.ops.object.select_all(action='DESELECT')
            start_time = time.time()
            
            bpy.ops.wm.usd_import(
                filepath=file_path,
                import_subdivision=True,
                property_import_mode='ALL',
                apply_unit_conversion_scale=True,
                validate_meshes=True,
                read_mesh_uvs=True,
                read_mesh_attributes=True,
                read_mesh_colors=True
            )
            
            elapsed_time = time.time() - start_time
                
        except Exception as e:
            self.report({'ERROR'}, f"Error importing USD: {e}")
            return {'CANCELLED'}

        selected = context.selected_objects
        if selected:
            self.report({'INFO'}, f"Successfully pasted {len(selected)} objects in {elapsed_time:.4f} seconds.")
        else:
            self.report({'WARNING'}, "No objects appeared to be pasted.")

        return {'FINISHED'}
