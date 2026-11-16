HAND v2 deterministic fixtures

model_poses.json: actual MediaPipe VIDEO output from official static photos. Source URL, image SHA-256 and model SHA-256 are stored per sample. No camera frames are included. The stored features reflect the original defect; regression expectations are authored in test_model_pose_regression.py.

gesture_suite.json: manually authored 21-landmark geometry, 14 positive gestures and 4 rejection cases. Expected gesture IDs are written independently from the recognizer by scripts/build_gesture_fixtures.py. This is recognition-only evidence. Integration tests separately connect these inputs to the production controller and RecordingKeyboard/FakeCapture. No operating-system input is used. It does not establish human accuracy.

landmarks/start_back_stop: full application LANDMARKS replay with explicit scripted keyboard outcomes and release ACK.
