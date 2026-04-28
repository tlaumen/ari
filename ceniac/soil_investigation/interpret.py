from dataclasses import dataclass
from typing import Protocol
import tkinter as tk
from tkinter import ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt

from ceniac.soil_investigation.borehole import Borehole
from ceniac.soil_investigation.cpt import Cpt, load_cpt, plot_cpt
from ceniac.soil_profile import soil_profile
from ceniac.soil_profile.soil_profile import SoilProfile
from ceniac.soil_profile.soil_profile import Layer
from ceniac.parameters.model import Color

STIPPLE = "gray50"  # https://tkdocs.com/shipman/bitmaps.html


def group_layers(interpretation: list[Layer]) -> list[Layer]:
    """Combines adjacent layers of the same soil and groups them into a single layer"""
    i = 0
    grouped_layers: list[Layer] = []
    while i < len(interpretation) - 1:
        top_group = interpretation[i].top
        soil_group = interpretation[i].soil
        for j, layer in enumerate(interpretation[i:], start=i):
            if layer.soil != soil_group:
                i = j
                grouped_layers.append(
                    Layer(
                        soil=soil_group, top=top_group, bottom=layer.top
                    )  # top of layer deviating is equal to bottom of last similar layer
                )
                break
        else:
            i = len(interpretation) - 1
            grouped_layers.append(
                Layer(
                    soil=soil_group, top=top_group, bottom=layer.bottom
                )  # top of layer deviating is equal to bottom of last similar layer
            )

    return grouped_layers


def _filter_small_layers(layers: list[Layer], min_thickness: float) -> list[Layer]:
    """Filters layers smaller than a minimum thickness from the soil profile"""
    filtered_layers: list[Layer] = []
    for layer in layers:
        if layer.thickness < min_thickness:
            continue
        filtered_layers.append(layer)
    return filtered_layers


def naive_qc_rf(cpt: Cpt, min_layer_thickness: float | None = None) -> SoilProfile:
    """Classifies every cpt measurement with the _interpret_cpt_measurement method, groups layers when multiple measurements have the same soil and the filters too small layers. From these layers, it constructs a SoilProfile object and returns this."""

    def _interpret_cpt_measurement(qc: float, fr: float) -> str:
        """Interprets every cpt measurement based on cone resistance (qc) and friction ratio (fr) into a soil type: 'zand', 'klei', 'silt' or 'veen'"""
        if qc > 5:
            return "zand"
        if fr > 5:
            return "veen"  # peat
        elif fr < 0.5:
            return "zand"
        elif 1.5 < fr < 5:
            return "klei"
        else:
            return "silt"

    interpretation: list[Layer] = []
    for l_top, l_bottom, qc, fr in zip(
        cpt.levels[:-1], cpt.levels[1:], cpt.qc[:-1], cpt.fr[:-1]
    ):  # depth of interpretation from measurment to next level hence [1:] where all others [:-1]
        soil = _interpret_cpt_measurement(qc, fr)
        interpretation.append(Layer(soil=soil, top=l_top, bottom=l_bottom))

    layers = group_layers(interpretation)
    if not min_layer_thickness is None:
        layers = _filter_small_layers(layers, min_thickness=min_layer_thickness)
        layers = group_layers(layers)
    return SoilProfile(
        name=cpt.id_, surface_level=cpt.surface_level, layers=layers, bottom=cpt.bottom
    )


class CptCorrelation(Protocol):
    """Abstract class for cpt correlations to classify soil layers"""

    def _filter_small_layers(
        self, layers: list[Layer], min_thickness: float
    ) -> list[Layer]:
        """Filters layers smaller than a minimum thickness from the soil profile"""
        filtered_layers: list[Layer] = []
        for layer in layers:
            if layer.thickness < min_thickness:
                continue
            filtered_layers.append(layer)
        return filtered_layers

    def classify(self, cpt: Cpt) -> SoilProfile: ...


