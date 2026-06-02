@tool
extends RefCounted


func get_selected_node(editor_interface: EditorInterface) -> Node:
    if editor_interface == null:
        return null
    var selection := editor_interface.get_selection()
    if selection == null:
        return null
    var selected_nodes := selection.get_selected_nodes()
    if selected_nodes.is_empty():
        return null
    return selected_nodes[0]
