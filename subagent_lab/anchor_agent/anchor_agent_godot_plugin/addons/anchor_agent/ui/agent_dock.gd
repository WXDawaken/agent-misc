@tool
extends VBoxContainer

@onready var _target_summary: Label = $TargetSummary
@onready var _actions: ItemList = $Actions
@onready var _preview: RichTextLabel = $Preview

var _current_action_ids: Array[String] = []
const EMPTY_TARGET_SUMMARY := "Select a node to inspect its context and suggested actions."
const EMPTY_PREVIEW_TEXT := "Choose an action to review a preview plan before any editor-side change."
const CONFIRMATION_HEADER := "Confirmation Required:"
const CONFIRMATION_REVIEW_HEADER := "Review Before Apply:"
const CONFIRMATION_LINES := [
    "Review this preview before any editor-side apply.",
    "Actual editor mutation stays local to the plugin."
]


func _ready() -> void:
    if _target_summary.text == "" or _target_summary.text == "No selection":
        reset_for_empty_selection()
        return
    if _preview.text == "" or _preview.text == "No preview yet.":
        _preview.text = EMPTY_PREVIEW_TEXT


func reset_for_empty_selection() -> void:
    _target_summary.text = EMPTY_TARGET_SUMMARY
    _clear_interaction_state()


func show_selected_snapshot(snapshot: Dictionary) -> void:
    if snapshot.is_empty():
        reset_for_empty_selection()
        return
    var lines: Array[String] = []
    var display_name := str(snapshot.get("display_name", "Unnamed node"))
    var type_name := str(snapshot.get("type_name", "Node"))
    var node_path := str(snapshot.get("path", ""))
    var scene_path := str(snapshot.get("scene_path", ""))
    lines.append("Selected: %s (%s)" % [display_name, type_name])
    if node_path != "":
        lines.append("Path: %s" % node_path)
    if scene_path != "":
        lines.append("Scene: %s" % scene_path)
    _target_summary.text = "\n".join(lines)
    _clear_interaction_state()


func set_target_summary(text: String) -> void:
    _target_summary.text = text


func set_actions(actions: Array) -> void:
    _actions.clear()
    _current_action_ids.clear()
    for action in actions:
        var title := str(action.get("title", "Untitled action"))
        _actions.add_item(title)
        _current_action_ids.append(str(action.get("id", "")))


func show_plan(summary: String, steps: Array, risk: String) -> void:
    var lines: Array[String] = []
    lines.append("Summary: %s" % summary)
    lines.append("Risk: %s" % risk)
    lines.append("Steps:")
    for step in steps:
        lines.append("- %s" % str(step))
    _preview.text = "\n".join(lines)


func show_plan_payload(plan: Dictionary) -> void:
    var lines: Array[String] = []
    lines.append("Summary: %s" % str(plan.get("summary", "")))
    lines.append("Risk: %s" % str(plan.get("risk", "")))
    _append_confirmation_callout(lines, plan)

    var preview_sections = plan.get("preview_sections", [])
    if preview_sections is Array and not preview_sections.is_empty():
        for section in preview_sections:
            var title := str(section.get("title", "Preview"))
            lines.append("")
            lines.append("%s:" % title)
            for entry in section.get("lines", []):
                lines.append("- %s" % str(entry))
    else:
        lines.append("Steps:")
        for step in plan.get("steps", []):
            lines.append("- %s" % str(step))

    _preview.text = "\n".join(lines)


func _clear_interaction_state() -> void:
    set_actions([])
    _preview.text = EMPTY_PREVIEW_TEXT


func _append_confirmation_callout(lines: Array[String], plan: Dictionary) -> void:
    if not bool(plan.get("requires_confirmation", false)):
        return
    lines.append("")
    lines.append(CONFIRMATION_HEADER)
    var confirmation_details = plan.get("confirmation_details", {})
    if confirmation_details is Dictionary:
        var reason := str(confirmation_details.get("reason", ""))
        if reason != "":
            lines.append("- %s" % reason)

        var review_items = confirmation_details.get("review_items", [])
        if review_items is Array and not review_items.is_empty():
            lines.append(CONFIRMATION_REVIEW_HEADER)
            for entry in review_items:
                lines.append("- %s" % str(entry))

        if reason != "" or (review_items is Array and not review_items.is_empty()):
            return

    for entry in CONFIRMATION_LINES:
        lines.append("- %s" % entry)
