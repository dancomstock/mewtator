import tkinter as tk


class WideScrollbar(tk.Canvas):
    """Very thicc and epic scrollbar!"""

    THICKNESS = 22
    MIN_THUMB_LENGTH = 32
    THUMB_PADDING = 0
    REPEAT_DELAY_MS = 350
    REPEAT_INTERVAL_MS = 65

    def __init__(self, parent, orient: str, command=None):
        self.orient = orient
        self.command = command
        self._vertical = str(orient).lower().startswith("v")

        size_options = (
            {"width": self.THICKNESS}
            if self._vertical
            else {"height": self.THICKNESS}
        )

        super().__init__(
            parent,
            borderwidth=0,
            highlightthickness=0,
            relief="flat",
            takefocus=True,
            **size_options,
        )

        self._first = 0.0
        self._last = 1.0
        self._scrolling_required = True
        self._forced_hidden = False
        self._visibility_job = None
        self._redraw_job = None
        self._dragging = False
        self._drag_offset = 0.0
        self._thumb_start = 0.0
        self._thumb_end = 0.0
        self._track_color = "#292929"
        self._thumb_color = "#666666"
        self._thumb_active_color = "#7a7a7a"
        self._arrow_color = "#f2f2f2"
        self._hover_part = None
        self._pressed_part = None
        self._repeat_job = None
        self._repeat_direction = 0

        self.bind("<Configure>", lambda _event: self._schedule_redraw())
        self.bind("<Button-1>", self._on_press)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Motion>", self._on_motion)
        self.bind("<Leave>", self._on_leave)

    def set(self, first, last):
        first_value = max(0.0, min(1.0, float(first)))
        last_value = max(first_value, min(1.0, float(last)))
        self._first = first_value
        self._last = last_value
        self._scrolling_required = (
            first_value > 0.000001 or last_value < 0.999999
        )

        if not self._scrolling_required:
            self._cancel_arrow_repeat()

        if not self._forced_hidden and self._visibility_job is None:
            self._visibility_job = self.after_idle(self._apply_visibility)

        self._schedule_redraw()

    def set_forced_hidden(self, hidden: bool):
        self._forced_hidden = bool(hidden)

        if self._visibility_job is not None:
            try:
                self.after_cancel(self._visibility_job)
            except tk.TclError:
                pass
            self._visibility_job = None

        if self._forced_hidden:
            self._cancel_arrow_repeat()

            if self.winfo_manager() == "grid":
                self.grid_remove()

        elif self._visibility_job is None:
            self._visibility_job = self.after_idle(self._apply_visibility)

    def _apply_visibility(self):
        self._visibility_job = None
        manager = self.winfo_manager()

        if self._forced_hidden:
            if manager == "grid":
                self.grid_remove()
            return
        if self._scrolling_required:
            if not manager:
                self.grid()
            self._schedule_redraw()
        elif manager == "grid":
            self.grid_remove()

    def apply_theme(self, colors: dict):
        self._track_color = colors["scrollbar_trough_bg"]
        self._thumb_color = colors["scrollbar_bg"]
        self._thumb_active_color = colors["scrollbar_active_bg"]
        self._arrow_color = colors["scrollbar_arrow_fg"]
        self.configure(background=self._track_color)
        self._schedule_redraw()

    def _schedule_redraw(self):
        if self._redraw_job is None:
            self._redraw_job = self.after_idle(self._redraw)

    def _axis_length(self):
        return self.winfo_height() if self._vertical else self.winfo_width()

    def _cross_length(self):
        return self.winfo_width() if self._vertical else self.winfo_height()

    def _event_position(self, event):
        return event.y if self._vertical else event.x

    def _thumb_geometry(self):
        length = max(1.0, float(self._axis_length()))
        arrow_length = min(
            max(1.0, float(self._cross_length())),
            length / 2,
        )

        track_start = arrow_length
        track_end = max(track_start, length - arrow_length)
        track_length = max(0.0, track_end - track_start)
        visible_fraction = max(0.0, min(1.0, self._last - self._first))

        thumb_length = max(
            float(self.MIN_THUMB_LENGTH),
            visible_fraction * track_length,
        )

        thumb_length = min(track_length, thumb_length)
        max_offset = max(0.0, track_length - thumb_length)
        max_first = max(0.0, 1.0 - visible_fraction)

        if max_offset and max_first:
            thumb_start = (
                track_start + (self._first / max_first) * max_offset
            )
        else:
            thumb_start = track_start
        return (
            length,
            arrow_length,
            track_start,
            track_end,
            thumb_start,
            thumb_start + thumb_length,
        )

    def _redraw(self):
        self._redraw_job = None
        self.delete("all")

        if not self._scrolling_required:
            return

        (
            length,
            arrow_length,
            _,
            _,
            self._thumb_start,
            self._thumb_end,
        ) = self._thumb_geometry()

        cross_length = max(1.0, float(self._cross_length()))
        padding = min(self.THUMB_PADDING, max(0.0, cross_length / 3))

        color = (
            self._thumb_active_color
            if (
                self._hover_part == "thumb"
                or self._pressed_part == "thumb"
                or self._dragging
            )
            else self._thumb_color
        )

        self._draw_arrow_button(
            "start_arrow",
            0.0,
            arrow_length,
            cross_length,
            -1,
        )

        self._draw_arrow_button(
            "end_arrow",
            max(0.0, length - arrow_length),
            length,
            cross_length,
            1,
        )

        if self._vertical:
            coordinates = (
                padding,
                self._thumb_start,
                cross_length - padding,
                self._thumb_end,
            )
        else:
            coordinates = (
                self._thumb_start,
                padding,
                self._thumb_end,
                cross_length - padding,
            )

        self.create_rectangle(
            *coordinates,
            fill=color,
            outline="",
            tags=("scrollbar_parts", "thumb"),
        )

    def _draw_arrow_button(
        self,
        part,
        axis_start,
        axis_end,
        cross_length,
        direction,
    ):
        active = part in (self._hover_part, self._pressed_part)

        background = (
            self._thumb_active_color if active else self._thumb_color
        )

        if self._vertical:
            button_coordinates = (0, axis_start, cross_length, axis_end)
        else:
            button_coordinates = (axis_start, 0, axis_end, cross_length)
        self.create_rectangle(
            *button_coordinates,
            fill=background,
            outline="",
            tags=("scrollbar_parts", part),
        )

        axis_center = (axis_start + axis_end) / 2
        cross_center = cross_length / 2

        arrow_size = max(
            2.0,
            min(4.5, (axis_end - axis_start) * 0.22, cross_length * 0.22),
        )

        if self._vertical:
            if direction < 0:
                points = (
                    cross_center,
                    axis_center - arrow_size,
                    cross_center - arrow_size,
                    axis_center + arrow_size,
                    cross_center + arrow_size,
                    axis_center + arrow_size,
                )
            else:
                points = (
                    cross_center,
                    axis_center + arrow_size,
                    cross_center - arrow_size,
                    axis_center - arrow_size,
                    cross_center + arrow_size,
                    axis_center - arrow_size,
                )
        elif direction < 0:
            points = (
                axis_center - arrow_size,
                cross_center,
                axis_center + arrow_size,
                cross_center - arrow_size,
                axis_center + arrow_size,
                cross_center + arrow_size,
            )
        else:
            points = (
                axis_center + arrow_size,
                cross_center,
                axis_center - arrow_size,
                cross_center - arrow_size,
                axis_center - arrow_size,
                cross_center + arrow_size,
            )

        self.create_polygon(
            *points,
            fill=self._arrow_color,
            outline="",
            tags=("scrollbar_parts", part, "arrow"),
        )

    def _part_at(self, position):
        (
            length,
            arrow_length,
            _,
            _,
            thumb_start,
            thumb_end,
        ) = self._thumb_geometry()
        if position < arrow_length:
            return "start_arrow"
        if position >= length - arrow_length:
            return "end_arrow"
        if thumb_start <= position <= thumb_end:
            return "thumb"
        return "track"

    def _on_press(self, event):
        if not self._scrolling_required:
            return "break"

        position = self._event_position(event)
        part = self._part_at(position)
        self._pressed_part = part
        self._hover_part = part

        if part == "thumb":
            self._dragging = True
            self._drag_offset = position - self._thumb_start
        elif part == "start_arrow":
            self._scroll_arrow(-1)
            self._start_arrow_repeat(-1)
        elif part == "end_arrow":
            self._scroll_arrow(1)
            self._start_arrow_repeat(1)
        else:
            self._move_thumb_to(position, center=True)

        self._schedule_redraw()
        return "break"

    def _on_drag(self, event):
        if self._dragging:
            position = self._event_position(event) - self._drag_offset
            self._move_thumb_to(position)
        return "break"

    def _on_release(self, event):
        self._cancel_arrow_repeat()
        self._dragging = False
        self._pressed_part = None
        self._hover_part = self._part_at(self._event_position(event))
        self._schedule_redraw()
        return "break"

    def _on_motion(self, event):
        part = self._part_at(self._event_position(event))
        
        if part != self._hover_part:
            self._hover_part = part
            self._schedule_redraw()

    def _on_leave(self, _event):
        if not self._dragging and self._hover_part is not None:
            self._hover_part = None
            self._schedule_redraw()

    def _scroll_arrow(self, direction):
        if self.command is not None:
            self.command("scroll", direction, "units")

    def _start_arrow_repeat(self, direction):
        self._cancel_arrow_repeat()
        self._repeat_direction = direction
        self._repeat_job = self.after(
            self.REPEAT_DELAY_MS,
            self._repeat_arrow,
        )

    def _repeat_arrow(self):
        self._repeat_job = None

        if self._pressed_part not in ("start_arrow", "end_arrow"):
            return
        
        self._scroll_arrow(self._repeat_direction)
        self._repeat_job = self.after(
            self.REPEAT_INTERVAL_MS,
            self._repeat_arrow,
        )

    def _cancel_arrow_repeat(self):
        if self._repeat_job is not None:
            try:
                self.after_cancel(self._repeat_job)
            except tk.TclError:
                pass
            self._repeat_job = None

    def _move_thumb_to(self, thumb_start, center=False):
        if self.command is None:
            return

        (
            _,
            _,
            track_start,
            track_end,
            current_start,
            current_end,
        ) = self._thumb_geometry()

        thumb_length = current_end - current_start
        
        if center:
            thumb_start -= thumb_length / 2

        max_start = max(track_start, track_end - thumb_length)
        thumb_start = max(track_start, min(max_start, thumb_start))
        max_offset = max(0.0, max_start - track_start)
        visible_fraction = max(0.0, min(1.0, self._last - self._first))
        max_first = max(0.0, 1.0 - visible_fraction)
        fraction = (
            ((thumb_start - track_start) / max_offset) * max_first
            if max_offset and max_first
            else 0.0
        )
        self.command("moveto", fraction)
