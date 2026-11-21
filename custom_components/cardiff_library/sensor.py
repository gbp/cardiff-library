from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_LABEL, DOMAIN
from .coordinator import LoansCoordinator
from .parsing import Loan


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([LoansSensor(entry.runtime_data, entry)])


def loan_attributes(loans: list[Loan]) -> list[dict[str, Any]]:
    return [
        {
            "title": loan.title,
            "author": loan.author,
            "due": loan.due.isoformat(),
            "status": loan.status,
            "cover": loan.cover,
        }
        for loan in sorted(loans, key=lambda loan: loan.due)
    ]


class LoansSensor(CoordinatorEntity[LoansCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "loans"
    _attr_native_unit_of_measurement = "books"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:bookshelf"

    def __init__(self, coordinator: LoansCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._label = entry.data[CONF_LABEL]
        self._attr_unique_id = f"{entry.entry_id}_loans"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"Library {self._label}",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def native_value(self) -> int:
        return len(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        loans = self.coordinator.data
        return {
            "account": self._label,
            "next_due": min(loan.due for loan in loans).isoformat() if loans else None,
            "loans": loan_attributes(loans),
        }
