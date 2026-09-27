import Cocoa
import WebKit
import Carbon

final class IntentWindow: NSPanel {
    override var canBecomeKey: Bool { true }
    override var canBecomeMain: Bool { true }
}

final class AppDelegate: NSObject, NSApplicationDelegate, NSWindowDelegate, WKNavigationDelegate, WKUIDelegate, WKScriptMessageHandler {
    var window: IntentWindow!
    var web: WKWebView!
    var hotKey: EventHotKeyRef?
    var expanded = false
    var keyMonitor: Any?

    func applicationDidFinishLaunching(_ notification: Notification) {
        let app = NSApplication.shared
        app.setActivationPolicy(.accessory)
        installShortcut()
        let screen = NSScreen.main?.visibleFrame ?? NSRect(x: 0, y: 0, width: 1440, height: 900)
        let size = NSSize(width: min(980, screen.width - 48), height: 144)
        window = IntentWindow(contentRect: NSRect(origin: .zero, size: size),
            styleMask: [.borderless, .nonactivatingPanel], backing: .buffered, defer: false)
        window.title = "万界门 · 意图搜索"
        window.isOpaque = false
        window.backgroundColor = .clear
        window.level = .floating
        window.hidesOnDeactivate = false
        window.isFloatingPanel = true
        window.isReleasedWhenClosed = false
        window.delegate = self
        window.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]
        window.hasShadow = false
        let surface = NSView(frame: NSRect(origin: .zero, size: size))
        surface.wantsLayer = true
        surface.layer?.backgroundColor = NSColor.clear.cgColor
        surface.autoresizingMask = [.width, .height]
        let config = WKWebViewConfiguration()
        config.userContentController.add(self, name: "layout")
        web = WKWebView(frame: surface.bounds, configuration: config)
        web.setValue(false, forKey: "drawsBackground")
        web.autoresizingMask = [.width, .height]
        web.navigationDelegate = self
        web.uiDelegate = self
        surface.addSubview(web)
        window.contentView = surface
        window.setFrameOrigin(NSPoint(x: screen.midX - size.width / 2, y: screen.midY + 60 - size.height / 2))
        keyMonitor = NSEvent.addLocalMonitorForEvents(matching: .keyDown) { [weak self] event in
            if event.keyCode == 53 { self?.hide(); return nil }
            return event
        }
        var url = URLComponents(string: "http://127.0.0.1:5175/launcher")!
        url.queryItems = [URLQueryItem(name: "native", value: "1")]
        if CommandLine.arguments.count > 1 && !CommandLine.arguments[1].isEmpty {
            url.queryItems?.append(URLQueryItem(name: "q", value: String(CommandLine.arguments[1].prefix(1800))))
        }
        web.load(URLRequest(url: url.url!))
        show()
    }
    func installShortcut() {
        var spec = EventTypeSpec(eventClass: OSType(kEventClassKeyboard), eventKind: UInt32(kEventHotKeyPressed))
        InstallEventHandler(GetApplicationEventTarget(), { _, _, context -> OSStatus in
            guard let context = context else { return OSStatus(eventNotHandledErr) }
            let owner = Unmanaged<AppDelegate>.fromOpaque(context).takeUnretainedValue()
            owner.toggle()
            return noErr
        }, 1, &spec, Unmanaged.passUnretained(self).toOpaque(), nil)
        let identity = EventHotKeyID(signature: OSType(0x574A4741), id: 1)
        let status = RegisterEventHotKey(UInt32(kVK_Space), UInt32(controlKey | optionKey), identity,
                                        GetApplicationEventTarget(), 0, &hotKey)
        if status != noErr { NSLog("WanjieGate shortcut unavailable: %d", status) }
    }
    func show() {
        guard window != nil else { return }
        window.makeKeyAndOrderFront(nil)
        NSApplication.shared.activate(ignoringOtherApps: true)
        window.makeFirstResponder(web)
        NSLog("WanjieGate panel shown visible=%d", window.isVisible ? 1 : 0)
        web.evaluateJavaScript("document.getElementById('intent')?.focus()", completionHandler: nil)
    }
    func hide() { window.orderOut(nil); NSLog("WanjieGate panel hidden visible=%d", window.isVisible ? 1 : 0) }
    func toggle() { if window?.isVisible == true { hide() } else { show() } }
    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool { show(); return true }
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { false }
    func windowShouldClose(_ sender: NSWindow) -> Bool { hide(); return false }
    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        show()
        if hotKey == nil {
            web.evaluateJavaScript("document.querySelector('.shortcut-hint').textContent='快捷键已占用 · 从 Vicinae 打开'", completionHandler: nil)
        }
    }
    func userContentController(_ controller: WKUserContentController, didReceive message: WKScriptMessage) {
        guard message.frameInfo.isMainFrame, message.frameInfo.securityOrigin.host == "127.0.0.1",
              let value = message.body as? [String: Any], let next = value["expanded"] as? Bool,
              next != expanded, window != nil else { return }
        expanded = next
        let screen = window.screen?.visibleFrame ?? NSScreen.main!.visibleFrame
        let height: CGFloat = next ? min(560, screen.height - 60) : 144
        var frame = window.frame
        let center = frame.midY
        frame.size.height = height
        frame.origin.y = min(screen.maxY - height - 12, max(screen.minY + 12, center - height / 2))
        window.setFrame(frame, display: true, animate: true)
    }
    func external(_ url: URL) {
        if url.scheme == "https" || (url.scheme == "vicinae" && url.host == "open") {
            NSWorkspace.shared.open(url)
        }
    }
    func webView(_ webView: WKWebView, decidePolicyFor action: WKNavigationAction,
                 decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        guard let url = action.request.url else { decisionHandler(.cancel); return }
        if url.scheme == "http" && url.host == "127.0.0.1" && url.port == 5175 {
            decisionHandler(.allow)
        } else {
            if action.navigationType == .linkActivated { external(url) }
            decisionHandler(.cancel)
        }
    }
    func webView(_ webView: WKWebView, createWebViewWith configuration: WKWebViewConfiguration,
                 for action: WKNavigationAction, windowFeatures: WKWindowFeatures) -> WKWebView? {
        if let url = action.request.url { external(url) }
        return nil
    }
}
let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.run()
