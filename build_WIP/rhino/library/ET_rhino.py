#! python 3
# r: usd-core

import Rhino
import Rhino.DocObjects
import Rhino.ApplicationSettings
import os
import System
import time
import struct
import base64
from System.Drawing import Color
from System import Guid
from Eto.Forms import Clipboard
from pxr import Usd, UsdGeom, Gf, Sdf


USD_TYPE_CONFIG = {
    # ===  (float32) ===
    'float': ('f', 0), 'half': ('f', 0),
    'float2': ('f', 1), 'texCoord2f': ('f', 1), 'half2': ('f', 1),
    'float3': ('f', 1), 'point3f': ('f', 1), 'vector3f': ('f', 1), 'normal3f': ('f', 1), 'color3f': ('f', 1), 'half3': ('f', 1), 'point3h': ('f', 1), 'normal3h': ('f', 1), 'color3h': ('f', 1),
    'float4': ('f', 1), 'color4f': ('f', 1), 'quatf': ('f', 1), 'half4': ('f', 1), 'texCoord2h': ('f', 1),
    
    # ===  (float64) ===
    'double': ('d', 0),
    'double2': ('d', 1), 'texCoord2d': ('d', 1),
    'double3': ('d', 1), 'point3d': ('d', 1), 'vector3d': ('d', 1), 'normal3d': ('d', 1), 'color3d': ('d', 1),
    'double4': ('d', 1), 'color4d': ('d', 1), 'quatd': ('d', 1),
    'matrix2d': ('d', 2), 'matrix3d': ('d', 2), 'matrix4d': ('d', 2), 
    
    # ===  ===
    'int': ('i', 0), 'uint': ('I', 0),
    'int2': ('i', 1), 'int3': ('i', 1), 'int4': ('i', 1),
    'int64': ('q', 0), 'uint64': ('Q', 0),
    'bool': ('?', 0)
}

