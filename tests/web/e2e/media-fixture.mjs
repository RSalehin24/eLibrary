export function silentAudio() {
  const samples = 4 * 8000, audio = Buffer.alloc(44 + samples * 2);
  audio.write("RIFF"); audio.writeUInt32LE(audio.length - 8, 4); audio.write("WAVEfmt ", 8);
  audio.writeUInt32LE(16, 16); audio.writeUInt16LE(1, 20); audio.writeUInt16LE(1, 22);
  audio.writeUInt32LE(8000, 24); audio.writeUInt32LE(16000, 28); audio.writeUInt16LE(2, 32);
  audio.writeUInt16LE(16, 34); audio.write("data", 36); audio.writeUInt32LE(samples * 2, 40);
  return audio;
}
