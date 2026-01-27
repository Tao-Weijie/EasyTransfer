import bpy
import json
import os
from mathutils import Matrix
import numpy as np

class ToJSON:
    @staticmethod
    def convert_mesh(obj):
        """Converts a Blender mesh Object to JSON dictionary."""
        mesh = obj.data
        n_verts = len(mesh.vertices)
        n_edges = len(mesh.edges)
        
        # 1. Vertices
        co_array = np.zeros(n_verts * 3, dtype=np.float32)
        mesh.vertices.foreach_get("co", co_array)
        co_array = co_array.reshape(n_verts, 3)
        np.round(co_array, 6, out=co_array)
        
        # Vertex Creases
        v_crease_array = np.zeros(n_verts, dtype=np.float32)
        if "crease_vert" in mesh.attributes:
            att = mesh.attributes["crease_vert"]
            if att.domain == 'POINT':
                att.data.foreach_get("value", v_crease_array)
        
        co_list = co_array.tolist() 
        vc_list = v_crease_array.tolist()

        json_vertices = [
            {"co": c, "crease": vc} 
            for c, vc in zip(co_list, vc_list)
        ]

        # 2. Edges
        edge_verts = np.zeros(n_edges * 2, dtype=np.int32)
        mesh.edges.foreach_get("vertices", edge_verts)
        edge_verts = edge_verts.reshape(n_edges, 2)
        
        e_crease_array = np.zeros(n_edges, dtype=np.float32)
        if "crease_edge" in mesh.attributes:
            att = mesh.attributes["crease_edge"]
            if att.domain == 'EDGE':
                att.data.foreach_get("value", e_crease_array)
                
        e_list = edge_verts.tolist() 
        ec_list = e_crease_array.tolist()
        json_edges = [
            {"ids": ev, "crease": ec}
            for ev, ec in zip(e_list, ec_list)
        ]

        # 3. Faces
        json_faces = []
        for poly in mesh.polygons:
            f_data = {
                "ids": list(poly.vertices)
            }
            json_faces.append(f_data)

        mw = obj.matrix_world
        flat_matrix = [col for row in mw for col in row]

        subd = 0
        if obj.modifiers:
            mod = obj.modifiers[-1]
            if mod.type == 'SUBSURF' and mod.subdivision_type == 'CATMULL_CLARK':
                subd = mod.levels
        
        obj_data = {
            "guid": None, 
            "software": "Blender",
            "type": "MESH",
            "subd": subd,
            "unit": bpy.context.scene.unit_settings.scale_length,
            "matrix": flat_matrix,
            "vertices": json_vertices,
            "edges": json_edges,
            "faces": json_faces
        }

        return obj_data
    
    @staticmethod
    def calculate_knots(pt, degree, use_cyclic_u, use_endpoint_u, use_bezier_u):
        """
        Calculates a standard knot vector covering all 8 Blender topology cases.
        """
        # 1. Determine Knot Count
        count = len(pt)
        n_knots = count + degree + 1
        if use_cyclic_u:
            n_knots += degree
        
        points = []
        knots = [] 
        

        A = use_cyclic_u    # Cyclic (Closed)
        B = use_endpoint_u  # Endpoint (Clamped)
        C = use_bezier_u    # Bezier (Piecewise)

        if A and B and C:
            if count % degree == 0:
                n_knots = (count // degree) * degree + degree + 1
                knots = [0.0] * n_knots
                
                for i in range(n_knots):
                    knots[i] = float((i - 1) // degree) + 1


        elif A and B and not C:
            n_knots = count + 2*degree + 1
            knots = [0.0]*n_knots
            points = pt

            for i in range(1, degree + 1):
                knots[i] = 1.0
            for i in range(degree + 1, count + 1):
                knots[i] = float(i - degree + 1)
            end_clamp_val = knots[count] + 1.0
            for i in range(count + 1, count + degree + 1):
                knots[i] = end_clamp_val
            current_val = end_clamp_val
            for i in range(count + degree + 1, n_knots):
                current_val += 1.0
                knots[i] = current_val

        elif A and not B and C:
            if count % degree == 0:
                n_knots = (count // degree) * degree + degree + 1
                knots = [0.0] * n_knots
                
                for i in range(1,n_knots):
                    knots[i] = float((i - 1) // degree) +1

        elif A and not B and not C:
            n_knots = count + 2*degree + 1
            knots = [0.0]*n_knots
            points = pt

            for i in range(n_knots):
                knots[i] = float(i)


        elif not A and B and C:
            n_knots = ((count - 1) // degree) * degree + 1 + degree + 1
            knots = [0.0] * n_knots

            for i in range(1,n_knots):
                knots[i] = float((i - 1) // degree) + 1

        elif not A and B and not C:
            n_knots = count + degree + 1
            knots = [0.0]*n_knots
            points = pt
            
            for i in range(degree + 1):
                knots[i] = 0.0
            
            span_count = count - degree
            for i in range(1, span_count):
                knots[degree + i] = float(i)
            
            max_val = float(span_count)
            for i in range(degree + span_count, n_knots):
                knots[i] = max_val

        elif not A and not B and C:
            n_knots = ((count - 2) // degree) * degree + 1 + degree + 1
            knots = [0.0]*n_knots

            for i in range(1,n_knots):
                knots[i] = float((i - 1) // degree) +1

        elif not A and not B and not C:
            n_knots = count + degree + 1
            knots = [0.0]*n_knots
            points = pt
            
            for i in range(n_knots):
                knots[i] = float(i)

        return knots, points

    @staticmethod
    def convert_poly(spline,matrix):
        """Converts Blender Poly splines to JSON."""
        n_points = len(spline.points)
        co_array = np.zeros(n_points * 4, dtype=np.float32)
        spline.points.foreach_get("co", co_array)
        co_array = co_array.reshape(n_points, 4)
        
        # Poly usually ignores w, but keep x,y,z
        # Using numpy to round
        np.round(co_array, 6, out=co_array)
        
        co_list = co_array[:, :3].tolist() # Take x,y,z
        
        json_vertices = [{"co": c} for c in co_list]
                
        json_obj = {
            "guid": None, 
            "software": "Blender",
            "type": "POLY",
            "unit": bpy.context.scene.unit_settings.scale_length,
            "matrix": matrix,
            "points": json_vertices,
            "degree": 1,
            "closed": spline.use_cyclic_u,
        }
            
        return json_obj

    @staticmethod
    def convert_bezier(spline,matrix):
        """Converts Blender Bezier splines to JSON (Degree 3 NURBS)."""
        n_points = len(spline.bezier_points)
        
        co = np.zeros(n_points * 3, dtype=np.float32)
        left = np.zeros(n_points * 3, dtype=np.float32)
        right = np.zeros(n_points * 3, dtype=np.float32)
        
        spline.bezier_points.foreach_get("co", co)
        spline.bezier_points.foreach_get("handle_left", left)
        spline.bezier_points.foreach_get("handle_right", right)
        
        co = co.reshape(n_points, 3)
        left = left.reshape(n_points, 3)
        right = right.reshape(n_points, 3)
        
        np.round(co, 6, out=co)
        np.round(left, 6, out=left)
        np.round(right, 6, out=right)
        
        json_vertices = [
            {"co": c.tolist(), "left": l.tolist(), "right": r.tolist()} 
            for c, l, r in zip(co, left, right)
        ]
            
        json_obj = {
            "guid": None, 
            "software": "Blender",
            "type": "BEZIER",
            "unit": bpy.context.scene.unit_settings.scale_length,
            "matrix": matrix,
            "points": json_vertices,
            "degree": 3,
            "closed": spline.use_cyclic_u,
        }
            
        return json_obj
            
    @staticmethod
    def convert_nurbs(spline,matrix):
        """Converts Blender NURBS splines to JSON."""
        n_points = len(spline.points)
        co_array = np.zeros(n_points * 4, dtype=np.float32)
        spline.points.foreach_get("co", co_array)
        co_array = co_array.reshape(n_points, 4)
        
        np.round(co_array, 6, out=co_array)
        
        # Only converting to list of dicts as per requirement
        
        knots, points = ToJSON.calculate_knots(spline.points, spline.order_u - 1, spline.use_cyclic_u, spline.use_endpoint_u, spline.use_bezier_u)
        
        json_vertices = [{"co": c.tolist()} for c in points]
 
        json_obj = {
            "guid": None, 
            "software": "Blender",
            "type": "NURBS",
            "unit": bpy.context.scene.unit_settings.scale_length,
            "matrix": matrix,
            "points": json_vertices,
            "degree": spline.order_u - 1,
            "closed": spline.use_cyclic_u,
            "knots": knots
        }
        return json_obj
            
    @staticmethod
    def convert_curve(obj):
        """Dispatches to all converters to handle mixed types."""
        all_objects = []
        curve = obj.data
      
        mw = obj.matrix_world
        flat_matrix = [col for row in mw for col in row]
        
        for spline in curve.splines:
            if spline.type == 'POLY':
                crv = ToJSON.convert_poly(spline,flat_matrix)          
                if crv:
                    all_objects.append(crv)
            elif spline.type == 'BEZIER':
                crv = ToJSON.convert_bezier(spline,flat_matrix)
                if crv:
                    all_objects.append(crv)
            elif spline.type == 'NURBS':
                crv = ToJSON.convert_nurbs(spline,flat_matrix)
                if crv:
                    all_objects.append(crv)
            
        return all_objects if all_objects else None
       


class ToOBJ:
    @staticmethod
    def create_mesh(obj_data):
        """Creates a standard mesh object."""
        if "vertices" not in obj_data or "faces" not in obj_data or "edges" not in obj_data:
            return None

        # 1. Prepare Mesh Data
        json_verts = obj_data.get("vertices", [])
        
        verts_co = np.array([v["co"] for v in json_verts], dtype=np.float32)
        v_crease = np.array([v["crease"] for v in json_verts], dtype=np.float32)
        faces_ids = [f_data["ids"] for f_data in obj_data["faces"]]

        # 2. Create Mesh
        software = obj_data.get("software", "Imported")
        mesh_name = f"{software}Mesh"
        mesh = bpy.data.meshes.new(name=mesh_name)
        
        mesh.from_pydata(verts_co, [], faces_ids)
        mesh.polygons.foreach_set("use_smooth", [True] * len(mesh.polygons))
        
        # 3. Apply Creases
        if v_crease.any():
            try:
                if "crease_vert" not in mesh.attributes:
                    vc_att = mesh.attributes.new(name="crease_vert", type='FLOAT', domain='POINT')
                else:
                    vc_att = mesh.attributes["crease_vert"]
                vc_att.data.foreach_set("value", v_crease)
            except Exception as e:
                print(f"Failed to set vertex crease: {e}")
        
        # 4. Apply Creases
        creased_pairs = {}
        
        for e_data in obj_data["edges"]:
            crease_val = e_data.get("crease", 0.0)
            if crease_val > 0.0:
                ids = e_data.get("ids", [])
                pair = tuple(sorted((ids[0], ids[1])))
                creased_pairs[pair] = crease_val
        
        if creased_pairs:
            try:
                if "crease_edge" not in mesh.attributes:
                    crease_att = mesh.attributes.new(name="crease_edge", type='FLOAT', domain='EDGE')
                else:
                    crease_att = mesh.attributes["crease_edge"]
                
                n_edges = len(mesh.edges)
                edge_verts = np.zeros(n_edges * 2, dtype=np.int32)
                mesh.edges.foreach_get("vertices", edge_verts)
                edge_verts = edge_verts.reshape(n_edges, 2)
                
                values = np.zeros(n_edges, dtype=np.float32)
                
                for i, ev in enumerate(edge_verts):
                    pair = tuple(sorted((ev[0], ev[1])))                        
                    val = creased_pairs.get(pair)
                    if val:
                        values[i] = val
                
                crease_att.data.foreach_set("value", values)
            except Exception as e:
                print(f"Failed to set crease attribute: {e}")

        mesh.update()
        
        # 4. Create Object
        obj = bpy.data.objects.new(mesh_name, mesh)
        bpy.context.collection.objects.link(obj)
        ToOBJ.apply_matrix(obj, obj_data)
        
        # 5. Add Modifier if SubD
        if obj_data.get("subd", 0) > 0:
            mod = obj.modifiers.new(name="Subdivision", type='SUBSURF')
            mod.levels = obj_data.get("subd")
            
        return obj

    @staticmethod
    def analyze_knots(knots, degree, point_count):
        """
        Analyzes knot vector to determine curve periodicity and clamping.
        Returns (is_closed, is_endpoint, is_bezier)
        """
        if not knots or len(knots) < 2 * degree:
            return False, False, False

        knots = np.array(knots, dtype=np.float32)
        
        # Check Clamping (Endpoint)
        # First degree+1 knots should be equal
        start_clamped = np.allclose(knots[:degree+1], knots[0])
        end_clamped = np.allclose(knots[-(degree+1):], knots[-1])
        is_endpoint = start_clamped and end_clamped
        
        # Check Closed (Cyclic)
        # If not clamped, and knots are uniform?
        # A simple uniformity check: gaps are approx equal
        # But closed curves might just be "not clamped".
        is_closed = False
        if not is_endpoint:
            # Check for uniformity
            diffs = np.diff(knots)
            # Ignore tiny diffs
            valid_diffs = diffs[diffs > 1e-6]
            if len(valid_diffs) > 0:
                 # Check if all steps are roughly the same
                 mean_step = np.mean(valid_diffs)
                 is_uniform = np.allclose(valid_diffs, mean_step, rtol=1e-3)
                 if is_uniform:
                     is_closed = True

        # Check Bezier
        # Clamped ends + specific internal structure (if any)
        is_bezier = False
        if is_endpoint:
             # Basic check: just one segment?
             if point_count == degree + 1:
                 is_bezier = True
             else:
                 # Multi-segment bezier: internal knots have multiplicity 'degree'
                 pass

        return is_closed, is_endpoint, is_bezier

    @staticmethod
    def create_curve(obj_data, crvtype='NURBS'):
        """Generic curve creation handling."""
        if "points" not in obj_data and "degree" not in obj_data:
            return None
            
        software = obj_data.get("software", "Imported")
        curve_name = f"{software}Curve"
        
        # Create Curve Data
        curve_data = bpy.data.curves.new(name=curve_name, type='CURVE')
        curve_data.dimensions = '3D'
        spline = curve_data.splines.new(crvtype)
        
        degree = obj_data.get("degree", 1)
        spline.order_u = degree + 1
        
        global_points = obj_data.get("points", [])
        knots = obj_data.get("knots", [])
        
        # Analyze knots if present to override/set flags
        is_closed = obj_data.get("closed", False)
        use_endpoint = False # Default
        
        if knots:
            calc_closed, calc_endpoint, calc_bezier = ToOBJ.analyze_knots(knots, degree, len(global_points))
            # Use calculated properties to refine
            if calc_endpoint:
                use_endpoint = True
                is_closed = False # Clamped is typically not cyclic in Blender sense
            elif calc_closed:
                is_closed = True
                
        spline.use_cyclic_u = is_closed
        spline.use_endpoint_u = use_endpoint # Valid only for NURBS/Poly
        
        n_points = len(global_points)
        
        if crvtype == 'POLY':
            spline.points.add(n_points - 1)
            
            co_flat = []
            for pt in global_points:
                co = pt.get("co", [0,0,0])
                if len(co) == 3:
                     co_flat.extend([co[0], co[1], co[2], 1.0])
                else:
                     co_flat.extend(co)
            
            spline.points.foreach_set("co", co_flat)
                       
        elif crvtype == 'BEZIER':          
            spline.bezier_points.add(n_points - 1)
            
            co_flat = []
            left_flat = []
            right_flat = []
            
            for pt in global_points:
                co_flat.extend(pt.get("co", [0,0,0]))
                left_flat.extend(pt.get("handle_left", [0,0,0])) # Use default if missing
                right_flat.extend(pt.get("handle_right", [0,0,0]))
            # Re-doing the loop to be correct with keys.
            co_flat = []
            left_flat = []
            right_flat = []
            for pt in global_points:
                 co_flat.extend(pt.get("co", [0,0,0]))
                 
                 # left/right
                 l = pt.get("left") if "left" in pt else pt.get("handle_left", [0,0,0])
                 r = pt.get("right") if "right" in pt else pt.get("handle_right", [0,0,0])
                 
                 left_flat.extend(l)
                 right_flat.extend(r)

            spline.bezier_points.foreach_set("co", co_flat)
            spline.bezier_points.foreach_set("handle_left", left_flat)
            spline.bezier_points.foreach_set("handle_right", right_flat)            

            for bp in spline.bezier_points:
                bp.handle_right_type = 'FREE'
                bp.handle_left_type = 'FREE'
            
            spline.use_endpoint_u = True 
            
        else: # NURBS
            spline.points.add(n_points - 1)
            
            co_flat = []
            for pt in global_points:
                co = pt.get("co", [0,0,0,1])
                if len(co) == 3:
                     co_flat.extend([co[0], co[1], co[2], 1.0])
                else:
                     co_flat.extend(co)
            
            spline.points.foreach_set("co", co_flat)
        
        obj = bpy.data.objects.new(curve_name, curve_data)
        bpy.context.collection.objects.link(obj)
        ToOBJ.apply_matrix(obj, obj_data)
        
        return obj

    @staticmethod
    def apply_matrix(obj, obj_data):
        if "matrix" in obj_data and len(obj_data["matrix"]) == 16:
            try:
                m_list = obj_data["matrix"]
                rows = [m_list[i:i+4] for i in range(0, 16, 4)]
                obj.matrix_world = Matrix(rows)
            except Exception as e:
                print(f"Failed to apply matrix: {e}")


class BlenderCopy(bpy.types.Operator):
    """Copy selected meshes to clipboard"""
    bl_idname = "object.easy_copy"
    bl_label = "Copy to Clipboard"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        """Copies selected objects to JSON format."""
        # 1. Check Selection
        if not context.selected_objects:
            self.report({'WARNING'}, "No supported objects selected.")
            return {'CANCELLED'}

        # 2. Convert Selected Objects
        data_list = []
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                obj_data = ToJSON.convert_mesh(obj)
                if obj_data:
                    data_list.append(obj_data)
            elif obj.type == 'CURVE':
                obj_data = ToJSON.convert_curve(obj)
                if obj_data:
                    data_list.extend(obj_data)
            
        if not data_list:
             return {'CANCELLED'}

        # 3.Write to File
        try:
            # Mac/Linux/Windows 'Desktop'
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            file_path = os.path.join(desktop, "_temp.json")
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data_list, f, indent=2)
                
            self.report({'INFO'}, f"Copied {len(data_list)} objects")
            
            # Copy to Clipboard
            context.window_manager.clipboard = file_path
            
        except Exception as e:
            self.report({'ERROR'}, f"Error writing file: {e}")
            return {'CANCELLED'}
            
        return {'FINISHED'}

class BlenderPaste(bpy.types.Operator):
    """Paste JSON from Clipboard"""
    bl_idname = "object.easy_paste"
    bl_label = "Paste from Clipboard"
    bl_options = {'REGISTER', 'UNDO'}
        
    def execute(self, context):
        """Reads file path from clipboard and loads JSON data."""
        try:
            file_path = context.window_manager.clipboard.strip().strip('"')
            
            if not os.path.exists(file_path):
                # Fallback to desktop default if not in clipboard or invalid
                desktop = os.path.join(os.path.expanduser("~"), "Desktop")
                fallback = os.path.join(desktop, "_temp.json")
                if os.path.exists(fallback):
                    file_path = fallback
                else:
                    self.report({'ERROR'}, f"File not found at path: {file_path}")
                    return {'CANCELLED'}
    
            with open(file_path, 'r', encoding='utf-8') as f:
                data_list = json.load(f)
                
            if isinstance(data_list, dict):
                data_list = [data_list]
            elif not isinstance(data_list, list):
                self.report({'ERROR'}, "Invalid JSON structure")
                return {'CANCELLED'}
                
        except Exception as e:
            self.report({'ERROR'}, f"Error reading file: {e}")
            return {'CANCELLED'}
    
        bpy.ops.object.select_all(action='DESELECT')
        
        target_scale = context.scene.unit_settings.scale_length
        pasted_objects = []
        
        count = 0
        for obj_data in data_list:
            # Calculate Scale Factor
            scale_factor = 1.0
            source_scale = obj_data.get("unit", 1.0) # Default to 1.0 if not present (legacy)
            
            # Avoid division by zero (unlikely for scale_length)
            if abs(source_scale - target_scale) > 1e-9:
                scale_factor = source_scale / target_scale
            
            obj = None
            type_str = obj_data.get("type", "").upper()
            
            if type_str == "MESH":
                obj = ToOBJ.create_mesh(obj_data)
            elif type_str == "POLY":
                obj = ToOBJ.create_curve(obj_data,crvtype = "POLY")
            elif type_str == "BEZIER":
                obj = ToOBJ.create_curve(obj_data,crvtype = "BEZIER")
            elif type_str == "NURBS":
                obj = ToOBJ.create_curve(obj_data,crvtype = "NURBS")

            
            if obj:
                # Handle Scaling
                if abs(scale_factor - 1.0) > 1e-6:
                    obj.scale = (scale_factor, scale_factor, scale_factor)
                    
                    # Apply Transform (Scale) to Geometry
                    # We need to ensure ONLY this object is selected/active for the operator
                    bpy.ops.object.select_all(action='DESELECT')
                    obj.select_set(True)
                    context.view_layer.objects.active = obj
                    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
                
                pasted_objects.append(obj)
                count += 1
        
        # Select all pasted objects
        bpy.ops.object.select_all(action='DESELECT')
        for obj in pasted_objects:
            obj.select_set(True)
            # Set the last one as active, standard blender behavior
            context.view_layer.objects.active = obj
                
        self.report({'INFO'}, f"Successfully pasted {count} objects.")
        return {'FINISHED'}