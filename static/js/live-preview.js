// One KEV request at a time; newer input replaces queued work, never replays old UI.
export class LivePreview {
  constructor(request, apply, status = () => {}) {
    this.request = request; this.apply = apply; this.status = status;
    this.revision = 0; this.pending = null; this.running = false;
  }
  clear() {this.revision++; this.pending = null;}
  update(payload) {
    this.pending = {payload, revision: ++this.revision};
    this.drain();
  }
  async drain() {
    if (this.running || !this.pending) return;
    const next = this.pending; this.pending = null; this.running = true;
    this.status('理解中');
    try {
      const result = await this.request(next.payload);
      if (next.revision === this.revision) this.apply(result);
    } catch (error) {
      if (next.revision === this.revision) this.status('本地预览',error);
    } finally {this.running = false; this.drain();}
  }
}
