"""V2-T40: watchdog survives a blocked main callback and never reports clean exit."""
import os,subprocess,sys
from pathlib import Path
from hand_v2.adapters.shutdown import ShutdownWatchdog


def test_cancelled_watchdog_does_not_cleanup_or_exit():
    calls=[]
    guard=ShutdownWatchdog(lambda:calls.append('cleanup'),lambda code:calls.append(code))
    guard.arm(.1);guard.cancel();guard.thread.join(.5)
    assert calls==[]


def test_blocked_main_callback_exits_two_and_writes_failure(tmp_path):
    marker=tmp_path/'watchdog.txt'
    program='''import sys,time
from pathlib import Path
from hand_v2.adapters.shutdown import ShutdownWatchdog
def cleanup(): Path(sys.argv[1]).write_text('forced; key/file completion unconfirmed')
guard=ShutdownWatchdog(cleanup)
# Keep a bounded two-second deadline while allowing 200ms for filesystem IO.
# The previous 20ms cleanup reserve could exit between opening and flushing.
guard.arm(2)
time.sleep(30)
'''
    env=dict(os.environ,PYTHONPATH=str(Path(__file__).parents[2]/'src'))
    result=subprocess.run([sys.executable,'-c',program,str(marker)],env=env,timeout=5,capture_output=True)
    assert result.returncode==2
    assert 'unconfirmed' in marker.read_text()