class Attribute:
    """Handles User Attributes and Primvars."""

    @staticmethod
    def Encode(usd_array, usd_type, function="base64"):

        if function == "base64":
            if not usd_array or len(usd_array) == 0:
                return None

            config = USD_TYPE_CONFIG.get(usd_type)
            if not config:
                print(f"Warning: Unsupported USD type '{usd_type}'")
                return None
            
            fmt_char, flatten_level = config

            try:
                if flatten_level == 0:
                    flat_list = usd_array
                
                elif flatten_level == 1:
                    flat_list = [val for vec in usd_array for val in vec]
                
                else:
                    flat_list = [val for mat in usd_array for row in mat for val in row]

                fmt = f"<{len(flat_list)}{fmt_char}"
                packed = struct.pack(fmt, *flat_list)
                
                return base64.b64encode(packed).decode('ascii')
                
            except Exception as e:
                print(f"Error packing type '{usd_type}': {e}")
                return None
        
        elif function == "string":
            return str(usd_array)
    
    
    @staticmethod
    def Export(rh_obj, usd_prim):
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
    def ImportMeshAttr(usd_prim, rh_attr):
        """Imports USD Custom Attributes and Primvars to Rhino User Strings for Meshes."""
        user_props = usd_prim.GetAuthoredAttributes()
        for attr in user_props:
            if not attr.IsCustom(): continue
            name = attr.GetName()
            base_name = name.split("userProperties:", 1)[1] if "userProperties:" in name else name
            usd_type = str(attr.GetTypeName().scalarType)
            domain_key = f"{base_name}[{usd_type}]"
            rh_attr.SetUserString(domain_key, str(attr.Get()))

        primvars = UsdGeom.PrimvarsAPI(usd_prim).GetPrimvars()
        for attr in primvars:
            base_name = attr.GetBaseName()
            if base_name in ["displayColor", "displayOpacity", "st"]: continue
            interpolation = attr.GetInterpolation()
            data = attr.ComputeFlattened()
            usd_type = str(attr.GetTypeName().scalarType)
            
            if interpolation == UsdGeom.Tokens.constant:
                if hasattr(data, '__iter__') and not isinstance(data, str): data = data[0]
                rh_attr.SetUserString(f"{base_name}[{usd_type}]", str(data))
            else:
                encoded_data = Attribute.Encode(data, usd_type, function="string")
                if encoded_data:
                    rh_attr.SetUserString(f"{interpolation}:{base_name}[{usd_type}]", encoded_data)

    @staticmethod
    def ImportPointAttr(usd_prim, rh_attr):
        """Imports USD Custom Attributes and Primvars to Rhino User Strings for Points."""
        user_props = usd_prim.GetAuthoredAttributes()
        for attr in user_props:
            if not attr.IsCustom(): continue
            name = attr.GetName()
            base_name = name.split("userProperties:", 1)[1] if "userProperties:" in name else name
            usd_type = str(attr.GetTypeName().scalarType)
            domain_key = f"{base_name}[{usd_type}]"
            rh_attr.SetUserString(domain_key, str(attr.Get()))

        primvars = UsdGeom.PrimvarsAPI(usd_prim).GetPrimvars()
        for attr in primvars:
            base_name = attr.GetBaseName()
            if base_name in ["displayColor", "displayOpacity", "widths"]: continue
            interpolation = attr.GetInterpolation()
            data = attr.ComputeFlattened()
            usd_type = str(attr.GetTypeName().scalarType)
            
            if interpolation == UsdGeom.Tokens.constant:
                if hasattr(data, '__iter__') and not isinstance(data, str): data = data[0]
                rh_attr.SetUserString(f"{base_name}[{usd_type}]", str(data))
            else:
                encoded_data = Attribute.Encode(data, usd_type, function="string")
                if encoded_data:
                    rh_attr.SetUserString(f"{interpolation}:{base_name}[{usd_type}]", encoded_data)

    @staticmethod
    def ImportCurveAttr(usd_prim, rh_attrs):
        """Imports USD Custom Attributes and Primvars to Rhino User Strings for Curves."""
        user_props = usd_prim.GetAuthoredAttributes()
        for attr in user_props:
            if not attr.IsCustom(): continue
            name = attr.GetName()
            base_name = name.split("userProperties:", 1)[1] if "userProperties:" in name else name
            data = attr.Get()
            usd_type = str(attr.GetTypeName().scalarType)
            
            if hasattr(data, '__iter__') and not isinstance(data, str) and len(data) == len(rh_attrs):
                for i, obj in enumerate(rh_attrs):
                    obj.SetUserString(f"{base_name}[{usd_type}]", str(data[i]))
            else:
                for obj in rh_attrs:
                    obj.SetUserString(f"{base_name}[{usd_type}]", str(data))

        primvars = UsdGeom.PrimvarsAPI(usd_prim).GetPrimvars()
        for attr in primvars:
            base_name = attr.GetBaseName()
            if base_name in ["displayColor", "displayOpacity", "widths"]: continue
            interpolation = attr.GetInterpolation()
            data = attr.ComputeFlattened()
            usd_type = str(attr.GetTypeName().scalarType)
            
            if interpolation == UsdGeom.Tokens.constant:
                if hasattr(data, '__iter__') and not isinstance(data, str): data = data[0]
                for obj in rh_attrs:
                    obj.SetUserString(f"{base_name}[{usd_type}]", str(data))
            elif interpolation == UsdGeom.Tokens.uniform:
                for i, obj in enumerate(rh_attrs):
                    if i < len(data):
                        obj.SetUserString(f"{base_name}[{usd_type}]", str(data[i]))
            else:
                encoded_data = Attribute.Encode(data, usd_type, function="string")
                if encoded_data:
                    for obj in rh_attrs:
                        obj.SetUserString(f"{interpolation}:{base_name}[{usd_type}]", encoded_data)
            
    @staticmethod
    def GetValidName(name):
        """Sanitizes a string to be a valid USD identifier."""
        if not name:
            return None
        
        valid_name = "".join(c if c.isalnum() or c == '_' else '_' for c in name)
        
        if valid_name and valid_name[0].isdigit():
            valid_name = "_" + valid_name
            
        return valid_name

