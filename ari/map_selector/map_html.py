"""
HTML and JavaScript generation for Leaflet-based interactive maps.

This module generates the HTML, CSS, and JavaScript required to render
an interactive map using Leaflet.js with CartoDB tiles (OSM-based,
works without Referer header requirements).
"""

from typing import TYPE_CHECKING

from ari.map_selector.coordinates import rd_to_lat_lon

if TYPE_CHECKING:
    from ceniac.soil_investigation.cpt import Cpt


def generate_map_html(cpts: list["Cpt"], icon_path: str) -> str:
    """
    Generate HTML content for an interactive Leaflet map with CPT markers.

    Creates a complete HTML document containing a Leaflet.js map configured
    with OpenStreetMap tiles, CPT markers, and event handlers for double-click
    selection.

    Parameters
    ----------
    cpts : list[Cpt]
        List of CPT objects to display as markers. Must have x, y attributes
        in RD coordinates and id_ for labeling.
    icon_path : str
        Path to the CPT icon image file (relative or absolute).

    Returns
    -------
    str
        Complete HTML document as a string ready to render in webview.
    """
    if not cpts:
        raise ValueError("cpts list cannot be empty")

    cpt_markers_js = _generate_cpt_markers_js(cpts, icon_path)
    map_init_js = _generate_map_init_js(cpts)
    dblclick_handler_js = _generate_dblclick_handler_js()

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CPT Location Selector</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
          integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY="
          crossorigin=""/>
    <style>
        body {{
            margin: 0;
            padding: 0;
            font-family: Arial, sans-serif;
        }}
        #map {{
            width: 100vw;
            height: 100vh;
        }}
        .cpt-label {{
            background-color: rgba(255, 255, 255, 0.8);
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 12px;
            font-weight: bold;
            color: #000;
            border: 1px solid #333;
        }}
    </style>
</head>
<body>
    <div id="map"></div>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
            integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo="
            crossorigin=""></script>
    <script>
        {map_init_js}
        {cpt_markers_js}
        {dblclick_handler_js}
    </script>
</body>
</html>"""
    return html


def _generate_cpt_markers_js(cpts: list["Cpt"], icon_path: str) -> str:
    """
    Generate JavaScript code for creating CPT markers on the map.

    Parameters
    ----------
    cpts : list[Cpt]
        CPT objects to create markers for.
    icon_path : str
        Path to the marker icon image.

    Returns
    -------
    str
        JavaScript code for creating markers.
    """
    if not cpts:
        raise ValueError("cpts list cannot be empty")

    lines = ["// CPT Markers"]

    for cpt in cpts:
        lat, lon = rd_to_lat_lon(cpt.x, cpt.y)
        lines.append(f"""
        // CPT {cpt.id_}
        L.marker([{lat:.6f}, {lon:.6f}], {{
            icon: L.divIcon({{
                className: 'cpt-marker',
                html: '<div class="cpt-label">{cpt.id_}</div>',
                iconSize: [60, 20],
                iconAnchor: [30, 10]
            }})
        }}).addTo(map).bindPopup('CPT: {cpt.id_}');""")

    return "\n".join(lines)


def _generate_map_init_js(cpts: list["Cpt"]) -> str:
    """
    Generate JavaScript for initializing the Leaflet map.

    Parameters
    ----------
    cpts : list[Cpt]
        CPT objects to determine map bounds.

    Returns
    -------
    str
        JavaScript code for map initialization.
    """
    if not cpts:
        raise ValueError("cpts list cannot be empty")

    # Calculate bounds from all CPTs
    lats = []
    lons = []
    for cpt in cpts:
        lat, lon = rd_to_lat_lon(cpt.x, cpt.y)
        lats.append(lat)
        lons.append(lon)

    min_lat, max_lat = min(lats), max(lats)
    min_lon, max_lon = min(lons), max(lons)

    # Add padding for single CPT case
    if len(cpts) == 1:
        lat_padding = 0.001
        lon_padding = 0.002
    else:
        lat_padding = (max_lat - min_lat) * 0.1
        lon_padding = (max_lon - min_lon) * 0.1

    return f"""
        // Initialize map
        var map = L.map('map');

        // Add CartoDB tile layer (OSM-based, works without Referer header)
        L.tileLayer('https://{{s}}.basemaps.cartocdn.com/rastertiles/voyager/{{z}}/{{x}}/{{y}}{{r}}.png', {{
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
            subdomains: 'abcd',
            maxZoom: 20
        }}).addTo(map);

        // Set bounds to fit all CPTs
        var bounds = L.latLngBounds(
            L.latLng({min_lat - lat_padding:.6f}, {min_lon - lon_padding:.6f}),
            L.latLng({max_lat + lat_padding:.6f}, {max_lon + lon_padding:.6f})
        );
        map.fitBounds(bounds);
"""


def _generate_dblclick_handler_js() -> str:
    """
    Generate JavaScript for double-click event handling.

    Returns
    -------
    str
        JavaScript code for handling double-click events.
    """
    return """
        // Double-click handler for point selection
        var tempMarker = null;
        var isApiReady = false;

        // Wait for pywebview API to be ready
        window.addEventListener('pywebviewready', function() {
            console.log('PyWebView API is ready');
            isApiReady = true;
        });

        map.on('dblclick', function(e) {
            var lat = e.latlng.lat;
            var lon = e.latlng.lng;

            // Remove previous temporary marker if exists
            if (tempMarker) {
                map.removeLayer(tempMarker);
            }

            // Add temporary marker at clicked location
            tempMarker = L.marker([lat, lon], {
                icon: L.divIcon({
                    className: 'selection-marker',
                    html: '<div class="cpt-label" style="background-color: #ff6b6b;">Selected</div>',
                    iconSize: [60, 20],
                    iconAnchor: [30, 10]
                })
            }).addTo(map);

            // Show confirmation dialog
            var message = 'Are you sure you want to select this location?\\n\\n' +
                         'Latitude: ' + lat.toFixed(6) + '\\n' +
                         'Longitude: ' + lon.toFixed(6);
            var confirmed = confirm(message);

            if (confirmed) {
                // User confirmed - call Python callback via pywebview
                if (window.pywebview && window.pywebview.api && window.pywebview.api.on_double_click) {
                    window.pywebview.api.on_double_click(lat, lon);
                } else {
                    console.log('pywebview API not ready yet');
                    alert('Error: Unable to communicate with the application. Please try again.');
                    if (tempMarker) {
                        map.removeLayer(tempMarker);
                        tempMarker = null;
                    }
                }
            } else {
                // User cancelled - remove the temporary marker
                if (tempMarker) {
                    map.removeLayer(tempMarker);
                    tempMarker = null;
                }
            }
        });
    """
