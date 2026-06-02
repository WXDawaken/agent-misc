@tool
extends RefCounted


func build_snapshot(node: Node) -> Dictionary:
    if node == null:
        return {}

    var script := node.get_script()
    var script_path := ""
    if script != null and script.has_method("get_path"):
        script_path = str(script.get_path())

    return {
        "object_id": str(node.get_instance_id()),
        "engine": "godot",
        "object_kind": "node",
        "display_name": node.name,
        "type_name": node.get_class(),
        "path": str(node.get_path()),
        "scene_path": _scene_path_for(node),
        "parent_id": str(node.get_parent().get_instance_id()) if node.get_parent() != null else null,
        "properties": {
            "attached_script_path": script_path,
            "has_script": script != null,
            "has_collision_shape": _has_collision_shape_child(node)
        },
        "relations": [],
        "diagnostics": [],
        "capabilities": _infer_capabilities(node, script != null),
        "selection_state": {
            "selected": true,
            "selection_index": 0
        }
    }


func _scene_path_for(node: Node) -> String:
    if node != null and node.get_tree() != null and node.get_tree().edited_scene_root != null:
        return str(node.get_tree().edited_scene_root.scene_file_path)
    return ""


func _infer_capabilities(node: Node, has_script: bool) -> Array:
    var capabilities: Array[String] = []
    var has_collision_shape := _has_collision_shape_child(node)
    if node.get_class() == "CharacterBody3D":
        capabilities.append("move")
        if has_collision_shape:
            capabilities.append("has_collision_shape")
    if has_script:
        capabilities.append("has_script")
    if _scene_path_for(node) != "":
        capabilities.append("scene_editable")
    return capabilities


func _has_collision_shape_child(node: Node) -> bool:
    for child in node.get_children():
        if child is Node and (child.get_class() == "CollisionShape3D" or child.get_class() == "CollisionPolygon3D"):
            return true
    return false
