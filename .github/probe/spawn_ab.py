"""Run Git bash W-wide in parallel over script variants; count crashes (non-zero) per variant."""
import collections, os, platform, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from hermes_platform.resolver import locate_command

sys.path.insert(0, os.getcwd())
from tests.ci import workflow_steps

bash = locate_command("bash").command[0]
git = locate_command("git").command[0]
print("python:", sys.executable, platform.machine(), platform.python_version())
VARIANTS = {
    "msys-forks": 'x=$(printf a | tr a b)\n[ "$x" = b ]\n',
    "native-python": '"$REPLAY_PYTHON" -c pass\n',
    "python3-name": 'python3 -c pass\n',
    "python-name": 'python -c pass\n',
    "procsub-find": "mapfile -t f < <(find tests/e2e/core/upgrade -maxdepth 1 -name 'test_*.py' | sort)\n[ ${#f[@]} -gt 0 ]\n",
    "heredoc-python3": "x=$(python3 - <<'PY'\nprint(1)\nPY\n)\n[ \"$x\" = 1 ]\n",
}
mode, n, workers = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
root = Path(tempfile.mkdtemp(prefix="ab-"))
dirs = workflow_steps._interpreter_dirs(root)
script = root / "s.sh"; script.write_text(VARIANTS[mode], encoding="utf-8")
env = {"PATH": os.pathsep.join((*dirs, os.defpath, str(Path(bash).parent), str(Path(git).parent))),
       "HOME": str(root), "RUNNER_TEMP": str(root), "REPLAY_PYTHON": sys.executable}
def one(_):
    r = subprocess.run([bash, "--noprofile", "--norc", "-eo", "pipefail", str(script)], cwd=os.getcwd(), env=env,
                       stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=60)
    return r.returncode
with ThreadPoolExecutor(workers) as ex:
    codes = collections.Counter(ex.map(one, range(n)))
bad = sum(v for k, v in codes.items() if k != 0)
print(f"AB {mode}: bad={bad}/{n} codes={dict((hex(k & 0xFFFFFFFF), v) for k, v in codes.items())}")
