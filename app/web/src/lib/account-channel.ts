const channelName = "bengali-library-account";
const changeMessage = "account-changed";

function openChannel() {
  if (typeof BroadcastChannel === "undefined") return null;
  try {
    return new BroadcastChannel(channelName);
  } catch (error) {
    if (!(error instanceof DOMException) || error.name !== "SecurityError") throw error;
    console.warn("Account notifications are unavailable; sessions will be checked on focus.");
    return null;
  }
}

export function notifyAccountChange() {
  window.dispatchEvent(new Event(changeMessage));
}

export function subscribeAccountChanges(onChange: () => void, onLocalChange: () => void) {
  const channel = openChannel();
  const notify = () => { onLocalChange(); channel?.postMessage(changeMessage); };
  window.addEventListener(changeMessage, notify);
  if (channel) channel.onmessage = (event: MessageEvent<unknown>) => {
    if (event.data === changeMessage) onChange();
  };
  return () => { window.removeEventListener(changeMessage, notify); channel?.close(); };
}
