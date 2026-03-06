"""Device detection and coloring utilities for HR plot visualization."""

# Device name to color mapping
# Use easily distinguishable colors for different HR data sources
DEVICE_COLORS = {
    "Garmin Edge 530": "#1f77b4",          # Blue (chest strap)
    "Garmin Forerunner 255": "#ff7f0e",    # Orange (watch)
    "Garmin Forerunner 955": "#2ca02c",    # Green (watch)
    "Apple Watch": "#d62728",              # Red (watch)
    "Whoop Band": "#9467bd",               # Purple (wrist)
    "Polar H10": "#8c564b",                # Brown (chest strap)
    "Wahoo Tickr": "#e377c2",              # Pink (chest strap)
}

# Default color for unknown devices
DEFAULT_DEVICE_COLOR = "#7f7f7f"  # Gray


def get_device_color(device_name: str) -> str:
    """
    Get color for a device.

    Args:
        device_name: Name of the device (or None)

    Returns:
        Hex color code for the device, or default gray for unknown devices
    """
    if device_name is None or (isinstance(device_name, float) and device_name != device_name):
        # NaN or None
        return DEFAULT_DEVICE_COLOR

    device_str = str(device_name).strip()
    return DEVICE_COLORS.get(device_str, DEFAULT_DEVICE_COLOR)


def get_device_legend_colors() -> dict[str, str]:
    """
    Get a mapping of unique device names to colors for legend.

    Returns:
        Dictionary of device_name -> color for devices that have explicit colors defined
    """
    return DEVICE_COLORS.copy()


def create_device_legend(devices_in_data: set[str] | list[str]) -> list[dict]:
    """
    Create legend entries for devices present in data.

    Args:
        devices_in_data: Set or list of device names from the data

    Returns:
        List of dicts with name and color for each device
    """
    legend = []
    for device in sorted(set(devices_in_data)):
        if device is not None and not (isinstance(device, float) and device != device):
            color = get_device_color(device)
            legend.append({"name": device, "color": color})

    # Add "Unknown" entry if there are any unknown devices
    if len(devices_in_data) > len(legend):
        legend.append({"name": "Unknown / No Device", "color": DEFAULT_DEVICE_COLOR})

    return legend
