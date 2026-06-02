@tool
extends RichTextLabel


func set_preview_lines(lines: Array) -> void:
    text = "\n".join(lines)
