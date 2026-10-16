import type { ReaderProgress } from "@/api/types";

export type SaveStatus = "saved" | "pending" | "failed";
type SaveProgress = (progress: ReaderProgress) => Promise<unknown>;

export class ProgressWriter {
  private pending: ReaderProgress | null = null;
  private flight: Promise<boolean> | null = null;
  private failed = false;
  private readonly save: SaveProgress;
  private readonly report: (status: SaveStatus) => void;

  constructor(save: SaveProgress, report: (status: SaveStatus) => void) { this.save = save; this.report = report; }

  get hasFailed() { return this.failed; }

  enqueue(progress: ReaderProgress) {
    this.pending = progress;
    if (!this.failed) this.report("pending");
  }

  async flush(): Promise<boolean> {
    if (this.flight) return await this.flight ? this.flush() : false;
    if (!this.pending) return true;
    const progress = this.pending;
    this.pending = null;
    this.flight = this.persist(progress);
    const success = await this.flight;
    this.flight = null;
    return success && (this.pending ? this.flush() : true);
  }

  private async persist(progress: ReaderProgress): Promise<boolean> {
    try { await this.save(progress); this.failed = false; this.report(this.pending ? "pending" : "saved"); return true; }
    catch { this.pending ??= progress; this.failed = true; this.report("failed"); return false; }
  }
}
