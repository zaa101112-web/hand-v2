import json
from pathlib import Path

from hand_v2.domain.models import ForegroundSnapshot, Gesture, GestureEvent, KeyboardState, ReleaseResult, ExecutionMode,TrackingFrame,Hand,Landmark
from hand_v2.adapters.timing import ManualClock


def run_fixture(directory):
    from hand_v2.bootstrap import build_runtime
    directory = Path(directory)
    manifest = json.loads((directory/"manifest.json").read_text(encoding="utf-8"))
    if manifest["fixture_format_version"] != 1 or manifest["schema_name"] != "hand-v2" or manifest["schema_version"] != 1:
        raise ValueError("unsupported fixture schema")
    if manifest["kind"] not in ('CONTROL','LANDMARKS') or manifest["execution_mode"] != "REPLAY":
        raise ValueError("unsupported replay mode")
    if manifest['kind']=='LANDMARKS':
        from hand_v2.adapters.resources import EXPECTED_MODEL_SHA256
        if manifest.get('model_sha256')!=EXPECTED_MODEL_SHA256 or not manifest.get('source_commit') or not manifest.get('config_sha256'):
            raise ValueError('landmark replay requires pinned model/config/source')
    clock = ManualClock(manifest["start_at_ms"])
    runtime = build_runtime(ExecutionMode.REPLAY, clock, initialize=False)
    app = runtime.controller
    inputs = [json.loads(line) for line in (directory/"inputs.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    if inputs != sorted(inputs, key=lambda row:(row["at_ms"],row["seq"])):
        raise ValueError("fixture inputs must be ordered")
    for row in inputs:
        runtime.scheduler.advance_to(row["at_ms"])
        value, channel = row["value"], row["channel"]
        if channel == "foreground":
            runtime.foreground.current = ForegroundSnapshot(**value)
        elif channel == "initialize":
            app.initialize(**value)
        elif channel == "keyboard_state":
            value["owned_keys"] = tuple(value["owned_keys"])
            runtime.keyboard.state = KeyboardState(**value)
            app.on_keyboard_state(runtime.keyboard.state)
        elif channel == "release_result":
            app.on_release_result(ReleaseResult(**value))
        elif channel == "neutral":
            app.neutral(value)
        elif channel == "gesture":
            app.handle(GestureEvent(value["event_id"], Gesture(value["gesture"]), tuple(value["hand_ids"]),
                                    value["captured_at_ms"], row["at_ms"], value["context_version"], value.get("camera_epoch",0)))
        elif channel == 'tracking':
            if manifest['kind']!='LANDMARKS':raise ValueError('tracking requires LANDMARKS fixture')
            value['hands']=tuple(Hand(**{**h,'landmarks':tuple(Landmark(**p) for p in h['landmarks'])}) for h in value['hands'])
            runtime.vision.accept(TrackingFrame(**value))
        elif channel == "keyboard_outcome":
            value["keyboard_state"]["owned_keys"] = tuple(value["keyboard_state"]["owned_keys"])
            runtime.keyboard.outcomes.append(value)
        elif channel == "flush":
            app.flush_executor()
        elif channel == "stop":
            app.stop(value)
        else:
            raise ValueError(f"unknown channel {channel}")
    runtime.scheduler.advance_to(manifest["end_at_ms"])
    result = {"sent_chords":[list(c) for c in runtime.keyboard.sent_chords], "activation":app.state.activation.value,
              "owned_keys":list(app.state.keyboard_state.owned_keys), "release_pending":app.state.release_pending,
              "last_stop_reason":app.state.last_stop_reason, "context_version":app.state.context_version}
    if manifest['kind']=='LANDMARKS':
        result['recognized']=[{'gesture':event.gesture.value,'at_ms':event.captured_at_ms} for event in runtime.vision.recognized_events]
    expected = json.loads((directory/"expected.json").read_text(encoding="utf-8"))
    if result != expected or runtime.keyboard.outcomes:
        raise AssertionError(f"Replay mismatch: expected {expected}, got {result}; unused outcomes={len(runtime.keyboard.outcomes)}")
    return result
