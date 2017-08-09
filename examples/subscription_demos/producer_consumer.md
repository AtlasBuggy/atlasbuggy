# Feed Subscriptions

In many ways this example is simplier that the "simple" example. In this example, we will implement a true producer-consumer model by making use of atlasbuggy's Feed subscription type.

Here our producer is simply a counter that increments every 0.5 seconds:

```python
class Producer(AsyncStream):
    """This stream produces content"""

    def __init__(self):
        self.counter = 0  # shared resource
        super(Producer, self).__init__(log_level=20)

    async def run(self):
        while self.is_running():
            await asyncio.sleep(0.5)  # wait 0.5 seconds
            self.logger.info("I'm producing '%s'" % self.counter)  # signal that counter was posted
            self.counter += 1  # change the value
```

All this does is increment a counter. We need one more line to make this useful:

```python
            await self.post(self.counter)  # post the shared resource
```

This line will send self.counter to all of Producer's subscribers. How do we receive this post? Let's implement the consumer stream.

```python
from atlasbuggy.subscriptions import *


class Consumer(AsyncStream):
    """This stream consumes content"""

    def __init__(self):
        super(Consumer, self).__init__(log_level=20)

        self.producer_tag = "producer"  # a unique tag naming the subscription
        self.producer_feed = None  # the object that acts a pipe between Producer and Consumer
        self.require_subscription(self.producer_tag, Feed, Producer)  # signal that this is a required subscription
```

This should look familiar (if not look at the subscriptions tutorial: [subscriptions.md](./subscriptions.md)), except this time we are supplying the Feed class instead of the Subscription class. The Feed subscription hides a queue. Queues are first-in-first-out (FIFO). They behave exactly like normal lines that people stand in. The first person there is the first person to exit the queue (assuming nobody is a bad person).

Another note is we will be using ```self.producer_feed``` as opposed to ```self.producer``` since we don't need an instance of Producer. We only need the queue.

Let's retrieve that queue:

```python
    def take(self, subscriptions):
        self.producer_feed = subscriptions[self.producer_tag].get_feed()  # obtain the queue
```

Last time we used ```get_stream()``` to get an instance of the producer stream. You can still do that here, but we only need the queue so we'll only use ```get_feed()```. One subtle point, calling ```get_feed()``` on a Subscription class will raise an exception.

Let's actually do something with the data we get.

```python
    async def run(self):
        while self.is_running():
            counter = await self.producer_feed.get()  # wait for producer to post something
            self.producer_feed.task_done()  # when you're done getting, make sure to call this
            self.logger.info("I consumed '%s'" % counter)  # print to terminal
```

Here, we wait for the producer to post something and print that we got it. An important implementation detail, make sure to call ```self.producer_feed.task_done()``` after you're done getting. You _must_ call ```task_done``` after ```get``` but you also can't call ```task_done``` if you don't call ```get```.

Say you wrote your get loop like this:

```python
        while self.is_running():
            while not self.producer_feed.empty():
                counter = await self.producer_feed.get()  # wait for producer to post something
                self.producer_feed.task_done()  # when you're done getting, make sure to call this
                self.logger.info("I consumed '%s'" % counter)  # print to terminal
            await asyncio.sleep(0.0)
```

Note the addition of ```await asyncio.sleep(0.0)``` here. This is an asyncio detail. This tells asyncio it's ok to switch contexts here. This code will work because you called ```task_done``` after ```get```. This may fail:

```python
        while self.is_running():
            while not self.producer_feed.empty():
                counter = await self.producer_feed.get()  # wait for producer to post something
                self.logger.info("I consumed '%s'" % counter)  # print to terminal
            self.producer_feed.task_done()  # when you're done getting, make sure to call this
            await asyncio.sleep(0.0)
```

Here, I have put ```task_done``` outside the inner while loop. If the feed happens to be empty, ```task_done``` will be called before ```get```. This will cause the program to crash.

Let's finish it off:

```python
robot = Robot(write=False)

producer = Producer()
consumer = Consumer()

consumer.subscribe(Feed(consumer.producer_tag, producer))

robot.run(producer, consumer)
```

Note how I defined Feed as the subscription type.

One thing to try is add a 0.5 second sleep in the consumer stream using ```await asyncio.sleep(0.5)``` and decreasing the producer stream's sleep time to 0.1 seconds. You'll notice the consumer quickly falls behind. If you use the ```while not self.producer_feed.empty():``` code block instead, the consumer will dequeue all values before letting producer post again.

If you set the wait time to 0.0, you'll find that 100% of you CPU is being used. This is because the feed is being checked if it's empty as fast as possible. To avoid this, use this code instead:

```python
    async def run(self):
        while self.is_running():
            await self.get_counter()
            while not self.producer_feed.empty():
                await self.get_counter()
            self.producer_feed.task_done()  # when you're done getting, make sure to call this
    
    async def get_counter(self):
        counter = await self.producer_feed.get()  # wait for producer to post something
        self.logger.info("I consumed '%s'" % counter)  # print to terminal

```

It will wait for the feed to produce content then empty the feed if any more content is available. Note you can call ```get``` as many times as you want before you call ```task_done```.

# Mixing Asynchronous and Threaded Streams

async\_and\_sync.py contains a similar example except the Consumer is a ThreadedStream. Almost everything is the same except when you run it, the program doesn't properly exit until you force quit it.

This is an important difference between threads and asynchronous coroutines and one of the reasons I implemented both in atlasbuggy. When a thread starts, there's very little the main can do to stop it. The reason this program doesn't exit is because ```get``` blocks until new content is posted. Unfortunately, when we exit, no more content is posted so the thread waits forever for new content.

There's a few ways to solve this. We can add a timeout, we can set the thread to be a daemon thread, or we can change how we check the feed.

For the timeout we'd change this line:

```python
       counter = self.producer_feed.get(timeout=0.2)
```

This leaves an ugly error message every time we close the program.

To set the thread to be a daemon thread, we call ```self.set_to_daemon()``` in the constructor (```__init__```). This causes a problem because now self.stop isn't called. This is because the main thread exits and the subthreads don't have time to call the teardown methods.

A more elegant solution is to poll at a rate similar to the producer:

```python
    def run(self):
        while self.is_running():
            while not self.producer_feed.empty():
                self.get_counter()
                self.producer_feed.task_done()
            time.sleep(0.05)
```

In this case, I halved the polling speed. It doesn't really matter how frequently you poll since the ```while not self.producer_feed.empty():``` loop will catch up on any content it missed. This only becomes an issue if you process content at a slower rate than it's produced. For example:

```python
        while self.is_running():
            while not self.producer_feed.empty():
                if not self.is_running():  # prevent the loop from processing frame after shutdown
                    return
                
                self.get_counter()

                time.sleep(0.5)  # some time consuming operation

                self.producer_feed.task_done()
            time.sleep(0.05)
```

If this is your problem, you should consider the Update subscription type.

# Update Subscriptions

Update subscriptions are containers that only hold the latest piece of content. If a producer creates new content before the consumer has time to finish consuming it, the old content is thrown out in exchange for the new content.

update.py has this example. Update subscriptions still work between asynchronous and threaded streams.

Everything is the same except for some subtle differences. For Update subscription types, there is no need to call ```task_done```. Also since this isn't a queue, there's no need to call ```self.producer_feed.empty()``` in a loop.

Now when the program is run, the consumer is only consuming the latest piece of data. Hooray, problem solved!

The next example details what to do when you want a producer to produce different kinds of data: [services.md](./services.md)