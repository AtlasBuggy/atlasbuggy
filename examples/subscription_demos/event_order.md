# Event Order

When setting up your data streams, it's important to know what order things are called in so you don't break anything by accident. Python is a thread-safe language, but things can still go horribly wrong.

## Static Streams

If you uncomment line 162, ```robot.run(static)``` you'll see how atlasbuggy handles static streams. Only ```take```, ```start```, and ```stopped``` are called. ```started```, ```run```, and ```stop``` are ignored.

```started``` and ```stop``` are called just before and after ```run```. The distinction is that ```start``` and ```stopped``` are called by the main thread while ```started``` and ```stop``` are called by the stream's thread. If you're using an asynchronous stream, this distinct doesn't matter as much. This starts to matter when, for instance, you're using pyserial and you want to make sure you're done reading or writing before you close the serial port.

If this distinction doesn't matter to you, just use ```start``` and ```stop```. This behavior will do what you want most of the time.

## Asynchronous and Threaded Streams

Asynchronous and threaded streams behave similarly to each other. If you enabled tracebacks at the top of the file, you'll see where the calls are made from. Note for ```start```, Robot calls ```start``` directly while the asynchronous ```started``` method is called through asyncio's loop. The threaded ```started``` method is called the from the threading module. This applies to ```stop``` and ```stopped```.

## When should I use these events?

These events are important when you start using shared resources by other subscriptions. You can't access other subscriptions from ```__init__``` because Robot assigns subscriptions at run time. However, you can guarantee when ```start``` is called, all subscriptions have been assigned.

```run``` and ```started``` guarantee that ```start``` has been called for all streams. So if there's some startup behavior that you rely on, this is important to know. This applies to teardown methods too. ```stopped``` guarantees that all streams have called ```stop```.

So use ```take``` for applying subscriptions, ```start``` for startup behavior that doesn't rely on volatile resources (mostly for threaded streams), ```started``` for guaranteeing that all streams have started, ```run``` for your main running behavior (use ```while self.is_running():``` to continuously run until any streams signals to exit), ```stop``` to run teardown behavior in the stream's thread or coroutine, and ```stopped``` for guaranteeing that all streams have stopped.

There's a lot of functionality I haven't discussed but at this point you should be able to tackle most of the code in the atlasbuggy package!! 🎉🎉🎉
