#!/usr/bin/env python3
"""WanjieGate 自测:playwright 驱动真实页面,验证 idle→ghost→commit→清空 全链路。"""
import sys, time, json
from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5173/index.html"
SHOTS = ".ai/shots"
import os; os.makedirs(SHOTS, exist_ok=True)

errors = []
def state(page, tag):
    cards = page.eval_on_selector_all(
        "#stage .card",
        "els => els.map(e => ({id: e.dataset.id, op: +getComputedStyle(e).opacity, "
        "p: +(e.dataset.p||0), t: +(e.dataset.target||0), "
        "ghost: e.classList.contains('ghost'), emph: e.classList.contains('emph')}))")
    idle = page.eval_on_selector("#app", "e => e.classList.contains('idle')")
    conn = page.text_content("#conn")
    print(f"[{tag}] idle={idle} conn={conn!r} cards={json.dumps(cards, ensure_ascii=False)}")
    page.screenshot(path=f"{SHOTS}/{tag}.png")
    return cards, idle

with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path="/usr/bin/chromium",
                                 args=["--no-sandbox", "--disable-gpu"])
    page = browser.new_page(viewport={"width": 1400, "height": 900})
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(URL)
    page.wait_for_timeout(1200)

    # 1) idle: 无卡片,输入框居中
    cards, idle = state(page, "1-idle")
    assert idle, "初始应是 idle"
    assert not cards, "初始不应有卡片"
    box = page.locator("#composer").bounding_box()
    vh = page.viewport_size["height"]
    print(f"  composer top={box['y']:.0f} (期望 ~{vh*0.33:.0f})")

    # 2) 逐字输入中文 → 决策帧到达后卡片应以幽灵/实体浮现
    page.click("#input")
    for ch in "看看这周的销售数据和趋势":
        page.keyboard.type(ch); page.wait_for_timeout(60)
    page.wait_for_timeout(400)                    # debounce 之后一帧
    cards, _ = state(page, "2-ghosting")

    page.wait_for_timeout(1500)                   # 材质收敛
    cards, idle = state(page, "3-live")
    assert not idle, "有内容后应离开 idle"
    assert cards, "应有卡片浮现"
    solid = [c["id"] for c in cards if c["op"] > 0.8]
    ghost = [c["id"] for c in cards if c["op"] <= 0.8]
    print(f"  solid={solid} ghost={ghost}")
    assert "chart-card" in [c["id"] for c in cards], "数据语境应有 chart-card"
    chart = next(c for c in cards if c["id"] == "chart-card")
    assert chart["t"] == 1.0, f"意图确定后高概率卡应实体化到 t=1(got {chart})"
    alert = next((c for c in cards if c["id"] == "alert-banner"), None)
    assert not alert or alert["t"] == 0, f"纯销售语境已判定,弱 alert(p~0.2)应退场(got {alert})"

    # 3) 追加 alert 语境 → banner 应顶行出现
    page.keyboard.type("，等等,错误率也飙升了")
    page.wait_for_timeout(2000)
    cards, _ = state(page, "4-alert")
    ids = [c["id"] for c in cards]
    print(f"  cards={ids}")
    alert = next((c for c in cards if c["id"] == "alert-banner"), None)
    assert alert and alert["t"] >= 0.4, f"alert 语境应召出 banner(got {alert})"
    # 空间分划:banner 应是舞台顶部的整宽条带
    stage_box = page.locator("#stage").bounding_box()
    abox = page.locator('.card[data-id="alert-banner"]').bounding_box()
    assert abs(abox["y"] - stage_box["y"]) < 24 and abox["width"] > stage_box["width"] * 0.95, \
        f"banner 应为顶行整宽条带(stage={stage_box}, alert={abox})"

    # 4) 清空 → 收回 idle
    page.fill("#input", "")
    page.wait_for_timeout(1600)
    cards, idle = state(page, "5-cleared")
    assert idle, "清空后应回到 idle"
    assert not [c for c in cards if c["op"] > 0.05], "清空后卡片应散尽"

    browser.close()

print("\nconsole errors:", errors or "none")
print("PASS" if not errors else "PASS (with console errors)")
