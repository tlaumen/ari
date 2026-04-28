from dataclasses import dataclass
from itertools import pairwise

from jinja2.runtime import V


@dataclass
class Layer:
    """
    Represents a single soil layer.

    Combined, the soil layers represent a profile.

    Attributes
    ----------
    soil
        The soil present in this layer
    top
        The top level of the layer
    bottom
        The bottom level of the layer


    Examples
    --------
    >>> # Typical initialization and basic usage
    >>> layer = Layer(soil="sand", top=1.3, bottom=-2.0)
    >>> thickness = layer.thickness


    Notes
    -----
    - The top level should always be higher than the bottom level
    - Can be empty, in case the top level is equal to the bottom
    - Is mainly used in constructing a SoilProfile object
    """

    soil: str
    top: float
    bottom: float

    @property
    def thickness(self) -> float:
        """The thicknes of the layer, derived from the top and bottom attributes of the class"""
        return self.top - self.bottom

    def is_empty(self) -> bool:
        """Method checking if the layer is 'empty' and with that faulty, derived from the top and bottom attributes of the class"""
        if self.top == self.bottom:
            print(f"{self} is empty")
            return True
        return False

    def has_top_above_bottom(self) -> bool:
        """Method checking is faulty, occuringwhen the bottom of the layer is above the top"""
        if self.top > self.bottom:
            return True
        print(f"In {self}, the top of the layer is below the bottom")
        return False


