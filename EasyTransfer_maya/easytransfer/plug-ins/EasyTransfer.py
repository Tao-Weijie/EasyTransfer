import maya.cmds as cmds
import maya.mel as mel
import maya.api.OpenMaya as om
import sys
import os
import importlib

# Import Core Logic
import ET_maya

# Plugin Information
PLUGIN_NAME = "EasyTransfer"
VERSION = "0.1.1"

# Commands
kCopyCommandName = "EasyCopy"
kPasteCommandName = "EasyPaste"

# --- Commands ---

class EasyCopyCmd(om.MPxCommand):
    def __init__(self):
        om.MPxCommand.__init__(self)

    def doIt(self, args):
        ET_maya.easy_copy_core()

    @staticmethod
    def creator():
        return EasyCopyCmd()

class EasyPasteCmd(om.MPxCommand):
    def __init__(self):
        om.MPxCommand.__init__(self)

    def doIt(self, args):
        ET_maya.easy_paste_core()

    @staticmethod
    def creator():
        return EasyPasteCmd()

# --- Plugin Registration ---

def maya_useNewAPI():
    """
    The presence of this function tells Maya that the plugin produces, and
    expects this file to be passed, objects created using the Maya Python API 2.0.
    """
    pass

def initializePlugin(mobject):
    mplugin = om.MFnPlugin(mobject, "Weijie Tao", "0.1.1", "Any")
    
    try:
        mplugin.registerCommand(kCopyCommandName, EasyCopyCmd.creator)
        mplugin.registerCommand(kPasteCommandName, EasyPasteCmd.creator)
        
        if not cmds.about(batch=True):
            # Evaluate import in global namespace. 
            # ET_maya is in sys.path because of module definition (+:= scripts)
            importlib.reload(ET_maya)
            cmds.evalDeferred("import ET_maya; ET_maya.create_menu()")
            cmds.evalDeferred("import ET_maya; ET_maya.setup_hotkeys()")
            
    except Exception as e:
        sys.stderr.write(f"Failed to register command: {e}")
        raise

def uninitializePlugin(mobject):
    mplugin = om.MFnPlugin(mobject)
    
    try:
        if not cmds.about(batch=True):
            # Call remove_menu from imported module
            # We can also do it via evalDeferred if necessary, or just call it if imported
            # Since uninitialize might run in a clean state, better valid import
            import ET_maya
            ET_maya.remove_menu()
            
        mplugin.deregisterCommand(kCopyCommandName)
        mplugin.deregisterCommand(kPasteCommandName)
    except Exception as e:
        sys.stderr.write(f"Failed to unregister command: {e}")
        raise
