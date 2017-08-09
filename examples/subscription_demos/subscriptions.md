# Subscriptions

I've mentioned this concept in earlier examples. It's a bit confusing at first and is essential to working with large projects using atlasbuggy. We'll discuss four important use cases.

We'll be using examples/subscription_demos/simple.py for this example. Data streams are a great to manage multiple threads and to keep your project organized. One feature that's sacrificed, however, is easy data sharing. It's easy to define a global variable in a single threaded application. Not so when your project is spread across multiple files and classes. Subscriptions make passing data between data streams managable and organized.

The problem we are trying to avoid is code that looks like this:

```python
robot = Robot()

data_generator = DataGenerator()
consumer_and_generator = DataConsumerAndGenerator(data_generator)
consumer = DataConsumer(consumer_and_generator)

robot.run(data_generator, consumer_and_generator, consumer)
```

Say we have a data stream that produces content (e.g. DataGenerator), a stream that takes DataGenerator's output and produces new content, and a stream that takes that new content and does something with it. I hope it's clear that passing references around like this isn't scalable. What if DataConsumer created data that DataGenerator wanted? You'd have to rewrite the code like this:

```python
robot = Robot()

data_generator = DataGenerator()
consumer_and_generator = DataConsumerAndGenerator(data_generator)
consumer = DataConsumer(consumer_and_generator)

data_generator.give_me_consumer(consumer)  # feed consumer back into data_generator

robot.run(data_generator, consumer_and_generator, consumer)
```

It quickly devolves into spaghetti references and it makes coding difficult. Subscriptions give us a solution to this problem.

Subscriptions in atlasbuggy follow what's called the producer-consumer model. One entity produces content while another (or many) consume that content. A producer can also be a consumer and vice versa. Let's move to an actual (somewhat contrieved) example.

# Static Subscriptions

We'll start simple. Say we have a data stream called "StaticStream." It has functionality that another stream, "SomeStream," wants. In this case, StaticStream is the producer since it has information SomeStream wants. SomeStream is consuming the resources StaticStream has.

Let's write some code out. We'll fill the gaps later.

```python
from atlasbuggy.subscriptions import *  # import all subscription types

robot = Robot(write=False)

static = StaticStream()
some_stream = SomeStream()

some_stream.subscribe(Subscription(...))  # tell SomeStream to subscribe to StaticStream

robot.run(static, some_stream)

```

When subscribing to another stream, you need to supply an object that defines the relationship between the two streams. These objects are contained in ```atlasbuggy.subscriptions```. The one we're using here is called Subscription. All it does is offer an instance of the producer stream to the consumer stream. When SomeStream subscribes to StaticStream using the Susbcription relationship, SomeStream now has access to the instance of StaticStream you created.

The Subscription class takes two required arguments. The first is the subscription tag and the stream you are subscribing to. What are subscription tags? Subscriptions are stored in internal dictionaries, so they need a unique identifier. Each stream has its own subscription dictionary so the keys need only be unique between streams. Let's fill that in

```python
some_stream.subscribe(Subscription(some_stream.static_stream_tag, static))  # tell SomeStream to subscribe to StaticStream
```

Note my usage of ```some_stream.static_stream_tag```. We'll define this property when we write the SomeStream class. In general, the consumer stream defines the tag. Producers don't care who consumes their resources. Only the consumer is concerned since it is the entity that needs the resources.

Let's write the SomeStream class.

```python
class SomeStream(AsyncStream):
    """This stream runs and performs some tasks on a stream is subscribes to"""
    def __init__(self):
        super(SomeStream, self).__init__(log_level=20)  # logger.info statements will show up in the output

        self.static_stream_tag = "static"  # a unique tag naming the subscription
        self.static_stream = None  # instance of the stream being subscribed to
        self.require_subscription(...)
```

Let's break this down. ```self.static_stream_tag``` is the tag we used earlier. It can be anything hashable by a dictionary, but I use strings for clarity. ```self.static_stream``` is the instance that the subscription will give us. I've assigned None to it to indicate that this value will be supplied later. 

Let's discuss what ```self.require_subscription``` does. To minimize runtime errors, I've created the require_subscription method to make clear what kinds of resources this stream expects. If those requirements aren't met, an error is thrown.

Let's fill in some of those parameters:

```python
        self.require_subscription(self.static_stream_tag, Subscription)
```

So we're requiring a subscription with the name "static," and the relationship must be of type "Subscription." We can go further and say that the producer stream must be of a certain class type:

```python
        self.require_subscription(self.static_stream_tag, Subscription, StaticStream)
```

We'll create the StaticStream class in a moment.

We want ```self.static_stream``` to contain an instance of StaticStream. This won't happen unless we add a bit of code:

