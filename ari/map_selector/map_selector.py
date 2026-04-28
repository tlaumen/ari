"""
Core MapPointSelector implementation using webview-based map rendering.

This module provides the MapPointSelector class which displays an interactive
map in a tkinter window using an embedded webview with Leaflet.js.
"""

import tkinter as tk
from pathlib import Path
from typing import TYPE_CHECKING

from PIL import ImageGrab
from PIL.Image import Image

from ari.map_selector.coordinates import lat_lon_to_rd
from ari.map_selector.map_html import generate_map_html
from ari.map_selector.webview_wrapper import MapWebviewWrapper

if TYPE_CHECKING:
    from ceniac.soil_investigation.cpt import Cpt


class MapPointSelector:
    """
    Interactive map component for selecting geographic locations via double-click.

    Displays CPT markers on an interactive map and allows the user to select
    a location by double-clicking. Returns the selected point in RD coordinates.

    Attributes
    ----------
    root : tk.Tk
        The tkinter root window containing the map.
    selected_point : tuple[float, float] | None
        The selected point as (latitude, longitude) in WGS84, or None if not selected.
    top_view_image : Image | None
        Screenshot of the map for reporting purposes.

    Parameters
    ----------
    root : tk.Tk
        The tkinter root window for the map.
    cpts : list[Cpt]
        List of CPT objects to display as markers on the map.
    """

    def __init__(self, root: tk.Tk, cpts: list["Cpt"]) -> None:
        """
        Initialize the MapPointSelector with a tkinter root and CPT markers.

        Creates a webview-based map widget displaying the given CPT locations.
        Sets up event handlers for double-click selection.

        Parameters
        ----------
        root : tk.Tk
            The tkinter root window.
        cpts : list[Cpt]
            CPT objects to display as markers. Each Cpt has x, y attributes
            in RD coordinates which will be converted to lat/lon for display.

        Raises
        ------
        TypeError
            If root is not a tk.Tk instance.
        ValueError
            If cpts list is empty.
        """
        if not isinstance(root, tk.Tk):
            raise TypeError(f"root must be tk.Tk, got {type(root).__name__}")
        if not cpts:
            raise ValueError("cpts list cannot be empty")

        self.root = root
        self.cpts = cpts
        self.selected_point: tuple[float, float] | None = None
        self.top_view_image: Image | None = None
        self._temp_marker_removed = False

        # Configure window
        self.root.geometry("800x600")
        self.root.title("Click to Select Point")

        # Get CPT icon path
        icon_path = str(Path(__file__).parent.parent.parent / "media" / "cpt-icon.png")

        # Generate HTML content
        html_content = generate_map_html(cpts, icon_path)

        # Create webview wrapper
        self._webview = MapWebviewWrapper(
            root=self.root,
            width=800,
            height=600,
            html_content=html_content,
        )

        # Expose Python callback to JavaScript
        self._webview.expose("on_double_click", self.on_double_click)

        # Start the webview (must be done after exposing all functions)
        self._webview.start()

    def on_double_click(self, latitude: float, longitude: float) -> None:
        """
        Handle double-click event on the map.

        Called by the JavaScript map when user double-clicks and confirms
        the selection via the confirmation dialog. Stores the selected point
        and closes the window.

        Parameters
        ----------
        latitude : float
            Latitude of the clicked location in WGS84.
        longitude : float
            Longitude of the clicked location in WGS84.

        Raises
        ------
        ValueError
            If latitude or longitude is out of valid range.
        """
        if not -90 <= latitude <= 90:
            raise ValueError(f"latitude must be in range [-90, 90], got {latitude}")
        if not -180 <= longitude <= 180:
            raise ValueError(f"longitude must be in range [-180, 180], got {longitude}")

        # Store the selected coordinates (user already confirmed in JavaScript dialog)
        self.selected_point = (latitude, longitude)

        # Create screenshot for reports
        self._create_topview_screenshot()

        # Close the window
        self._cleanup_and_close()

    def _remove_temp_marker(self) -> None:
        """Remove the temporary marker from the map via JavaScript."""
        if self._webview and not self._temp_marker_removed:
            script = """
                if (tempMarker) {
                    map.removeLayer(tempMarker);
                    tempMarker = null;
                }
            """
            self._webview.evaluate_js(script)

    def _cleanup_and_close(self) -> None:
        """Clean up resources and close the window."""
        if self._webview:
            self._webview.destroy()
            self._webview = None
        # Must destroy tkinter root from main thread, not from pywebview callback thread
        self.root.after(0, self.root.destroy)

    def _zoom_to_all_cpts(self) -> None:
        """
        Set the map view to include all CPT markers.

        This is handled automatically during map initialization via the
        fitBounds() call in the generated JavaScript.
        """
        # Zoom is handled during map initialization in map_html.py
        # This method exists for API compatibility with the old implementation
        pass

    def _create_topview_screenshot(self) -> None:
        """
        Capture a screenshot of the map widget area.

        Uses PIL.ImageGrab to capture the webview widget area for
        inclusion in reports. Stores the image in self.top_view_image.
        """
        # Get the geometry of the root window
        x1 = self.root.winfo_rootx()
        y1 = self.root.winfo_rooty()
        x2 = x1 + self.root.winfo_width()
        y2 = y1 + self.root.winfo_height()

        # Capture the screenshot
        self.top_view_image = ImageGrab.grab(bbox=(x1, y1, x2, y2))

        # Convert to RGB if necessary (for compatibility with reporting)
        if self.top_view_image.mode != "RGB":
            self.top_view_image = self.top_view_image.convert("RGB")

    def get_point(self) -> tuple[float, float]:
        """
        Return the selected point in RD coordinates.

        Converts the stored WGS84 coordinates back to RD (Rijksdriehoek)
        coordinate system (EPSG:28992).

        Returns
        -------
        tuple[float, float]
            Selected point as (x, y) in RD coordinates (meters).

        Raises
        ------
        ValueError
            If no point was selected (user cancelled or closed window).
        """
        if self.selected_point is None:
            raise ValueError(
                "No point was selected, something went wrong in the MapPointSelector!"
            )

        latitude, longitude = self.selected_point
        return lat_lon_to_rd(latitude, longitude)
