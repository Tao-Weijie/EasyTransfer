import maya.cmds as cmds
import maya.mel as mel
import maya.OpenMaya as om
import maya.OpenMayaMPx as omMPx
import os
import sys

try:
    from PySide2.QtGui import QClipboard
    from PySide2.QtWidgets import QApplication
except ImportError:
    try:
        from PySide6.QtGui import QClipboard
        from PySide6.QtWidgets import QApplication
    except ImportError:
        pass

# Plugin Information
PLUGIN_NAME = "EasyTransfer"
MENU_NAME = "EasyTransfer"

# Commands
kCopyCommandName = "EasyCopy"
kPasteCommandName = "EasyPaste"

# Helper
def get_temp_path():
    home = os.path.expanduser("~")
    return os.path.join(home, "Desktop", "_temp.usda")

def copy_to_clipboard(text):
    clipboard = QClipboard()
    clipboard.setText(text)

def get_from_clipboard():
    clipboard = QClipboard()
    return clipboard.text()

# --- EasyCopy Command ---
class EasyCopy(omMPx.MPxCommand):
    def __init__(self):
        omMPx.MPxCommand.__init__(self)

    def doIt(self, args):
        selection = cmds.ls(selection=True)
        if not selection:
            om.MGlobal.displayWarning("EasyTransfer: No objects selected.")
            return

        file_path = get_temp_path()
        
        # Ensure plugin is loaded
        if not cmds.pluginInfo("mayaUsdPlugin", query=True, loaded=True):
             try:
                 cmds.loadPlugin("mayaUsdPlugin")
             except:
                 om.MGlobal.displayError("EasyTransfer: maya-usd plugin not found.")
                 return

        try:
            # Export Selected
            # options: 
            #  - exportUVs=1
            #  - exportSkels=auto
            #  - exportSkin=auto
            #  - defaultPrim=None 
            #  - materialsScopeName=mtl
            
            options = ";".join([
                "exportUVs=1",
                "exportSkels=auto",
                "exportSkin=auto",
                "exportColorSets=1",
                "defaultMeshScheme=catmullClark",
                "defaultUSDFormat=usda"
            ])
            
            cmds.file(file_path, force=True, options=options, typ="USD Export", pr=True, es=True)
            
            copy_to_clipboard(file_path)
            om.MGlobal.displayInfo(f"EasyTransfer: Copied to {file_path}")
            
        except Exception as e:
            om.MGlobal.displayError(f"EasyTransfer Export Error: {e}")

    @staticmethod
    def creator():
        return omMPx.asMPxPtr(EasyCopy())

# --- EasyPaste Command ---
class EasyPaste(omMPx.MPxCommand):
    def __init__(self):
        omMPx.MPxCommand.__init__(self)

    def doIt(self, args):
        file_path = get_from_clipboard()
        
        if not file_path:
            # Fallback
            file_path = get_temp_path()
            
        file_path = file_path.strip().strip('"')
        
        if not os.path.exists(file_path):
             om.MGlobal.displayError(f"EasyTransfer: File not found: {file_path}")
             return

        # Ensure plugin is loaded
        if not cmds.pluginInfo("mayaUsdPlugin", query=True, loaded=True):
             try:
                 cmds.loadPlugin("mayaUsdPlugin")
             except:
                 om.MGlobal.displayError("EasyTransfer: maya-usd plugin not found.")
                 return

        try:
            cmds.file(file_path, i=True, type="USD Import", ignoreVersion=True, ra=True, mergeNamespacesOnClash=False, options=";readAnimData=0")
            om.MGlobal.displayInfo(f"EasyTransfer: Imported from {file_path}")
            
        except Exception as e:
            om.MGlobal.displayError(f"EasyTransfer Import Error: {e}")

    @staticmethod
    def creator():
        return omMPx.asMPxPtr(EasyPaste())

# --- Menu ---
def create_menu():
    if cmds.menu(MENU_NAME, exists=True):
        cmds.deleteUI(MENU_NAME)
    
    gMainWindow = mel.eval('$tmpVar=$gMainWindow')
    cmds.menu(MENU_NAME, parent=gMainWindow, label=MENU_NAME, tearOff=True)
    
    cmds.menuItem(label="Easy Copy", command=lambda x: cmds.EasyCopy())
    cmds.menuItem(label="Easy Paste", command=lambda x: cmds.EasyPaste())

def remove_menu():
    if cmds.menu(MENU_NAME, exists=True):
        cmds.deleteUI(MENU_NAME)

# --- Plugin Registration ---
def initializePlugin(mobject):
    mplugin = omMPx.MFnPlugin(mobject, "Weijie Tao", "0.1.0", "Any")
    
    try:
        mplugin.registerCommand(kCopyCommandName, EasyCopy.creator)
        mplugin.registerCommand(kPasteCommandName, EasyPaste.creator)
        
        # Defer menu creation to ensure GUI is ready
        if not cmds.about(batch=True):
            cmds.evalDeferred("import EasyTransfer; EasyTransfer.create_menu()")
            
    except Exception as e:
        sys.stderr.write(f"Failed to register command: {e}")
        raise

def uninitializePlugin(mobject):
    mplugin = omMPx.MFnPlugin(mobject)
    
    try:
        if not cmds.about(batch=True):
            remove_menu()
            
        mplugin.deregisterCommand(kCopyCommandName)
        mplugin.deregisterCommand(kPasteCommandName)
    except Exception as e:
        sys.stderr.write(f"Failed to unregister command: {e}")
        raise
