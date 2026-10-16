export type UpdateParticipant = { dirty: boolean; prepare?: () => Promise<boolean> };

export class UpdateCoordinator {
  private readonly participants = new Set<UpdateParticipant>();

  register(participant: UpdateParticipant) {
    this.participants.add(participant);
    return () => { this.participants.delete(participant); };
  }

  async prepare() {
    if (this.hasDirtyWork()) return false;
    const results = await Promise.all(Array.from(this.participants).map((participant) => participant.prepare?.() ?? true));
    return results.every(Boolean) && !this.hasDirtyWork();
  }

  private hasDirtyWork() { return Array.from(this.participants).some((participant) => participant.dirty); }
}
