#!/usr/bin/env python3
"""按前端 buildQuestions() 同款问题集探测 kev 服务,对比意图判定质量。"""
import json, sys, urllib.request

BASE = "http://127.0.0.1:8208"
MANIFEST = json.load(open("/home/vimalinx/Projects/VimalinxOS/projects/WanjieGate/static/manifest.json"))

def build_questions():
    q = {}
    for qid, d in MANIFEST["questions"].items():
        q[qid] = {"type": d["type"], "instructions": d["instructions"], "criteria": d.get("criteria")}
    for cid, c in MANIFEST["components"].items():
        q["vis_" + cid] = {"type": "noul", "instructions": c["ask"]}
        if c.get("bind"):
            q["bind_" + cid] = {"type": "choice", "instructions": c["bind"]["question"], "criteria": c["bind"]["options"]}
    for ctx, a in (MANIFEST.get("attachments") or {}).items():
        q["att_" + ctx] = {"type": "noul", "instructions": a["cue"]}
    return q

QUESTIONS = build_questions()

def ask(state, label, show_all=False):
    body = json.dumps({
        "state": {
            "role": "You are the layout engine of an adaptive UI canvas. Decide which interface elements fit the user's text.",
            "note": MANIFEST.get("stateNote", ""),
            "user_text_so_far": state,
            "currently_visible": [],
        },
        "model": "kev-latest",
        "questions": QUESTIONS,
    }).encode()
    req = urllib.request.Request(BASE + "/v1/systemone", data=body, headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        out = json.loads(r.read())
    a = out["answers"]
    intent = a["intent"]
    ps = sorted(intent["probabilities"].items(), key=lambda x: -x[1])
    margin = ps[0][1] - ps[1][1]
    att = {k[4:]: round(v["noul"], 2) for k, v in a.items() if k.startswith("att_") and v["noul"] > 0.25}
    top_vis = {k[4:]: round(v["noul"], 2) for k, v in a.items() if k.startswith("vis_") and v["noul"] > 0.4}
    print(f"\n=== {label}: {state!r}  ({out['latency_ms']}ms)")
    print(f"  intent: {intent['choice']} margin={margin:.2f}  " + "  ".join(f"{k}={v:.2f}" for k, v in ps[:3]))
    print(f"  attach: {att}")
    print(f"  vis>0.4: {top_vis}")

STATES = [
    ("social-ambiguous", "大家在干啥?"),
    ("social-friends", "朋友们都在忙什么"),
    ("social-watch", "看看大家都在干嘛"),
    ("social-full", "我的朋友们最近都咋样了"),
    ("data", "看看这周的销售数据和趋势"),
    ("diary", "今天拍了好多照片,记个日记吧"),
    ("article", "写一篇关于本地大模型的文章"),
    ("bug", "api 一直 502,帮我看看"),
    ("plan", "安排一下明天的工作"),
]

if __name__ == "__main__":
    only = sys.argv[1:] or None
    for label, s in STATES:
        if only and label not in only:
            continue
        ask(s, label)
