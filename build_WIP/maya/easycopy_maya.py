import maya.cmds as cmds
import maya.mel as mel
import maya.api.OpenMaya as om
import json
import os
import sys

def maya_useNewAPI():
    """
    The presence of this function tells Maya that the plugin produces, and
    expects to be passed, objects created using the Maya Python API 2.0.
    """
    return True

# ------------------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------------------
kPluginCmdNameCopy = "EasyCopyCmd"
kPluginCmdNamePaste = "EasyPasteCmd"
kMenuLabel = "EasyCopy"
kVersioning = "0.1.0"

# ------------------------------------------------------------------------------
# Clipboard Helpers
# ------------------------------------------------------------------------------
try:
    from PySide2 import QtGui, QtWidgets
    _PYSIDE_AVAILABLE = True
except ImportError:
    _PYSIDE_AVAILABLE = False

def copy_to_clipboard(text):
    if _PYSIDE_AVAILABLE:
        clipboard = QtGui.QGuiApplication.clipboard()
        clipboard.setText(text)
    else:
        # Fallback for Mac
        os.system('echo "%s" | pbcopy' % text)

def get_clipboard_text():
    if _PYSIDE_AVAILABLE:
        clipboard = QtGui.QGuiApplication.clipboard()
        return clipboard.text()
    else:
        # Fallback for Mac
        import subprocess
        return subprocess.check_output('pbpaste', env={'LANG': 'en_US.UTF-8'}).decode('utf-8')

# ------------------------------------------------------------------------------
# Logic Classes (Kept as requested)
# ------------------------------------------------------------------------------
class MayaCopy:
    def execute(self):
        selection = om.MGlobal.getActiveSelectionList()
        if selection.isEmpty():
            om.MGlobal.displayError("Nothing selected.")
            return

        all_json_objects = []
        
        # Iterate over selection
        iter = om.MItSelectionList(selection, om.MFn.kTransform)
        
        while not iter.isDone():
            m_dag_path = iter.getDagPath()
            
            # Check for Shape
            shape_dag_path = m_dag_path.extendToShape()
            if shape_dag_path.apiType() == om.MFn.kMesh:
                mesh_fn = om.MFnMesh(shape_dag_path)
                data = self.process_mesh(mesh_fn, m_dag_path)
                all_json_objects.append(data)
                
            iter.next()

        if not all_json_objects:
            om.MGlobal.displayWarning("No meshes found in selection.")
            return

        # Write to File
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        file_path = os.path.join(desktop, "_temp.json")
        
        try:
            with open(file_path, 'w') as f:
                json.dump(all_json_objects, f, indent=2)
            
            # Copy path to clipboard
            copy_to_clipboard(file_path)
            om.MGlobal.displayInfo("Copied {} objects. Path in clipboard.".format(len(all_json_objects)))
            
        except Exception as e:
            om.MGlobal.displayError("Error writing file: {}".format(e))

    def process_mesh(self, meshobj, transform_dag_path):
        
        points = meshobj.getPoints(om.MSpace.kObject)
        json_vertices = []
        for i in range(len(points)):
            p = points[i]
            json_vertices.append({
                "id": i,
                "co": [round(p.x, 6), round(p.y, 6), round(p.z, 6)],
                "tag": "Smooth" 
            })
            
        # 2. Faces
        polygons_iter = om.MItMeshPolygon(transform_dag_path)
        json_faces = []
        while not polygons_iter.isDone():
            ids = polygons_iter.getVertices()
            json_faces.append({"ids": list(ids)})
            polygons_iter.next()
            
        # 3. Edges (Creases)
        json_edges = []
        try:
            edge_creases = meshobj.getCreaseEdges() # (MUintArray edgeIds, MDoubleArray creaseData)
        except:
            edge_creases = None
            
        if edge_creases and len(edge_creases) == 2 and len(edge_creases[0]) > 0:
            edge_ids = edge_creases[0]
            crease_vals = edge_creases[1]
            for i in range(len(edge_ids)):
                if crease_vals[i] > 0.1:
                    eid = edge_ids[i]
                    # Get vertices of this edge
                    v_ids = meshobj.getEdgeVertices(eid)
                    e_data = {
                        "ids": [v_ids[0], v_ids[1]],
                        "tag": "Crease"
                    }
                    json_edges.append(e_data)

        # 4. Matrix
        #transform_fn = om.MFnTransform(transform_dag_path)
        # Get World Matrix
        mm = transform_dag_path.inclusiveMatrix()
        mm_transposed = mm.transpose()
        flat_matrix = list(mm_transposed) # 16 floats
        
        obj_data = {
            "guid": str(meshobj.uuid()),
            "type": "Mesh",
            "software": "Maya",
            "matrix": flat_matrix,
            "vertices": json_vertices,
            "edges": json_edges,
            "faces": json_faces
        }
        return obj_data