@dataclass
class SoilProfile:
    """
    Reperesents a soil profile.

    Used to make geotechnical calculations with.
    Has implemented methods to make changes to the layers attribute, namely:
    - change layer: change top or bottom level
    - remove layer: remove it from layers and fill the resulting gap (if requested)
    - add layer: add layer to the existing list

    Attributes
    ----------
    surface_level
        Top level of the soil profile. Should match with the top of the 1st layer
    layers
        Layers comprising the soil profile. Sorted from top to bottom. Has to be (at least) one. To be valid, adjacent layers should have equal top and bottom levels.
    bottom
        Bottom level of the soil profile. Should match with the bottom of the last layer
    based_on
        The CPT id this soil profile is derived from. None for manually created profiles.

    Examples
    --------
    >>> # Typical initialization and basic usage
    >>> surface_level = 2.3
    >>> bottom_level = -3.2
    >>> sand_layer = Layer(soil="sand", top=surface_level, bottom_level=-1.0)
    >>> clay_layer = Layer(soil="clay", top=-1.0, bottom=bottom_level)
    >>> soil_profile = SoilProfile(surface_level=surface_level, layers=[sand_layer, clay_layer], bottom=bottom_level)
    >>> # Change layer in the soil profile
    >>> soil_profile.change_layer(layer=sand_layer, new_bottom=-2.0)
    >>> new_layer = Layer(soil="silt", top=0.3, bottom=-0.7)
    >>> soil_profile.add_layer(new_layer=new_layer)

    Notes
    -----
    - The layers of the soil profile can be added, removed, . This should be done with care to make sure the soil profile is valid.
    - The layers input variable (at instantiation) should be sorted top to bottom layers, i.e. reverse relative to top or bottom level.
    - The layers input variable (at instantiation) should have matching tops and bottom, i.e. the bottom of the first layers should be equal to the bottom of the second layer and onwards through all layers.
    - The validity of an object can be assessed with the `validate` method.

    See Also
    --------
    RelatedClass : Brief relationship note
    """

    name: str
    surface_level: float  # m+NAP
    layers: list[Layer]
    bottom: float  # m+NAP
    based_on: str | None = (
        None  # CPT id this profile is derived from; None for manual profiles
    )

    # def __init__(self, name: str, surface_level: float, layers: list[Layer], bottom: float):
    #     """Creates a soil profile"""
    # self.name = name
    # self.surface_level = surface_level  # m+NAP
    # self.layers = layers
    # self.bottom = bottom  # m+NAP

    @property
    def soils(self) -> list[str]:
        return [layer.soil for layer in self.layers]

    def _change_layer_bounds(
        self,
        layer: Layer,
        new_top: float | None = None,
        new_bottom: float | None = None,
    ):
        """Changes the top and bottom boundaries of a given layer"""
        if new_top is None and new_bottom is None:
            raise ValueError(
                "A value should be provided for either the top or the bottom"
            )

        if new_top is not None:
            if new_top <= layer.bottom:
                raise ValueError(
                    f"The new top at {new_top} of {layer} should be above the existing bottom"
                )
            layer.top = new_top
        if new_bottom is not None:
            if new_bottom >= layer.top:
                raise ValueError(
                    f"The new bottom at {new_bottom} of {layer} should be below the existing top"
                )
            layer.bottom = new_bottom

    def _get_layer_idx(self, layer: Layer) -> int:
        """Based on a layer, get its index in the list of layers attribute: 'self.layers'"""
        for i, _layer in enumerate(self.layers):
            if _layer == layer:
                return i
        else:
            raise ValueError(
                f"Layer: {layer} not present in self.layers: {self.layers}"
            )

    def change_layer(
        self,
        layer: Layer,
        new_top: float | None = None,
        new_bottom: float | None = None,
    ):
        """Changes the boundaries of a given layer, and if required, also the layer above and below"""
        if not layer in self.layers:
            raise ValueError("The layer is not present in the soil profile")

        if new_top is None and new_bottom is None:
            raise ValueError("Either the top or bottom of the layer should be changed")

        # Change top and bottom of requested layer
        i = self._get_layer_idx(
            layer
        )  # Get layer in SoilProfile to change the correct object in memory
        self._change_layer_bounds(
            layer=self.layers[i], new_top=new_top, new_bottom=new_bottom
        )

        # If more than 1 layer is present, find the layers above and below and change their boundaries also
        if len(self.layers) != 1:
            if i == 0:  # If first layer -> only change layer below
                self._change_layer_bounds(layer=self.layers[i + 1], new_top=new_bottom)
            elif i == len(self.layers) - 1:  # If last layer -> only change layer above
                self._change_layer_bounds(layer=self.layers[i - 1], new_bottom=new_top)
            else:
                self._change_layer_bounds(layer=self.layers[i + 1], new_top=new_bottom)
                self._change_layer_bounds(layer=self.layers[i - 1], new_bottom=new_top)

    def remove_layer(self, layer: Layer, fill: bool = True):
        """Removes layers and fills the layers above and below if requested"""
        if not layer in self.layers:
            raise ValueError("The layer is not present in the soil profile")

        if len(self.layers) == 1:
            raise ValueError(
                "There is only one layer present in the soil profile. You cannot remove it!"
            )

        # Get the layer index
        idx = self._get_layer_idx(layer)

        # If the layers above and below should be filled, change their top and bottom
        # Do this before the layer is removed to preserve indices!
        if fill:
            if idx == 0:  # First layer, only change the layer below
                self._change_layer_bounds(layer=self.layers[idx + 1], new_top=layer.top)
            elif idx == len(self.layers) - 1:
                self._change_layer_bounds(
                    layer=self.layers[idx - 1], new_bottom=layer.bottom
                )
            else:
                middle = (layer.top + layer.bottom) / 2
                self._change_layer_bounds(layer=self.layers[idx + 1], new_top=middle)
                self._change_layer_bounds(layer=self.layers[idx - 1], new_bottom=middle)

        # Remove the layer as requested
        self.layers.pop(idx)

    def _fill(self) -> "SoilProfile":
        """
        TODO: This logic should be tested and further extended with more thought given to it in a later stage.

        Fills gaps or removes overlaps between adjacent layers by shifting boundaries to meet at the midpoint.
        Also ensures the top of the top layer matches surface_level and the bottom of the bottom layer matches bottom.
        """
        if len(self.layers) < 1:
            return self

        self.layers[0].top = self.surface_level
        self.layers[-1].bottom = self.bottom

        for layer1, layer2 in pairwise(self.layers):
            mid = (layer1.bottom + layer2.top) / 2
            layer1.bottom = mid
            layer2.top = mid

        return self

    def add_layer(self, new_layer: Layer):
        """Add a layer to the soil profile, change the boundaries of the top and bottom of the layers below"""
        if new_layer in self.layers:
            raise ValueError("The layer is already in the soil profile")

        # Check no layers are completely overwritten
        for existing_layer in self.layers:
            if (
                existing_layer.top <= new_layer.top
                and existing_layer.bottom >= new_layer.bottom
            ):
                raise ValueError(
                    "A layer is completely overwritten, this is (for now) not allowed!"
                )

        # Add layer
        self.layers.append(new_layer)
        self.layers.sort(
            key=lambda x: (x.top + x.bottom) / 2, reverse=True
        )  # sort based on middle of layer since top and bottoms of layers can be equal --> abritrary sort in this case!
        self.change_layer(
            new_layer, new_top=new_layer.top, new_bottom=new_layer.bottom
        )  # Hacky solution to reduce code

    def get_soil_at_level(self, level: float) -> str:
        if level > self.surface_level:
            raise ValueError("The requested level should be below the surface level")

        if level < self.bottom:
            raise ValueError(
                "The requested level should be above the bottom of the soil profile"
            )

        for layer in self.layers:
            if level == layer.top or level == layer.bottom:
                raise ValueError(
                    "You are requesting a soil layer at exactly the interface of two layers. This cannot be done."
                )
            if layer.top > level > layer.bottom:
                return layer.soil
        raise ValueError("Something unexpected went wrong, no soil could be found!")

    def _validate_no_holes(self) -> bool:
        """
        Checks that all layers in the soil profile have matching top and bottom, and that the surface level and bottom are matched.
        This method is implemented with the assumption the soil profile is sorted"""

        # Check surface level is equal to the top of the 1st layer
        if self.layers[0].top != self.surface_level:
            print(
                "The top of the 1st soil layer is not equal to the surface level. Both should match!"
            )  # TODO: add to proper logging later
            return False

        # Check bottom is equal to bottom of last layer
        if self.layers[-1].bottom != self.bottom:
            print(
                "The bottom of the last soil layer is not equal to the bottom of the soil profile. Both should match!"
            )  # TODO: add to proper logging later
            return False

        if len(self.layers) > 1:
            # Check the top and bottom of adjacent layers match
            for layer1, layer2 in pairwise(self.layers):
                if layer1.bottom != layer2.top:
                    print(
                        f"The bottom of {layer1} is not equal to the top of {layer2}. Both should match!"
                    )  # TODO: add to proper logging later
                    return False
        return True

    def _validate_sorting(self) -> bool:
        """Validate the soil layers are in the correct order"""
        if len(self.layers) > 1:
            for layer1, layer2 in pairwise(self.layers):
                if layer1.top <= layer2.top:
                    print(
                        f"The layers are not in the correct order: {layer1} comes after {layer2}"
                    )
                    return False
        return True

    def _validate_correct_layers(self) -> bool:
        """Validate the layers itself are correct, i.e. not empty, top above bottom, ..."""
        for layer in self.layers:
            if layer.is_empty():
                return False
            if not layer.has_top_above_bottom():
                return False
        return True

    def validate(self) -> bool:
        """Validates the soil profile is correct and useable"""
        if not self._validate_correct_layers():
            return False
        if not self._validate_sorting():
            return False
        if not self._validate_no_holes():
            return False
        return True


