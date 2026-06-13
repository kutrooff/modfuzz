from state.snapshot import ResourceSnapshot, SnapshotStore, extract_identity


class StateAssertionAnalyzer:
    def analyze_sequence(self, results):
        created = False
        deleted = False
        created_identity = None
        pending_update = None
        store = SnapshotStore()

        for result in results:
            method = result.case.method.upper()
            status = result.status_code

            if (
                method in {"POST", "GET", "PUT", "PATCH"}
                and self._is_2xx(status)
                and isinstance(result.response_body, dict)
            ):
                store.add(
                    ResourceSnapshot(
                        source_method=method,
                        source_path=result.case.endpoint.path,
                        status_code=status,
                        body=result.response_body,
                        identity=extract_identity(result.response_body),
                    )
                )

            if method == "POST" and self._is_2xx(status):
                created = True
                deleted = False
                created_identity = extract_identity(result.response_body)
                self._check_location_matches_body_id(result)
                continue

            if method == "GET":
                if created and not deleted and not self._is_2xx(status):
                    self._add_issue(result, "state_read_after_create_failed")

                if created and not deleted and self._is_2xx(status):
                    self._check_same_identity(result, created_identity)

                    if pending_update:
                        self._check_update_visible(pending_update, result)
                        pending_update = None

                if deleted and status not in (404, 410):
                    self._add_issue(result, "state_delete_not_applied")

                continue

            if method in {"PUT", "PATCH"}:
                if created and not deleted and not self._is_2xx(status):
                    self._add_issue(result, "state_update_failed")

                if created and not deleted and self._is_2xx(status):
                    self._check_same_identity(result, created_identity)
                    pending_update = result

                continue

            if method == "DELETE":
                if created and not deleted:
                    if self._is_2xx(status):
                        deleted = True
                    else:
                        self._add_issue(result, "state_delete_failed")

    def _is_2xx(self, status):
        return status is not None and 200 <= status < 300

    def _add_issue(self, result, issue):
        if issue not in result.analysis.issues:
            result.analysis.issues.append(issue)

        result.analysis.severity = "high"
        result.success = False

    def _check_location_matches_body_id(self, result):
        location = result.response_headers.get(
            "location"
        ) or result.response_headers.get("Location")

        if not location:
            return

        body_id = extract_identity(result.response_body)

        if body_id is None:
            return

        location_id = location.rstrip("/").split("/")[-1]

        if str(body_id) != str(location_id):
            self._add_issue(result, "state_location_id_mismatch")

    def _check_same_identity(self, result, expected_identity):
        if expected_identity is None:
            return

        actual_identity = extract_identity(result.response_body)

        if actual_identity is None:
            return

        if str(actual_identity) != str(expected_identity):
            self._add_issue(result, "state_identity_mismatch")

    def _check_update_visible(self, update_result, read_result):
        update_body = update_result.case.body

        if not isinstance(update_body, dict):
            return

        read_body = read_result.response_body

        if not isinstance(read_body, dict):
            return

        for key, expected_value in update_body.items():
            if not self._contains_updated_value(read_body, key, expected_value):
                self._add_issue(read_result, "state_update_not_visible")
                return

    def _contains_updated_value(self, data, key, expected_value):
        if isinstance(data, dict):
            if key in data and self._values_equal(data[key], expected_value):
                return True

            nested_resource = self._resource_from_id_key(key)
            if nested_resource:
                nested_data = data.get(nested_resource)

                if isinstance(nested_data, dict) and self._values_equal(
                    nested_data.get("id"),
                    expected_value,
                ):
                    return True

            return any(
                self._contains_updated_value(value, key, expected_value)
                for value in data.values()
            )

        if isinstance(data, list):
            return any(
                self._contains_updated_value(item, key, expected_value)
                for item in data
            )

        return False

    def _resource_from_id_key(self, key):
        if not key.endswith("_id"):
            return None

        resource = key[: -len("_id")]

        return resource or None

    def _values_equal(self, actual_value, expected_value):
        if actual_value == expected_value:
            return True

        if actual_value is None or expected_value is None:
            return False

        return str(actual_value) == str(expected_value)
