"""
Webview wrapper for embedding Leaflet maps in tkinter applications.

Provides a thin abstraction over pywebview for rendering HTML-based
interactive maps within a tkinter frame.
"""

import os

# Must be set before importing pywebview or any Qt binding
os.environ["QT_API"] = "pyside6"

import tkinter as tk
from typing import Callable


class MapWebviewWrapper:
    """
    Wrapper for pywebview to render an interactive map in tkinter.

    Manages the lifecycle of a webview window displaying a Leaflet.js map
    and provides methods for bidirectional Python-JavaScript communication.

    Note: pywebview must run on the main thread. This wrapper coordinates
    with tkinter by running both in the main thread using webview's
    event loop with periodic tkinter updates.

    Attributes
    ----------
    root : tk.Tk
        The parent tkinter window.
    webview : object
        The pywebview window instance.
    _exposed_functions : dict[str, Callable]
        Dictionary of functions exposed to JavaScript.
    _is_destroyed : bool
        Flag indicating if the webview has been destroyed.

    Parameters
    ----------
    root : tk.Tk
        The parent tkinter window.
    width : int
        Width of the webview in pixels.
    height : int
        Height of the webview in pixels.
    html_content : str
        HTML content to render in the webview.
    """

    def __init__(
        self,
        root: tk.Tk,
        width: int,
        height: int,
        html_content: str,
    ) -> None:
        """
        Initialize the webview wrapper with HTML content.

        The webview is created but not started. Call start() to display it.

        Parameters
        ----------
        root : tk.Tk
            The parent tkinter window.
        width : int
            Width of the webview in pixels.
        height : int
            Height of the webview in pixels.
        html_content : str
            HTML content containing the Leaflet map.

        Raises
        ------
        ValueError
            If width or height is not positive.
        TypeError
            If root is not a tk.Tk instance.
        """
        if not isinstance(root, tk.Tk):
            raise TypeError(f"root must be tk.Tk, got {type(root).__name__}")
        if width <= 0:
            raise ValueError(f"width must be positive, got {width}")
        if height <= 0:
            raise ValueError(f"height must be positive, got {height}")
        if not html_content:
            raise ValueError("html_content cannot be empty")

        self.root = root
        self._width = width
        self._height = height
        self._html_content = html_content
        self._exposed_functions: dict[str, Callable] = {}
        self._is_destroyed = False
        self._webview_started = False

        # Create a frame to host the webview
        self._frame = tk.Frame(root, width=width, height=height)
        self._frame.pack(fill="both", expand=True)

    def start(self) -> None:
        """
        Start the webview window.

        This method creates the webview window and starts the event loop.
        It must be called on the main thread. This method blocks until
        the window is closed.

        Raises
        ------
        RuntimeError
            If the webview has already been started or destroyed.
        """
        if self._is_destroyed:
            raise RuntimeError("Cannot start: webview has been destroyed")
        if self._webview_started:
            raise RuntimeError("Webview has already been started")

        self._webview_started = True

        # Create the webview window
        self.webview = webview.create_window(
            title="Map Selector",
            html=self._html_content,
            width=self._width,
            height=self._height,
        )

        # Expose all registered functions
        for name, func in self._exposed_functions.items():
            wrapper = self._create_named_wrapper(func, name)
            self.webview.expose(wrapper)

        # Start the webview event loop (blocks until window is closed)
        webview.start(debug=False)

    def expose(self, name: str, func: Callable) -> None:
        """
        Expose a Python function to JavaScript.

        Makes the given Python function callable from JavaScript via
        window.pywebview.api.<name>().

        Must be called before start().

        Parameters
        ----------
        name : str
            Name to expose the function as in JavaScript.
        func : Callable
            The Python function to expose.

        Raises
        ------
        ValueError
            If name is empty or not a valid identifier.
        TypeError
            If func is not callable.
        RuntimeError
            If the webview has been started or destroyed.
        """
        if self._is_destroyed:
            raise RuntimeError("Cannot expose function: webview has been destroyed")
        if self._webview_started:
            raise RuntimeError(
                "Cannot expose function: webview has already been started"
            )
        if not name:
            raise ValueError("name cannot be empty")
        if not name.isidentifier():
            raise ValueError(f"name must be a valid Python identifier, got '{name}'")
        if not callable(func):
            raise TypeError(f"func must be callable, got {type(func).__name__}")

        self._exposed_functions[name] = func

    def _create_named_wrapper(self, func: Callable, name: str) -> Callable:
        """
        Create a wrapper function with a specific __name__ attribute.

        pywebview exposes functions using their __name__, so we need to create
        a wrapper that has the desired name.

        Parameters
        ----------
        func : Callable
            The original function to wrap.
        name : str
            The desired name for the wrapper function.

        Returns
        -------
        Callable
            A wrapper function with the specified __name__.
        """

        # Use a closure to capture func
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        # Set the wrapper's __name__ to the desired name
        wrapper.__name__ = name
        wrapper.__doc__ = func.__doc__
        wrapper.__module__ = func.__module__

        return wrapper

    def evaluate_js(self, script: str) -> None:
        """
        Execute JavaScript code in the webview.

        Parameters
        ----------
        script : str
            JavaScript code to execute.

        Raises
        ------
        ValueError
            If script is empty.
        RuntimeError
            If the webview has been destroyed or not started.
        """
        if self._is_destroyed:
            raise RuntimeError("Cannot evaluate JS: webview has been destroyed")
        if not self._webview_started:
            raise RuntimeError("Cannot evaluate JS: webview has not been started")
        if not script:
            raise ValueError("script cannot be empty")

        # Execute JavaScript in the webview context
        if hasattr(self, "webview") and self.webview is not None:
            self.webview.evaluate_js(script)

    def destroy(self) -> None:
        """
        Clean up and destroy the webview window.

        Should be called when the map is no longer needed to release
        resources properly. This method is idempotent - calling it multiple
        times has no effect after the first call.
        """
        if self._is_destroyed:
            return

        self._is_destroyed = True

        # Destroy webview window
        if hasattr(self, "webview") and self.webview is not None:
            if hasattr(self.webview, "destroy"):
                self.webview.destroy()

        # Clean up tkinter frame
        if self._frame and self._frame.winfo_exists():
            self._frame.destroy()

        # Clear references
        self._exposed_functions.clear()
        self.webview = None
