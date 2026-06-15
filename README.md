# Surface Snap Offset

Snap selected vertices to surfaces with a controllable normal offset.

## Features

- Adds **Snap with Offset** settings to Blender's snap popover.
- Uses **G** when Blender snapping is enabled and Snap with Offset is on.
- Uses **Alt+G** as a temporary offset snap override.
- Adjusts offset interactively with the mouse wheel during the move operation.
- Preserves free move behavior when no surface is detected under the cursor.
- Pressing **G** again switches to Blender's Vert/Edge Slide.
- Pressing **X**, **Y**, or **Z** exits offset mode and switches to Blender's native constrained move.

## Recommended retopology setup

For retopology over a high-poly mesh, use Blender's snap target selection like this:

- Disable **Include Active**.
- Disable **Include Edited**.
- Enable **Include Non-Edited**.

This prevents the edited retopology mesh from snapping to itself.

## Usage

1. Enable Blender snapping and set the snap target to Face.
2. Enable **Snap with Offset** in the snap popover.
3. Select vertices in Edit Mode.
4. Press **G** and move the cursor over a target surface.
5. Use the mouse wheel to adjust the offset.
6. Confirm with LMB or Enter.

Use **Alt+G** to run Surface Snap Offset for one move even when the checkbox is disabled.

## License

GPL-3.0-or-later.