class Export:
    """Handles conversion from Rhino Geometry to USD Prims."""
    @staticmethod
    def Mesh(rh_obj, stage, parent_path, name, mesh_override=None):
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
        Attribute.Export(rh_obj, usd_mesh.GetPrim())
        
        
        return usd_mesh

    @staticmethod
    def SubD(rh_obj, stage, parent_path, name):
        """Converts a Rhino Object's SubD to a USD Mesh Prim with Catmull-Clark subdivision."""
        subd = rh_obj.Geometry
        ctrl_mesh = Rhino.Geometry.Mesh.CreateFromSubDControlNet(subd)

        usd_mesh = Export.Mesh(rh_obj, stage, parent_path, name, mesh_override=ctrl_mesh)
        
        usd_mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.catmullClark)
        Attribute.Export(rh_obj, usd_mesh.GetPrim())
        
        return usd_mesh

    @staticmethod
    def PointCloud(rh_obj, stage, parent_path, name):
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
        
        # 4. Widths
        if geo.ContainsPointValues:
            rh_widths = geo.GetPointValues()
            usd_points.CreateWidthsAttr(rh_widths)
            
        # Extent
        bbox = geo.GetBoundingBox(True)
        extent = [Gf.Vec3f(bbox.Min.X, bbox.Min.Y, bbox.Min.Z), Gf.Vec3f(bbox.Max.X, bbox.Max.Y, bbox.Max.Z)]
        usd_points.CreateExtentAttr(extent)
        
        # User Attributes
        Attribute.Export(rh_obj, usd_points.GetPrim())
        
        return usd_points

    @staticmethod
    def Curve(rh_obj, stage, parent_path, name):
        """Converts a Rhino Object's Curve to a USD NurbsCurves Prim."""
        geo = rh_obj.Geometry
        nurbs_curve = geo.ToNurbsCurve()
        if not nurbs_curve:
            return None
        
        curve_path = f"{parent_path}/{name}"
        usd_curves = UsdGeom.NurbsCurves.Define(stage, curve_path)
        
        # Points and Weights
        points = []
        weights = []
        is_rational = nurbs_curve.IsRational
        
        for p in nurbs_curve.Points:
            loc = p.Location
            points.append(Gf.Vec3f(loc.X, loc.Y, loc.Z))
            if is_rational:
                weights.append(p.Weight)
            
        usd_curves.CreatePointsAttr(points)
        if is_rational:
            usd_curves.CreatePointWeightsAttr(weights)
            
        usd_curves.CreateCurveVertexCountsAttr([nurbs_curve.Points.Count])
        usd_curves.CreateOrderAttr([nurbs_curve.Order])
        
        rh_knots = list(nurbs_curve.Knots)
        if rh_knots:
            knots = [rh_knots[0]] + rh_knots + [rh_knots[-1]]
            usd_curves.CreateKnotsAttr(knots)
            
        # Extent
        bbox = nurbs_curve.GetBoundingBox(True)
        extent = [Gf.Vec3f(bbox.Min.X, bbox.Min.Y, bbox.Min.Z), Gf.Vec3f(bbox.Max.X, bbox.Max.Y, bbox.Max.Z)]
        usd_curves.CreateExtentAttr(extent)
        
        # User Attributes
        Attribute.Export(rh_obj, usd_curves.GetPrim())
        
        return usd_curves

