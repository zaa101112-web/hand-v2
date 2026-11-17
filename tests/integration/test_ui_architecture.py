import ast
from pathlib import Path

from PySide6.QtCore import Qt
from hand_v2.bootstrap import build_runtime
from hand_v2.adapters.qt.window import MainWindow
from hand_v2.adapters.timing import ManualClock
from hand_v2.domain.models import Activation


def test_ui_reports_simulated_output_and_stop_separately(qtbot, tmp_path):
    runtime = build_runtime(clock=ManualClock(1000))
    window = MainWindow(runtime)
    qtbot.addWidget(window)
    window.show()
    assert "시뮬레이션" in window.banner.text()
    qtbot.mouseClick(window.start_button, Qt.MouseButton.LeftButton)
    qtbot.mouseClick(window.neutral_button, Qt.MouseButton.LeftButton)
    runtime.scheduler.advance_to(1180)
    qtbot.mouseClick(window.back_button, Qt.MouseButton.LeftButton)
    assert runtime.keyboard.sent_chords == [("ALT","LEFT")]
    assert "가상 전송" in window.command_label.text()
    qtbot.mouseClick(window.stop_button, Qt.MouseButton.LeftButton)
    assert runtime.controller.state.activation == Activation.WAITING
    assert "가상 전송" in window.command_label.text()
    assert "중단 버튼" in window.reason_label.text()
    assert window.grab().save(str(tmp_path/"simulated-ui.png"))


def test_menu_pages_have_accessible_descriptions(qtbot):
    window = MainWindow(build_runtime(clock=ManualClock(1000)))
    qtbot.addWidget(window)
    for key in ("practice", "settings"):
        window.select_page(key)
        assert window.pages.currentWidget().accessibleDescription()
        assert "구현 예정" not in window.pages.currentWidget().accessibleDescription()


def test_core_dependencies_point_inwards():
    root = Path(__file__).parents[2]/"src/hand_v2"
    forbidden = {"PySide6","cv2","mediapipe","ctypes","os","pathlib","time","subprocess","threading","multiprocessing","mss","pyautogui","json"}
    for folder in ("domain","application"):
        for path in (root/folder).rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node,ast.Import):
                    assert not any(a.name.split('.')[0] in forbidden for a in node.names), path
                    assert not any(".adapters" in a.name for a in node.names), path
                elif isinstance(node,ast.ImportFrom):
                    assert (node.module or '').split('.')[0] not in forbidden, path
                    assert "adapters" not in (node.module or '').split('.'), path
                elif isinstance(node,ast.Call) and isinstance(node.func,ast.Name):
                    assert node.func.id not in {"open","__import__","eval","exec"}, path


def test_keyboard_port_has_no_mouse_methods():
    from hand_v2.application.ports import KeyboardPort
    public = {n for n in vars(KeyboardPort) if not n.startswith('_')}
    assert public == {"submit_chord","release_owned_keys"}


def test_offscreen_window_has_renderable_korean_fonts(qtbot):
    from PySide6.QtGui import QFontDatabase, QRawFont
    window=MainWindow(build_runtime(clock=ManualClock(1000)))
    qtbot.addWidget(window)
    assert "Malgun Gothic" in QFontDatabase.families()
    raw=QRawFont.fromFont(window.gesture_label.font())
    assert raw.isValid()
    assert raw.supportsCharacter(ord("한"))
