#!/usr/bin/env bash
# #88 pull0 stall diagnostics on e (not a Research Run; like the earlier p2 diag): per checkpoint, eval on pull0 starts only
# (1 round, 128 traced envs) -> classify (door angle, gripper width, TCP vs door edge, TCP-handle distance per frame)
# -> render 3 failed and 2 successful episodes.
set -uo pipefail
cd /dev/shm/e10-door88/repo
export ROBODOJO_ASSETS_ROOT=$HOME/contact_rl/factory/assets/root CONTACT_RL_ROOT=$HOME/contact_rl OMNI_KIT_ACCEPT_EULA=YES PYTHONNOUSERSITE=1 TMPDIR=/dev/shm/e10-door88/tmp
IL=$HOME/a2r-e10/IsaacLab/source
export PYTHONPATH=.:$IL/isaaclab:$IL/isaaclab_assets:$IL/isaaclab_tasks:$IL/isaaclab_rl:$IL/isaaclab_mimic:$IL/isaaclab_contrib
SIM=$HOME/a2r-e10/py311/bin/python; LEARN=$HOME/a2r-environments/envs/train-3de9461f2664/bin/python
C=/dev/shm/e10-door88/diagck
runs=(
 "R338-16M|$C/scratch-s3/train/model_001999.pt|"
 "R338-16M-sampled|$C/scratch-s3/train/model_001999.pt|--eval_stochastic"
 "R338-25M|$C/scratch-s3/train/model_002999.pt|"
 "R334-33M|$C/scratch/train/model_003999.pt|"
 "R338-final|$C/scratch-s3/train/model.pt|"
)
for j in "${runs[@]}"; do
  IFS='|' read -r name ck extra <<< "$j"
  out=/dev/shm/e10-door88/diag-pull0/$name; [ -e "$out/phases.json" ] && continue
  mkdir -p "$out"
  while [ "$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits | head -1)" -lt 9000 ]; do sleep 60; done
  echo "$(date) $name eval"
  $LEARN -u scripts/contact_rl_learn.py eval --config a2r/benchmark/contact_rl/configs/runs/single-open_cabinet_door-pull.yaml \
    --cache_root /dev/shm/e10-door88/banks-final --output "$out/eval" --sim_python $SIM --checkpoint "$ck" \
    --eval_types pull0 --rounds 1 --trace_envs 128 --seed 9911 $extra > "$out/eval.log" 2>&1 < /dev/null
  trace=$(ls "$out"/eval/sim_*/trace*.pt | head -1)
  $SIM -u scripts/contact_rl_trace_phases.py classify --trace "$trace" --out "$out/phases.json" > "$out/classify.log" 2>&1 < /dev/null
  python3 - "$out/phases.json" > "$out/pick.txt" <<'PY'
import json, sys
eps = json.load(open(sys.argv[1]))["episodes"]
chosen = {}
for want, n in ((False, 3), (True, 2)):
    for r in [r for r in eps if r["success"] == want][:n]:
        chosen.setdefault(r["episode"], []).append(r["env"])
for k, envs in sorted(chosen.items()):
    print(f"{k}:{','.join(map(str, sorted(envs)))}")
PY
  while IFS=: read k envs; do
    $SIM -u scripts/contact_rl_render.py --task spec:kitchen/open_cabinet_door --trace "$trace" --out "$out/videos/ep$k" \
      --envs "$envs" --episode "$k" --stride 2 --slow 0.5 --width 480 --height 360 --label "$name" > "$out/render_ep$k.log" 2>&1 < /dev/null
  done < "$out/pick.txt"
  echo "$(date) $name done: $(grep -o 'eval open_cabinet_door: [^{]*' $out/eval.log)"
done
echo DIAG_DONE