class Import:
    """Handles conversion from USD Prims to Rhino Geometry."""
    @staticmethod
    def Mesh(usd_mesh_geom):
        """Converts a USD Mesh Prim to a Rhino Mesh Object."""

        points_attr = usd_mesh_geom.GetPointsAttr().Get()
        counts_attr = usd_mesh_geom.GetFaceVertexCountsAttr().Get()
        indices_attr = usd_mesh_geom.GetFaceVertexIndicesAttr().Get()
        
        if not points_attr or not counts_attr or not indices_attr:
            return None
        
        # 1. Add Points
        rh_mesh = Rhino.Geometry.Mesh()
        rh_points = [Utility.ToRhinoPoint(p) for p in points_attr]
        rh_mesh.Vertices.AddVertices(rh_points)
        
        # Add Colors
        colors_attr = usd_mesh_geom.GetPrim().GetAttribute("primvars:displayColor").Get()
        if colors_attr and len(colors_attr) == len(rh_points):
            rh_colors = [Utility.ToColor(c) for c in colors_attr]
            rh_mesh.VertexColors.AppendColors(rh_colors)
        
        # 2. Add Faces
        mesh_faces = []
        ngon_data = []
        idx_ptr = 0

        for count in counts_attr:
            if count == 3:
                mesh_faces.append(Rhino.Geometry.MeshFace(
                    indices_attr[idx_ptr], 
                    indices_attr[idx_ptr + 1], 
                    indices_attr[idx_ptr + 2]
                ))
                
            elif count == 4:
                mesh_faces.append(Rhino.Geometry.MeshFace(
                    indices_attr[idx_ptr], 
                    indices_attr[idx_ptr + 1], 
                    indices_attr[idx_ptr + 2], 
                    indices_attr[idx_ptr + 3]
                ))
                
            else:
                start_face_idx = len(mesh_faces) # 记录当前所在的全局面索引
                new_face_indices = []
                
                v0 = indices_attr[idx_ptr] 
                
                for i in range(count - 2):
                    mesh_faces.append(Rhino.Geometry.MeshFace(
                        v0,
                        indices_attr[idx_ptr + i + 1],
                        indices_attr[idx_ptr + i + 2]
                    ))
                    new_face_indices.append(start_face_idx + i)
                    
                ngon_data.append(new_face_indices)

            idx_ptr += count
        rh_mesh.Faces.AddFaces(mesh_faces)

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
            ngons = []
            for f_indices in ngon_data:
                v_indices = []
                
                for i,face_idx in enumerate(f_indices):
                    f = rh_mesh.Faces[face_idx]
                    if i==0:
                        v_indices.append(f.A)
                        v_indices.append(f.B)
                    elif i==len(f_indices)-1:
                        v_indices.append(f.B)
                        v_indices.append(f.C)
                    else:
                        v_indices.append(f.B)
                    ngon = Rhino.Geometry.MeshNgon.Create(v_indices, f_indices)
                    ngons.append(ngon)

            rh_mesh.Ngons.AddNgons(ngons)

        
        rh_mesh.Normals.ComputeNormals()
        rh_mesh.Compact()
        
        if not rh_mesh.IsValid:
            return None
        
        rh_attr = Rhino.DocObjects.ObjectAttributes()
        Attribute.ImportMeshAttr(usd_mesh_geom.GetPrim(), rh_attr)
        
        return rh_mesh, rh_attr

    @staticmethod
    def SubD(usd_mesh_geom):
        """Converts a USD Mesh Prim (SubD) to a Rhino SubD Object."""

        res = Import.Mesh(usd_mesh_geom)
        if not res:
            return None
            
        rh_mesh, rh_attr = res
        rh_subd = Rhino.Geometry.SubD.CreateFromMesh(rh_mesh,Rhino.Geometry.SubDCreationOptions.InteriorCreases)
        
        if not rh_subd:
            return None

        return rh_subd, rh_attr

    @staticmethod
    def Points(usd_points_geom):
        """Converts a USD Points Prim to a Rhino PointCloud Object."""
        # Get Points
        points_attr = usd_points_geom.GetPointsAttr().Get()
        if not points_attr:
            return None
            
        rh_pc = Rhino.Geometry.PointCloud()
        rh_points = [Utility.ToRhinoPoint(p) for p in points_attr]
        
        # Get Attributes (Normals, Colors)
        normals_attr = usd_points_geom.GetNormalsAttr().Get()
        colors_attr = usd_points_geom.GetDisplayColorAttr().Get()
        width_attr = usd_points_geom.GetWidthsAttr().Get()

        rh_normals = None
        if normals_attr and len(normals_attr) == len(rh_points):
            rh_normals = [Utility.ToRhinoVector(n) for n in normals_attr]
            
        rh_colors = None
        if colors_attr and len(colors_attr) == len(rh_points):
            rh_colors = [Utility.ToColor(c) for c in colors_attr]

        rh_widths = None
        if width_attr and len(width_attr) == len(rh_points):
            rh_widths = [w for w in width_attr]
                
        if rh_normals and rh_colors and rh_widths:
            rh_pc.AddRange(rh_points, rh_normals, rh_colors, rh_widths)
        elif rh_normals and rh_colors:
            rh_pc.AddRange(rh_points, rh_normals, rh_colors)
        elif rh_normals:
            rh_pc.AddRange(rh_points, rh_normals)
        elif rh_colors:
            rh_pc.AddRange(rh_points, rh_colors)
        else:
            rh_pc.AddRange(rh_points)
             
        rh_attr = Rhino.DocObjects.ObjectAttributes()
        Attribute.ImportPointAttr(usd_points_geom.GetPrim(), rh_attr)
        
        return rh_pc, rh_attr

    @staticmethod
    def NurbsCurves(usd_curves_geom):
        """Converts a USD NurbsCurves Prim to a list of Rhino NurbsCurve Objects."""
        counts_attr = usd_curves_geom.GetCurveVertexCountsAttr().Get()
        points_attr = usd_curves_geom.GetPointsAttr().Get()
        order_attr = usd_curves_geom.GetOrderAttr().Get()
        knots_attr = usd_curves_geom.GetKnotsAttr().Get()
        weights_attr = usd_curves_geom.GetPointWeightsAttr().Get()
        
        if not counts_attr or not points_attr or not order_attr or not knots_attr:
            return []
            
        rh_curves = []
        rh_attrs = []
        idx_ptr = 0
        knot_ptr = 0
        
        for i, count in enumerate(counts_attr):
            order = order_attr[i] if len(order_attr) > i else order_attr[0]
            is_rational = True if weights_attr else False
            
            rh_curve = Rhino.Geometry.NurbsCurve(3, is_rational, order, count)
            
            for j in range(count):
                p = points_attr[idx_ptr + j]
                if is_rational:
                    w = weights_attr[idx_ptr + j] if (weights_attr and len(weights_attr) > idx_ptr + j) else 1.0
                    rh_curve.Points.SetPoint(j, Utility.ToRhinoPoint(p), w)
                else:
                    rh_curve.Points.SetPoint(j, Utility.ToRhinoPoint(p))
            
            if len(knots_attr) >= knot_ptr + count + order:
                for j in range(count + order - 2):
                    rh_curve.Knots[j] = knots_attr[knot_ptr + 1 + j]
                    
            if rh_curve.IsValid:
                rh_curves.append(rh_curve)
                rh_attrs.append(Rhino.DocObjects.ObjectAttributes())

                
            idx_ptr += count
            knot_ptr += count + order
            
        if rh_curves:
            Attribute.ImportCurveAttr(usd_curves_geom.GetPrim(), rh_attrs)
            
        return list(zip(rh_curves, rh_attrs))

    @staticmethod
    def BasisCurves(usd_curves_geom):
        """Converts a USD BasisCurves Prim to a list of Rhino NurbsCurve Objects."""
        counts_attr = usd_curves_geom.GetCurveVertexCountsAttr().Get()
        points_attr = usd_curves_geom.GetPointsAttr().Get()
        
        curve_type = usd_curves_geom.GetTypeAttr().Get() if usd_curves_geom.GetPrim().HasAttribute("curveVertexCounts") else UsdGeom.Tokens.linear
        basis = usd_curves_geom.GetBasisAttr().Get() if usd_curves_geom.GetPrim().HasAttribute("curveVertexCounts") else UsdGeom.Tokens.bezier
        wrap = usd_curves_geom.GetWrapAttr().Get() if usd_curves_geom.GetPrim().HasAttribute("curveVertexCounts") else UsdGeom.Tokens.nonperiodic
        
        if not counts_attr or not points_attr:
            return []
            
        is_periodic = (wrap == UsdGeom.Tokens.periodic)
        rh_curves = []
        rh_attrs = []
        idx_ptr = 0
        
        for count in counts_attr:
            if count == 0:
                continue
                
            rh_pts = [Utility.ToRhinoPoint(points_attr[idx_ptr + j]) for j in range(count)]
            idx_ptr += count 
            
            # ==================== A. 直线 / 折线 (Linear) ====================
            if curve_type == UsdGeom.Tokens.linear:
                if is_periodic and len(rh_pts) > 0 and rh_pts[0].DistanceTo(rh_pts[-1]) > 1e-6:
                    rh_pts.append(rh_pts[0]) # 闭合
                    
                if len(rh_pts) >= 2:
                    polyline = Rhino.Geometry.Polyline(rh_pts)
                    plc = Rhino.Geometry.PolylineCurve(polyline)
                
                    if plc and plc.IsValid:
                        rh_curves.append(plc)
                        rh_attrs.append(Rhino.DocObjects.ObjectAttributes())

            # ==================== B. 三次平滑曲线 (Cubic) ====================
            elif curve_type == UsdGeom.Tokens.cubic:
                
                # 1. 贝塞尔曲线 (Bezier)
                if basis == UsdGeom.Tokens.bezier:
                    # 周期性闭合处理
                    if is_periodic and len(rh_pts) > 0 and len(rh_pts) % 3 == 0:
                        rh_pts.append(rh_pts[0])
                    
                    # 每 4 个点构成一段贝塞尔，步长为 3
                    if len(rh_pts) >= 4 and (len(rh_pts) - 1) % 3 == 0:
                        polycurve = Rhino.Geometry.PolyCurve()
                        for i in range(0, len(rh_pts) - 1, 3):
                            segment_pts = rh_pts[i : i+4]
                            # 【优化】使用 Rhino 原生贝塞尔类，自动处理 Knots
                            bez = Rhino.Geometry.BezierCurve(segment_pts)
                            polycurve.Append(bez.ToNurbsCurve())
                            
                        if polycurve.IsValid:
                            # 转成单一 NurbsCurve，保证后续操作更稳定
                            rh_curves.append(polycurve.ToNurbsCurve())
                            rh_attrs.append(Rhino.DocObjects.ObjectAttributes())

                # 2. B-样条 (B-Spline)
                elif basis == UsdGeom.Tokens.bspline:
                    nc = Rhino.Geometry.NurbsCurve.Create(False, 3, rh_pts)
                    if nc and nc.IsValid:
                        if is_periodic:
                            nc.MakeClosed(0.001) # 让 Rhino 自动平滑缝合端点
                        rh_curves.append(nc)
                        rh_attrs.append(Rhino.DocObjects.ObjectAttributes())

                # 3. Catmull-Rom (穿过所有控制点的插值曲线)
                elif basis == UsdGeom.Tokens.catmullRom:
                    if is_periodic and len(rh_pts) > 0 and rh_pts[0].DistanceTo(rh_pts[-1]) > 1e-6:
                        rh_pts.append(rh_pts[0])

                    nc = Rhino.Geometry.Curve.CreateInterpolatedCurve(rh_pts, 3, Rhino.Geometry.CurveKnotStyle.Uniform)
                    if nc and nc.IsValid:
                        rh_curves.append(nc)
                        rh_attrs.append(Rhino.DocObjects.ObjectAttributes())

        if rh_curves:
            Attribute.ImportCurveAttr(usd_curves_geom.GetPrim(), rh_attrs)

        return list(zip(rh_curves, rh_attrs))

