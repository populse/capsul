var backend = {};
window.onload = function()
{
    new QWebChannel(qt.webChannelTransport, function(channel) {
        backend = channel.objects.backend;
    });
}