class NaiveQcRfCorrelation(CptCorrelation):
    """Concrete implementation of a class for cpt correlations to classify soil layers based on cone resistance (qc) and friction ratio (fr)"""

    def _interpret_cpt_measurement(self, qc: float, fr: float) -> str:
        """Interprets every cpt measurement based on cone resistance (qc) and friction ratio (fr) into a soil type: 'zand', 'klei', 'silt' or 'veen'"""
        if qc > 5:
            return "zand"
        if fr > 5:
            return "veen"  # peat
        elif fr < 0.5:
            return "zand"
        elif 1.5 < fr < 5:
            return "klei"
        else:
            return "silt"

    def classify(
        self, cpt: Cpt, min_layer_thickness: float | None = None
    ) -> SoilProfile:
        """Classifies every cpt measurement with the _interpret_cpt_measurement method, groups layers when multiple measurements have the same soil and the filters too small layers. From these layers, it constructs a SoilProfile object and returns this."""
        interpretation: list[Layer] = []
        for l_top, l_bottom, qc, fr in zip(
            cpt.levels[:-1], cpt.levels[1:], cpt.qc[:-1], cpt.fr[:-1]
        ):  # depth of interpretation from measurment to next level hence [1:] where all others [:-1]
            soil = self._interpret_cpt_measurement(qc, fr)
            interpretation.append(Layer(soil=soil, top=l_top, bottom=l_bottom))

        layers = group_layers(interpretation)
        if not min_layer_thickness is None:
            layers = self._filter_small_layers(
                layers, min_thickness=min_layer_thickness
            )
            layers = group_layers(layers)
        return SoilProfile(
            name=cpt.id_,
            surface_level=cpt.surface_level,
            layers=layers,
            bottom=cpt.bottom,
        )


@dataclass
class CptInterpretation:
    """Class to classify a cpt based on a correlation and compare it to adjacent boreholes"""

    """
    [What role/responsibility this class has in the system]
    
    [Optional: Extended description of the problem it solves, key behaviors,
    design considerations, or performance characteristics]
    
    Parameters
    ----------
    init_param1
        What this controls. Guidance on typical values or ranges.
    init_param2
        What this affects. Interdependencies with other parameters.
    
    Attributes
    ----------
    public_attr1 : Type
        What this tracks. When/how it changes. Initial value if not obvious.
    public_attr2 : Type
        What this represents. How users should interpret it.
    
    Examples
    --------
    >>> # Typical initialization and basic usage
    >>> obj = ClassName(param1, param2)
    >>> result = obj.main_method()
    
    Notes
    -----
    - Thread-safety considerations
    - Lifecycle/cleanup requirements
    - Design patterns or architecture notes
    
    See Also
    --------
    RelatedClass : Brief relationship note
    """
    cpt: Cpt
    boreholes: list[Borehole]
    soil_profile: SoilProfile | None = None

    def classify(self, correlation: CptCorrelation):
        """Applies a cpt correlation to classify the cpt into a soil profile"""
        self.soil_profile = correlation.classify(self.cpt)

    def interpret(self):
        """Creates a UI object to compare the automated classification of the cpt, stored in the soil_profile attribute, to the adjacent boreholes"""
        pass


