import maya.cmds as cmds
import maya.OpenMaya as om
import os
import time
import maya.mel as mel # Added for menu

try:
    from PySide2.QtGui import QClipboard
    from PySide2.QtWidgets import QApplication
except ImportError:
    try:
        from PySide6.QtGui import QClipboard
        from PySide6.QtWidgets import QApplication
    except ImportError:
        pass

# --- Helper Functions ---

def get_temp_path():
    # Use optionVar if available, otherwise default to Desktop
    if cmds.optionVar(exists="EasyTransfer_TempPath"):
        temp_dir = cmds.optionVar(query="EasyTransfer_TempPath")
    else:
        temp_dir = os.path.join(os.path.expanduser("~"), "Desktop")
    
    if cmds.optionVar(exists="EasyTransfer_TempName"):
        temp_name = cmds.optionVar(query="EasyTransfer_TempName")
    else:
        temp_name = "_temp.usd"
        
    return os.path.join(temp_dir, temp_name)

def copy_to_clipboard(text):
    clipboard = QClipboard()
    clipboard.setText(text)

def get_from_clipboard():
    clipboard = QClipboard()
    text = clipboard.text()
    if text:
        return text.strip().strip('"')
    return None

def set_usd_scheme_attribute(shape_node, scheme_type):
    attr_name = "USD_subdivisionScheme"
    if not cmds.attributeQuery(attr_name, node=shape_node, exists=True):
        cmds.addAttr(shape_node, longName=attr_name, dataType="string")
    cmds.setAttr(f"{shape_node}.{attr_name}", scheme_type, type="string")

def tag_creases():
    shapes = cmds.ls(selection=True, dag=True, type="mesh", noIntermediate=True)
    if not shapes:
        return

    for shape in shapes:
        try:
            # Check for smooth mesh preview or just assume defaults?
            # User script: if displaySmoothMesh != 0 -> catmullClark
            smooth_state = cmds.getAttr(f"{shape}.displaySmoothMesh")
            if smooth_state != 0:
                set_usd_scheme_attribute(shape, "catmullClark")
            else:
                set_usd_scheme_attribute(shape, "none")
        except Exception as e:
            om.MGlobal.displayWarning(f"Error processing {shape}: {e}")

# --- Core Logic ---

def easy_copy_core():
    # 1. Check Plugin
    if not cmds.pluginInfo("mayaUsdPlugin", query=True, loaded=True):
        try:
            cmds.loadPlugin("mayaUsdPlugin")
        except:
            om.MGlobal.displayError("EasyTransfer: maya-usd plugin not found.")
            return

    # 2. Check Selection
    selection = cmds.ls(selection=True)
    if not selection:
        om.MGlobal.displayWarning("EasyTransfer: No objects selected.")
        return

    # 3. Process Meshes (Tag Creases)
    tag_creases()

    # 4. Determine Path
    file_path = get_temp_path()

    # 5. Export
    try:
        options = ";".join([
            "exportUVs=1",
            "exportSkels=auto",
            "exportSkin=auto",
            "exportColorSets=1",
            "defaultUSDFormat=usda",
            "exportComponentTags=0"
        ])
        
        start_time = time.time()
        
        cmds.file(
            file_path,  
            force=True, 
            type="USD Export", 
            pr=True, 
            es=True,
            options=options
        )
        
        elapsed_time = time.time() - start_time
        
        copy_to_clipboard(file_path)
        om.MGlobal.displayInfo(f"EasyTransfer: Exported to {file_path} in {elapsed_time:.4f} seconds")
        
    except Exception as e:
        om.MGlobal.displayError(f"EasyTransfer Export Error: {e}")

def easy_paste_core():
    # 1. Check Plugin
    if not cmds.pluginInfo("mayaUsdPlugin", query=True, loaded=True):
        try:
            cmds.loadPlugin("mayaUsdPlugin")
        except:
            om.MGlobal.displayError("EasyTransfer: maya-usd plugin not found.")
            return

    # 2. Determine Path
    file_path = get_from_clipboard()
    if not file_path:
        file_path = get_temp_path()
    
    if not os.path.exists(file_path):
        om.MGlobal.displayError(f"EasyTransfer: File not found: {file_path}")
        return

    # 3. Import
    try:
        options = ";".join([
            "readAnimData=0",
        ])

        start_time = time.time()

        cmds.file(
            file_path, 
            i=True, 
            type="USD Import", 
            ignoreVersion=True, 
            ra=True, 
            mergeNamespacesOnClash=False, 
            namespace=":", # Merge into root namespace if possible or use default
            returnNewNodes=True, 
            options=options
        )

        elapsed_time = time.time() - start_time
        om.MGlobal.displayInfo(f"EasyTransfer: Imported from {file_path} in {elapsed_time:.4f} seconds")
        
    except Exception as e:
        om.MGlobal.displayError(f"EasyTransfer Import Error: {e}")

