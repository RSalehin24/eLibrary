use tokio::signal::unix::{Signal, SignalKind, signal};
use tokio::sync::watch;

/// Fires once on SIGTERM (container stop) or SIGINT; shared by every listener so all drain together.
#[derive(Clone)]
pub(crate) struct ShutdownSignal(watch::Receiver<bool>);

impl ShutdownSignal {
    /// Registers the handlers now, so a signal arriving during startup is not lost.
    pub(crate) fn install() -> std::io::Result<Self> {
        let terminate = signal(SignalKind::terminate())?;
        let interrupt = signal(SignalKind::interrupt())?;
        let (sender, receiver) = watch::channel(false);
        tokio::spawn(notify_on_signal(terminate, interrupt, sender));
        Ok(Self(receiver))
    }

    pub(crate) async fn wait(self) {
        let mut receiver = self.0;
        let _ = receiver.wait_for(|stopped| *stopped).await;
    }
}

async fn notify_on_signal(
    mut terminate: Signal,
    mut interrupt: Signal,
    sender: watch::Sender<bool>,
) {
    tokio::select! {
        _ = terminate.recv() => {}
        _ = interrupt.recv() => {}
    }
    let _ = sender.send(true);
}