@dataclass
class SoilStresses:
    """
    Represents the stresses in a soil. Contains logic to calculate the stresses at every level.
    The initial input for the stresses is on layer boundaries and the phreatic surface.
    Other stresses are interpolated.
    """

    phreatic_level: float  # m+NAP
    levels: list[float]  # m+NAP
    total_stresses: list[float]  # kPa
    pore_water_pressure: list[float]  # kPa
    effective_stresses: list[float]  # kPa

    def __post_init__(self):
        # Validate depths are in descending order
        if any(l1 - l2 <= 0 for l1, l2 in pairwise(self.levels)):
            raise ValueError("The depths should be provided in descending order")

    @property
    def surface_level(self) -> float:
        return self.levels[0]

    @property
    def bottom_level(self) -> float:
        return self.levels[-1]

    def get_stresses_at_level(self, level: float) -> tuple[float, float, float]:
        """Calculates stresses at level, respectively total stress, pore water pressure and effective stress"""
        if level > self.surface_level:
            raise ValueError(
                f"The level: {level} m+NAP is above the surface level: {self.surface_level}"
            )
        if level < self.bottom_level:
            raise ValueError(
                f"The level: {level} m+NAP is below the bottom level: {self.bottom_level}"
            )

        # If dpeth is exactly on layer boundary
        if level in self.levels:
            idx = self.levels.index(level)
            return (
                self.total_stresses[idx],
                self.pore_water_pressure[idx],
                self.effective_stresses[idx],
            )

        for idx_top, (l1, l2) in enumerate(pairwise(self.levels)):
            if l2 < level < l1:
                # Get deltas over layer
                delta_total_stress = (
                    self.total_stresses[idx_top] - self.total_stresses[idx_top + 1]
                )
                delta_pwp = (
                    self.pore_water_pressure[idx_top]
                    - self.pore_water_pressure[idx_top + 1]
                )
                delta_effective_stress = (
                    self.effective_stresses[idx_top]
                    - self.effective_stresses[idx_top + 1]
                )
                delta_depth = l1 - level
                depth_ratio_layer = delta_depth / (l2 - l1)

                # Get stresses at level
                total_stress = (
                    self.total_stresses[idx_top]
                    + depth_ratio_layer * delta_total_stress
                )
                pwp = self.pore_water_pressure[idx_top] + depth_ratio_layer * delta_pwp
                effective_stress = (
                    self.effective_stresses[idx_top]
                    + depth_ratio_layer * delta_effective_stress
                )

                return total_stress, pwp, effective_stress

        raise ValueError("Something unknown went wrong in determining the stresses!")