class Utility:
    @staticmethod
    def ToRhinoTransform(gf_mat):
        """Converts pxr.Gf.Matrix4d to Rhino.Geometry.Transform."""
        xform = Rhino.Geometry.Transform()
        xform.M00 = gf_mat[0][0]; xform.M01 = gf_mat[1][0]; xform.M02 = gf_mat[2][0]; xform.M03 = gf_mat[3][0]
        xform.M10 = gf_mat[0][1]; xform.M11 = gf_mat[1][1]; xform.M12 = gf_mat[2][1]; xform.M13 = gf_mat[3][1]
        xform.M20 = gf_mat[0][2]; xform.M21 = gf_mat[1][2]; xform.M22 = gf_mat[2][2]; xform.M23 = gf_mat[3][2]
        xform.M30 = gf_mat[0][3]; xform.M31 = gf_mat[1][3]; xform.M32 = gf_mat[2][3]; xform.M33 = gf_mat[3][3]
        return xform

    @staticmethod
    def ToRhinoPoint(gf_pt):
        """Converts pxr.Gf.Point3d to Rhino.Geometry.Point3d."""
        pt = Rhino.Geometry.Point3d(gf_pt[0], gf_pt[1], gf_pt[2])
        return pt

    @staticmethod
    def ToRhinoVector(gf_vec):
        """Converts pxr.Gf.Vec3d to Rhino.Geometry.Vector3d."""
        vec = Rhino.Geometry.Vector3d(gf_vec[0], gf_vec[1], gf_vec[2])
        return vec

    @staticmethod
    def ToColor(gf_color):
        """
        Converts pxr.Gf.Vec3f to System.Drawing.Color (Safe for HDR values).
        Used for Layers, Materials, and Object Display Colors.
        """

        r = int(max(0.0, min(1.0, gf_color[0])) * 255)
        g = int(max(0.0, min(1.0, gf_color[1])) * 255)
        b = int(max(0.0, min(1.0, gf_color[2])) * 255)
    
        return Color.FromArgb(255, r, g, b)

