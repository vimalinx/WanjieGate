#!/usr/bin/env python3
"""kev sanity check: 中英文 state + UI 决策问题,打印概率分布与延迟。"""
import json, sys, urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8208"

QUESTIONS = {
    "intent": {
        "type": "choice",
        "instructions": "What is the user most likely doing with this text?",
        "criteria": {
            "analyze-data": "describing or asking about numbers, metrics, trends, or a dataset",
            "write-document": "drafting prose, notes, an article, or documentation",
            "monitor-status": "watching a system, service, or ongoing process",
            "plan-work": "listing tasks, steps, a schedule, or a timeline",
            "report-issue": "describing a problem, bug, alert, or something broken",
            "explore": "just exploring, chatting, or no clear task yet",
        },
    },
    "show_chart": {"type": "noul", "instructions": "Should the UI show a trend chart?"},
    "show_alert": {"type": "noul", "instructions": "Should the UI show a prominent alert/warning banner?"},
    "show_table": {"type": "noul", "instructions": "Should the UI show a detail table of rows?"},
    "density": {
        "type": "score",
        "instructions": "How much information should be on screen? 0 = almost nothing, 4 = dense dashboard.",
        "criteria": ["nearly empty", "one or two elements", "a few elements", "several elements", "dense dashboard"],
    },
}

STATES = [
    ("zh-data", "帮我看看这周的销售数据趋势,营收好像涨得不错,把图表和明细表都摆出来"),
    ("zh-alert", "线上服务挂了!错误率飙升,赶紧看监控"),
    ("zh-plan", "列一下明天要做的事:\n- 设计评审\n- 接口联调\n- 发布"),
    ("zh-empty", "嗯"),
    ("en-data", "show me the weekly sales trend and put the detail table next to it"),
    ("en-alert", "prod is down, error rate spiked to 12%, need the monitoring dashboard now"),
]


def ask(state, label):
    body = json.dumps({
        "state": {
            "role": "You are the layout engine of an adaptive UI canvas. Decide which interface elements fit the user's text.",
            "note": "The user is typing; text may be mid-sentence.",
            "user_text_so_far": state,
        },
        "model": "kev-latest",
        "questions": QUESTIONS,
    }).encode()
    req = urllib.request.Request(BASE + "/v1/systemone", data=body, headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        out = json.loads(r.read())
    print(f"\n=== {label}: {state[:40]!r}  ({out['latency_ms']}ms, {out['usage']['input_tokens']} tok)")
    for qid, a in out["answers"].items():
        if a["type"] == "noul":
            print(f"  {qid:12s} p(yes)={a['noul']:.3f}")
        elif a["type"] == "choice":
            probs = "  ".join(f"{k}={v:.2f}" for k, v in sorted(a["probabilities"].items(), key=lambda x: -x[1]))
            print(f"  {qid:12s} {a['choice']} (conf {a['confidence']:.2f})  [{probs}]")
        else:
            print(f"  {qid:12s} score={a['score']:.2f}  {a['probabilities']}")


if __name__ == "__main__":
    for label, s in STATES:
        ask(s, label)
