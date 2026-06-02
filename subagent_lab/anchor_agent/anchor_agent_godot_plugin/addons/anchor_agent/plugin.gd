@tool
extends EditorPlugin

const AGENT_DOCK_SCENE := preload("res://addons/anchor_agent/ui/agent_dock.tscn")
const SelectionAdapter := preload("res://addons/anchor_agent/adapters/selection_adapter.gd")
const SnapshotBuilder := preload("res://addons/anchor_agent/adapters/snapshot_builder.gd")

var _dock_instance
var _selection_adapter := SelectionAdapter.new()
var _snapshot_builder := SnapshotBuilder.new()
var _editor_selection: EditorSelection


func _enter_tree() -> void:
    _dock_instance = AGENT_DOCK_SCENE.instantiate()
    add_control_to_dock(DOCK_SLOT_RIGHT_UL, _dock_instance)
    _connect_selection_lifecycle()
    _refresh_selection_state()


func _exit_tree() -> void:
    _disconnect_selection_lifecycle()
    if _dock_instance != null:
        remove_control_from_docks(_dock_instance)
        _dock_instance.queue_free()
        _dock_instance = null


func _connect_selection_lifecycle() -> void:
    var editor_interface := get_editor_interface()
    if editor_interface == null:
        return
    _editor_selection = editor_interface.get_selection()
    if _editor_selection == null:
        return
    var selection_changed_handler := Callable(self, "_on_editor_selection_changed")
    if not _editor_selection.selection_changed.is_connected(selection_changed_handler):
        _editor_selection.selection_changed.connect(selection_changed_handler)


func _disconnect_selection_lifecycle() -> void:
    if _editor_selection == null:
        return
    var selection_changed_handler := Callable(self, "_on_editor_selection_changed")
    if _editor_selection.selection_changed.is_connected(selection_changed_handler):
        _editor_selection.selection_changed.disconnect(selection_changed_handler)
    _editor_selection = null


func _on_editor_selection_changed() -> void:
    _refresh_selection_state()


func _refresh_selection_state() -> void:
    if _dock_instance == null:
        return
    var selected_node := _selection_adapter.get_selected_node(get_editor_interface())
    if selected_node == null:
        _dock_instance.reset_for_empty_selection()
        return
    var snapshot := _snapshot_builder.build_snapshot(selected_node)
    if snapshot.is_empty():
        _dock_instance.reset_for_empty_selection()
        return
    _dock_instance.show_selected_snapshot(snapshot)
