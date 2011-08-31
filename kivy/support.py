'''
Support: activate other framework/toolkit inside our event loop
'''

__all__ = ('install_gobject_iteration', )


def install_gobject_iteration():
    '''Import and install gobject context iteration inside our event loop.
    This is used as soon as gobject is used (like gstreamer)
    '''

    from kivy.clock import Clock
    import gobject
    if hasattr(gobject, '_gobject_already_installed'):
        # already installed, don't do it twice.
        return

    gobject._gobject_already_installed = True

    # get gobject mainloop / context
    loop = gobject.MainLoop()
    gobject.threads_init()
    context = loop.get_context()

    # schedule the iteration each frame
    def _gobject_iteration(*largs):
        # XXX we need to loop over context here, otherwise, we might have a lag.
        loop = 0
        while context.pending() and loop < 10:
            context.iteration(False)
            loop += 1
    Clock.schedule_interval(_gobject_iteration, 0)



def install_twisted_reactor(*args, **kwargs):
    '''Installs a threaded twisted reactor, which will schedule one
    reactor iteration before the next frame only when twisted needs
    to do some work.

    any arguments or keyword arguments passed to this function will be
    passed on the the threadedselect reactors interleave function, these
    are the arguments one would usually pass to twisted's reactor.startRunning

    Unlike the default twisted reactor, the installed reactor will not handle
    any signals unnless you set the 'installSignalHandlers' keyword argument
    to 1 explicitly.  This is done to allow kivy to handle teh signals as
    usual, unless you specifically want the twisted reactor to handle the
    signals (e.g. SIGINT).'''
    import twisted

    #prevent installing more than once
    if hasattr(twisted, '_kivy_twisted_reactor_installed'):
        return
    twisted._kivy_twisted_reactor_installed = True

    #dont let twisted handle signals, unless specifically requested
    kwargs.setdefault('installSignalHandlers', 0)

    #install threaded-select reactor, to use with own event loop
    from twisted.internet import _threadedselect
    _threadedselect.install()

    #now we can import twisted reactor as usual
    from twisted.internet import reactor
    from kivy.base import EventLoop
    from kivy.clock import Clock
    from kivy.logger import Logger

    #hook up rector to our reactor wake function
    def reactor_wake(twisted_loop_next):
        '''called whenever twisted needs to do work
        '''

        def call_twisted(*args):
            Logger.trace("Entering Twisted event loop")
            twisted_loop_next()
        Clock.schedule_once(call_twisted, -1)
    reactor.interleave(reactor_wake, *args, **kwargs)

    #make sure twisted reactor is shutdown if eventloop exists
    def reactor_stop(*args):
        '''will shutdown the twisted reactor main loop'''
        from twisted.internet import reactor
        Logger.debug("Shutting down twisted reactor")
        reactor._mainLoopShutdown()
    EventLoop.add_stop_callback(reactor_stop)

