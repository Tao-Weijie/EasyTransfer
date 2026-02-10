#! python 3
# r: usd-core
import Rhino
import os
import System
from System.Drawing import Color
from System import Guid
from Eto.Forms import Clipboard
from pxr import Usd, UsdGeom, Gf, Sdf


class Converter:
    """Handles conversion between Rhino Geometry and USD Prims."""
    
    @staticmethod
    def ExportUserAttr(rh_obj, usd_prim):
        """Exports Rhino User Strings to USD Custom Attributes."""
        attrs = rh_obj.Attributes
        if not attrs:
            return
        
        user_strings = attrs.GetUserStrings()
        if user_strings:
            for key in user_strings.AllKeys:
                val = attrs.GetUserString(key)
                try:
                    attr_name = f"userProperties:{key}"
                    attr = usd_prim.CreateAttribute(attr_name, Sdf.ValueTypeNames.String)
                    attr.Set(str(val))
                except Exception:
                    pass

    @staticmethod
    def ImportUserAttr(usd_prim, rh_obj):
        """Imports USD Custom Attributes to Rhino User Strings."""
        # Get all attributes
        attrs = usd_prim.GetAttributes()
        if not attrs:
            return
            
        for attr in attrs:
            name = attr.GetName()
            if name.startswith("userProperties:"):
                key = name.split(":", 1)[1]
                val = attr.Get()
                if val is not None:
                    rh_obj.Attributes.SetUserString(key, str(val))


    @staticmethod
    def GetValidName(name):
        """Sanitizes a string to be a valid USD identifier."""
        if not name:
            return None
        
        valid_name = "".join(c if c.isalnum() or c == '_' else '_' for c in name)
        
        if valid_name and valid_name[0].isdigit():
            valid_name = "_" + valid_name
            
        return valid_name

    @staticmethod
    def ExportMesh(rh_obj, stage, parent_path, name, mesh_override=None):
        """Converts a Rhino Object's Mesh to a USD Mesh Prim."""
        mesh = mesh_override if mesh_override else rh_obj.Geometry
        
        mesh_path = f"{parent_path}/{name}"
        usd_mesh = UsdGeom.Mesh.Define(stage, mesh_path)
        
        # Vertices (Topology)
        topo_verts = mesh.TopologyVertices
        points = [Gf.Vec3f(v.X, v.Y, v.Z) for v in topo_verts]
        usd_mesh.CreatePointsAttr(points)
        
        # Helper to map mesh vertex index to topology vertex index
        def topo_idx(idx):
            return topo_verts.TopologyVertexIndex(idx)
        
        # Faces
        face_counts = []
        face_indices = []
        processed_faces = set()
        
        # 1. Export Ngons (Real Ngons)
        if mesh.Ngons.Count > 0:
            for ngon in mesh.Ngons:
                v_indices = ngon.BoundaryVertexIndexList()
                if v_indices and len(v_indices) > 0:
                    face_counts.append(len(v_indices))
                    topo_indices = [topo_idx(vi) for vi in v_indices]
                    face_indices.extend(topo_indices)
                    
                    f_indices = ngon.FaceIndexList()
                    for f_idx in f_indices:
                        processed_faces.add(f_idx)
        
        # 2. Export remaining Faces (Quads/Tris not in Ngons)
        faces = mesh.Faces
        for i in range(faces.Count):
            if i in processed_faces:
                continue
                
            f = faces[i]
            if f.IsQuad:
                face_counts.append(4)
                face_indices.extend([
                    topo_idx(f.A), 
                    topo_idx(f.B), 
                    topo_idx(f.C), 
                    topo_idx(f.D)
                ])
            else:
                face_counts.append(3)
                face_indices.extend([
                    topo_idx(f.A), 
                    topo_idx(f.B), 
                    topo_idx(f.C)
                ])
        
        usd_mesh.CreateFaceVertexCountsAttr(face_counts)
        usd_mesh.CreateFaceVertexIndicesAttr(face_indices)
        
        # 3. Handle Creases (Unwelded Edges)
        crease_indices = []
        crease_lengths = []
        crease_sharpnesses = []
        
        topo_edges = mesh.TopologyEdges
        
        for i in range(topo_edges.Count):
            connected_faces = topo_edges.GetConnectedFaces(i)
            
            if len(connected_faces) == 2:
                edge_topo_pair = topo_edges.GetTopologyVertices(i)
                tv1 = edge_topo_pair.I
                tv2 = edge_topo_pair.J
                
                if topo_edges.IsEdgeUnwelded(i):
                    crease_indices.extend([tv1, tv2])
                    crease_lengths.append(2)
                    crease_sharpnesses.append(10.0) # Sharp

        if crease_indices:
            usd_mesh.CreateCreaseIndicesAttr(crease_indices)
            usd_mesh.CreateCreaseLengthsAttr(crease_lengths)
            usd_mesh.CreateCreaseSharpnessesAttr(crease_sharpnesses)
        
        usd_mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
        # Extent (Bounding Box)
        bbox = mesh.GetBoundingBox(True)
        extent = [Gf.Vec3f(bbox.Min.X, bbox.Min.Y, bbox.Min.Z), Gf.Vec3f(bbox.Max.X, bbox.Max.Y, bbox.Max.Z)]
        usd_mesh.CreateExtentAttr(extent)
        
        # User Attributes
        Converter.ExportUserAttr(rh_obj, usd_mesh.GetPrim())
        
        return usd_mesh

    @staticmethod
    def ExportSubD(rh_obj, stage, parent_path, name):
        """Converts a Rhino Object's SubD to a USD Mesh Prim with Catmull-Clark subdivision."""
        subd = rh_obj.Geometry
        ctrl_mesh = Rhino.Geometry.Mesh.CreateFromSubDControlNet(subd)

        usd_mesh = Converter.ExportMesh(rh_obj, stage, parent_path, name, mesh_override=ctrl_mesh)
        
        usd_mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.catmullClark)
        Converter.ExportUserAttr(rh_obj, usd_mesh.GetPrim())
        
        return usd_mesh

    @staticmethod
    def ExportPointCloud(rh_obj, stage, parent_path, name):
        """Converts a Rhino Object's PointCloud to a USD Points Prim."""
        geo = rh_obj.Geometry
        
        points_path = f"{parent_path}/{name}"
        usd_points = UsdGeom.Points.Define(stage, points_path)
        
        # 1. Points
        rh_points = geo.GetPoints()
        points = [Gf.Vec3f(p.X, p.Y, p.Z) for p in rh_points]
        usd_points.CreatePointsAttr(points)
        
        # 2. Colors 
        if geo.ContainsColors:
            rh_colors = geo.GetColors()
            colors = [Gf.Vec3f(c.R / 255.0, c.G / 255.0, c.B / 255.0) for c in rh_colors]
            usd_points.CreateDisplayColorAttr(colors)
        
        # 3. Normals
        if geo.ContainsNormals:
            rh_normals = geo.GetNormals()
            normals = [Gf.Vec3f(n.X, n.Y, n.Z) for n in rh_normals]
            usd_points.CreateNormalsAttr(normals)
            
        # Extent
        bbox = geo.GetBoundingBox(True)
        extent = [Gf.Vec3f(bbox.Min.X, bbox.Min.Y, bbox.Min.Z), Gf.Vec3f(bbox.Max.X, bbox.Max.Y, bbox.Max.Z)]
        usd_points.CreateExtentAttr(extent)
        
        # User Attributes
        Converter.ExportUserAttr(rh_obj, usd_points.GetPrim())
        
        return usd_points

    @staticmethod
    def ImportMesh(usd_mesh_geom):
        """Converts a USD Mesh Prim to a Rhino Mesh Object."""

        points_attr = usd_mesh_geom.GetPointsAttr().Get()
        counts_attr = usd_mesh_geom.GetFaceVertexCountsAttr().Get()
        indices_attr = usd_mesh_geom.GetFaceVertexIndicesAttr().Get()
        
        if not points_attr or not counts_attr or not indices_attr:
            return None
        
        # 1. Add Points
        rh_mesh = Rhino.Geometry.Mesh()
        rh_points = [Rhino.Geometry.Point3d(p[0], p[1], p[2]) for p in points_attr]
        rh_mesh.Vertices.AddVertices(rh_points)
        
        # 2. Add Faces
        idx_ptr = 0
        ngon_data = []
        for count in counts_attr:
            face_verts = indices_attr[idx_ptr : idx_ptr + count]
            
            if count == 3:
                rh_mesh.Faces.AddFace(
                    face_verts[0], face_verts[1], face_verts[2]
                )
            elif count == 4:
                rh_mesh.Faces.AddFace(
                    face_verts[0], face_verts[1], face_verts[2], face_verts[3]
                )
            else:
                new_face_indices = []
                for i in range(count - 2):
                    f_idx = rh_mesh.Faces.AddFace(
                        face_verts[0],
                        face_verts[i+1],
                        face_verts[i+2]
                    )
                    new_face_indices.append(f_idx)
                
                ngon_data.append(new_face_indices)
            
            idx_ptr += count

        # 3. Unweld Edges
        topo_verts = rh_mesh.TopologyVertices
        def topo_idx(idx):
            return topo_verts.TopologyVertexIndex(idx)
            
        crease_indices = usd_mesh_geom.GetCreaseIndicesAttr().Get()
        crease_lengths = usd_mesh_geom.GetCreaseLengthsAttr().Get()
        
        crease_edge= []
        if crease_indices and crease_lengths:
            idx_ptr = 0
            topo_edges = rh_mesh.TopologyEdges
            
            for length in crease_lengths:
                chain = crease_indices[idx_ptr : idx_ptr + length]
               
                for i in range(len(chain) - 1):
                    idx1 = chain[i]
                    idx2 = chain[i+1]  
                    edge_idx = topo_edges.GetEdgeIndex(topo_idx(idx1), topo_idx(idx2))
                    if edge_idx == -1:
                        edge_idx = topo_edges.GetEdgeIndex(topo_idx(idx2), topo_idx(idx1))

                    if edge_idx != -1:
                        crease_edge.append(edge_idx)
                idx_ptr += length

            rh_mesh.UnweldEdge(crease_edge, False)    

        # 4. Reconstruct Ngons
        if ngon_data:
            for f_indices in ngon_data:
                # Collect boundary edges
                v_indices = []
                
                for f_idx ,i in enumerate(f_indices):
                    f = rh_mesh.Faces[f_idx]
                    if i==0:
                        v_indices.append(f.A)
                        v_indices.append(f.B)
                    elif i==len(f_indices)-1:
                        v_indices.append(f.B)
                        v_indices.append(f.C)
                    else:
                        v_indices.append(f.B)
                try:
                    ngon = Rhino.Geometry.MeshNgon.Create(v_indices, f_indices)
                    rh_mesh.Ngons.AddNgon(ngon)
                except Exception:
                    pass
        
        rh_mesh.Normals.ComputeNormals()
        rh_mesh.Compact()
        
        if not rh_mesh.IsValid:
            return None
        
        return rh_mesh

    @staticmethod
    def ImportSubD(usd_mesh_geom):
        """Converts a USD Mesh Prim (SubD) to a Rhino SubD Object."""

        rh_mesh = Converter.ImportMesh(usd_mesh_geom)
        if not rh_mesh or not rh_mesh.IsValid:
            return None
            
        rh_subd = Rhino.Geometry.SubD.CreateFromMesh(rh_mesh,Rhino.Geometry.SubDCreationOptions.InteriorCreases)
        
        if not rh_subd:
            return None

        return rh_subd

    @staticmethod
    def ImportPoints(usd_points_geom):
        """Converts a USD Points Prim to a Rhino PointCloud Object."""
        # Get Points
        points_attr = usd_points_geom.GetPointsAttr().Get()
        if not points_attr:
            return None
            
        rh_pc = Rhino.Geometry.PointCloud()
        rh_points = [Rhino.Geometry.Point3d(p[0], p[1], p[2]) for p in points_attr]
        
        # Get Attributes (Normals, Colors)
        normals_attr = usd_points_geom.GetNormalsAttr().Get()
        colors_attr = usd_points_geom.GetDisplayColorAttr().Get()
        
        has_normals = normals_attr is not None and len(normals_attr) == len(rh_points)
        has_colors = colors_attr is not None and len(colors_attr) == len(rh_points)
        
        if has_normals and has_colors:
             for i in range(len(rh_points)):
                 # Colors in USD are linear float 0-1, Rhino expects System.Drawing.Color
                 c = colors_attr[i]
                 # Clamp and convert
                 r = int(max(0, min(1, c[0])) * 255)
                 g = int(max(0, min(1, c[1])) * 255)
                 b = int(max(0, min(1, c[2])) * 255)
                 rh_color = Color.FromArgb(r, g, b)
                 
                 n = normals_attr[i]
                 rh_normal = Rhino.Geometry.Vector3d(n[0], n[1], n[2])
                 
                 rh_pc.Add(rh_points[i], rh_normal, rh_color)
                 
        elif has_normals:
             for i in range(len(rh_points)):
                 n = normals_attr[i]
                 rh_normal = Rhino.Geometry.Vector3d(n[0], n[1], n[2])
                 rh_pc.Add(rh_points[i], rh_normal)
                 
        elif has_colors:
             for i in range(len(rh_points)):
                 c = colors_attr[i]
                 r = int(max(0, min(1, c[0])) * 255)
                 g = int(max(0, min(1, c[1])) * 255)
                 b = int(max(0, min(1, c[2])) * 255)
                 rh_color = Color.FromArgb(r, g, b)
                 
                 rh_pc.Add(rh_points[i], rh_color)
        else:
             # Fastest bulk add
             rh_pc.AddRange(rh_points)
             
        return rh_pc

    @staticmethod
    def ToRhinoTransform(gf_mat):
        """Converts pxr.Gf.Matrix4d to Rhino.Geometry.Transform."""
        xform = Rhino.Geometry.Transform()
        xform.M00 = gf_mat[0][0]; xform.M01 = gf_mat[1][0]; xform.M02 = gf_mat[2][0]; xform.M03 = gf_mat[3][0]
        xform.M10 = gf_mat[0][1]; xform.M11 = gf_mat[1][1]; xform.M12 = gf_mat[2][1]; xform.M13 = gf_mat[3][1]
        xform.M20 = gf_mat[0][2]; xform.M21 = gf_mat[1][2]; xform.M22 = gf_mat[2][2]; xform.M23 = gf_mat[3][2]
        xform.M30 = gf_mat[0][3]; xform.M31 = gf_mat[1][3]; xform.M32 = gf_mat[2][3]; xform.M33 = gf_mat[3][3]
        return xform

