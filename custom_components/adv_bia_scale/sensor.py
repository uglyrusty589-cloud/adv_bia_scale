"""Пассивный BLE-листенер и вычислитель BIA метрик для мульти-профилей."""

from __future__ import annotations

import logging
from typing import Any, Callable

from homeassistant.components.bluetooth import (
    BluetoothScanningMode,
    async_register_callback,
)
from homeassistant.components.bluetooth.models import BluetoothServiceInfoBleak
from homeassistant.components.sensor import RestoreSensor, SensorEntity
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
    CONF_USERS,
    CONF_PROFILE_NAME,
    CONF_WEIGHT_MIN,
    CONF_WEIGHT_MAX,
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


class BiaScaleCoordinator(DataUpdateCoordinator):
    """Координатор слушает BLE ADV для одного MAC и матчит пользователя по весу."""

    def __init__(
        self,
        hass: HomeAssistant,
        mac_address: str,
        device_name: str,
        users: list[dict[str, Any]],
    ) -> None:
        """Инициализация."""
        self.mac_address = mac_address.upper()
        self.device_name = device_name
        self.users = users
        self._cancel_callback: Callable[[], None] | None = None
        self._latest_raw: dict[str, Any] = {}
        self._matched_user_index = -1

        super().__init__(
            hass,
            _LOGGER,
            name=f"OKOK BIA Scale {mac_address}",
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
            _LOGGER.debug(
                "Manufacturer %s not in data %s",
                MANUFACTURER_ID_OKOK,
                mfg_data,
            )
            return

        raw_bytes = mfg_data[MANUFACTURER_ID_OKOK]
        parsed = parse_okok_advertisement(raw_bytes)
        _LOGGER.debug("Parsed: %s", parsed)
        if not parsed:
            return

        weight = parsed.get("weight_kg", 0)
        self._match_user(weight)
        self._latest_raw = {
            "raw": parsed,
            "matched_user_index": self._matched_user_index,
        }
        self.async_set_updated_data(self._latest_raw)

    def _match_user(self, weight_kg: float) -> None:
        """Найти ближайшего пользователя по весу."""
        if not weight_kg or weight_kg <= 0:
            self._matched_user_index = -1
            return

        best_idx = -1
        best_diff = float("inf")
        for idx, user in enumerate(self.users):
            w_min = user.get(CONF_WEIGHT_MIN, 0.0)
            w_max = user.get(CONF_WEIGHT_MAX, float("inf"))
            if w_min <= weight_kg <= w_max:
                diff = 0.0
            else:
                diff = min(abs(weight_kg - w_min), abs(weight_kg - w_max))
            if diff < best_diff:
                best_diff = diff
                best_idx = idx
        self._matched_user_index = best_idx
        _LOGGER.debug(
            "Matched user index %s for weight %.1f kg (diff=%.1f)",
            best_idx,
            weight_kg,
            best_diff,
        )

    @property
    def matched_user_index(self) -> int:
        """Индекс последнего сматченного пользователя."""
        return self._matched_user_index

    def compute_metrics(self, user_index: int) -> dict[str, Any]:
        """Вычислить все BIA метрики для конкретного пользователя."""
        data = self._latest_raw.get("raw", {})
        if not data:
            return {}

        weight = data.get("weight_kg", 0)
        impedance = data.get("impedance", 0)
        hr = data.get("heart_rate", 0)

        if not weight or weight <= 0:
            return {}

        if user_index < 0 or user_index >= len(self.users):
            return {}

        user = self.users[user_index]
        height = user.get(CONF_HEIGHT, 175)
        birth_date = user.get(CONF_BIRTH_DATE)
        age = calculate_age(birth_date) if birth_date else user.get("age", 30)
        gender = user.get(CONF_GENDER, "male")
        activity = user.get(CONF_ACTIVITY_LEVEL, "moderate")

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


class UserBiaScaleSensor(CoordinatorEntity, RestoreSensor):
    """Сенсор BIA Весов для конкретного профиля пользователя."""

    _attr_has_entity_name = True
    _attr_translation_domain = DOMAIN

    def __init__(
        self,
        coordinator: BiaScaleCoordinator,
        entry_id: str,
        user_index: int,
        user_name: str,
        sensor_type: str,
        device_name: str,
    ) -> None:
        """Инициализация."""
        super().__init__(coordinator)
        self._sensor_type = sensor_type
        self._user_index = user_index
        self._user_name = user_name
        self._entry_id = entry_id
        self._device_name = device_name

        self._attr_unique_id = f"{entry_id}_{user_name}_{sensor_type}"
        self._attr_translation_key = sensor_type

        info = SENSOR_TYPES[sensor_type]
        self._attr_native_unit_of_measurement = info.get("unit")
        self._attr_device_class = info.get("device_class")
        self._attr_icon = info.get("icon")
        self._attr_state_class = info.get("state_class")

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_{user_name}")},
            name=f"{device_name} — {user_name}",
            manufacturer="OKOK",
            model="Bluetooth-весы с анализатором",
        )

        # Последнее известное значение (для fallback когда BLE данных нет)
        self._last_value: Any = None

    async def async_added_to_hass(self) -> None:
        """Вызвано когда сенсор добавлен в HA."""
        await super().async_added_to_hass()
        # Восстановить последнее значение из прошлого состояния
        last_state = await self.async_get_last_sensor_data()
        if last_state is not None:
            self._last_value = last_state.native_value
            _LOGGER.debug(
                "Restored %s = %s",
                self._attr_unique_id,
                self._last_value,
            )

    @ha_callback
    def _handle_coordinator_update(self) -> None:
        """Вызывается при обновлении координатора."""
        # Сначала обновляем _last_value новым значением
        new_value = self._compute_native_value()
        if new_value is not None:
            self._last_value = new_value
        super()._handle_coordinator_update()

    def _compute_native_value(self) -> Any:
        """Вычислить значение из координатора (без fallback на _last_value)."""
        data = self.coordinator.data
        if not data or "raw" not in data:
            return None

        raw = data["raw"]
        weight = raw.get("weight_kg")
        impedance = raw.get("impedance")

        matched = self.coordinator.matched_user_index

        # Вес и импеданс — общие данные устройства, показываем только
        # для сматченного профиля; если не сматчено (matched == -1),
        # показываем только для первого профиля, чтобы не дублировать.
        if self._sensor_type == SENSOR_WEIGHT:
            if weight is None or weight <= 0:
                return None
            if matched == -1:
                return weight if self._user_index == 0 else None
            return weight if matched == self._user_index else None

        if self._sensor_type == SENSOR_IMPEDANCE:
            if matched == -1:
                return impedance if self._user_index == 0 else None
            return impedance if matched == self._user_index else None

        # Для остальных сенсоров (BIA-расчёты) обновляем только
        # если вес > 0 и профиль сматчился
        if weight is None or weight <= 0:
            return None

        if matched != self._user_index:
            return None

        metrics = self.coordinator.compute_metrics(self._user_index)
        return metrics.get(self._sensor_type)

    @property
    def native_value(self) -> Any:
        """Вернуть значение сенсора — fallback на последнее известное значение."""
        fresh = self._compute_native_value()
        if fresh is not None:
            return fresh
        # Если свежих данных нет — показываем последнее запомненное
        return self._last_value

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Доп. атрибуты для сенсора веса."""
        if self._sensor_type != SENSOR_WEIGHT:
            return None

        data = self.coordinator.data
        if not data or "raw" not in data:
            return None

        raw = data["raw"]
        attrs: dict[str, Any] = {
            "raw_hex": raw.get("raw_hex"),
            "status": raw.get("status"),
        }

        # TDEE добавляем только если пользователь сматчен и вес > 0
        if (
            self.coordinator.matched_user_index == self._user_index
            and raw.get("weight_kg", 0) > 0
        ):
            metrics = self.coordinator.compute_metrics(self._user_index)
            attrs["tdee"] = metrics.get("tdee")

        return attrs


async def async_setup_entry(
    hass: HomeAssistant,
    entry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Установка платформы sensor."""
    mac = entry.data.get(CONF_MAC)
    device_name = entry.data.get(CONF_NAME, "OKOK BIA Scale")
    users = entry.data.get(CONF_USERS, [])

    if not mac:
        _LOGGER.error("MAC-адрес не задан")
        return

    if not users:
        _LOGGER.error("Список пользователей пуст")
        return

    coordinator = BiaScaleCoordinator(hass, mac, device_name, users)
    await coordinator.async_start()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id + "_coordinator"] = coordinator

    entities: list[UserBiaScaleSensor] = []
    entry_id = entry.entry_id
    for user_index, user in enumerate(users):
        user_name = user.get(CONF_PROFILE_NAME, f"Пользователь {user_index + 1}")
        for sensor_type in SENSOR_TYPES:
            entities.append(
                UserBiaScaleSensor(
                    coordinator=coordinator,
                    entry_id=entry_id,
                    user_index=user_index,
                    user_name=user_name,
                    sensor_type=sensor_type,
                    device_name=device_name,
                )
            )

    async_add_entities(entities)
    await coordinator.async_request_refresh()

    # Cleanup orphaned entities from v1 (legacy single-profile)
    await _async_cleanup_orphaned_entities(hass, entry, users, entities)


