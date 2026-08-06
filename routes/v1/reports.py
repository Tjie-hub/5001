"""Forward-Testing Report APIs (Production Engine Phase 2, Workstream 2C
Task 2C-3). See docs/superpowers/specs/2026-08-06-2c3-report-api-design.md.

forward_testing.reporting is the only persisted, structured report
subsystem in this codebase (EOD/Premarket "reports" are already the
Watchlist/Snapshot APIs, 2C-1/2C-2) -- no placeholder endpoints for those.
Thin controllers over forward_testing.reporting.build_forward_test_data()
plus the two existence-check reads added alongside it.
"""
import config
from forward_testing import reporting as ft_reporting
from routes.v1 import api_v1_bp
from routes.v1.envelope import ApiError, ok


@api_v1_bp.route("/reports", methods=["GET"])
def reports_latest():
    latest = ft_reporting.latest_report_date(config.DB_PATH)
    if latest is None:
        raise ApiError("NO_REPORT_DATA", 404, "no forward-test report has been generated yet")
    return ok(ft_reporting.build_forward_test_data(config.DB_PATH, latest))


@api_v1_bp.route("/reports/<date_str>", methods=["GET"])
def reports_by_date(date_str):
    if not ft_reporting.report_exists(config.DB_PATH, date_str):
        raise ApiError("NO_REPORT_DATA", 404,
                        f"no forward-test report for date={date_str!r}")
    return ok(ft_reporting.build_forward_test_data(config.DB_PATH, date_str))
