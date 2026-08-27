"""Automated UI verification for the dashboard using Streamlit AppTest.

Runs every page and clicks every primary interaction, asserting zero
uncaught exceptions and that expected outputs appear.  Run directly:

    python tests/test_dashboard_ui.py
"""
import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest

SCRIPT = str(Path(__file__).resolve().parent.parent / "dashboard.py")
TIMEOUT = 600


def fresh(page: str | None = None) -> AppTest:
    at = AppTest.from_file(SCRIPT, default_timeout=TIMEOUT)
    if page:
        at.session_state["nav"] = page
    at.run()
    return at


def click(at: AppTest, key: str) -> AppTest:
    btn = at.button(key=key)
    if isinstance(btn, list):
        assert btn, f"button {key!r} not found"
        btn = btn[0]
    btn.click()
    at.run()
    return at


def expect_clean(at: AppTest, where: str) -> None:
    assert not at.exception, \
        f"{where}: {len(at.exception)} exception(s): " + \
        "; ".join(str(e.value)[:400] for e in at.exception)


def test_all_pages_render():
    at = fresh()
    expect_clean(at, "Overview")
    for page in ["Live Radar", "Simulation Lab", "Benchmarks",
                 "Dataset Studio", "Model Zoo"]:
        at.radio(key="nav").set_value(page).run()
        expect_clean(at, page)
    print("PASS all pages render clean")


def test_overview_one_click_demo():
    at = fresh("Overview")
    click(at, "ov_demo")
    expect_clean(at, "Overview one-click demo")
    print("PASS overview one-click demo")


def test_sim_lab_run_episode():
    at = fresh("Simulation Lab")
    click(at, "sl_run")
    expect_clean(at, "Simulation Lab run")
    assert len(at.metric) >= 8, "expected headline metric cards"
    print("PASS simulation lab episode")


def test_live_radar_advance():
    at = fresh("Live Radar")
    click(at, "lr_step")
    expect_clean(at, "Live Radar advance")
    markdown_text = " ".join(str(m.value) for m in at.markdown)
    assert "slots scanned live" in markdown_text, "expected live KPI cards"
    assert "live_spec" in at.session_state, "spectrum state should persist"
    print("PASS live radar advance")


def test_dataset_studio_import_and_calibrate():
    at = fresh("Dataset Studio")
    click(at, "ds_import")
    expect_clean(at, "Dataset import")
    assert "ds_ready" in at.session_state, "import should set ds_ready"
    click(at, "ds_calib")
    expect_clean(at, "Dataset calibrate+run")
    print("PASS dataset studio import + calibrate")


def test_model_zoo_evaluate_and_train():
    at = fresh("Model Zoo")
    files = sorted(Path("models").glob("*.npz"))
    if files:
        click(at, "mz_eval")
        expect_clean(at, "Model Zoo evaluate")
    click(at, "mz_train")
    expect_clean(at, "Model Zoo train+save")
    print("PASS model zoo evaluate + train")


def test_benchmarks_render_tables():
    at = fresh("Benchmarks")
    expect_clean(at, "Benchmarks")
    assert len(at.dataframe) >= 1, "expected benchmark tables"
    print("PASS benchmarks render")


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for fn in fns:
        try:
            fn()
        except AssertionError as exc:
            failed += 1
            print(f"FAIL {fn.__name__}: {exc}")
    print(f"\n{len(fns) - failed}/{len(fns)} UI tests passed")
    sys.exit(1 if failed else 0)
