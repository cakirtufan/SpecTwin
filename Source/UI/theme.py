from pathlib import Path

import dearpygui.dearpygui as dpg


RGB = {
    "background": (16, 20, 23),
    "surface_1": (23, 29, 33),
    "surface_2": (32, 40, 45),
    "surface_3": (43, 53, 59),
    "border": (58, 70, 77),
    "border_strong": (86, 99, 107),
    "text": (238, 245, 247),
    "text_secondary": (170, 183, 190),
    "text_muted": (116, 130, 138),
    "primary": (31, 182, 213),
    "secondary": (242, 169, 59),
    "success": (57, 185, 128),
    "warning": (242, 169, 59),
    "error": (225, 93, 93),
    "info": (99, 167, 242),
    "excluded": (184, 92, 92),
}

SPACING = {
    "2xs": 2,
    "xs": 4,
    "sm": 8,
    "md": 16,
    "lg": 24,
    "xl": 32,
    "2xl": 48,
    "3xl": 64,
}

FONT_TAGS = {
    "default": "spectwin_font_default",
    "data": "spectwin_font_data",
}

THEME_TAGS = {
    "app": "spectwin_theme_app",
    "plot": "spectwin_theme_plot",
    "primary_button": "spectwin_theme_button_primary",
    "secondary_button": "spectwin_theme_button_secondary",
    "warning_button": "spectwin_theme_button_warning",
    "success_button": "spectwin_theme_button_success",
    "error_button": "spectwin_theme_button_error",
    "included_button": "spectwin_theme_button_included",
    "excluded_button": "spectwin_theme_button_excluded",
    "warning_text": "spectwin_theme_text_warning",
    "error_text": "spectwin_theme_text_error",
    "muted_text": "spectwin_theme_text_muted",
}


def rgba(name, alpha=255):
    return (*RGB[name], alpha)


def _first_existing(paths):
    for path in paths:
        if path.exists():
            return path
    return None


def load_fonts(source_dir, size=18, data_size=16):
    """Load project fonts once per Dear PyGui context."""
    source_dir = Path(source_dir)
    font_dir = source_dir / "fonts"

    preferred_default = _first_existing(
        [
            font_dir / "SourceSans3-Regular.ttf",
            font_dir / "SourceSans3.ttf",
            font_dir / "verdana.ttf",
        ]
    )
    preferred_data = _first_existing(
        [
            font_dir / "IBMPlexMono-Regular.ttf",
            font_dir / "IBM-Plex-Mono-Regular.ttf",
            font_dir / "verdana.ttf",
        ]
    )

    if preferred_default is None:
        raise FileNotFoundError(f"No usable UI font found in {font_dir}")
    if preferred_data is None:
        preferred_data = preferred_default

    with dpg.font_registry():
        if not dpg.does_item_exist(FONT_TAGS["default"]):
            dpg.add_font(str(preferred_default), size, tag=FONT_TAGS["default"])
        if not dpg.does_item_exist(FONT_TAGS["data"]):
            dpg.add_font(str(preferred_data), data_size, tag=FONT_TAGS["data"])

    return dict(FONT_TAGS)


def build_app_theme():
    if dpg.does_item_exist(THEME_TAGS["app"]):
        return dpg.get_alias_id(THEME_TAGS["app"])

    with dpg.theme(tag=THEME_TAGS["app"]):
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, rgba("background"), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, rgba("surface_1"), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_PopupBg, rgba("surface_2"), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_Text, rgba("text"), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_TextDisabled, rgba("text_muted"), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_Border, rgba("border"), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg, rgba("surface_3"), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, rgba("border"), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, rgba("border_strong"), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_Button, rgba("surface_2"), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, rgba("surface_3"), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, rgba("border_strong"), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_Header, rgba("surface_2"), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered, rgba("surface_3"), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_HeaderActive, rgba("primary"), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_Tab, rgba("surface_2"), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_TabHovered, rgba("surface_3"), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_TabActive, rgba("primary", 170), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_TableHeaderBg, rgba("surface_3"), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_TableRowBg, rgba("surface_1"), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_TableRowBgAlt, rgba("surface_2"), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_CheckMark, rgba("primary"), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_Separator, rgba("border"), category=dpg.mvThemeCat_Core)
            dpg.add_theme_style(dpg.mvStyleVar_WindowRounding, 4, category=dpg.mvThemeCat_Core)
            dpg.add_theme_style(dpg.mvStyleVar_ChildRounding, 4, category=dpg.mvThemeCat_Core)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 2, category=dpg.mvThemeCat_Core)
            dpg.add_theme_style(dpg.mvStyleVar_TabRounding, 4, category=dpg.mvThemeCat_Core)
            dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 12, 12, category=dpg.mvThemeCat_Core)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 8, 6, category=dpg.mvThemeCat_Core)
            dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 8, 8, category=dpg.mvThemeCat_Core)
    return dpg.get_alias_id(THEME_TAGS["app"])


