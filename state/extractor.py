from typing import Any, Dict

from execution.result import ExecutionResult


class StateExtractor:
    ID_FIELDS = {"id", "uuid", "user_id", "userId", "order_id", "orderId"}
    TOKEN_FIELDS = {"token", "access_token", "refresh_token"}

    def extract(self, result: ExecutionResult) -> Dict[str, Any]:
        extracted: Dict[str, Any] = {}

        if result.status_code is None:
            return extracted

        self._extract_from_body(result, extracted)
        self._extract_from_headers(result, extracted)

        return extracted

    def _extract_from_body(
        self,
        result: ExecutionResult,
        extracted: Dict[str, Any],
    ) -> None:
        body = result.response_body

        if isinstance(body, dict):
            resource_name = self._resource_name_from_path(result.case.endpoint.path)

            for field_name, value in body.items():
                if field_name in self.ID_FIELDS or field_name.endswith("_id"):
                    extracted[f"{resource_name}.{field_name}"] = value
                    extracted[f"{resource_name}.last_id"] = value

                if field_name in self.TOKEN_FIELDS:
                    extracted[f"auth.{field_name}"] = value

        elif isinstance(body, list):
            for item in body:
                if isinstance(item, dict):
                    fake_result = result
                    fake_result.response_body = item
                    self._extract_from_body(fake_result, extracted)


    def _extract_from_headers(
        self,
        result: ExecutionResult,
        extracted: Dict[str, Any],
    ) -> None:
        headers = {
            key.lower(): value
            for key, value in result.response_headers.items()
        }

        location = headers.get("location")
        if location:
            extracted["location.last"] = location

            last_part = location.rstrip("/").split("/")[-1]
            if last_part:
                resource_name = self._resource_name_from_path(result.case.endpoint.path)
                extracted[f"{resource_name}.last_id"] = last_part


    def _resource_name_from_path(self, path: str) -> str:
        """
        Возвращает имя пути.
        :param path передаваемый путь
        :return: str значение пути
        """
        parts = [part for part in path.split("/") if part and part.startswith("{")]

        if not parts:
            return "resourse"

        return parts[0]