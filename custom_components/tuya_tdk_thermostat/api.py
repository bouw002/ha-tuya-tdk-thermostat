import logging
from typing import Dict, Any, List, Optional

from tuya_connector import TuyaOpenAPI

_LOGGER = logging.getLogger(__name__)

class TuyaTDKClient:
    """
    Wrapper around TuyaOpenAPI using Tuya Connector (TDK).
    Prefers Device Shadow properties to get fields like 'work_state'.
    """

    def __init__(self, endpoint: str, access_id: str, access_secret: str) -> None:
        self._endpoint = endpoint
        self._access_id = access_id
        self._access_secret = access_secret
        self._openapi: Optional[TuyaOpenAPI] = None

    def connect(self) -> None:
        _LOGGER.debug("Connecting to Tuya Cloud endpoint=%s", self._endpoint)
        self._openapi = TuyaOpenAPI(self._endpoint, self._access_id, self._access_secret)
        self._openapi.connect()
        _LOGGER.info("Connected to Tuya Cloud.")

    def list_devices(self) -> List[Dict[str, Any]]:
        if not self._openapi:
            raise RuntimeError("Tuya client not connected.")
        res = self._openapi.get("/v1.0/iot-03/devices", {})
        if res.get("success") is True:
            return res.get("result", {}).get("list", [])
        _LOGGER.error("Tuya list_devices failed: %s", res)
        raise RuntimeError(f"Tuya list_devices failed: {res}")

    def get_device_status(self, device_id: str) -> Dict[str, Any]:
        """
        Raw /status endpoint -> returns list of {code,value}; convert to map.
        """
        if not self._openapi:
            raise RuntimeError("Tuya client not connected.")
        res = self._openapi.get(f"/v1.0/devices/{device_id}/status", {})
        if res.get("success") is True:
            status_list = res.get("result", [])
            return {item["code"]: item["value"] for item in status_list if "code" in item}
        _LOGGER.warning("Tuya get_device_status failed for %s: %s", device_id, res)
        return {}

    def get_device_shadow_properties(self, device_id: str) -> Dict[str, Any]:
        """
        Preferred: /v2.0/cloud/thing/{device_id}/shadow/properties
        Returns {'code': value, ...}
        """
        if not self._openapi:
            raise RuntimeError("Tuya client not connected.")
        path = f"/v2.0/cloud/thing/{device_id}/shadow/properties"
        res = self._openapi.get(path, {})
        if res.get("success") is True:
            result = res.get("result") or {}
            props = result.get("properties") or []
            mapped: Dict[str, Any] = {}
            for p in props:
                code = p.get("code")
                value = p.get("value")
                if code is not None:
                    mapped[code] = value
            return mapped
        _LOGGER.warning("Shadow properties not available for %s: %s", device_id, res)
        return {}

    def get_device_status_map(self, device_id: str) -> Dict[str, Any]:
        """
        Unified status fetch:
        1) Try Shadow (often includes 'work_state').
        2) Fallback to /status.
        Merge both, preferring Shadow values.
        """
        shadow = self.get_device_shadow_properties(device_id) or {}
        status = self.get_device_status(device_id) or {}
        if shadow and status:
            merged = dict(status)
            merged.update(shadow)
            return merged
        return shadow or status

    def get_device_functions(self, device_id: str) -> Dict[str, Any]:
        if not self._openapi:
            raise RuntimeError("Tuya client not connected.")
        res = self._openapi.get(f"/v1.0/devices/{device_id}/functions", {})
        if res.get("success") is True:
            return res.get("result", {})
        _LOGGER.warning("get_device_functions not available or failed for %s: %s", device_id, res)
        return {}

    def send_commands(self, device_id: str, commands: List[Dict[str, Any]]) -> bool:
        if not self._openapi:
            raise RuntimeError("Tuya client not connected.")
        payload = {"commands": commands}
        res = self._openapi.post(f"/v1.0/devices/{device_id}/commands", payload)
        if res.get("success") is True:
            return True
        _LOGGER.error("Failed to send commands to %s: %s", device_id, res)
        return False

