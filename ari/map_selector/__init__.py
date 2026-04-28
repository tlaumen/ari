"""
MapPointSelector package for interactive geographic location selection.

This package provides a replacement for the tkintermapview-based MapPointSelector
using a webview-based approach with Leaflet.js for map rendering.

Example
-------
>>> from ari.map_selector import MapPointSelector
>>> import tkinter as tk
>>> from ceniac.soil_investigation.cpt import Cpt
>>>
>>> root = tk.Tk()
>>> cpts = [...]  # List of Cpt objects
>>> selector = MapPointSelector(root, cpts)
>>> root.mainloop()
>>> point = selector.get_point()  # Returns (x, y) in RD coordinates
"""

from ari.map_selector.map_selector import MapPointSelector

__version__ = "1.0.0"

__all__ = ["MapPointSelector"]
