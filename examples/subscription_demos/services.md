# Services

Services are for the case for when different consumers need different kinds of data from the same producer. For example, a video viewer will want the image output from a computer vision pipeline. A data stream that controls a physical robot will want just the important information extracted from the camera. Am I too close to an obstacle for example.

Take a look at camera\_demo.py in examples/camera\_demos for an example on services with computer vision pipelines.

## FloatGenerator

Here, we will go over a more contrived example. Open examples/subscriptions_demos/services.py if you want to follow along. I won't be pasting all the code here. We'll make a data stream that generates floats in different formats. The default service will generate random floating point numbers. We'll add a new service that gives the 8-byte hex representation of the randomly generated float.

```python
        self.hex_byte_service_tag = "hex_byte"
        self.add_service(self.hex_byte_service_tag)
```

Here, I am creating a new service. Every stream has the "default" service so we only need to define the new service we want to add.

Check the file for generating the random floating point number. The important lines are the following:

```python
            await self.post(number)
            
            # ...
            
            hex_bytes = self.float_to_hex(number)
            await self.post(hex_bytes, self.hex_byte_service_tag)
```

To post to the default service, you just call post (if you're in an AsyncStream, make sure to put "await" in front). For new services you add, you need to specify the service tag. That's the second post call.

## FloatConsumer

Let's write a consumer that consumes this new service. You'll see FloatConsumer below FloatGenerator. It should look familiar except now every time it receives a number, it posts a value to its default service:

```python
    async def get_number(self):
        number = await self.float_generator_feed.get()
        self.logger.info("Got number: '%s'" % number)
        await self.post(100.0)
```

This is demonstrating that producers can be consumers and vice versa. In a moment, we'll hook this up such that when FloatGenerator posts something, FloatConsumer will post something in return.

## HexByteConsumer

HexByteConsumer has some minor changes from FloatConsumer:

```python
        self.float_generator_tag = "float_generator"
        self.float_generator_feed = None
        self.hex_byte_service_tag = "hex_byte"
        self.require_subscription(self.float_generator_tag, Feed, service_tag=self.hex_byte_service_tag)
```
Note how I'm using the same value for ```self.float_generator_tag```. You don't actually need to do this. I'm just doing it for consistency. Tags are only unique between streams. Also note how the feed follows the same pattern. In order to specify that we want the ```"hex_byte"``` service and not the default, we need to require it in the call to ```require_subscription```.

An important note, we don't actually need to require the service. Subscriptions are completed dictated by the call to ```consumer_stream.subscribe(consumer_stream.producer_tag, producer_stream)```. It's here that you define what stream you subscribe to, which service you're letting the consumer receive from, and the tag this subscription is using. As a protection against people doing something dumb, ```require_subscription``` was added to give the user some hints as to how the subscription can be configured. There's a big advantage to giving the user this much power which I will get into.

So now when HexByteConsumer is run, it will be receiving data from the ```"hex_byte"``` service instead of the default service, and thus it is the same as FloatConsumer in every other way.

## Testing it out

Let's try running it as is. We'll get to HexAndFloatConsumer, though you might've guessed what it does already.

Instead of using the runner that's in there, try this one:

```python
def run():
    robot = Robot(write=False)

    float_generator = FloatGenerator()
    float_consumer = FloatConsumer()
    hex_byte_consumer = HexByteConsumer(enabled=False)
    float_and_hex_consumer = HexAndFloatConsumer(enabled=False)

    float_consumer.subscribe(Feed(
        float_consumer.float_generator_tag,
        float_generator
    ))

    float_generator.subscribe(Feed(
        float_generator.multiplier_tag, float_consumer
    ))

    robot.run(float_generator, float_consumer, hex_byte_consumer, float_and_hex_consumer)
```

If you run this, you'll see a warning at the top the output. It says one of its subscription types isn't being consumed. This is a warning to you making sure you didn't forget to use one of your resources, so you don't confused when one of streams waits endlessly for data that isn't coming. Remedy this by putting back the ```hex_byte_consumer```:

```python
def run():
    robot = Robot(write=False)

    float_generator = FloatGenerator()
    float_consumer = FloatConsumer()
    hex_byte_consumer = HexByteConsumer()
    float_and_hex_consumer = HexAndFloatConsumer(enabled=False)

    float_consumer.subscribe(Feed(
        float_consumer.float_generator_tag,
        float_generator
    ))
    hex_byte_consumer.subscribe(Feed(
        hex_byte_consumer.float_generator_tag,
        float_generator,
        hex_byte_consumer.hex_byte_service_tag
    ))
    
    float_generator.subscribe(Feed(
        float_generator.multiplier_tag, float_consumer
    ))

    robot.run(float_generator, float_consumer, hex_byte_consumer, float_and_hex_consumer)
```

You may also notice that ```float_consumer``` is subscribing to ```float_generator``` but ```float_generator``` is also subscribing to ```float_consumer```. This is how you set up circular chains of data flow. ```float_generator``` generates data ```float_consumer``` wants but ```float_generator``` also uses the data ```float_consumer``` creates.

## HexAndFloatConsumer

It's also possible for a consumer to subscribe to multiple services provided by one producer stream. You just treat it like your subscribing to two different streams:

```python
        self.float_tag = "float"
        self.float_feed = None
        self.require_subscription(self.float_tag, Feed)

        self.hex_tag = "hex"
        self.hex_feed = None
        self.hex_byte_service_tag = "hex_byte"
        self.require_subscription(self.hex_tag, Feed, service_tag=self.hex_byte_service_tag)
```

I changed the tag names to keep things from getting verbose, but it doesn't matter what I call these so long as I'm consistent when I call ```consumer_stream.subscribe```.

The rest is copy-pasted from the other classes. You could use object-oriented programming here and remove a lot of the copy-pasted code, but I was lazy since this is an example 😁.

Next I would take a look at examples/camera\_demos/camera\_demo.py or go to the next tutorial: [event_order.md](./event_order.md)