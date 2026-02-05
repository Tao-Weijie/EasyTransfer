import bpy
import os

class EasyCopy(bpy.types.Operator):
    """Copy selected meshes to clipboard as USDA"""
    bl_idname = "object.easy_copy_usd"
    bl_label = "Copy to Clipboard (USD)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        """Copies selected objects to USDA format."""
        
        # 1. Check Selection
        if not context.selected_objects:
            self.report({'WARNING'}, "No objects selected.")
            return {'CANCELLED'}

        # 2. Export to USDA
        try:
            # Mac/Linux/Windows 'Desktop'
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            file_path = os.path.join(desktop, "_temp.usda")
            

            bpy.ops.wm.usd_export(
                filepath=file_path,
                selected_objects_only=True,
                export_custom_properties=True, 
                convert_world_material=False,
                export_subdivision='BEST_MATCH',
            )
                
            self.report({'INFO'}, f"Copied objects to {file_path}")
            
            # Copy path to Clipboard
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
        """Imports USDA from clipboard path."""
        try:
            file_path = context.window_manager.clipboard.strip().strip('"')
            
            if not os.path.exists(file_path):
                # Fallback to desktop default if not in clipboard or invalid
                desktop = os.path.join(os.path.expanduser("~"), "Desktop")
                fallback = os.path.join(desktop, "_temp.usda")
                if os.path.exists(fallback):
                    file_path = fallback
                else:
                    self.report({'ERROR'}, f"File not found at path: {file_path}")
                    return {'CANCELLED'}

            bpy.ops.object.select_all(action='DESELECT')
            
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
                
        except Exception as e:
            self.report({'ERROR'}, f"Error importing USD: {e}")
            return {'CANCELLED'}
        
        # The USD importer usually selects imported objects. 
        # Ensure the active object is set if there is a selection.
        selected = context.selected_objects
        if selected:
            self.report({'INFO'}, f"Successfully pasted {len(selected)} objects.")
        else:
            self.report({'WARNING'}, "No objects appeared to be pasted.")

        return {'FINISHED'}
