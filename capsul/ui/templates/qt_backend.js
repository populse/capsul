var backend = {};
window.addEventListener("load", (event) => {
    new QWebChannel(qt.webChannelTransport, function(channel) {
        backend = channel.objects.backend;
        event.currentTarget.dispatchEvent(backend_ready);
    });
});