class RectangleCanvas:
    """UI class to make a manual interpretation of a Cpt object"""

    """
    [What role/responsibility this class has in the system]
    
    [Optional: Extended description of the problem it solves, key behaviors,
    design considerations, or performance characteristics]
    
    Parameters
    ----------
    init_param1
        What this controls. Guidance on typical values or ranges.
    init_param2
        What this affects. Interdependencies with other parameters.
    
    Attributes
    ----------
    public_attr1 : Type
        What this tracks. When/how it changes. Initial value if not obvious.
    public_attr2 : Type
        What this represents. How users should interpret it.
    
    Examples
    --------
    >>> # Typical initialization and basic usage
    >>> obj = ClassName(param1, param2)
    >>> result = obj.main_method()
    
    Notes
    -----
    - Thread-safety considerations
    - Lifecycle/cleanup requirements
    - Design patterns or architecture notes
    
    See Also
    --------
    RelatedClass : Brief relationship note
    """

    def __init__(
        self,
        root,
        fig: plt.Figure,
        ax1: plt.Axes,
        ax2: plt.Axes,
        interpretation: SoilProfile,
        soil_colors: list[Color],
    ):
        """Constructor of the RectangleCanvas class"""
        self.root = root
        self.root.title("Right-Click Rectangle Canvas")
        # self.root.geometry("800x600")

        # Create canvas
        self.fig: plt.Figure = fig
        self.ax1: plt.Axes = ax1
        self.ax2: plt.Axes = ax2

        # Maximize window and match tkinter window size and figure
        width, height = self.root.maxsize()
        dpi = self.fig.get_dpi()
        self.fig.set_size_inches(width / dpi, (height / dpi) - 1)

        # Create canvas from figure
        self.canvas = FigureCanvasTkAgg(
            fig, master=root
        ).get_tk_widget()  # Convert the Figure to a tkinter widget
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Variables to track rectangle drawing
        self.start_y = None
        self.current_rect: int | None = None
        self.is_drawing = False
        self.colors_map = {c.soil: c.color for c in soil_colors}

        # Variables to track rectangle editing
        self.editing_rect = None
        self.editing_edge = None  # 'top' or 'bottom'
        self.is_editing = False
        self.edge_tolerance = 10  # pixels tolerance for edge detection

        # Bind mouse events
        self.canvas.bind("<Button-3>", self.on_right_click)  # Right mouse button press
        self.canvas.bind("<B3-Motion>", self.on_right_drag)  # Right mouse button drag
        self.canvas.bind(
            "<ButtonRelease-3>", self.on_right_release
        )  # Right mouse button release
        self.canvas.bind(
            "<Double-Button-1>", self.on_left_double_click
        )  # Left mouse double click removes rectangle

        # Left mouse button events for editing
        self.canvas.bind("<Button-1>", self.on_left_click)  # Left mouse button press
        self.canvas.bind("<B1-Motion>", self.on_left_drag)  # Left mouse button drag
        self.canvas.bind(
            "<ButtonRelease-1>", self.on_left_release
        )  # Left mouse button release

        # Add instructions
        instructions = tk.Label(
            root,
            text="Right-click drag: Create rectangle | Left-click edge drag: Edit rectangle",
            bg="lightgray",
            pady=5,
        )
        instructions.pack(side=tk.BOTTOM, fill=tk.X)

        # Plot interpretation
        self.rect_id_layer_map: dict[int, Layer] = {}
        self.interpretation = interpretation
        self.result = None
        # To show the interpret/kaation, it needs to be executed with delay
        # If not, the interpretation squares will not be shown
        root.after(500, self._plot_interpretation)

    def _plot_interpretation(self):
        """Plots the soil layers on the canvas"""
        self.xmin_rect, self.xmax_rect = self._get_xbounds_rect()
        _, _fig_height_inch = self.fig.get_size_inches()
        dpi = self.fig.get_dpi()
        for layer in self.interpretation.layers:
            px_top = y_to_canvas_pixel(layer.top, self.ax1, _fig_height_inch, dpi)
            px_bottom = y_to_canvas_pixel(layer.bottom, self.ax1, _fig_height_inch, dpi)

            # Create initial soil profile
            top_left_corner = (self.xmin_rect, px_top)
            bottom_right_corner = (self.xmax_rect, px_bottom)
            rect_id = self.canvas.create_rectangle(
                top_left_corner,
                bottom_right_corner,
                outline="",
                fill=self.colors_map[layer.soil],
                stipple=STIPPLE,
            )
            self.rect_id_layer_map[rect_id] = layer

    def _get_xbounds_rect(self) -> tuple[int, int]:
        """Gets the minimum and maximum pixel of the rectangles to be drawn on the canvas"""
        self.canvas.update_idletasks()

        canvas_width_px = self.canvas.winfo_width()

        ax1_bbox = self.ax1.get_position()
        ax2_bbox = self.ax2.get_position()
        ax1_left = ax1_bbox.x0
        axes_width = (ax1_bbox.width + ax2_bbox.width) * canvas_width_px

        axes_left_px = ax1_left * canvas_width_px
        return round(axes_left_px), round(axes_left_px + axes_width - 4)

    def on_right_click(self, event):
        """Handle right mouse button press"""
        self.start_y = event.y
        self.is_drawing = True

        # Create initial rectangle (will be updated as mouse moves)
        self.current_rect = self.canvas.create_rectangle(
            self.xmin_rect,
            self.start_y,
            self.xmax_rect,
            self.start_y,
            outline="blue",
            fill="lightblue",
            stipple=STIPPLE,
        )

    def on_right_drag(self, event):
        """Handle right mouse button drag"""
        if not self.is_drawing or self.current_rect is None:
            return

        # Calculate rectangle coordinates
        top_y = min(self.start_y, event.y)
        bottom_y = max(self.start_y, event.y)

        # Update rectangle coordinates
        self.canvas.coords(
            self.current_rect, self.xmin_rect, top_y, self.xmax_rect, bottom_y
        )

    def on_right_release(self, event):
        """Handle right mouse button release"""
        self.is_drawing = False

        # Optionally, you could finalize the rectangle here
        # For example, change its appearance or add it to a list of permanent rectangles
        # Select soil
        soil_selection_window = SelectionDialog(
            ["klei", "zand", "veen"], parent=self.root
        )
        soil = soil_selection_window.show()
        if not soil is None and not self.current_rect is None:
            _, ytop, _, ybottom = self.canvas.coords(self.current_rect)
            layer = Layer(
                soil,
                top=canvas_pixel_to_y_data(ytop, self.canvas, self.fig, self.ax1),
                bottom=canvas_pixel_to_y_data(ybottom, self.canvas, self.fig, self.ax1),
            )
            self.rect_id_layer_map[self.current_rect] = layer
            self.interpretation.add_layer(layer)
            # Change the rectangle to a more permanent appearance
            self.canvas.itemconfig(
                self.current_rect, fill=self.colors_map[soil], stipple=STIPPLE
            )

        # Reset for next rectangle
        self.current_rect = None
        self.start_y = None

    def find_rectangle_edge(self, x, y):
        """Find if click is near the top or bottom edge of any rectangle"""
        # Get all items at the click position
        items = self.canvas.find_overlapping(
            x - 1, y - self.edge_tolerance, x + 1, y + self.edge_tolerance
        )

        for item in items:
            # Check if it's a rectangle
            if self.canvas.type(item) == "rectangle":
                coords = self.canvas.coords(item)
                if len(coords) == 4:
                    x1, y1, x2, y2 = coords

                    # Check if click is near top edge
                    if abs(y - y1) <= self.edge_tolerance and x1 <= x <= x2:
                        return item, "top"

                    # Check if click is near bottom edge
                    if abs(y - y2) <= self.edge_tolerance and x1 <= x <= x2:
                        return item, "bottom"

        return None, None

    def find_rectangle(self, x, y):
        """Find the rectangle at x,y. Initially return the top rectangle"""
        # Get all items at the click position
        items = list(self.canvas.find_overlapping(x - 1, y - 1, x + 1, y + 1))
        if len(items) > 0:
            items.sort(reverse=True)
            return items[0]
        return None

    def on_left_double_click(self, event):
        """Handle double click left mouse button --> remove soil layer"""
        if self.is_drawing:
            return
        rect = self.find_rectangle(event.x, event.y)

        if rect is not None and rect > 1:  # rect number 1 is the matplotlib figure
            self.canvas.delete(rect)
            self.rect_id_layer_map.pop(rect)

    def on_left_click(self, event):
        """Handle left mouse button press for editing"""
        # Don't edit while drawing a new rectangle
        if self.is_drawing:
            return

        # Find if click is near an edge
        rect, edge = self.find_rectangle_edge(event.x, event.y)

        if rect and edge:
            self.editing_rect = rect
            self.editing_edge = edge
            self.is_editing = True

            # Change cursor to indicate resize mode
            self.canvas.config(cursor="sb_v_double_arrow")

            # Highlight the rectangle being edited
            self.canvas.itemconfig(rect, outline="red", width=2)

    def on_left_drag(self, event):
        """Handle left mouse button drag for editing"""
        if not self.is_editing or not self.editing_rect:
            return

        # Get current rectangle coordinates
        coords = self.canvas.coords(self.editing_rect)
        if len(coords) != 4:
            return

        x1, y1, x2, y2 = coords

        # Update the appropriate edge
        if self.editing_edge == "top":
            # Move top edge, but don't let it go below bottom edge
            new_y1 = min(event.y, y2 - 5)  # 5 pixel minimum height
            self.canvas.coords(self.editing_rect, x1, new_y1, x2, y2)
        elif self.editing_edge == "bottom":
            # Move bottom edge, but don't let it go above top edge
            new_y2 = max(event.y, y1 + 5)  # 5 pixel minimum height
            self.canvas.coords(self.editing_rect, x1, y1, x2, new_y2)

    def on_left_release(self, event):
        """Handle left mouse button release"""
        if self.is_editing and self.editing_rect:
            # Reset rectangle appearance
            layer = self.rect_id_layer_map[self.editing_rect]
            self.canvas.itemconfig(
                self.editing_rect, fill=self.colors_map[layer.soil], width=1
            )

            # Adapt soil profile in attributes
            if self.editing_edge == "top":
                _, ytop, _, _ = self.canvas.coords(self.editing_rect)
                self.interpretation.change_layer(
                    layer,
                    new_top=canvas_pixel_to_y_data(
                        ytop, self.canvas, self.fig, self.ax1
                    ),
                )
            elif self.editing_edge == "bottom":  # bottom
                _, _, _, ybottom = self.canvas.coords(self.editing_rect)
                self.interpretation.change_layer(
                    layer,
                    new_bottom=canvas_pixel_to_y_data(
                        ybottom, self.canvas, self.fig, self.ax1
                    ),
                )
            else:
                raise ValueError("Something is going wrong with the self.editing_edge!")
            # Reset cursor
            self.canvas.config(cursor="")

        # Reset editing state
        self.is_editing = False
        self.editing_rect = None
        self.editing_edge = None

    def close_and_save(self):
        """Save interpretation and close window"""
        self.root.quit()  # DO NOT REMOVE, this ensures the mainloop is stopped when clicking 'x' button
        self.root.destroy()

    def show(self) -> SoilProfile:
        """Returns the interpretation when the human is done working in the UI"""
        return self.interpretation


