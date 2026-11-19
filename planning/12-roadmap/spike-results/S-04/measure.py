import resource, subprocess, sys, time
start = time.time()
done = subprocess.run(sys.argv[1:], capture_output=True, text=True, timeout=120)
peak_mib = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 1024
text = done.stdout + done.stderr
errors = sum(1 for l in text.splitlines() if l.startswith(("ERROR", "FATAL")))
warnings = sum(1 for l in text.splitlines() if l.startswith("WARNING"))
print(f"exit {done.returncode}, {time.time()-start:.1f} s, peak {peak_mib:.0f} MiB, {errors} errors, {warnings} warnings")
open(sys.argv[-1] + ".log", "w").write(text)