class Execute:
    """Main entry point for EasyTransfer USD operations."""
    
    @staticmethod
    def GetTempPath():
        home = os.path.expanduser("~")
        path = os.path.join(home, "Desktop","_temp.usda")
        return path

    @staticmethod
    def EasyCopy():
        # Get selected objects directly from RhinoDoc
        rh_objs = list(Rhino.RhinoDoc.ActiveDoc.Objects.GetSelectedObjects(False, False))
        if not rh_objs:
            print("No objects selected.")
            return

        # 1. Setup Stage (In Memory)
        stage = Usd.Stage.CreateInMemory()
        UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
        
        # Set Units
        active_doc = Rhino.RhinoDoc.ActiveDoc
        model_units = active_doc.ModelUnitSystem
        scale_to_meters = Rhino.RhinoMath.UnitScale(model_units, Rhino.UnitSystem.Meters)
        UsdGeom.SetStageMetersPerUnit(stage, scale_to_meters)
        
        root_path = ""
        count = 0
        used_names = set()
        
        for i, rh_obj in enumerate(rh_objs):           
            geo = rh_obj.Geometry
            
            # Determine Name
            raw_name = rh_obj.Attributes.Name
            valid_name = Converter.GetValidName(raw_name)
            
            if not valid_name:
                valid_name = f"RhinoObject_{i}"
            
            # Handle duplicates
            base_name = valid_name
            dup_count = 1
            while valid_name in used_names:
                valid_name = f"{base_name}_{dup_count}"
                dup_count += 1
            
            used_names.add(valid_name)
            
            usd_prim = None
            
            if isinstance(geo, Rhino.Geometry.SubD):
                usd_prim = Converter.ExportSubD(rh_obj, stage, root_path, valid_name)
            elif isinstance(geo, Rhino.Geometry.Mesh):
                usd_prim = Converter.ExportMesh(rh_obj, stage, root_path, valid_name)
            elif isinstance(geo, Rhino.Geometry.PointCloud):
                usd_prim = Converter.ExportPointCloud(rh_obj, stage, root_path, valid_name)
            
            if usd_prim:
                count += 1

        # 3. Export to File
        file_path = Execute.GetTempPath()
        stage.GetRootLayer().Export(file_path)
        print(f"Exported {count} objects to {file_path}")
        
        try:
            Clipboard.Instance.Text = file_path
        except Exception as e:
            print("Failed to set clipboard:", e)

    @staticmethod
    def EasyPaste():
        # 1. Get Path
        file_path = None
        try:
            if Clipboard.Instance.ContainsText: 
                clip_text = Clipboard.Instance.Text
                clip_path = clip_text.strip().strip('"')
                if os.path.exists(clip_path):
                    file_path = clip_path
        except Exception:
            pass

        if not file_path:
            print("No valid USD file found in clipboard or desktop.")
            return

        # 2. Open Stage
        stage = Usd.Stage.Open(file_path)
        if not stage:
            print("Failed to open USD stage.")
            return

        # 3. Handle Units
        file_meters = UsdGeom.GetStageMetersPerUnit(stage)
        current_meters_factor = Rhino.RhinoMath.UnitScale(Rhino.RhinoDoc.ActiveDoc.ModelUnitSystem, Rhino.UnitSystem.Meters)       
        world_scale = 1.0
        if current_meters_factor > 0:
            world_scale = file_meters / current_meters_factor

        # 4. Traverse and Import
        Rhino.RhinoDoc.ActiveDoc.Objects.UnselectAll()
        
        added_ids = []
        
        for prim in stage.Traverse():
            geometry = None
            
            if prim.IsA(UsdGeom.Mesh):
                mesh_geom = UsdGeom.Mesh(prim)
                scheme = mesh_geom.GetSubdivisionSchemeAttr().Get()
                if scheme == UsdGeom.Tokens.catmullClark:
                    geometry = Converter.ImportSubD(mesh_geom)
                else:
                    geometry = Converter.ImportMesh(mesh_geom)
            elif prim.IsA(UsdGeom.Points):
                points_geom = UsdGeom.Points(prim)
                geometry = Converter.ImportPoints(points_geom)
                
            if geometry:
                # 1. Apply USD Transform (Local -> World USD)
                xformable = UsdGeom.Xformable(prim)
                if xformable:
                    usd_xform = xformable.ComputeLocalToWorldTransform(Usd.TimeCode.Default())
                    rh_xform = Converter.ToRhinoTransform(usd_xform)
                    geometry.Transform(rh_xform)
                
                # 2. Apply Unit Scale (World USD -> World Rhino)
                if world_scale != 1.0:
                    geometry.Scale(world_scale)
                
                if geometry:
                    guid = Guid.Empty
                    if isinstance(geometry, Rhino.Geometry.SubD):
                        guid = Rhino.RhinoDoc.ActiveDoc.Objects.AddSubD(geometry)
                    elif isinstance(geometry, Rhino.Geometry.Mesh):
                        guid = Rhino.RhinoDoc.ActiveDoc.Objects.AddMesh(geometry)
                    elif isinstance(geometry, Rhino.Geometry.PointCloud):
                        guid = Rhino.RhinoDoc.ActiveDoc.Objects.AddPointCloud(geometry)
                    
                    rh_obj = Rhino.RhinoDoc.ActiveDoc.Objects.FindId(guid)
                    rh_obj = Rhino.RhinoDoc.ActiveDoc.Objects.FindId(guid)
                    if rh_obj:
                        # Restore Name
                        rh_obj.Attributes.Name = prim.GetName()
                        # Restore User Attributes
                        Converter.ImportUserAttr(prim, rh_obj)
                        
                        rh_obj.CommitChanges()
                        rh_obj.Select(True)
                    added_ids.append(guid)
                    
        Rhino.RhinoDoc.ActiveDoc.Views.Redraw()
        print(f"Imported {len(added_ids)} objects from {file_path}")
