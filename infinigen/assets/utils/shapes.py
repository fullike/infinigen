# Copyright (c) Princeton University.
# This source code is licensed under the BSD 3-Clause license found in the LICENSE file in the root directory of this source tree.

# Authors: Lingjie Mei
import bpy
import numpy as np
import shapely
from shapely import Polygon, remove_repeated_points, simplify

from shapely.ops import linemerge, orient, polygonize, unary_union, shared_paths
from trimesh.creation import triangulate_polygon

from infinigen.assets.utils.decorate import write_co, read_co, select_faces, read_normal
from infinigen.assets.utils.object import new_circle, data2mesh, mesh2obj, join_objects
from infinigen.core.util import blender as butil


def is_valid_polygon(p):
    if isinstance(p, Polygon) and p.area > 0 and p.is_valid:
        if len(p.interiors) == 0:
            return True
    return False


def simplify_polygon(p):
    with np.errstate(invalid="ignore"):
        p = remove_repeated_points(simplify(p, 1e-6).normalize(), .01)
        return p


def cut_polygon_by_line(polygon, *args):
    merged = linemerge([polygon.boundary, *args])
    borders = unary_union(merged)
    polygons = polygonize(borders)
    return list(polygons)


def safe_polygon2obj(p, reversed=False, z=0):
    ps = [p] if p.geom_type == 'Polygon' else p.geoms
    objs_ = []
    for p in ps:
        p = orient(p).segmentize(.005)
        try:
            obj = triangulate_polygon2obj(p)
            objs_.append(obj)
        except:
            try:
                obj = polygon2obj(p)
                objs_.append(obj)
            except:
                pass
    if len(objs_) == 0:
        return None
    obj = join_objects(objs_)
    obj.location[-1] = z
    butil.apply_transform(obj, True)
    point_normal_up(obj, reversed)
    return obj


def polygon2obj(p, reversed=False, z=0):
    p = orient(p)
    coords = np.array(p.exterior.coords)[:-1, :2]
    obj = new_circle(vertices=len(coords))
    write_co(obj, np.concatenate([coords, np.zeros((len(coords), 1))], -1))
    objs = [obj]
    for i in p.interiors:
        coords = np.array(i.coords)[:-1, :2]
        o = new_circle(vertices=len(coords))
        write_co(o, np.concatenate([coords, np.zeros((len(coords), 1))], -1))
        objs.append(o)
    obj = join_objects(objs)
    butil.modify_mesh(obj, 'WELD', merge_threshold=1e-6)
    with butil.ViewportMode(obj, 'EDIT'):
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.fill()
    dissolve_limited(obj)
    obj.location[-1] = z
    butil.apply_transform(obj, True)
    point_normal_up(obj, reversed)
    return obj


def point_normal_up(obj, reversed=False):
    with butil.ViewportMode(obj, 'EDIT'):
        no_z = read_normal(obj)[:, -1]
        select_faces(obj, (no_z > 0) if reversed else (no_z < 0))
        bpy.ops.mesh.flip_normals()


def triangulate_polygon2obj(p):
    vertices, faces = triangulate_polygon(orient(p))
    vertices = np.concatenate([vertices, np.zeros((len(vertices), 1))], -1)
    obj = mesh2obj(data2mesh(vertices=vertices, faces=faces))
    co = read_co(obj)
    co[:, -1] = 0
    write_co(obj, co)
    butil.modify_mesh(obj, 'WELD', merge_threshold=1e-6)
    dissolve_limited(obj)
    return obj


def dissolve_limited(obj):
    with butil.ViewportMode(obj, 'EDIT'), butil.Suppress():
        for angle_limit in reversed(.05 * .1 ** np.arange(5)):
            bpy.ops.mesh.select_mode(type='FACE')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.dissolve_limited(angle_limit=angle_limit)


def obj2polygon(obj):
    co = read_co(obj)[:, :2]
    p = shapely.union_all(
        [shapely.make_valid(orient(shapely.Polygon(co[p.vertices]))) for p in obj.data.polygons]
    )
    return shapely.make_valid(shapely.simplify(p, 1e-6))


def buffer(p, distance):
    with np.errstate(invalid="ignore"):
        return remove_repeated_points(simplify(p.buffer(distance, join_style='mitre', cap_style='flat'), 1e-6))


def segment_filter(mls, margin):
    for ls in mls.geoms if mls.geom_type == 'MultiLineString' else [mls]:
        coords = np.array(ls.coords)
        if len(coords) < 2:
            continue
        elif np.any(np.linalg.norm(coords[1:] - coords[:-1], axis=-1) > margin):
            return True
    return False


def shared(s, t):
    with np.errstate(invalid="ignore"):
        forward, backward = shared_paths(s.boundary, t.boundary).geoms
    if forward.length > 0:
        return forward
    elif backward.length > 0:
        return backward
    else:
        return shapely.MultiLineString()
