from __future__ import annotations
from pathlib import Path
from typing import Any, List
import app.cmd.pipeline_service as ps
from app.cmd.pipeline_service import PipelineDeps, run_pipeline


class FakeHelpdeskService:
    def __init__(self, requests_: list[Any]) -> None:
        self.requests = requests_
        self.called = False

    def load_helpdesk_requests(self) -> list[Any]:
        self.called = True
        return self.requests

class FakeServiceCatalogClient:
    def __init__(self) -> None:
        self.called = False

    def fetch_catalog(self) -> Any:
        self.called = True
        return object()

class FakeLLMClassifier:
    def __init__(self) -> None:
        self.batches: list[list[Any]] = []

    def classify_batch(self, batch: list[Any], service_catalog: Any) -> list[Any]:
        # not used directly by run_pipeline, classify_requests will be monkeypatched
        self.batches.append(batch)
        return batch

class FakeReportLog:
    def __init__(self) -> None:
        self.marked: list[Path] = []

    def get_record(self, path: Path) -> Any:
        return None

    def mark_sent(self, path: Path, created_at: Any) -> None:
        self.marked.append(path)

# no unsent reports, classification and send happen
def test_run_pipeline_happy_path(monkeypatch, tmp_path) -> None:
    # arrange
    fake_helpdesk = FakeHelpdeskService(requests_=["req1", "req2"])
    fake_catalog_client = FakeServiceCatalogClient()
    fake_llm = FakeLLMClassifier()
    fake_log = FakeReportLog()

    deps = PipelineDeps(
        project_root=tmp_path,
        helpdesk_service=fake_helpdesk,
        service_catalog_client=fake_catalog_client,
        llm_classifier=fake_llm,
        report_log=fake_log,
        batch_size=10,
    )

    sent_reports: list[List[Path]] = []

    def fake_collect_unsent_reports(*args, **kwargs):
        # no unsent reports, no explicit report already sent
        return [], None

    def fake_load_service_catalog(_client):
        return "fake_catalog"

    def fake_classify_requests(llm, service_catalog, requests_, batch_size: int):
        # echo requests back
        assert llm is fake_llm
        assert service_catalog == "fake_catalog"
        assert requests_ == ["req1", "req2"]
        assert batch_size == 10
        return ["classified1", "classified2"]

    def fake_missing_sla(requests_, service_catalog):
        # no-op, ensure it is called with classified requests
        assert requests_ == ["classified1", "classified2"]
        assert service_catalog == "fake_catalog"

    def fake_save_excel(requests_):
        # ensure we get classified requests
        assert requests_ == ["classified1", "classified2"]
        path = tmp_path / "report.xlsx"
        path.write_bytes(b"test")
        return str(path)

    def fake_send_report(report_paths, report_log):
        sent_reports.append(list(report_paths))
        assert report_log is fake_log

    # NEW: avoid touching real _log_sample_requests (which expects HelpdeskRequest)
    def fake_log_sample_requests(requests_, limit: int = 5) -> None:
        # we only care that run_pipeline reaches this point, not the logging content
        assert requests_ == ["req1", "req2"]

    # patch module-level functions used by run_pipeline
    monkeypatch.setattr(ps, "_collect_unsent_reports", fake_collect_unsent_reports)
    monkeypatch.setattr(ps, "_load_service_catalog", fake_load_service_catalog)
    monkeypatch.setattr(ps, "classify_requests", fake_classify_requests)
    monkeypatch.setattr(ps, "missing_sla", fake_missing_sla)
    monkeypatch.setattr(ps, "save_excel", fake_save_excel)
    monkeypatch.setattr(ps, "_send_report", fake_send_report)
    monkeypatch.setattr(ps, "_log_sample_requests", fake_log_sample_requests)

    # act
    run_pipeline(deps, explicit_report_path=None)

    # assert
    assert fake_helpdesk.called is True
    assert len(sent_reports) == 1
    assert len(sent_reports[0]) == 1
    assert sent_reports[0][0].name == "report.xlsx"


def test_run_pipeline_sends_unsent_reports(monkeypatch, tmp_path) -> None:
    fake_helpdesk = FakeHelpdeskService(requests_=["req1"])
    fake_catalog_client = FakeServiceCatalogClient()
    fake_llm = FakeLLMClassifier()
    fake_log = FakeReportLog()

    deps = PipelineDeps(
        project_root=tmp_path,
        helpdesk_service=fake_helpdesk,
        service_catalog_client=fake_catalog_client,
        llm_classifier=fake_llm,
        report_log=fake_log,
        batch_size=10,
    )

    unsent1 = tmp_path / "unsent1.xlsx"
    unsent2 = tmp_path / "unsent2.xlsx"
    unsent1.write_bytes(b"data1")
    unsent2.write_bytes(b"data2")

    sent_reports: list[List[Path]] = []

    def fake_collect_unsent_reports(*args, **kwargs):
        # two unsent reports, no explicit report
        return [unsent1, unsent2], None

    def fake_send_report(report_paths, report_log):
        sent_reports.append(list(report_paths))
        assert report_log is fake_log

    # ensure these are not called
    def fail_classify_requests(*args, **kwargs):
        raise AssertionError("classify_requests should not be called when unsent reports exist")

    def fail_save_excel(*args, **kwargs):
        raise AssertionError("save_excel should not be called when unsent reports exist")

    monkeypatch.setattr(ps, "_collect_unsent_reports", fake_collect_unsent_reports)
    monkeypatch.setattr(ps, "_send_report", fake_send_report)
    monkeypatch.setattr(ps, "classify_requests", fail_classify_requests)
    monkeypatch.setattr(ps, "save_excel", fail_save_excel)

    run_pipeline(deps, explicit_report_path=None)

    assert len(sent_reports) == 1
    assert set(sent_reports[0]) == {unsent1, unsent2}
    # helpdesk should never be called in this branch
    assert fake_helpdesk.called is False