class MayaPaste:
    def execute(self):
        # Read clipboard
        txt = get_clipboard_text()
        if not txt:
            om.MGlobal.displayError("Clipboard empty.")
            return

        file_path = txt.strip().strip('"')
        
        if not os.path.exists(file_path):
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            fallback = os.path.join(desktop, "_temp.json")
            if os.path.exists(fallback):
                file_path = fallback
                print("Reading from fallback: {}".format(file_path))
            else:
                om.MGlobal.displayError("File not found: {}".format(file_path))
                return

        try:
            with open(file_path, 'r') as f:
                data_list = json.load(f)
        except Exception as e:
            om.MGlobal.displayError("JSON Parse Error: {}".format(e))
            return
            
        if isinstance(data_list, dict):
            data_list = [data_list]

        # Process
        count = 0
        new_objects = []
        for obj_data in data_list:
            if obj_data.get("type") == "Mesh":
                res = self.create_object(obj_data)
                if res:
                    count += 1
                    new_objects.append(res)
        
        if new_objects:
            cmds.select(new_objects, replace=True)
            
        om.MGlobal.displayInfo("Pasted {} objects.".format(count))

    def create_object(self, data):
        # 1. Prepare Arrays
        # Sort vertices by ID just in case
        verts_data = data.get("vertices", [])
        verts_data.sort(key=lambda x: x["id"])
        
        points = om.MPointArray()
        for v in verts_data:
            co = v["co"]
            points.append(om.MPoint(co[0], co[1], co[2]))
            
        faces_data = data.get("faces", [])
        #num_polygons = len(faces_data)
        polygon_counts = om.MIntArray()
        polygon_connects = om.MIntArray()
        
        for f in faces_data:
            ids = f["ids"]
            polygon_counts.append(len(ids))
            for vid in ids:
                polygon_connects.append(vid)
                
        # 2. Create Mesh
        mesh_fn = om.MFnMesh()
        new_mesh_obj = mesh_fn.create(points, polygon_counts, polygon_connects)
        
        # 3. Creases
        edges_data = data.get("edges", [])
        crease_edge_ids = om.MIntArray()
        crease_vals = om.MDoubleArray()

        if edges_data:
            target_creases = set()
            for e_data in edges_data:
                if e_data.get("tag") == "Crease":
                    ids = e_data.get("ids")
                    if len(ids) == 2:
                        key = tuple(sorted(ids))
                        target_creases.add(key)
            
            if target_creases:
                num_edges = mesh_fn.numEdges
                for i in range(num_edges):
                    v_ids = mesh_fn.getEdgeVertices(i)
                    key = tuple(sorted(v_ids))
                    if key in target_creases:
                        crease_edge_ids.append(i)
                        crease_vals.append(2.0) 
            
            if len(crease_edge_ids) > 0:
                mesh_fn.setCreaseEdges(crease_edge_ids, crease_vals)
                
        # 4. Handle Transform & Attributes
        # Get parent transform
        dag_node_fn = om.MFnDagNode(new_mesh_obj)
        parent_obj = om.MObject.kNullObj
        if dag_node_fn.parentCount() > 0:
            parent_obj = dag_node_fn.parent(0)

        transform_path_str = ""
        shape_path_str = ""

        # Rename Transform
        if not parent_obj.isNull():
            parent_fn = om.MFnDependencyNode(parent_obj)
            parent_fn.setName("ImportedMesh") # This might auto-rename to ImportedMesh1, etc.
            
            # Get clean full path
            # We re-acquire DAG path from the MObject to be safe
            parent_dag = om.MDagPath.getAPathTo(parent_obj)
            transform_path_str = parent_dag.fullPathName()
            
            # Apply Matrix
            if "matrix" in data and len(data["matrix"]) == 16:
                mat_list = data["matrix"]
                try:
                    cmds.xform(transform_path_str, m=mat_list, ws=True)
                except Exception as e:
                    om.MGlobal.displayWarning("Could not apply matrix to {}: {}".format(transform_path_str, e))
        
        # Rename Shape (optional, but good for cleanliness)
        mesh_fn.setName("ImportedMeshShape")
        shape_dag = om.MDagPath.getAPathTo(new_mesh_obj)
        shape_path_str = shape_dag.fullPathName()

        # 6. Assign Shader & Attributes
        if transform_path_str:
            try:
                cmds.sets(transform_path_str, edit=True, forceElement="lambert1") # Explicit lambert1
            except Exception as e:
                # Try initialShadingGroup if lambert1 fails for some reason
                try:
                     cmds.sets(transform_path_str, edit=True, forceElement="initialShadingGroup")
                except:
                    om.MGlobal.displayWarning("Could not assign lambert1/initialShadingGroup to {}".format(transform_path_str))
                    
        if shape_path_str:
            try:
                cmds.setAttr(shape_path_str + ".displaySmoothMesh", 2) # 2 = Smooth Mesh Preview
            except Exception as e:
                om.MGlobal.displayWarning("Could not set Smooth Mesh Preview: {}".format(e))
        
        return transform_path_str

