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
        location = (
                result.response_headers.get("location")
                or result.response_headers.get("Location")
        )

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
            if read_body.get(key) != expected_value:
                self._add_issue(read_result, "state_update_not_visible")
                return


