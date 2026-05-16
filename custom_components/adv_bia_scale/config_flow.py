"""Config flow для интеграции BIA Весы."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_MAC, CONF_NAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    DOMAIN,
    CONF_HEIGHT,
    CONF_AGE,
    CONF_GENDER,
    CONF_ACTIVITY_LEVEL,
    ACTIVITY_MULTIPLIERS,
)

_LOGGER = logging.getLogger(__name__)

GENDER_OPTIONS = {"male": "Мужской", "female": "Женский"}
ACTIVITY_OPTIONS = {
    "sedentary": "Сидячий (1.2)",
    "light": "Малая активность (1.375)",
    "moderate": "Умеренная активность (1.55)",
    "active": "Активный (1.725)",
    "very_active": "Очень активный (1.9)",
}


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
                age = int(user_input.get(CONF_AGE, 30))
                if not (50 <= height <= 250):
                    errors[CONF_HEIGHT] = "invalid_height"
                if not (5 <= age <= 120):
                    errors[CONF_AGE] = "invalid_age"
            except (ValueError, TypeError):
                errors["base"] = "invalid_input"

            if not errors:
                return self.async_create_entry(
                    title=user_input.get(CONF_NAME, "BIA Весы"),
                    data={
                        CONF_MAC: mac,
                        CONF_NAME: user_input.get(CONF_NAME, "BIA Весы"),
                        CONF_HEIGHT: height,
                        CONF_AGE: age,
                        CONF_GENDER: user_input.get(CONF_GENDER, "male"),
                        CONF_ACTIVITY_LEVEL: user_input.get(CONF_ACTIVITY_LEVEL, "moderate"),
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_MAC, default=""): str,
                    vol.Required(CONF_NAME, default="BIA Весы"): str,
                    vol.Required(CONF_HEIGHT, default=175): vol.All(
                        vol.Coerce(int), vol.Range(min=50, max=250)
                    ),
                    vol.Required(CONF_AGE, default=30): vol.All(
                        vol.Coerce(int), vol.Range(min=5, max=120)
                    ),
                    vol.Required(CONF_GENDER, default="male"): vol.In(
                        list(GENDER_OPTIONS.keys())
                    ),
                    vol.Required(CONF_ACTIVITY_LEVEL, default="moderate"): vol.In(
                        list(ACTIVITY_OPTIONS.keys())
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
        return AdvBiaScaleOptionsFlow(config_entry)


class AdvBiaScaleOptionsFlow(config_entries.OptionsFlow):
    """Настройки профиля."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Инициализация."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Изменение профиля."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                height = int(user_input.get(CONF_HEIGHT, 175))
                age = int(user_input.get(CONF_AGE, 30))
                if not (50 <= height <= 250):
                    errors[CONF_HEIGHT] = "invalid_height"
                if not (5 <= age <= 120):
                    errors[CONF_AGE] = "invalid_age"
            except (ValueError, TypeError):
                errors["base"] = "invalid_input"

            if not errors:
                return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_HEIGHT,
                        default=self.config_entry.data.get(CONF_HEIGHT, 175),
                    ): vol.All(vol.Coerce(int), vol.Range(min=50, max=250)),
                    vol.Required(
                        CONF_AGE,
                        default=self.config_entry.data.get(CONF_AGE, 30),
                    ): vol.All(vol.Coerce(int), vol.Range(min=5, max=120)),
                    vol.Required(
                        CONF_ACTIVITY_LEVEL,
                        default=self.config_entry.data.get(CONF_ACTIVITY_LEVEL, "moderate"),
                    ): vol.In(list(ACTIVITY_OPTIONS.keys())),
                }
            ),
            errors=errors,
        )