def canvas_pixel_to_y_data(canvas_y_pixel, canvas_widget, figure, axes):
    """
    Convert tkinter canvas pixel coordinates to matplotlib y-axis data values.

    Parameters:
    -----------
    canvas_y_pixel : float
        Y-coordinate in canvas pixels (0 = top of canvas)
    canvas_widget : tk.Canvas
        The matplotlib canvas widget embedded in tkinter
    figure : matplotlib.figure.Figure
        The matplotlib figure object
    axes : matplotlib.axes.Axes
        The matplotlib axes object

    Returns:
    --------
    float
        Corresponding y-axis data value
    """
    # Get canvas dimensions
    canvas_height = canvas_widget.winfo_height()

    # Get figure size in inches and DPI
    _, fig_height_inch = figure.get_size_inches()
    dpi = figure.get_dpi()

    # Calculate figure size in pixels
    fig_height_px = fig_height_inch * dpi

    # Get axes position in figure coordinates (0-1)
    axes_bbox = axes.get_position()
    axes_bottom = axes_bbox.y0
    axes_height = axes_bbox.height

    # Convert axes position to pixels within the figure
    axes_bottom_px = axes_bottom * fig_height_px
    axes_height_px = axes_height * fig_height_px

    # Calculate scaling factors between canvas and figure
    scale_y = canvas_height / fig_height_px

    # Convert canvas pixel to figure pixel coordinates
    fig_y_pixel = canvas_y_pixel / scale_y

    # Convert figure coordinates to axes coordinates
    # Note: In figure coordinates, y=0 is bottom, but in canvas y=0 is top
    fig_y_from_bottom = fig_height_px - fig_y_pixel
    axes_y_pixel = fig_y_from_bottom - axes_bottom_px

    # Normalize to axes coordinate system (0-1)
    axes_y_normalized = axes_y_pixel / axes_height_px

    # Convert to data coordinates
    y_min, y_max = axes.get_ylim()
    y_data = y_min + axes_y_normalized * (y_max - y_min)

    return y_data


