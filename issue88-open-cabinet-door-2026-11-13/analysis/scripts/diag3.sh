#!/usr/bin/env bash
# #88 diagnostics (not a Research Run): pull0-only eval of resume checkpoints at matched env steps, fast vs stuck seeds.
# One job: name|checkpoint. Eval 128 traced envs, classify, render 2 failed + 2 successful episodes.
set -uo pipefail
name=$1 ck=$2 extra=${3:-}
cd /dev/shm/e10-door88/repo
export ROBODOJO_ASSETS_ROOT=$HOME/contact_rl/factory/assets/root CONTACT_RL_ROOT=$HOME/contact_rl OMNI_KIT_ACCEPT_EULA=YES PYTHONNOUSERSITE=1 TMPDIR=/dev/shm/e10-door88/tmp
IL=$HOME/a2r-e10/IsaacLab/source
export PYTHONPATH=.:$IL/isaaclab:$IL/isaaclab_assets:$IL/isaaclab_tasks:$IL/isaaclab_rl:$IL/isaaclab_mimic:$IL/isaaclab_contrib
SIM=$HOME/a2r-e10/py311/bin/python; LEARN=$HOME/a2r-environments/envs/train-3de9461f2664/bin/python
out=/dev/shm/e10-door88/diag-seeds/$name; [ -e "$out/phases.json" ] && exit 0
mkdir -p "$out"
while [ ! -s "$ck" ]; do sleep 30; done
while [ "$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits | head -1)" -lt 8000 ]; do sleep 60; done
echo "$(date +%T) $name eval"
$LEARN -u scripts/contact_rl_learn.py eval --config a2r/benchmark/contact_rl/configs/runs/single-open_cabinet_door-pull.yaml \
  --cache_root /dev/shm/e10-door88/banks-final --output "$out/eval" --sim_python $SIM --checkpoint "$ck" \
  --eval_types pull0 --rounds 1 --trace_envs 128 --seed 9911 $extra > "$out/eval.log" 2>&1 < /dev/null
trace=$(ls "$out"/eval/sim_*/trace*.pt | head -1)
$SIM -u scripts/contact_rl_trace_phases.py classify --trace "$trace" --out "$out/phases.json" > "$out/classify.log" 2>&1 < /dev/null
python3 - "$out/phases.json" > "$out/pick.txt" <<'PY'
import json, sys
eps = json.load(open(sys.argv[1]))["episodes"]
chosen = {}
for want in (False, True):
    for r in [r for r in eps if r["success"] == want][:2]:
        chosen.setdefault(r["episode"], []).append(r["env"])
for k, envs in sorted(chosen.items()):
    print(f"{k}:{','.join(map(str, sorted(envs)))}")
PY
while IFS=: read k envs; do
  $SIM -u scripts/contact_rl_render.py --task spec:kitchen/open_cabinet_door --trace "$trace" --out "$out/videos/ep$k" \
    --envs "$envs" --episode "$k" --stride 2 --slow 0.5 --width 480 --height 360 --label "$name" > "$out/render_ep$k.log" 2>&1 < /dev/null
done < "$out/pick.txt"
echo "$(date +%T) $name done: $(grep -o 'eval open_cabinet_door: [^{]*' $out/eval.log)"
