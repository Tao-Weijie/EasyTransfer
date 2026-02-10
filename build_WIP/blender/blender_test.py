import bpy
import os
import time

def GetTempPath():
    """Returns a fixed temp path for export."""
    return os.path.join(os.path.expanduser("~"), "Desktop", "_temp.usda")

def GetClipboardPath(context):
    """Retrieves the USD file path from clipboard."""
    try:
        file_path = context.window_manager.clipboard.strip().strip('"')
        if os.path.exists(file_path) and os.path.isfile(file_path):
             return file_path
    except:
        pass
    return None

def EasyCopy():
    """Copies selected objects to USDA format."""
    context = bpy.context
    
    # 1. Check Selection
    if not context.selected_objects:
        print("WARNING: No objects selected.")
        return

    # 2. Export to USD
    try:
        file_path = GetTempPath()
        
        start_time = time.time()
        
        bpy.ops.wm.usd_export(
            filepath=file_path,
            selected_objects_only=True,
            root_prim_path="",
            merge_parent_xform=True,
            author_blender_name=False,
            evaluation_mode='VIEWPORT',
            export_custom_properties=True, 
            convert_world_material=False,
            export_subdivision='BEST_MATCH',
        )
            
        elapsed_time = time.time() - start_time
        print(f"INFO: Copied objects to {file_path} in {elapsed_time:.4f} seconds")
        
        # Copy path to Clipboard
        context.window_manager.clipboard = file_path
        
    except Exception as e:
        print(f"ERROR: Error exporting USD: {e}")

def EasyPaste():
    """Imports USDA from clipboard path."""
    context = bpy.context
    try:
        file_path = GetClipboardPath(context)
        
        if not file_path:
            print("ERROR: Clipboard does not contain a valid file path.")
            return

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
        print(f"ERROR: Error importing USD: {e}")
        return

    selected = context.selected_objects
    if selected:
        print(f"INFO: Successfully pasted {len(selected)} objects in {elapsed_time:.4f} seconds.")
    else:
        print("WARNING: No objects appeared to be pasted.")

# Uncomment one of these to run
EasyCopy()
# EasyPaste()
