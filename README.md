# Untitled

# EasyTransfer Tool

**EasyTransfer** is a plugin designed to rapidly copy and paste geometric objects between different 3D software. It aims to achieve a seamless workflow between modeling applications without the need for manual import and export steps. The plugin currently uses `.usd`(Universal Scene Description) as the standard medium, ensuring that the complete data structure of objects is preserved as much as possible during transfer.

**EasyTransfer** 是一个在不同三维软件之间快速拷贝几何物体的插件，旨在实现实现不同建模软件的无痛切换，而不需要通过导入和导出。该插件现通过`.usd`作为标准模型媒介，从而尽可能在不同软件之间拷贝完整的物体数据结构。

## 🔧 Mechanism

- **Blender:** Leverages Blender's native support for reading and writing `.usd` files by calling the official export methods.
    
    在**blender**端，已经存在官方的对于`.usd`文件的读取和写入，因此该插件调用官方导出方法。
    

- **Rhino:** Since Rhino 8.0 does not yet support native methods for reading/writing `.usd` files via API, this plugin requires the **Pixar USD Library**.
    - *Note: This library is automatically downloaded and installed when you install the plugin.*
    
    在**rhino**端，8.0版本尚不支持对于`.usd`的读取和写入方法，因此该插件需要安装Pixar开发的USD文件标准库(默认在安装时自动下载）。
    

## 📦 Version History

- **v0.1.0** - Initial Release
    
    v 0.1.0 初始版本
    

## 💻 Supported Software

rhino 8.0

blender 4.5  or higher

### 📐 Supported Geometry

| **Type** | **Description** | **Notes** |
| --- | --- | --- |
| **Mesh** | Polygonal mesh objects containing vertices, edges, and faces. Supports **N-gons** (faces with ≥4 vertices).  多边形网格物体，包含顶点，边，面，支持≥4多边形面 | In Rhino, N-gons are described as a collection of triangles and quads wrapped into a single polygon face. 在rhino中，多边形面会被描述为多个三角面和四边形面的集合，然后包裹进一个多边形面 |
| **Subdivided mesh** | Same basic structure as Mesh but includes **Crease** information and **subdivision** data. 多边形网格细分物体，基础结构结构与mesh相同，除此之外还包含折痕信息和细分 | In Blender, this applies a Subdivision Surface modifier. In Rhino, it is converted to a native **SubD** object. 在blender，subD会在mesh的基础上添加细分修改器，在rhino端会被转换为subD |
| **Point cloud** | A collection of 3D points containing position, color, and normal vectors.三维点集合，包含点位置，颜色和向量 | Blender also supports point **Radius**. 在blender端还支持点的半径 |

### 🚀 Installation

- Rhino 8
    
    Locate the `.yak` file in the folder `/easy_transfer_rhino/rh8/` and **drag and drop** it into the Rhino viewport (or use the Package Manager).
    
    rhino 8.0: 拖入`/easy_transfer_rhino/rh8/`中的`.yak`文件。
    

- Blender
    
    **Drag and drop** the `.zip` installation package into Blender (or install via `Edit > Preferences > Add-ons`).
    
    blender: 拖入`.zip`安装包(或者通过`Edit > Preferences > Add-ons`安装）
    

.