# ------------------------------------------------------------------------------
# Plugin Commands
# ------------------------------------------------------------------------------
class EasyCopyCommand(om.MPxCommand):
    def __init__(self):
        om.MPxCommand.__init__(self)

    def doIt(self, args):
        MayaCopy().execute()

    @staticmethod
    def creator():
        return EasyCopyCommand()

class EasyPasteCommand(om.MPxCommand):
    def __init__(self):
        om.MPxCommand.__init__(self)

    def doIt(self, args):
        MayaPaste().execute()

    @staticmethod
    def creator():
        return EasyPasteCommand()

# ------------------------------------------------------------------------------
# Plugin Setup (initialize/uninitialize)
# ------------------------------------------------------------------------------
def create_menu():
    gMainWindow = mel.eval('$temp=$gMainWindow')
    if cmds.menu(kMenuLabel, exists=True):
        cmds.deleteUI(kMenuLabel)
    
    menu = cmds.menu(kMenuLabel, parent=gMainWindow, tearOff=True, label=kMenuLabel)
    cmds.menuItem(label="Copy", command=lambda x: cmds.EasyCopyCmd(), image="copy.png")
    cmds.menuItem(label="Paste", command=lambda x: cmds.EasyPasteCmd(), image="paste.png")

def remove_menu():
    if cmds.menu(kMenuLabel, exists=True):
        cmds.deleteUI(kMenuLabel)

def setup_hotkeys():
    # Only if not batch mode
    if cmds.about(batch=True):
        return

    # Name Commands
    # We create the NameCommands that call our plugin commands (which are registered as Global commands by the plugin)
    # The plugin command names are defined by kPluginCmdNameCopy/Paste.
    
    # Ensure they exist as cmds before linking.
    # Note: MPxCommand registers them as MEL commands too.
    
    cmds.nameCommand("EasyCopyNameCmd", annotation="EasyCopy", command=kPluginCmdNameCopy)
    cmds.nameCommand("EasyPasteNameCmd", annotation="EasyPaste", command=kPluginCmdNamePaste)

    # Hotkeys: Ctrl+Shift+C / V (Maya Style: Uppercase implies Shift)
    try:
        cmds.hotkey(keyShortcut='C', ctl=True, name="EasyCopyNameCmd")
        cmds.hotkey(keyShortcut='V', ctl=True, name="EasyPasteNameCmd")
    except Exception as e:
        sys.stderr.write("EasyCopy: Failed to register hotkeys: {}\n".format(e))

def remove_hotkeys():
    # Optional: We usually don't remove hotkeys on unload to avoid messing up user config too much, 
    # but strictly we should clean up.
    try:
        cmds.hotkey(keyShortcut='C', ctl=True, name="")
        cmds.hotkey(keyShortcut='V', ctl=True, name="")
    except:
        pass

def initializePlugin(mobject):
    mplugin = om.MFnPlugin(mobject, "Weijie Tao", kVersioning, "Any")
    
    # Cleanup legacy unique Runtime Commands if they exist (collisions)
    if cmds.runTimeCommand(kPluginCmdNameCopy, exists=True):
        cmds.runTimeCommand(kPluginCmdNameCopy, edit=True, delete=True)
    if cmds.runTimeCommand(kPluginCmdNamePaste, exists=True):
        cmds.runTimeCommand(kPluginCmdNamePaste, edit=True, delete=True)

    try:
        mplugin.registerCommand(kPluginCmdNameCopy, EasyCopyCommand.creator)
        mplugin.registerCommand(kPluginCmdNamePaste, EasyPasteCommand.creator)
    except Exception as e:
        sys.stderr.write("Failed to register command: {}\n".format(e))
        raise

    # UI setup
    try:
        if not cmds.about(batch=True):
            create_menu()
            setup_hotkeys()
    except Exception as e:
         sys.stderr.write("Failed to setup UI: {}\n".format(e))

def uninitializePlugin(mobject):
    mplugin = om.MFnPlugin(mobject)
    
    try:
        mplugin.deregisterCommand(kPluginCmdNameCopy)
        mplugin.deregisterCommand(kPluginCmdNamePaste)
    except Exception as e:
        sys.stderr.write("Failed to deregister command: {}\n".format(e))
        raise
        
    # UI cleanup
    if not cmds.about(batch=True):
        try:
            remove_menu()
        except:
            pass
            
        try:
            remove_hotkeys()
        except:
            pass
