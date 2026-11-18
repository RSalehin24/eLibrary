def render_preview_single_tab_guard_script():
    return """
    <script>
      (function () {
        var LOCK_PREFIX = "ebook_preview_lock:";
        var HEARTBEAT_MS = 4000;
        var STALE_MS = 15000;
        var lockKey = LOCK_PREFIX + String(window.location.pathname || "");
        var tabId =
          (window.crypto && typeof window.crypto.randomUUID === "function"
            ? window.crypto.randomUUID()
            : String(Date.now()) + ":" + Math.random().toString(16).slice(2));
        var heartbeatId = null;
        var blocked = false;

        function nowMs() {
          return Date.now();
        }

        function parseLock(rawValue) {
          if (!rawValue) {
            return null;
          }
          try {
            return JSON.parse(rawValue);
          } catch (error) {
            return null;
          }
        }

        function readLock() {
          try {
            return parseLock(window.localStorage.getItem(lockKey));
          } catch (error) {
            return null;
          }
        }

        function isActiveLock(lockValue) {
          return Boolean(
            lockValue &&
              lockValue.tabId &&
              typeof lockValue.ts === "number" &&
              nowMs() - lockValue.ts <= STALE_MS,
          );
        }

        function writeOwnLock() {
          try {
            window.localStorage.setItem(
              lockKey,
              JSON.stringify({ tabId: tabId, ts: nowMs() }),
            );
          } catch (error) {
            return;
          }
        }

        function clearOwnLock() {
          var lockValue = readLock();
          if (lockValue && lockValue.tabId === tabId) {
            try {
              window.localStorage.removeItem(lockKey);
            } catch (error) {
              return;
            }
          }
        }

        function showBlockedMessage() {
          if (blocked) {
            return;
          }
          blocked = true;
          if (heartbeatId) {
            window.clearInterval(heartbeatId);
          }
          clearOwnLock();
          try {
            window.stop();
          } catch (error) {
            // no-op
          }
          document.open();
          document.write(
            "<!doctype html><html lang='en'><head><meta charset='utf-8'/><meta name='viewport' content='width=device-width, initial-scale=1'/><title>Preview unavailable</title><style>body{font-family:Arial,sans-serif;margin:0;background:#f7f7f7;color:#222;display:flex;min-height:100vh;align-items:center;justify-content:center;padding:24px}main{max-width:560px;background:#fff;border:1px solid #ddd;border-radius:10px;padding:24px;box-shadow:0 8px 24px rgba(0,0,0,.06)}h1{margin:0 0 12px;font-size:20px}p{margin:0;line-height:1.5}</style></head><body><main><h1>Preview already open</h1><p>This book preview is already open in another tab or window. Close the existing preview and try again.</p></main></body></html>",
          );
          document.close();
        }

        function acquireLock() {
          var currentLock = readLock();
          if (isActiveLock(currentLock) && currentLock.tabId !== tabId) {
            return false;
          }
          writeOwnLock();
          var confirmedLock = readLock();
          return Boolean(confirmedLock && confirmedLock.tabId === tabId);
        }

        if (!acquireLock()) {
          showBlockedMessage();
          return;
        }

        heartbeatId = window.setInterval(function () {
          if (blocked) {
            return;
          }
          var currentLock = readLock();
          if (isActiveLock(currentLock) && currentLock.tabId !== tabId) {
            showBlockedMessage();
            return;
          }
          writeOwnLock();
        }, HEARTBEAT_MS);

        window.addEventListener("storage", function (event) {
          if (blocked || event.key !== lockKey) {
            return;
          }
          var currentLock = readLock();
          if (isActiveLock(currentLock) && currentLock.tabId !== tabId) {
            showBlockedMessage();
          }
        });

        window.addEventListener("beforeunload", clearOwnLock);
        window.addEventListener("pagehide", clearOwnLock);
      })();
    </script>
    """
