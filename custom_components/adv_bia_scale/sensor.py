"""Пассивный BLE-листенер и вычислитель BIA метрик."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, Callable

from homeassistant.components.bluetooth import (
    BluetoothScanningMode,
    async_register_callback,
)
from homeassistant.components.bluetooth.models import BluetoothServiceInfoBleak
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import CONF_MAC, CONF_NAME
from homeassistant.core import HomeAssistant, callback as ha_callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import (
    DOMAIN,
    SENSOR_TYPES,
    SENSOR_WEIGHT,
    SENSOR_IMPEDANCE,
    SENSOR_BMI,
    SENSOR_BODY_FAT,
    SENSOR_MUSCLE_MASS,
    SENSOR_WATER,
    SENSOR_BONE_MASS,
    SENSOR_VISCERAL_FAT,
    SENSOR_BMR,
    SENSOR_METABOLIC_AGE,
    SENSOR_BODY_TYPE,
    SENSOR_PROTEIN,
    SENSOR_FAT_FREE_MASS,
    SENSOR_SUBCUTANEOUS_FAT,
    SENSOR_HEART_RATE,
    CONF_HEIGHT,
    CONF_BIRTH_DATE,
    CONF_GENDER,
    CONF_ACTIVITY_LEVEL,
    MANUFACTURER_ID_OKOK,
    calculate_bmi,
    calculate_body_fat,
    calculate_muscle_mass,
    calculate_water,
    calculate_bone_mass,
    calculate_visceral_fat,
    calculate_bmr,
    calculate_metabolic_age,
    get_body_type,
    get_body_type_label,
    calculate_protein,
    calculate_subcutaneous_fat,
    calculate_fat_free_mass,
    calculate_tdee,
    calculate_age,
)
from .parser import parse_okok_advertisement

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=30)


class BiaScaleCoordinator(DataUpdateCoordinator):
    """Координатор слушает BLE ADV и считает BIA."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry,
        mac_address: str,
    ) -> None:
        """Инициализация."""
        self.entry = entry
        self.mac_address = mac_address.upper()
        self._cancel_callback: Callable[[], None] | None = None
        self._latest_raw: dict[str, Any] = {}

        super().__init__(
            hass,
            _LOGGER,
            name=f"BIA Весы {mac_address}",
            update_interval=None,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Вернуть последние данные."""
        return self._latest_raw

    @ha_callback
    def _async_handle_bluetooth_event(
        self, service_info: BluetoothServiceInfoBleak, change: Any
    ) -> None:
        """Обработка BLE ADV."""
        _LOGGER.debug(
            "BLE event from %s (mfg: %s)",
            service_info.address,
            service_info.manufacturer_data,
        )
        if service_info.address.upper() != self.mac_address:
            return

        mfg_data = service_info.manufacturer_data
        if MANUFACTURER_ID_OKOK not in mfg_data:
            _LOGGER.debug("Manufacturer %s not in data %s", MANUFACTURER_ID_OKOK, mfg_data)
            return

        raw_bytes = mfg_data[MANUFACTURER_ID_OKOK]
        parsed = parse_okok_advertisement(raw_bytes)
        _LOGGER.debug("Parsed: %s", parsed)
        if not parsed:
            return

        self._latest_raw = parsed
        self.async_set_updated_data(parsed)

    async def async_start(self) -> None:
        """Запустить слушание BLE."""
        try:
            self._cancel_callback = async_register_callback(
                self.hass,
                self._async_handle_bluetooth_event,
                {"address": self.mac_address},
                BluetoothScanningMode.PASSIVE,
            )
            _LOGGER.info("Registered BLE callback for %s", self.mac_address)
        except Exception as exc:
            _LOGGER.error("Ошибка регистрации BLE: %s", exc)
            raise

    async def async_shutdown(self) -> None:
        """Остановить слушание."""
        if self._cancel_callback:
            self._cancel_callback()
            self._cancel_callback = None

    def compute_metrics(self) -> dict[str, Any]:
        """Вычислить все BIA метрики."""
        data = self._latest_raw
        if not data or "weight_kg" not in data:
            return {}

        weight = data.get("weight_kg", 0)
        impedance = data.get("impedance", 0)
        hr = data.get("heart_rate", 0)

        # If only impedance data (no stabilized weight), return partial data
        if not weight or weight <= 0:
            _LOGGER.debug("No weight data yet (weight=%.1f), returning impedance only", weight)
            return {
                SENSOR_WEIGHT: 0,
                SENSOR_IMPEDANCE: impedance,
            }

        height = self.entry.data.get(CONF_HEIGHT, 175)
        birth_date = self.entry.data.get(CONF_BIRTH_DATE)
        if birth_date:
            age = calculate_age(birth_date)
        else:
            # Fallback для старых записей (legacy age field или birth_day/month/year)
            age = self.entry.data.get("age", 30)
        gender = self.entry.data.get(CONF_GENDER, "male")
        activity = self.entry.data.get(CONF_ACTIVITY_LEVEL, "moderate")

        bmi = calculate_bmi(weight, height)
        body_fat = calculate_body_fat(weight, impedance, age, gender, height)
        muscle = calculate_muscle_mass(weight, body_fat)
        water = calculate_water(weight, body_fat, gender)
        bone = calculate_bone_mass(weight, height, gender)
        visceral = calculate_visceral_fat(bmi, age, gender)
        bmr = calculate_bmr(weight, height, age, gender)
        tdee = calculate_tdee(bmr, activity)
        meta_age = calculate_metabolic_age(weight, height, age, gender, body_fat)
        body_type = get_body_type(bmi, body_fat, gender)
        protein = calculate_protein(weight, body_fat, muscle)
        subcut = calculate_subcutaneous_fat(body_fat, visceral)
        ffm = calculate_fat_free_mass(weight, body_fat)

        return {
            SENSOR_WEIGHT: weight,
            SENSOR_IMPEDANCE: impedance,
            SENSOR_BMI: bmi,
            SENSOR_BODY_FAT: body_fat,
            SENSOR_MUSCLE_MASS: muscle,
            SENSOR_WATER: water,
            SENSOR_BONE_MASS: bone,
            SENSOR_VISCERAL_FAT: visceral,
            SENSOR_BMR: bmr,
            SENSOR_METABOLIC_AGE: meta_age,
            SENSOR_BODY_TYPE: get_body_type_label(body_type),
            SENSOR_PROTEIN: protein,
            SENSOR_SUBCUTANEOUS_FAT: subcut,
            SENSOR_FAT_FREE_MASS: ffm,
            SENSOR_HEART_RATE: hr,
            "tdee": tdee,
            "status": data.get("status"),
            "raw_hex": data.get("raw_hex"),
        }


class BiaScaleSensor(CoordinatorEntity, SensorEntity):
    """Сенсор BIA Весов."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: BiaScaleCoordinator,
        entry,
        sensor_type: str,
        device_name: str,
    ) -> None:
        """Инициализация."""
        super().__init__(coordinator)
        self._sensor_type = sensor_type
        self._entry = entry
        self._device_name = device_name
        self._attr_unique_id = f"{entry.entry_id}_{sensor_type}"

        info = SENSOR_TYPES[sensor_type]
        self._attr_name = info["name"]
        self._attr_native_unit_of_measurement = info.get("unit")
        self._attr_device_class = info.get("device_class")
        self._attr_icon = info.get("icon")
        self._attr_state_class = info.get("state_class")

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=device_name,
            manufacturer="OKOK / BIA Весы",
            model="Bluetooth-весы с анализатором",
        )

    @property
    def native_value(self) -> Any:
        """Вернуть значение сенсора."""
        metrics = self.coordinator.compute_metrics()
        value = metrics.get(self._sensor_type)
        if value is None:
            return None
        return value

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Доп. атрибуты."""
        if self._sensor_type == SENSOR_WEIGHT:
            metrics = self.coordinator.compute_metrics()
            return {
                "raw_hex": metrics.get("raw_hex"),
                "status": metrics.get("status"),
                "tdee": metrics.get("tdee"),
            }
        return None


async def async_setup_entry(
    hass: HomeAssistant,
    entry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Установка платформы."""
    mac = entry.data.get(CONF_MAC)
    name = entry.data.get(CONF_NAME, "BIA Весы")

    if not mac:
        _LOGGER.error("MAC-адрес не задан")
        return

    coordinator = BiaScaleCoordinator(hass, entry, mac)
    await coordinator.async_start()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id + "_coordinator"] = coordinator

    entities = [
        BiaScaleSensor(coordinator, entry, sensor_type, name)
        for sensor_type in SENSOR_TYPES
    ]
    async_add_entities(entities)

    await coordinator.async_request_refresh()
