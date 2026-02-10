import maya.cmds as cmds
import maya.OpenMaya as om
import os
import time

try:
    from PySide2.QtGui import QClipboard
    from PySide2.QtWidgets import QApplication
except ImportError:
    try:
        from PySide6.QtGui import QClipboard
        from PySide6.QtWidgets import QApplication
    except ImportError:
        pass

# Helper
def GetTempPath():
    home = os.path.expanduser("~")
    return os.path.join(home, "Desktop", "_temp.usd")

def SetUsdSchemeAttribute(shape_node, scheme_type):
    attr_name = "USD_subdivisionScheme"
    
    if not cmds.attributeQuery(attr_name, node=shape_node, exists=True):
        cmds.addAttr(shape_node, longName=attr_name, dataType="string")
    
    cmds.setAttr(f"{shape_node}.{attr_name}", scheme_type, type="string")

def TagCreases():
    shapes = cmds.ls(selection=True, dag=True, type="mesh", noIntermediate=True)
    
    if not shapes:
        return

    for shape in shapes:
        try:
            smooth_state = cmds.getAttr(f"{shape}.displaySmoothMesh")
            
            if smooth_state != 0:
                SetUsdSchemeAttribute(shape, "catmullClark")
            else:
                SetUsdSchemeAttribute(shape, "none")            
        except Exception as e:
            print(f"Error processing {shape}: {e}")



# --- EasyCopy Logic ---
def EasyCopy():
    if not cmds.pluginInfo("mayaUsdPlugin", query=True, loaded=True):
        try:
            cmds.loadPlugin("mayaUsdPlugin")
        except:
            om.MGlobal.displayError("EasyTransfer: maya-usd plugin not found.")
            return
            
    selection = cmds.ls(selection=True)
    if not selection:
        om.MGlobal.displayWarning("EasyTransfer: No objects selected.")
        return
    
    TagCreases()

    file_path = GetTempPath()
    
    try:
        # Export Selected
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
        
        clipboard = QClipboard()
        clipboard.setText(file_path)
        om.MGlobal.displayInfo(f"EasyTransfer: Exported to {file_path} in {elapsed_time:.4f} seconds")
        
    except Exception as e:
        om.MGlobal.displayError(f"EasyTransfer Export Error: {e}")

# --- EasyPaste Logic ---
def EasyPaste():
    if not cmds.pluginInfo("mayaUsdPlugin", query=True, loaded=True):
        try:
            cmds.loadPlugin("mayaUsdPlugin")
        except:
            om.MGlobal.displayError("EasyTransfer: maya-usd plugin not found.")
            return
            
    clipboard = QClipboard()
    file_path = clipboard.text()
    
    if not file_path:
        file_path = GetTempPath()
        
    file_path = file_path.strip().strip('"')  
    if not os.path.exists(file_path):
        om.MGlobal.displayError(f"EasyTransfer: File not found: {file_path}")
        return

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
            namespace=":",
            returnNewNodes=True, 
            options=options
        )

        elapsed_time = time.time() - start_time
        om.MGlobal.displayInfo(f"EasyTransfer: Imported from {file_path} in {elapsed_time:.4f} seconds")
        
    except Exception as e:
        om.MGlobal.displayError(f"EasyTransfer Import Error: {e}")

