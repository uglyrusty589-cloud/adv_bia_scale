"""Config flow for Advanced BIA Scale integration."""
from __future__ import annotations

import re
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.const import CONF_MAC, CONF_NAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
)

from .const import (
    CONF_ACTIVITY_LEVEL,
    CONF_BIRTH_DATE,
    CONF_GENDER,
    CONF_HEIGHT,
    CONF_PROFILE_NAME,
    CONF_USERS,
    CONF_WEIGHT_MAX,
    CONF_WEIGHT_MIN,
    DOMAIN,
    GENDER_OPTIONS,
    ACTIVITY_OPTIONS,
    MANUFACTURER_ID_OKOK,
)


# --- Validation helpers ------------------------------------------------------


def _validate_mac(value: str) -> str:
    """Validate and normalize MAC address."""
    value = value.strip().upper()
    if not re.match(r"^([0-9A-F]{2}[:-]){5}[0-9A-F]{2}$", value):
        raise vol.Invalid("invalid_mac")
    return value.replace("-", ":")


def _validate_date(value: str) -> str:
    """Validate DD.MM.YYYY format."""
    value = value.strip()
    if not re.match(r"^(0[1-9]|[12]\d|3[01])\.(0[1-9]|1[0-2])\.(19|20)\d{2}$", value):
        raise vol.Invalid("invalid_date")
    return value


def _validate_profile_name(value: str) -> str:
    value = value.strip()
    if not value:
        raise vol.Invalid("invalid_profile_name")
    return value


# --- Shared schema builders --------------------------------------------------


