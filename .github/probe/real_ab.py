"""Real replay steps: threads in one process vs one sequential loop per process."""
import collections, os, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0, os.getcwd())
import hermes_yaml
from tests.ci import workflow_steps

REPO = Path(os.getcwd())
def step(rel, job, name):
    wf = hermes_yaml.safe_load((REPO / rel).read_text(encoding="utf-8"))
    return next(s for s in wf["jobs"][job]["steps"] if s.get("name", "").startswith(name))
STEPS = {
    "upgrade": (step(".github/workflows/tests.yml", "e2e-upgrade", "Run upgrade e2e tests"),
                {"matrix": {"shard": "core"}, "inputs": {"strict_acceptance": ""}}),
    "winupdate": (step(".github/workflows/windows-install-update-e2e.yml", "install-update", "Run Windows install + update E2E"),
                  {"inputs": {"strict_acceptance": ""}, "runner": {"temp": "C:\\t"}}),
    "simple": ({"run": 'x=$(printf a | tr a b)\n[ "$x" = b ]\n'}, {}),
}
def one(kind):
    s, ctx = STEPS[kind]
    try:
        if kind == "simple":
            workflow_steps.outputs(s, ctx)
        else:
            workflow_steps.selected_files(s, ctx, REPO)
        return "ok"
    except AssertionError as e:
        m = str(e).split("\n")[0]
        return m[:60]
mode, kind, n = sys.argv[1], sys.argv[2], int(sys.argv[3])
t = time.monotonic()
if mode == "threads":
    with ThreadPoolExecutor(32) as ex:
        res = collections.Counter(ex.map(one, [kind] * n))
else:
    res = collections.Counter(one(kind) for _ in range(n))
print(f"AB {mode} {kind}: {dict(res)} in {time.monotonic()-t:.0f}s", flush=True)