def y_to_canvas_pixel(
    y: float, ax: plt.Axes, fig_height_inch: float, dpi: float
) -> float:
    """Transforms the y value in a given Axes to a pixel in the tkinter canvas"""
    ymin, ymax = ax.get_ylim()
    axes_y_normalized = (ymax - y) / (ymax - ymin)

    # Get axes position in figure coordinates (0-1)
    axes_bbox = ax.get_position()
    axes_bottom = axes_bbox.y0
    axes_height = axes_bbox.height

    # Calculate figure height in pixels
    fig_height_px = fig_height_inch * dpi

    # Convert axes position to pixels within the figure
    axes_bottom_px = axes_bottom * fig_height_px
    axes_height_px = axes_height * fig_height_px

    return round(axes_bottom_px + axes_y_normalized * axes_height_px)


def run_interpreter(
    cpt: Cpt, interpretation: SoilProfile, soil_colors: list[Color]
) -> SoilProfile:
    """Runs the manual Cpt interpreter class RectangleCanvas and returns the final soil profile after the user is done"""

    root = tk.Tk()
    fig, ax1, ax2 = plot_cpt(cpt)
    interpretor = RectangleCanvas(
        root=root,
        fig=fig,
        ax1=ax1,
        ax2=ax2,
        interpretation=interpretation,
        soil_colors=soil_colors,
    )
    root.protocol("WM_DELETE_WINDOW", interpretor.close_and_save)
    root.mainloop()
    return interpretor.interpretation