```python
    def take(self, subscriptions):
        self.static_stream = subscriptions[self.static_stream_tag].get_stream()  # obtain the producer
```

```take``` is a method every data stream has. Override this method to receive subscriptions. At runtime, a dictionary of subscriptions is given to the consumer stream. In this case, there is only one entry in the dictionary. It's our Subscription class we instantiated earlier (```some_stream.subscribe(Subscription(...))```). The Subscription class has a method called ```get_stream()```. This will return an instance of the producer stream.

```take``` is called before ```start``` which is another method you can override. It's guarenteed that all subscriptions will be handed out by the time ```start``` is called.

It's worth noting that, since StaticStream is a global variable, the same effect could be achieved by using that global variable directly. The difference here is this way is far more scalable for projects spread across multiple files.

Awesome, so we have an instance of the producer stream. At this point, what you do next depends on what kind of data you're working with. Since we don't have any actual data, we'll create some contrieved functionality. Let's say StaticStream has a counter and a timer we want to manipulate. We want to be able to increment the counter, get the counter's value, and update the timer. We specify these requirements as a part of our subscription:

```python
        # signal that this is a required subscription. The producer stream must have attributes
        # "counter", "increment_counter", and "set_timer"
        self.require_subscription(self.static_stream_tag, Subscription, StaticStream,
                                  required_methods=("increment_counter", "set_timer"),
                                  required_attributes=("counter",))
```

```required_methods``` specifies that the producer stream must have those methods and ```required_attributes``` specifies that the producer stream must have those attributes. Note these must be given as tuples.

Let's implement the StaticStream class with these constraints in mind.

```python
class StaticStream(DataStream):
    def __init__(self):
        super(StaticStream, self).__init__(log_level=20)

        # shared resources
        self.counter = 0
        self.timer = 0.0
```

This class only needs two properties since those are the ones our consumer is requesting. Let's implement the two requested methods:

```python
    def increment_counter(self):
        """
        A required method as a producer for 'SomeStream'
        Increments the counter's value
        """
        self.counter += 1
        self.logger.info("Someone just set my counter to %s" % self.counter)

    def set_timer(self, new_time):
        """
        A required method as a producer for 'SomeStream'
        Sets the timer's value
        """
        self.timer = new_time
        dt = self.dt()
        self.logger.info("Someone just set my time to %0.4f. My current time is %0.4f\n"
                         "The difference is %s" % (self.timer, dt, dt - new_time))
```

Pretty straight forward. Let's do something interesting with these properties. We defined StaticStream as a DataStream which means its run method won't be called. We'll need to use SomeStream's run method to do something interesting. Let's implement that:

```python
    async def run(self):
        while self.is_running():
            await asyncio.sleep(0.5)  # wait for 0.5 seconds

            # update the producer stream's counter
            self.static_stream.increment_counter()
            self.logger.info("Setting %s's counter to %s" % (self.static_stream.name, self.static_stream.counter))

            # update the producer stream's time
            current_time = self.dt()
            self.static_stream.set_timer(current_time)
            self.logger.info("Setting %s's time to %0.4f" % (self.static_stream.name, current_time))
```

Here we making use of all three attributes we required. We are incrementing the counter, checking its value, and setting the timer.

At this point, if you run the program, it should run. Your output should look like this:

```
[StaticStream @ simple.py:63][INFO] 2017-08-09 14:28:10,465: Someone just set my counter to 1
[SomeStream @ simple.py:30][INFO] 2017-08-09 14:28:10,465: Setting StaticStream's counter to 1
[StaticStream @ simple.py:73][INFO] 2017-08-09 14:28:10,466: Someone just set my time to 0.5043. My current time is 0.5045
The difference is 0.00011897087097167969
[SomeStream @ simple.py:35][INFO] 2017-08-09 14:28:10,466: Setting StaticStream's time to 0.5043
[StaticStream @ simple.py:63][INFO] 2017-08-09 14:28:10,967: Someone just set my counter to 2
[SomeStream @ simple.py:30][INFO] 2017-08-09 14:28:10,968: Setting StaticStream's counter to 2
[StaticStream @ simple.py:73][INFO] 2017-08-09 14:28:10,968: Someone just set my time to 1.0066. My current time is 1.0068
The difference is 0.00017499923706054688
```

Note how the output says "Someone just set my counter" and not "SomeStream just set my counter." Producers know nothing about who's consuming their resources. Consumers on the other hand know exactly who they're getting resources from.

This was an exercise in scalable resource sharing. This isn't the true producer-consumer model. Let's explore an example that exactly follows that model: [producer_consumer.md](./producer_consumer.md)