# --- Settings UI ---

def get_default_path():
    return os.path.join(os.path.expanduser("~"), "Desktop")

def save_settings(temp_path_field, temp_name_field, copy_key_field, paste_key_field):
    t_path = cmds.textFieldButtonGrp(temp_path_field, query=True, text=True)
    t_name = cmds.textFieldGrp(temp_name_field, query=True, text=True)
    
    # Store settings
    cmds.optionVar(stringValue=("EasyTransfer_TempPath", t_path))
    cmds.optionVar(stringValue=("EasyTransfer_TempName", t_name))
    
    om.MGlobal.displayInfo("EasyTransfer: Settings Saved")

def browse_folder(field):
    result = cmds.fileDialog2(fileMode=3, caption="Select Temp Folder")
    if result:
        cmds.textFieldButtonGrp(field, edit=True, text=result[0])

def show_settings_ui(*args):
    if cmds.window("EasyTransferSettingsWin", exists=True):
        cmds.deleteUI("EasyTransferSettingsWin")
    
    window = cmds.window("EasyTransferSettingsWin", title="EasyTransfer Settings", widthHeight=(400, 200))
    cmds.columnLayout(adjustableColumn=True, rowSpacing=10, columnAttach=('both', 10))
    
    cmds.text(label="File Settings", align='left', font='boldLabelFont')
    
    current_path = cmds.optionVar(query="EasyTransfer_TempPath") if cmds.optionVar(exists="EasyTransfer_TempPath") else get_default_path()
    current_name = cmds.optionVar(query="EasyTransfer_TempName") if cmds.optionVar(exists="EasyTransfer_TempName") else "_temp.usd"
    
    path_field = cmds.textFieldButtonGrp(label="Temp Path:", text=current_path, buttonLabel="Browse", columnWidth3=[80, 240, 50])
    cmds.textFieldButtonGrp(path_field, edit=True, buttonCommand=lambda: browse_folder(path_field))
    
    name_field = cmds.textFieldGrp(label="Temp Name:", text=current_name, columnWidth2=[80, 290])
    
    cmds.separator(height=10, style='none')
    cmds.text(label="Shortcuts (Restart required to update)", align='left', font='boldLabelFont')
    cmds.text(label="Default: Ctrl+Shift+C / Ctrl+Shift+V", align='left')
    
    cmds.separator(height=20)
    cmds.button(label="Save Settings", command=lambda x: save_settings(path_field, name_field, None, None))
    
    cmds.showWindow(window)

# --- Hotkeys ---

def setup_hotkeys():
    # Define Runtime Commands
    if not cmds.runTimeCommand("EasyCopyRTC", exists=True):
        cmds.runTimeCommand("EasyCopyRTC", annotation="Easy Copy to USD", command='cmds.EasyCopy()', category="User")
    
    if not cmds.runTimeCommand("EasyPasteRTC", exists=True):
        cmds.runTimeCommand("EasyPasteRTC", annotation="Easy Paste from USD", command='cmds.EasyPaste()', category="User")

    # Define Name Commands
    cmds.nameCommand("EasyCopyNameCommand", annotation="EasyCopyNameCommand", command='EasyCopyRTC')
    cmds.nameCommand("EasyPasteNameCommand", annotation="EasyPasteNameCommand", command='EasyPasteRTC')

    # Assign Hotkeys (Ctrl+Shift+C / V)
    
    cmds.hotkey(k='C', ctl=True, sht=True, name="EasyCopyNameCommand")
    cmds.hotkey(k='V', ctl=True, sht=True, name="EasyPasteNameCommand")

# --- Menu ---
MENU_NAME = "EasyTransfer"

def create_menu():
    if cmds.menu(MENU_NAME, exists=True):
        cmds.deleteUI(MENU_NAME)
    
    gMainWindow = mel.eval('$tmpVar=$gMainWindow')
    cmds.menu(MENU_NAME, parent=gMainWindow, label=MENU_NAME, tearOff=True)
    
    cmds.menuItem(label="Easy Copy", command=lambda x: cmds.EasyCopy(), annotation="Export Selected to USD (Ctrl+Shift+C)")
    cmds.menuItem(label="Easy Paste", command=lambda x: cmds.EasyPaste(), annotation="Import USD from Clipboard (Ctrl+Shift+V)")
    cmds.menuItem(divider=True)
    cmds.menuItem(label="Settings", command=show_settings_ui)

def remove_menu():
    if cmds.menu(MENU_NAME, exists=True):
        cmds.deleteUI(MENU_NAME)