class SelectionDialog:
    """Dialog that is shown when a new layer is created in the RectangleCanvas and a new soil must be chosen"""

    def __init__(
        self, options, parent, title="Select an Option", prompt="Choose an option:"
    ):
        """Constructor of a SelectionDialog object"""
        self.result = None
        self.options = options

        # Create the dialog window
        self.root = tk.Toplevel(parent)
        self.root.title(title)
        self.root.geometry("300x150")
        self.root.resizable(False, False)

        # Make it modal
        if parent:
            self.root.transient(parent)
        self.root.grab_set()

        # Create and pack widgets
        self.create_widgets(prompt)

        # Center the window
        self.center_window()

    def create_widgets(self, prompt):
        """Method that creates the selection widget"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Prompt label
        prompt_label = ttk.Label(main_frame, text=prompt)
        prompt_label.pack(pady=(0, 10))

        # Dropdown (Combobox)
        self.dropdown = ttk.Combobox(
            main_frame, values=self.options, state="readonly", width=25
        )
        self.dropdown.pack(pady=(0, 20))

        # Set default selection to first option
        if self.options:
            self.dropdown.set(self.options[0])

        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack()

        # Select button
        select_button = ttk.Button(button_frame, text="Select", command=self.on_select)
        select_button.pack(side=tk.LEFT, padx=(0, 10))

        # Cancel button
        cancel_button = ttk.Button(button_frame, text="Cancel", command=self.on_cancel)
        cancel_button.pack(side=tk.LEFT)

        # Bind Enter key to select
        self.root.bind("<Return>", lambda e: self.on_select())
        self.root.bind("<Escape>", lambda e: self.on_cancel())

        # Focus on dropdown
        self.dropdown.focus()

    def center_window(self):
        """Method that centers the window into the center of the RectangleCanvas"""
        self.root.update_idletasks()

        # Get parent window if available
        parent = self.root.master
        if parent:
            # Center relative to parent window
            parent_x = parent.winfo_rootx()
            parent_y = parent.winfo_rooty()
            parent_width = parent.winfo_width()
            parent_height = parent.winfo_height()

            x = parent_x + (parent_width // 2) - (self.root.winfo_width() // 2)
            y = parent_y + (parent_height // 2) - (self.root.winfo_height() // 2)
        else:
            # Center on screen
            x = (self.root.winfo_screenwidth() // 2) - (self.root.winfo_width() // 2)
            y = (self.root.winfo_screenheight() // 2) - (self.root.winfo_height() // 2)

        self.root.geometry(f"+{x}+{y}")

    def on_select(self):
        """Method that destroys the SelectionDialog object when a soil is selected"""
        self.result = self.dropdown.get()
        self.root.destroy()

    def on_cancel(self):
        """Method that destroys the SelectionDialog object when the cancel button is selected"""
        self.result = None
        self.root.destroy()

    def show(self):
        """Method that runs the SelectionDialog until it is finished (and destroyed). Then returns the selected soil."""
        self.root.wait_window()
        return self.result