def calculate_stresses(
    soil_profile: SoilProfile,
    water_level: float,
    soil_weights: dict[str, tuple[float, float]],
) -> SoilStresses:
    """Calculates stresses: total stresses, porewater pressure and effective stress. The soil weights should be provided in a dictionary as follows: {'zand': (18, 20), ...} with 18 and 20 being the natural and saturated volumetric weights respectively."""

    # Check all soils are in the parameter table
    all_soils = [l.soil for l in soil_profile.layers]
    for soil in all_soils:
        if soil not in soil_weights:
            raise ValueError(
                f"The soil: {soil} is not in the soil_weights input: {soil_weights}"
            )

    # Calculate total stress at surface level -> when water level is above the surface level
    if water_level > soil_profile.surface_level:
        total_stress_surface_level = (water_level - soil_profile.surface_level) * 10
    else:
        total_stress_surface_level = 0

    # Calculate total stress and pwp in soil
    total_stress: list[float] = [total_stress_surface_level]
    levels: list[float] = [soil_profile.surface_level]
    pwp: list[float] = [total_stress_surface_level]
    total_stress_at_depth = total_stress_surface_level

    for layer in soil_profile.layers:
        volumetric_weight_nat, volumetric_weight_sat = soil_weights[layer.soil]
        if layer.bottom < water_level < layer.top:
            # Get how deep water is into the soil layer
            depth_top_layer_to_water = layer.top - water_level

            # Add stresses until water level
            total_stress_at_depth += depth_top_layer_to_water * volumetric_weight_nat
            total_stress.append(total_stress_at_depth)
            levels.append(water_level)
            pwp.append(0)

            # Add stresses from water level until bottom of layer
            depth_water_to_bottom_layer = water_level - layer.bottom
            total_stress_at_depth += depth_water_to_bottom_layer * volumetric_weight_sat
            total_stress.append(total_stress_at_depth)
            levels.append(layer.bottom)
            pwp.append(depth_top_layer_to_water * 10)

        elif water_level >= layer.top:
            total_stress_at_depth += layer.thickness * volumetric_weight_sat
            total_stress.append(total_stress_at_depth)
            levels.append(layer.bottom)
            pwp.append((water_level - layer.bottom) * 10)

        else:  # water_level <= layer.bottom:
            total_stress_at_depth += layer.thickness * volumetric_weight_nat
            total_stress.append(total_stress_at_depth)
            levels.append(layer.bottom)
            pwp.append(0)

    # Validation all data is taken at same levels
    if len(total_stress) != len(levels) != len(pwp):
        raise ValueError(
            "The length of the levels, total stress and pwp should be equal. Something horrible went wrong!"
        )

    # Calculate effective stresses from total stresses and pwp
    effective_stress: list[float] = [sigv - u for sigv, u in zip(total_stress, pwp)]

    return SoilStresses(
        phreatic_level=water_level,
        levels=levels,
        total_stresses=total_stress,
        pore_water_pressure=pwp,
        effective_stresses=effective_stress,
    )
