"""Config flow для интеграции OKOK ADV BIA Scale."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_MAC, CONF_NAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectOptionDict,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
)

from .const import (
    DOMAIN,
    CONF_HEIGHT,
    CONF_BIRTH_DATE,
    CONF_GENDER,
    CONF_ACTIVITY_LEVEL,
)

_LOGGER = logging.getLogger(__name__)

GENDER_OPTIONS: list[SelectOptionDict] = [
    {"value": "male", "label": "Мужской"},
    {"value": "female", "label": "Женский"},
]

ACTIVITY_OPTIONS: list[SelectOptionDict] = [
    {"value": "sedentary", "label": "Сидячий образ жизни (×1.2)"},
    {"value": "light", "label": "Лёгкая активность (×1.375)"},
    {"value": "moderate", "label": "Умеренная активность (×1.55)"},
    {"value": "active", "label": "Высокая активность (×1.725)"},
    {"value": "very_active", "label": "Очень высокая активность (×1.9)"},
]


class AdvBiaScaleConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Настройка BIA Весов."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Ручная настройка."""
        errors: dict[str, str] = {}

        if user_input is not None:
            mac = user_input.get(CONF_MAC, "")
            if mac:
                await self.async_set_unique_id(mac)
                self._abort_if_unique_id_configured()

            try:
                height = int(user_input.get(CONF_HEIGHT, 175))
                birth_date = user_input.get(CONF_BIRTH_DATE, "").strip()
                if not (50 <= height <= 250):
                    errors[CONF_HEIGHT] = "invalid_height"
                if not birth_date:
                    errors[CONF_BIRTH_DATE] = "invalid_date"
            except (ValueError, TypeError):
                errors["base"] = "invalid_input"

            if not errors:
                return self.async_create_entry(
                    title=user_input.get(CONF_NAME, "BIA Весы"),
                    data={
                        CONF_MAC: mac,
                        CONF_NAME: user_input.get(CONF_NAME, "BIA Весы"),
                        CONF_HEIGHT: height,
                        CONF_BIRTH_DATE: birth_date,
                        CONF_GENDER: user_input.get(CONF_GENDER, "male"),
                        CONF_ACTIVITY_LEVEL: user_input.get(
                            CONF_ACTIVITY_LEVEL, "moderate"
                        ),
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_MAC, default=""): str,
                    vol.Required(CONF_NAME, default=""): str,
                    vol.Required(CONF_HEIGHT, default=175): NumberSelector(
                        NumberSelectorConfig(
                            min=50,
                            max=250,
                            step=1,
                            unit_of_measurement="см",
                            mode=NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Required(CONF_BIRTH_DATE, default="20.05.1990"): TextSelector(
                        TextSelectorConfig(multiline=False)
                    ),
                    vol.Required(CONF_GENDER, default="male"): SelectSelector(
                        SelectSelectorConfig(
                            options=GENDER_OPTIONS,
                            mode="dropdown",
                        )
                    ),
                    vol.Required(CONF_ACTIVITY_LEVEL, default="moderate"): SelectSelector(
                        SelectSelectorConfig(
                            options=ACTIVITY_OPTIONS,
                            mode="dropdown",
                        )
                    ),
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> AdvBiaScaleOptionsFlow:
        """Настройки."""
        return AdvBiaScaleOptionsFlow()


class AdvBiaScaleOptionsFlow(config_entries.OptionsFlow):
    """Настройки профиля."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Изменение профиля."""
        if user_input is not None:
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data={**self.config_entry.data, **user_input},
            )
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            return self.async_create_entry(title="", data={})

        data = self.config_entry.data
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_HEIGHT,
                        default=data.get(CONF_HEIGHT, 175),
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
                        default=data.get(CONF_BIRTH_DATE, "20.05.1990"),
                    ): TextSelector(
                        TextSelectorConfig(multiline=False)
                    ),
                    vol.Required(
                        CONF_GENDER,
                        default=data.get(CONF_GENDER, "male"),
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=GENDER_OPTIONS,
                            mode="dropdown",
                        )
                    ),
                    vol.Required(
                        CONF_ACTIVITY_LEVEL,
                        default=data.get(CONF_ACTIVITY_LEVEL, "moderate"),
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=ACTIVITY_OPTIONS,
                            mode="dropdown",
                        )
                    ),
                }
            ),
        )
