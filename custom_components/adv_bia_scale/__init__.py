"""The Advanced BIA Scale integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import (
    DOMAIN,
    CONF_USERS,
    CONF_PROFILE_NAME,
    CONF_HEIGHT,
    CONF_BIRTH_DATE,
    CONF_GENDER,
    CONF_ACTIVITY_LEVEL,
    CONF_WEIGHT_MIN,
    CONF_WEIGHT_MAX,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR]


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate old config entry to new format."""
    if entry.version == 1:
        _LOGGER.info("Migrating adv_bia_scale entry '%s' from v1 to v2", entry.entry_id)
        # Convert old single-profile data to new multi-profile format
        old_data = dict(entry.data)
        user_profile = {
            CONF_PROFILE_NAME: old_data.get("name", "Пользователь"),
            CONF_HEIGHT: int(old_data.get(CONF_HEIGHT, 175)),
            CONF_BIRTH_DATE: old_data.get(CONF_BIRTH_DATE, "20.05.1990"),
            CONF_GENDER: old_data.get(CONF_GENDER, "male"),
            CONF_ACTIVITY_LEVEL: old_data.get(CONF_ACTIVITY_LEVEL, "moderate"),
            CONF_WEIGHT_MIN: old_data.get(CONF_WEIGHT_MIN, 50.0),
            CONF_WEIGHT_MAX: old_data.get(CONF_WEIGHT_MAX, 120.0),
        }
        new_data = {
            "mac": old_data.get("mac", ""),
            "name": old_data.get("name", "BIA Весы"),
            CONF_USERS: [user_profile],
        }
        hass.config_entries.async_update_entry(
            entry,
            data=new_data,
            version=2,
            minor_version=0,
        )
        _LOGGER.info(
            "Migration complete: created user profile '%s' with weight range %.1f–%.1f kg",
            user_profile[CONF_PROFILE_NAME],
            user_profile[CONF_WEIGHT_MIN],
            user_profile[CONF_WEIGHT_MAX],
        )
    return True


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Advanced BIA Scale component."""
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Advanced BIA Scale from a config entry."""
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = entry.data
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id + "_coordinator")
    if coordinator:
        await coordinator.async_shutdown()

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        domain_data = hass.data.get(DOMAIN, {})
        domain_data.pop(entry.entry_id, None)
        domain_data.pop(entry.entry_id + "_coordinator", None)
    return unload_ok