def _user_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    """Return schema for a single user profile."""
    if defaults is None:
        defaults = {}
    return vol.Schema(
        {
            vol.Required(
                CONF_PROFILE_NAME,
                default=defaults.get(CONF_PROFILE_NAME, ""),
            ): TextSelector(TextSelectorConfig(multiline=False)),
            vol.Required(
                CONF_HEIGHT,
                default=defaults.get(CONF_HEIGHT, 170),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=50,
                    max=250,
                    step=1,
                    unit_of_measurement="см",
                    mode=NumberSelectorMode.BOX,
                )
            ),
            vol.Required(
                CONF_BIRTH_DATE,
                default=defaults.get(CONF_BIRTH_DATE, "20.05.1990"),
            ): TextSelector(TextSelectorConfig(multiline=False)),
            vol.Required(
                CONF_GENDER,
                default=defaults.get(CONF_GENDER, GENDER_OPTIONS[0]["value"]),
            ): SelectSelector(
                SelectSelectorConfig(
                    options=[opt["value"] for opt in GENDER_OPTIONS],
                    translation_key=CONF_GENDER,
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Required(
                CONF_ACTIVITY_LEVEL,
                default=defaults.get(CONF_ACTIVITY_LEVEL, "sedentary"),
            ): SelectSelector(
                SelectSelectorConfig(
                    options=["sedentary", "light", "moderate", "active", "very_active"],
                    translation_key=CONF_ACTIVITY_LEVEL,
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Required(
                CONF_WEIGHT_MIN,
                default=defaults.get(CONF_WEIGHT_MIN, 60.0),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=20,
                    max=300,
                    step=0.1,
                    unit_of_measurement="кг",
                    mode=NumberSelectorMode.BOX,
                )
            ),
            vol.Required(
                CONF_WEIGHT_MAX,
                default=defaults.get(CONF_WEIGHT_MAX, 90.0),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=20,
                    max=300,
                    step=0.1,
                    unit_of_measurement="кг",
                    mode=NumberSelectorMode.BOX,
                )
            ),
        }
    )


def _validate_user_data(user_data: dict[str, Any]) -> dict[str, str]:
    """Validate user profile dict and return error dict (empty if OK)."""
    errors: dict[str, str] = {}
    height = user_data.get(CONF_HEIGHT)
    if height is not None and not (50 <= height <= 250):
        errors[CONF_HEIGHT] = "invalid_height"

    try:
        _validate_date(user_data.get(CONF_BIRTH_DATE, ""))
    except vol.Invalid:
        errors[CONF_BIRTH_DATE] = "invalid_date"

    try:
        _validate_profile_name(user_data.get(CONF_PROFILE_NAME, ""))
    except vol.Invalid:
        errors[CONF_PROFILE_NAME] = "invalid_profile_name"

    w_min = float(user_data.get(CONF_WEIGHT_MIN, 0))
    w_max = float(user_data.get(CONF_WEIGHT_MAX, 0))
    if w_min < 20 or w_max > 300 or w_min >= w_max:
        errors[CONF_WEIGHT_MIN] = "invalid_weight_range"
        errors[CONF_WEIGHT_MAX] = "invalid_weight_range"

    return errors


# ============================================================================
#  Config Flow
# ============================================================================

class AdvBiaScaleConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Advanced BIA Scale."""

    VERSION = 2

    def __init__(self) -> None:
        """Initialize flow."""
        self._discovered_mac: str | None = None
        self._users_list: list[dict[str, Any]] = []
        self._device_name: str = "BIA Весы"
        self._device_mac: str = ""

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> FlowResult:
        """Handle bluetooth discovery."""
        if discovery_info.manufacturer_id != MANUFACTURER_ID_OKOK:
            return self.async_abort(reason="not_supported")

        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()

        self._discovered_mac = discovery_info.address
        return await self.async_step_user()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step: device info + first profile."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate MAC
            try:
                mac = _validate_mac(user_input[CONF_MAC])
            except vol.Invalid:
                errors[CONF_MAC] = "invalid_mac"
            else:
                await self.async_set_unique_id(mac)
                self._abort_if_unique_id_configured()
                self._device_mac = mac

            self._device_name = user_input.get(CONF_NAME, "BIA Весы")

            # Extract profile fields from combined user input
            profile_data = {
                CONF_PROFILE_NAME: user_input[CONF_PROFILE_NAME],
                CONF_HEIGHT: user_input[CONF_HEIGHT],
                CONF_BIRTH_DATE: user_input[CONF_BIRTH_DATE],
                CONF_GENDER: user_input[CONF_GENDER],
                CONF_ACTIVITY_LEVEL: user_input[CONF_ACTIVITY_LEVEL],
                CONF_WEIGHT_MIN: float(user_input[CONF_WEIGHT_MIN]),
                CONF_WEIGHT_MAX: float(user_input[CONF_WEIGHT_MAX]),
            }

            profile_errors = _validate_user_data(profile_data)
            errors.update(profile_errors)

            if not errors:
                self._users_list.append(profile_data)
                return await self.async_step_profiles()

        # Build combined schema on one page for first user
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_MAC,
                    default=self._discovered_mac or "",
                ): TextSelector(TextSelectorConfig(multiline=False)),
                vol.Required(
                    CONF_NAME,
                    default=user_input.get(CONF_NAME, self._device_name)
                    if user_input
                    else self._device_name,
                ): TextSelector(TextSelectorConfig(multiline=False)),
                vol.Required(
                    CONF_PROFILE_NAME,
                    default=user_input.get(CONF_PROFILE_NAME, "")
                    if user_input
                    else "",
                ): TextSelector(TextSelectorConfig(multiline=False)),
                vol.Required(
                    CONF_HEIGHT,
                    default=user_input.get(CONF_HEIGHT, 170)
                    if user_input
                    else 170,
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=50,
                        max=250,
                        step=1,
                        unit_of_measurement="см",
                        mode=NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    CONF_BIRTH_DATE,
                    default=user_input.get(CONF_BIRTH_DATE, "20.05.1990")
                    if user_input
                    else "20.05.1990",
                ): TextSelector(TextSelectorConfig(multiline=False)),
                vol.Required(
                    CONF_GENDER,
                    default=user_input.get(CONF_GENDER, GENDER_OPTIONS[0]["value"])
                    if user_input
                    else GENDER_OPTIONS[0]["value"],
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=[opt["value"] for opt in GENDER_OPTIONS],
                        translation_key=CONF_GENDER,
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(
                    CONF_ACTIVITY_LEVEL,
                    default=user_input.get(CONF_ACTIVITY_LEVEL, "sedentary")
                    if user_input
                    else "sedentary",
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=["sedentary", "light", "moderate", "active", "very_active"],
                        translation_key=CONF_ACTIVITY_LEVEL,
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(
                    CONF_WEIGHT_MIN,
                    default=user_input.get(CONF_WEIGHT_MIN, 60.0)
                    if user_input
                    else 60.0,
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=20,
                        max=300,
                        step=0.1,
                        unit_of_measurement="кг",
                        mode=NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    CONF_WEIGHT_MAX,
                    default=user_input.get(CONF_WEIGHT_MAX, 90.0)
                    if user_input
                    else 90.0,
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=20,
                        max=300,
                        step=0.1,
                        unit_of_measurement="кг",
                        mode=NumberSelectorMode.BOX,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "device_name": "BIA Весы",
            },
        )

    async def async_step_add_profile(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle adding an extra profile."""
        errors: dict[str, str] = {}

        if user_input is not None:
            profile_data = {
                CONF_PROFILE_NAME: user_input[CONF_PROFILE_NAME],
                CONF_HEIGHT: user_input[CONF_HEIGHT],
                CONF_BIRTH_DATE: user_input[CONF_BIRTH_DATE],
                CONF_GENDER: user_input[CONF_GENDER],
                CONF_ACTIVITY_LEVEL: user_input[CONF_ACTIVITY_LEVEL],
                CONF_WEIGHT_MIN: float(user_input[CONF_WEIGHT_MIN]),
                CONF_WEIGHT_MAX: float(user_input[CONF_WEIGHT_MAX]),
            }

            errors = _validate_user_data(profile_data)
            if not errors:
                self._users_list.append(profile_data)
                return await self.async_step_profiles()

        return self.async_show_form(
            step_id="add_profile",
            data_schema=_user_schema(user_input if user_input else None),
            errors=errors,
        )

    async def async_step_profiles(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Show list of added profiles and allow more or finish."""
        return self.async_show_menu(
            step_id="profiles",
            menu_options=["add_profile", "finish"],
            description_placeholders={
                "profiles": "\n".join(
                    f"• {p[CONF_PROFILE_NAME]} ({p[CONF_HEIGHT]} см)"
                    for p in self._users_list
                )
                or "Нет добавленных профилей",
            },
        )

    async def async_step_finish(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Finalize config entry creation."""
        if not self._users_list:
            return await self.async_step_profiles()

        return self.async_create_entry(
            title=self._device_name,
            data={
                CONF_MAC: self._device_mac,
                CONF_NAME: self._device_name,
                CONF_USERS: self._users_list,
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> AdvBiaScaleOptionsFlow:
        """Get the options flow for this handler."""
        return AdvBiaScaleOptionsFlow(config_entry)


# ============================================================================
#  Options Flow
# ============================================================================

class AdvBiaScaleOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Advanced BIA Scale."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.entry = config_entry
        self._users_list: list[dict[str, Any]] = list(
            config_entry.data.get(CONF_USERS, [])
        )
        self._edit_index: int | None = None

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            action = user_input.get("action")
            if action == "add_profile":
                return await self.async_step_add_profile()
            if isinstance(action, str):
                if action.startswith("edit_"):
                    idx = int(action.split("_", 1)[1])
                    self._edit_index = idx
                    return await self.async_step_edit_profile()
                if action.startswith("delete_"):
                    idx = int(action.split("_", 1)[1])
                    self._edit_index = idx
                    return await self.async_step_confirm_delete()

        # Build selector options: one per user + add button
        options: list[dict[str, str]] = []
        for idx, user in enumerate(self._users_list):
            options.append(
                {
                    "value": f"edit_{idx}",
                    "label": f"Редактировать {user[CONF_PROFILE_NAME]}",
                }
            )
            options.append(
                {
                    "value": f"delete_{idx}",
                    "label": f"Удалить {user[CONF_PROFILE_NAME]}",
                }
            )
        options.append(
            {
                "value": "add_profile",
                "label": "Добавить профиль",
            }
        )

        schema = vol.Schema(
            {
                vol.Required("action"): SelectSelector(
                    SelectSelectorConfig(
                        options=[opt["value"] for opt in options],
                        translation_key="options_action",
                        mode=SelectSelectorMode.LIST,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "profiles": "\n".join(
                    f"• {p[CONF_PROFILE_NAME]} ({p[CONF_HEIGHT]} см, {p[CONF_WEIGHT_MIN]}–{p[CONF_WEIGHT_MAX]} кг)"
                    for p in self._users_list
                )
                or "Нет добавленных профилей",
            },
        )

    async def async_step_edit_profile(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Edit selected profile."""
        errors: dict[str, str] = {}
        idx = self._edit_index
        if idx is None or idx < 0 or idx >= len(self._users_list):
            return await self.async_step_init()

        user = self._users_list[idx]

        if user_input is not None:
            updated = {
                CONF_PROFILE_NAME: user_input[CONF_PROFILE_NAME],
                CONF_HEIGHT: user_input[CONF_HEIGHT],
                CONF_BIRTH_DATE: user_input[CONF_BIRTH_DATE],
                CONF_GENDER: user_input[CONF_GENDER],
                CONF_ACTIVITY_LEVEL: user_input[CONF_ACTIVITY_LEVEL],
                CONF_WEIGHT_MIN: float(user_input[CONF_WEIGHT_MIN]),
                CONF_WEIGHT_MAX: float(user_input[CONF_WEIGHT_MAX]),
            }
            errors = _validate_user_data(updated)
            if not errors:
                self._users_list[idx] = updated
                return await self._update_entry_and_finish()

        return self.async_show_form(
            step_id="edit_profile",
            data_schema=_user_schema(user),
            errors=errors,
        )

    async def async_step_add_profile(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add a new profile in options flow."""
        errors: dict[str, str] = {}

        if user_input is not None:
            profile_data = {
                CONF_PROFILE_NAME: user_input[CONF_PROFILE_NAME],
                CONF_HEIGHT: user_input[CONF_HEIGHT],
                CONF_BIRTH_DATE: user_input[CONF_BIRTH_DATE],
                CONF_GENDER: user_input[CONF_GENDER],
                CONF_ACTIVITY_LEVEL: user_input[CONF_ACTIVITY_LEVEL],
                CONF_WEIGHT_MIN: float(user_input[CONF_WEIGHT_MIN]),
                CONF_WEIGHT_MAX: float(user_input[CONF_WEIGHT_MAX]),
            }
            errors = _validate_user_data(profile_data)
            if not errors:
                self._users_list.append(profile_data)
                return await self._update_entry_and_finish()

        return self.async_show_form(
            step_id="add_profile",
            data_schema=_user_schema(user_input if user_input else None),
            errors=errors,
        )

    async def async_step_confirm_delete(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm deletion of a profile."""
        idx = self._edit_index
        if idx is None or idx < 0 or idx >= len(self._users_list):
            return await self.async_step_init()

        if user_input is not None:
            if user_input.get("confirm"):
                del self._users_list[idx]
                return await self._update_entry_and_finish()
            return await self.async_step_init()

        schema = vol.Schema(
            {
                vol.Required("confirm", default=False): bool,
            }
        )

        profile_name = self._users_list[idx][CONF_PROFILE_NAME]
        return self.async_show_form(
            step_id="confirm_delete",
            data_schema=schema,
            description_placeholders={
                "profile_name": profile_name,
            },
        )

    async def _update_entry_and_finish(self) -> FlowResult:
        """Update config entry data with modified users list."""
        data = {**self.entry.data, CONF_USERS: self._users_list}
        self.hass.config_entries.async_update_entry(self.entry, data=data)
        await self.hass.config_entries.async_reload(self.entry.entry_id)
        return self.async_create_entry(title="", data={})
