"""Sensor platform for the Unipolmove integration."""
from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import UnipolmoveCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: UnipolmoveCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            UnipolmoveImportoSensor(coordinator, entry),
            UnipolmoveDataFatturaSensor(coordinator, entry),
            UnipolmoveStatoSensor(coordinator, entry),
            UnipolmoveCostoTransitiSensor(coordinator, entry),
            UnipolmoveCostoAreaCSensor(coordinator, entry),
            UnipolmoveCostoParcheggiSensor(coordinator, entry),
            UnipolmoveCostoTraghettiSensor(coordinator, entry),
        ]
    )


class UnipolmoveEntity(CoordinatorEntity[UnipolmoveCoordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: UnipolmoveCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Unipolmove",
            manufacturer="UnipolSai / Utech",
        )

    @property
    def _latest(self):
        data = self.coordinator.data
        return data.latest_invoice if data else None

    def _discounted(self, field: str):
        """Return the agreement-adjusted amount, for use as an attribute."""
        data = self.coordinator.data
        if not data or not data.costi:
            return {}
        return {"importo_scontato": getattr(data.costi, field)}


class UnipolmoveImportoSensor(UnipolmoveEntity):
    _attr_translation_key = "importo_fattura"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "EUR"

    def __init__(self, coordinator: UnipolmoveCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_importo_fattura"

    @property
    def native_value(self):
        latest = self._latest
        return latest.amount if latest else None

    @property
    def extra_state_attributes(self):
        latest = self._latest
        if not latest:
            return {}
        return {
            "numero_fattura": latest.invoice_number,
            "merchant": latest.merchant,
            "residuo_rimborso": latest.refund_amount,
        }


class UnipolmoveDataFatturaSensor(UnipolmoveEntity):
    _attr_translation_key = "data_fattura"
    _attr_device_class = SensorDeviceClass.DATE

    def __init__(self, coordinator: UnipolmoveCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_data_fattura"

    @property
    def native_value(self):
        latest = self._latest
        return latest.invoice_date if latest else None


class UnipolmoveStatoSensor(UnipolmoveEntity):
    _attr_translation_key = "stato"

    def __init__(self, coordinator: UnipolmoveCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_stato"

    @property
    def native_value(self):
        latest = self._latest
        return latest.status if latest else None


class UnipolmoveCostoTransitiSensor(UnipolmoveEntity):
    _attr_translation_key = "costo_transiti"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "EUR"

    def __init__(self, coordinator: UnipolmoveCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_costo_transiti"

    @property
    def native_value(self):
        data = self.coordinator.data
        return data.costi.transiti if data and data.costi else None

    @property
    def extra_state_attributes(self):
        return self._discounted("transiti_scontato")


class UnipolmoveCostoAreaCSensor(UnipolmoveEntity):
    _attr_translation_key = "costo_area_c"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "EUR"

    def __init__(self, coordinator: UnipolmoveCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_costo_area_c"

    @property
    def native_value(self):
        data = self.coordinator.data
        return data.costi.area_c if data and data.costi else None

    @property
    def extra_state_attributes(self):
        return self._discounted("area_c_scontato")


class UnipolmoveCostoParcheggiSensor(UnipolmoveEntity):
    _attr_translation_key = "costo_parcheggi"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "EUR"

    def __init__(self, coordinator: UnipolmoveCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_costo_parcheggi"

    @property
    def native_value(self):
        data = self.coordinator.data
        return data.costi.parcheggi if data and data.costi else None

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data
        if not data or not data.costi:
            return {}
        return {
            "importo_scontato": data.costi.parcheggi_scontato,
            "prenotazione_parcheggi": data.costi.prenotazione_parcheggi,
            "prenotazione_parcheggi_scontato": data.costi.prenotazione_parcheggi_scontato,
        }


class UnipolmoveCostoTraghettiSensor(UnipolmoveEntity):
    _attr_translation_key = "costo_traghetti"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "EUR"

    def __init__(self, coordinator: UnipolmoveCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_costo_traghetti"

    @property
    def native_value(self):
        data = self.coordinator.data
        return data.costi.traghetti if data and data.costi else None

    @property
    def extra_state_attributes(self):
        return self._discounted("traghetti_scontato")