class Execute:
    """Main entry point for EasyTransfer USD operations."""
    
    @staticmethod
    def GetTempPath():
        home = os.path.expanduser("~")
        path = os.path.join(home, "Desktop","_temp.usda")
        return path

    @staticmethod
    def EasyCopy():
        start_time = time.time()
        doc_objects = Rhino.RhinoDoc.ActiveDoc.Objects
        rh_objs = list(doc_objects.GetSelectedObjects(False, False))
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
            valid_name = Attribute.GetValidName(raw_name)
            
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
                usd_prim = Export.SubD(rh_obj, stage, root_path, valid_name)
            elif isinstance(geo, Rhino.Geometry.Mesh):
                usd_prim = Export.Mesh(rh_obj, stage, root_path, valid_name)
            elif isinstance(geo, Rhino.Geometry.PointCloud):
                usd_prim = Export.PointCloud(rh_obj, stage, root_path, valid_name)
            elif isinstance(geo, Rhino.Geometry.Curve):
                usd_prim = Export.Curve(rh_obj, stage, root_path, valid_name)
            
            if usd_prim:
                count += 1

        file_path = Execute.GetTempPath()
        stage.GetRootLayer().Export(file_path)
        
        end_time = time.time()
        print(f"Exported {count} objects to {file_path} in {end_time - start_time:.6f} seconds")
        
        try:
            Clipboard.Instance.Text = file_path
        except Exception as e:
            print("Failed to set clipboard:", e)

    @staticmethod
    def EasyPaste():
        start_time = time.time()
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
        doc_objects = Rhino.RhinoDoc.ActiveDoc.Objects
        doc_objects.UnselectAll()
        
        added_ids = []
        
        for prim in stage.Traverse():
            geom_attr_pairs = []
            
            if prim.IsA(UsdGeom.Mesh):
                mesh_geom = UsdGeom.Mesh(prim)
                scheme = mesh_geom.GetSubdivisionSchemeAttr().Get()
                if scheme == UsdGeom.Tokens.catmullClark:
                    res = Import.SubD(mesh_geom)
                else:
                    res = Import.Mesh(mesh_geom)
                if res: geom_attr_pairs.append(res)
            elif prim.IsA(UsdGeom.Points):
                points_geom = UsdGeom.Points(prim)
                res = Import.Points(points_geom)
                if res: geom_attr_pairs.append(res)
            elif prim.IsA(UsdGeom.NurbsCurves):
                nurbs_geom = UsdGeom.NurbsCurves(prim)
                res_list = Import.NurbsCurves(nurbs_geom)
                geom_attr_pairs.extend(res_list)
            elif prim.IsA(UsdGeom.BasisCurves):
                basis_geom = UsdGeom.BasisCurves(prim)
                res_list = Import.BasisCurves(basis_geom)
                geom_attr_pairs.extend(res_list)
                
            for geometry, attr in geom_attr_pairs:
                # 1. Apply USD Transform (Local -> World USD)
                xformable = UsdGeom.Xformable(prim)
                if xformable:
                    usd_xform = xformable.ComputeLocalToWorldTransform(Usd.TimeCode.Default())
                    rh_xform = Utility.ToRhinoTransform(usd_xform)
                    geometry.Transform(rh_xform)
                
                # 2. Apply Unit Scale (World USD -> World Rhino)
                if world_scale != 1.0:
                    geometry.Scale(world_scale)
                
                # Assign Name to Attributes
                name_str = prim.GetName()
                if name_str:
                    attr.Name = name_str

                guid = doc_objects.Add(geometry, attr)
                
                if guid != Guid.Empty:
                    rh_obj = doc_objects.FindId(guid)
                    if rh_obj:
                        rh_obj.CommitChanges()
                        rh_obj.Select(True)
                        added_ids.append(guid)
            
        end_time = time.time()
        print(f"Imported {len(added_ids)} objects from {file_path} in {end_time - start_time:.6f} seconds")