def build_plot_theme():
    if dpg.does_item_exist(THEME_TAGS["plot"]):
        return dpg.get_alias_id(THEME_TAGS["plot"])

    with dpg.theme(tag=THEME_TAGS["plot"]):
        with dpg.theme_component(dpg.mvPlot):
            dpg.add_theme_color(dpg.mvPlotCol_PlotBg, rgba("surface_1"), category=dpg.mvThemeCat_Plots)
            dpg.add_theme_color(dpg.mvPlotCol_FrameBg, rgba("background"), category=dpg.mvThemeCat_Plots)
            dpg.add_theme_color(dpg.mvPlotCol_PlotBorder, rgba("border"), category=dpg.mvThemeCat_Plots)
            dpg.add_theme_color(dpg.mvPlotCol_AxisGrid, rgba("border", 95), category=dpg.mvThemeCat_Plots)
            dpg.add_theme_color(dpg.mvPlotCol_AxisText, rgba("text_secondary"), category=dpg.mvThemeCat_Plots)
            dpg.add_theme_color(dpg.mvPlotCol_Line, rgba("primary"), category=dpg.mvThemeCat_Plots)
            dpg.add_theme_color(dpg.mvPlotCol_MarkerFill, rgba("secondary"), category=dpg.mvThemeCat_Plots)
            dpg.add_theme_color(dpg.mvPlotCol_MarkerOutline, rgba("secondary"), category=dpg.mvThemeCat_Plots)
            dpg.add_theme_color(dpg.mvPlotCol_LegendBg, rgba("surface_2", 230), category=dpg.mvThemeCat_Plots)
            dpg.add_theme_color(dpg.mvPlotCol_LegendText, rgba("text"), category=dpg.mvThemeCat_Plots)
            dpg.add_theme_style(dpg.mvPlotStyleVar_LineWeight, 2, category=dpg.mvThemeCat_Plots)
            dpg.add_theme_style(dpg.mvPlotStyleVar_MajorGridSize, 1, category=dpg.mvThemeCat_Plots)
            dpg.add_theme_style(dpg.mvPlotStyleVar_PlotPadding, 10, 10, category=dpg.mvThemeCat_Plots)
    return dpg.get_alias_id(THEME_TAGS["plot"])


def _button_theme(tag, base, hover=None, active=None):
    if dpg.does_item_exist(tag):
        return dpg.get_alias_id(tag)
    hover = hover or base
    active = active or base
    with dpg.theme(tag=tag):
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (*base, 255), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (*hover, 255), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (*active, 255), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_Text, rgba("text"), category=dpg.mvThemeCat_Core)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 4, category=dpg.mvThemeCat_Core)
    return dpg.get_alias_id(tag)


def build_item_themes():
    themes = {}
    themes["primary_button"] = _button_theme(
        THEME_TAGS["primary_button"], RGB["primary"], (57, 204, 232), (24, 149, 176)
    )
    themes["secondary_button"] = _button_theme(
        THEME_TAGS["secondary_button"], RGB["surface_2"], RGB["surface_3"], RGB["border_strong"]
    )
    themes["warning_button"] = _button_theme(
        THEME_TAGS["warning_button"], RGB["warning"], (255, 191, 86), (196, 131, 39)
    )
    themes["success_button"] = _button_theme(
        THEME_TAGS["success_button"], RGB["success"], (75, 207, 148), (43, 148, 101)
    )
    themes["error_button"] = _button_theme(
        THEME_TAGS["error_button"], RGB["error"], (238, 119, 119), (176, 69, 69)
    )
    themes["included_button"] = _button_theme(
        THEME_TAGS["included_button"], RGB["success"], (75, 207, 148), (43, 148, 101)
    )
    themes["excluded_button"] = _button_theme(
        THEME_TAGS["excluded_button"], RGB["excluded"], (205, 108, 108), (143, 67, 67)
    )
    for key, color_name in [
        ("warning_text", "warning"),
        ("error_text", "error"),
        ("muted_text", "text_muted"),
    ]:
        tag = THEME_TAGS[key]
        if not dpg.does_item_exist(tag):
            with dpg.theme(tag=tag):
                with dpg.theme_component(dpg.mvText):
                    dpg.add_theme_color(dpg.mvThemeCol_Text, rgba(color_name), category=dpg.mvThemeCat_Core)
        themes[key] = tag
    return themes


def apply_global_theme(source_dir):
    fonts = load_fonts(source_dir)
    dpg.bind_font(fonts["default"])
    dpg.bind_theme(build_app_theme())
    build_plot_theme()
    build_item_themes()
    return fonts


def bind_button_theme(item, variant="secondary"):
    themes = build_item_themes()
    key = f"{variant}_button"
    dpg.bind_item_theme(item, themes.get(key, themes["secondary_button"]))
    return item


def bind_plot_theme(item):
    dpg.bind_item_theme(item, build_plot_theme())
    return item


def bind_text_theme(item, variant="muted"):
    themes = build_item_themes()
    key = f"{variant}_text"
    if key in themes:
        dpg.bind_item_theme(item, themes[key])
    return item


def add_section_title(text, parent=None):
    kwargs = {"color": rgba("text")}
    if parent is not None:
        kwargs["parent"] = parent
    return dpg.add_text(text, **kwargs)


def add_status_text(default="", state="idle", parent=None, tag=None, wrap=520):
    kwargs = {"wrap": wrap}
    if parent is not None:
        kwargs["parent"] = parent
    if tag is not None:
        kwargs["tag"] = tag
    item = dpg.add_text(default, **kwargs)
    if state in {"warning", "error", "muted"}:
        bind_text_theme(item, state)
    return item