async def _async_cleanup_orphaned_entities(
    hass: HomeAssistant, entry, users: list, new_entities: list
) -> None:
    """Remove orphaned entities: v1 format AND deleted profiles."""
    from homeassistant.helpers.entity_registry import async_get as _er_get
    entity_reg = _er_get(hass)
    entry_id = entry.entry_id

    # Build valid profile prefixes: entryId_ProfileName_
    valid_prefixes = {
        f"{entry_id}_{user.get(CONF_PROFILE_NAME, f'Пользователь {idx + 1}')}_"
        for idx, user in enumerate(users)
    }

    orphaned = []
    for ent in entity_reg.entities.values():
        if ent.config_entry_id != entry_id:
            continue
        if not ent.unique_id:
            continue

        # v1 format: entryId_sensorType (1 underscore)
        if ent.unique_id.count("_") == 1:
            orphaned.append(ent)
            continue

        # R2 format: entryId_ProfileName_sensorType (2+ underscores)
        # Check if starts with any valid prefix
        if not any(ent.unique_id.startswith(prefix) for prefix in valid_prefixes):
            orphaned.append(ent)

    for ent in orphaned:
        _LOGGER.info("Removing orphaned entity: %s", ent.entity_id)
        entity_reg.async_remove(ent.entity_id)

    # ------------------------------------------------------------------
    # Also remove orphaned devices (no remaining entities for this entry)
    # ------------------------------------------------------------------
    from homeassistant.helpers.device_registry import async_get as _dr_get
    device_reg = _dr_get(hass)
    devices = [
        dev
        for dev in device_reg.devices.values()
        if entry_id in dev.config_entries
    ]
    for dev in devices:
        remaining = [
            ent
            for ent in entity_reg.entities.values()
            if ent.device_id == dev.id and ent.config_entry_id == entry_id
        ]
        if not remaining:
            _LOGGER.info("Removing orphaned device: %s", dev.name_by_user or dev.name)
            device_reg.async_remove_device(dev.id)
