# Simple Arduino reader and writer

This is most important and most fun part of this code base in my opinion. What's a robot that can't move! Arduinos are the most common open source microcontroller, but atlasbuggy is flexible to any device that uses serial (MicroPython and the PyBoard is one example: http://micropython.org).

This example walks through the reader_writer.py example in examples/serial_demos. This example assumes you have some Arduino experience. If you don't, I would look up guides on getting started. Get to the point where you can run basic examples. Read up on the documentation for Serial: https://www.arduino.cc/en/Serial/Read and related pages.

## What does atlasbuggy for microcontrollers?
In short, atlasbuggy makes working with low level hardware easy and manageable. It creates a bridge high level software to low level devices (ex. sensors, motors, LEDs).

The general set up is an Arduino is hooked up to a unix computer (raspberry pi, ubuntu, or macOS machine) via USB or some other serial cable. The Arduino is serving as the mediator between low level sensors and actuators. Unless you have a special device, most personal computers can't directly interface with motors or sensors that you buy off Adafruit or Pololu. Nor would you need them to. The Arduino here isn't the main control unit but the glue between the PC and the sensors and motors.

## How do microcontrollers and PCs communicate?
Most computers at the time of writing have USB ports. Almost all Arduinos use this interface for loading programs and printing debug messages. We'll be using this same interface to transfer data. Serial.print isn't like a print statement in python. This function sends bytes over the USB wire to the serial monitor on your PC. Bytes can go the other way too (e.g. Serial.read).

Python has a great module called pyserial that allows Python programs to read and write data to and from serial devices. Atlasbuggy takes advantage of pyserial's functionality.

We'll only be atlasbuggy libraries to implement these examples. If you want to see how to use pyserial without atlasbuggy, check out this great example: https://www.instructables.com/id/Interface-Python-and-Arduino-with-pySerial/

This example uses the standard Arduino IDE, but platformio is encouraged for more advanced users comfortable with command line tools. Examples using both platforms are provided. Be sure to download this repository: https://github.com/Atlasbuggy/AtlasbuggyLowLevel

The low level libraries aren't included with atlasbuggy because this package doesn't care where the data comes from so long the device abides some loose protocols which we will discuss.

## Let's get started already!!
With the background out of the way, let's dive in. I'll be using the Arduino IDE for this example but the general set up for other development environments is similar enough. If you're writing the code from scratch, create a new folder. Inside that folder (I've called reader_writer_bot in the document), mimic the following diagram:

```
|--reader_writer_bot
|  |--ReaderWriter
|  |  |--ReaderWriter.ino
|  |--reader_writer.py
```

Creating a new Arduino sketch called ReaderWriter will put a .ino file inside a folder called ReaderWriter. Create an empty .py file called reader_writer under reader_writer_bot.

It doesn't actually matter where you put the Arduino sketch or the python file. This structure makes it clear these files belong to the reader_writer_bot. The .ino and .py files run on the Arduino and PC respectively. ino files for the Arduino, py files for the PC.

The second part is to install the atlasbuggy Arduino library. Navigate to AtlasbuggyLowLevel/Arduino/libraries/Atlasbuggy and copy the Atlasbuggy folder to the libraries folder in your Arduino sketchbook folder.

```
|--<Arduino sketchbook folder (usually in ~/Arduino)>
|  |--libraries
|  |  |--Atlasbuggy
|  |  |  |--Atlasbuggy.h
|  |  |  |--Atlasbuggy.cpp
|  |--Other Arduino sketches
|  |--...
|  |--...
```

That should be it!

## Implementing the Arduino code
Let's open ReaderWriter.ino. There should be two functions, setup and loop. The first thing we need to do is include the Atlasbuggy libraries:

```cpp
#include "Atlasbuggy.h"
```

Then instantiate an instance of atlasbuggy:

```cpp
Atlasbuggy robot("my_reader_writer_bot");
```

```"my_reader_writer_bot"``` is an important aspect of why working with atlasbuggy makes serial convenient. We'll get to exactly what this string means but essentially it's a unique identifier for your device. Every device that's connected to your PC should have a different identifier. You can name it whatever you like but it has to be unique!

Next, get the robot ready:
```cpp
robot.begin();
```

Behind the scenes, this is setting Serial's baud rate to 115200, timeout to 100ms, and lighting up LED13. If you don't know what this means, I highly recommend reading up on Arduino's Serial library first. If you require a different baud rate, there are workarounds for you. I'll do my best to provide an example.

Next, provide some initialization values. See the lines below ```// ...checking some values...```. You'll need to make your best judgement for this part.

Initialization data is data that's passed from the Arduino to the PC when the python program first starts up. These data are typically constants the Arduino uses and the PC should know about. Some specific examples are the update rate of a GPS, the maximum speed of a motor, the limits on a servo, the number of leds on a strip. These values are important constants that are subject to change. Bad use cases really depend on what kind of data you need. If you define a constant and send it over to the PC but never use it in the Arduino, that's a wasted resource. It'd be much easier to define that constant in python and leave the Arduino in ignorant bliss.

In the loop function, write this code block:

```cpp
    while (robot.available())
    {
        
    }
```

loop is called well... in a loop! This while loop doesn't loop forever. It loops while there's stuff available in the Arduino's serial buffer. 

Inside that block, add the following:

```cpp
        int status = robot.readSerial();
        if (status == 0) {  // user command
            String command = robot.getCommand();
        }
```

```robot.readSerial()``` utilizes Serial.read. Specifically ```Serial.readStringUntil('\n')```. Atlasbuggy reserves the newline character. Each new message is separated by \n (10 or 0xA in number form). Every time robot.readSerial is called, it discovers a new message on the buffer separated by \n characters.

It's worth mentioning atlasbuggy will only accept ascii characters \t, \n, \r and characters with values from 20 to 126 (all letter and number characters with some punctuation). This is to avoid decoding errors. So to send the number 240, instead of sending the character '\xf0' or 'ð', send three characters '2', '4', and '0'. Same applies to sending floating point numbers.

The important concept to understand about serial is data is sent one character or byte at a time. The maximum amount of data that can be sent at any one time is a value from 0...255. However, these characters can be concatenated together to form much more complex messages. The problem is when to stop concatenating? What separates one message from the next. The technique I've chosen here is to split the message whenever a particular character appears. This has the disadvantage of making the character \n unusable for anything else except message breaks, but it makes message forming very simple. Other devices like SICK's LMS200 LIDAR implement a different way of parsing bytes, but I won't go into detail here.

The status code indicates what sort of command was received. 0 indicates a user sent some data. 1 indicates the python program started and 2 indicates it stopped. There are a handful of other codes but we'll get to them later. PLEASE NOTE the letter s is reserved as a command. This is a fix for Arduinos under heavy CPU loads. It has the status code 5. -1 indicates the Arduino is paused (pausing occurs when the python program stops).

```String command = robot.getCommand();``` retrieves the data that was sent by the user. This is only needed for user commands since no other data is sent when stopping and starting. ```command``` contains the concatenated bytes up to but not including \n. So if you sent ```Hello Arduino from Python <3\n``` to the Arduino, ```command``` would contain the string ```Hello Arduino from Python <3```.

Add the following code blocks for completeness below the user status code block:

```cpp
        else if (status == 1) {  // stop event
        
        }
        else if (status == 2) {  // start event
        
    }
```

Finally, outside the robot.available() while loop block, add the following:

```cpp
    if (!robot.isPaused()) {
    
    }
```

Code in this block will run continously while the python program is running and be ignored when the python program stops.

Another important concept to understand here is the Arduino and PC run separately from each other. Arduinos are constantly executing code when powered on (delay just inserts a bunch of no operation instructions). So when the python program stops, the Arduino receives a stop event. This indicates that robot.isPaused() should return true and to call the stop event. While paused, the Arduino sleeps for 100ms and checks serial every loop. This saves the Arduino some CPU cycles.

## Filling in the code blocks

Let's make this code actually do something! Every Arduino is equipped with an LED on pin 13 as far as I know, so that's what we'll use. Surprise! This example was just a roundabout way of implementing blink.

The Atlasbuggy uses LED13 as a debug light to let the user know if it's running or not, but we can still use it without worry. In fact, let's use the setLed method in Atlasbuggy! We'll implement three methods associated with controlling a binary device: on, off, and toggle

Write the following code (user command block included for convenience):

```cpp
        if (status == 0) {  // user command
            String command = robot.getCommand();
        
            if (command == "on") {
                robot.setLed(true);
            }
            else if (command == "off") {
                robot.setLed(false);
            }
            else if (command == "toggle") {
                robot.setLed(!robot.getLed());
            }
        }
```

We'll also add create some dummy data to send back to the PC. For now, we'll send the Arduino's clock time. In the isPaused code block, write the following:

```cpp
        Serial.print(millis());
        Serial.print('\n');
```

Serial.write() is valid as well. Make sure to use ```Serial.print('\n');``` and not ```Serial.println(millis());```. Serial.println ends every message with \r\n. We don't want extraneous \r's in our messages.

This will completely flood our buffer with the current time in milliseconds. To avoid this, let's add a timer. When designing Arduino code for atlasbuggy __make sure you avoid using ```delay```__. Delay stops the program for listening to serial. The Arduino's serial buffer is limited so it's possible to drop large portions of your commands. I would also avoid any Arduino libraries that use delay in their code.

Add a timer variable somewhere below the ```#include "Atlasbuggy.h"```

```cpp
uint32_t timer = millis();
```

Insert this code:

```cpp
    if (!robot.isPaused()) {
        if (timer > millis())  timer = millis();  // reset the timer if there is overflow
        if ((millis() - ping_timer) > 500) {  // every 0.5 seconds, print the current time in milliseconds
            Serial.print(millis());
            Serial.print('\n');
        }
    }
```

Since that's the only thing I can guarentee you have on your Arduino, that's all I can do for this example unfortunately. I encourage you to get creative here and try adding some servos or sensors to this sketch. Take advantage of atlasbuggy's start and stop events for initializating and deinitializing elements and the isPaused method.

Before writing any python code, I suggest booting up Arduino's built-in serial monitor and testing your code out. The characters sent here are the same ones we'll be telling python to send.

Check the bottom right corner of the window. Make sure you see "Newlines" and "115200 baud." This ensures the correct baud rate and that we're sending \n characters every time we hit enter. All you really need to send is ```start```, but the sequence of commands sent are, ```whoareyou```, ```init?```, ```start```, ```stop```. I'll go over what all of these mean when we implement the python code. When you type ```start```, the Arduino is now ready to receive commands. 

If you wrote the example exactly as I wrote it, you should just see the current time since the Arduino started in milliseconds flooding your screen. Type ```stop``` to pause the Arduino.

While the Arduino is unpaused, try typing ```toggle```. You should see your Arduino's LED change state. Hooray!! You have the start of your own little robot. Now let's do in python.

Make sure to check https://github.com/Atlasbuggy/AtlasbuggyLowLevel/Arduino/ReaderWriter for the completed example.

## Implementing the Python code

Open your empty reader_writer.py file. This part requires some understanding of how object oriented programming works in Python. There's plenty of books and tutorials that explain this better than me. It's worth spending a minute reading up on if you're unfamiliar with this concept.

Everything that generates, passes, or processes data in an atlasbuggy project should be a data stream. In this case, a serial port is generating data. We will create an object that manages all serial ports and an object for each port. This managing object will be a subclass of SerialStream. Each port object is a SerialObject.

Let's start with the SerialObject. Put the following import statement at the top of your file:

```python
from atlasbuggy.serial import SerialStream, SerialObject
```

Create a new class and subclass SerialObject:

```python
class ReaderWriterInterface(SerialObject):
    def __init__(self):
        
```

Recall we sent two initialization values using setInitData in the Arduino code. Let link them in the python code. Create two variables in the \_\_init__ method and set them equal to None. I like to set variables that will be initialized later equal to None.

```python
    def __init__(self):
        self.magic_value_1 = None
        self.magic_value_2 = None
```

Now, since we're subclassing SerialObject, we need to call its constructor:

```python
        super(ReaderWriterInterface, self).__init__("my_reader_writer_bot")
```

This line is really important. You'll notice ```"my_reader_writer_bot"``` matches the string we defined in the Arduino code. Behind the scenes, this ID is called a "whoiam ID." If you want this SerialObject to be paired with the right Arduino at runtime, make sure these IDs match. If two of the same ID appear at runtime, atlasbuggy will point out that you likely uploaded the same code to two Arduinos by accident. When the command ```whoareyou``` is sent, ```my_reader_writer_bot``` should come back. That port is then assigned to this SerialObject.

As a side note, here's where you'd set an alternative baud rate. There's a parameter called baud. If you set this equal to something, atlasbuggy will attempt to switch to that baud rate after it finds your SerialObject's port. In the Arduino code, call ```robot.changeBaud()``` in the start event block. Make sure to call it again in the stop block to reset it: ```robot.changeBaud(DEFAULT_RATE);```

We want to assign these "magic values" something meaningful. There's no way to do this in the SerialObject's constructor. The ```init?``` command isn't sent until later. For this, we will override the ```receive_first``` method:

```python
    def receive_first(self, packet):
```

```packet``` contains the initialization data sent when the Arduino unpauses. We want a way to be able to parse out the information and assign it to ```self.magic_value_1``` and ```self.magic_value_2```. In reader_writer.py I have implemented three different ways of parsing. Choose the one you're most comfortable with. In the long run, I recommend regex (http://regex101.com/). It's a string parsing language. Once you get the hang of it, it's really easy to parse arbitrary and complex strings.

When designing this portion of the package, I tried to make it flexible. Instead of having to learn protocols, you get to define how data is sent and parsed. It makes life much simpler.

Here's the code to parse the values using regex (make sure to ```import re``` at the top of your file):

```python
        match = re.match(r"(?P<magic_val_1>[0-9]*)\t(?P<magic_val_2>[0-9]*)", packet)
        if match is None:
            self.logger.warning("Failed to parse initial packet: %s" % packet)
        else:
            values = match.groupdict()
            self.magic_value_1 = int(values["magic_val_1"])
            self.magic_value_2 = int(values["magic_val_2"])
```

We also said that we'd be sending the Arduino's current time every 0.5 seconds. Since there isn't a whole lot we can do with this information, let's just print it:

```python
    def receive(self, timestamp, packet):
        self.logger.info("interface received: '%s' @ %0.4f" % (packet, timestamp))
```

An important note is logger can only accept one string parameter. It doesn't behave like the print statement. Look up string formatting if you don't know what's going on in this line.

Finally, let's hook up the three commands ```on```, ```off```, and ```toggle```:

```python
    def on(self):
        self.send("on")

    def off(self):
        self.send("off")

    def toggle(self):
        self.send("toggle")
```
SerialObject implements a method called ```send```. Strings passed in will be sent to the Arduino.

That's everything we coded our Arduino to do, so we're done! At least, with this part.

### Implementing the serial manager

This object isn't actually a subclass of DataStream, so it won't do anything if we pass it to a Robot object. We need a SerialStream to manage all of our SerialObjects:

```python
class ReaderWriterRobot(SerialStream):
    def __init__(self, enabled=True, log_level=None):
    
```

I've added enabled and log_level as parameters so we can easily toggle this object and debug it.

Instantiate ReaderWriterInterface and give it to the super class:

```python
   self.interface = ReaderWriterInterface()
   super(ReaderWriterRobot, self).__init__(self.interface, enabled=enabled, log_level=log_level)
```

That's actually all we need to do for this class, but this is a pretty boring stream as it is. Let's tell the LED to toggle every 0.5 seconds.

Define a method called timed_toggle:

```python
    def timed_toggle(self):
        self.interface.toggle()
```

In the ```__init__``` method, let's tell SerialStream to call this method every 0.5 seconds. __Make sure to put this line after the call to ```super()```__. ```self.link_recurring``` adds to a lookup table that only gets initialized after the call to the super class.

```python
        self.link_recurring(0.5, self.timed_toggle)
```

Let's add a callback so the SerialStream knows when ReaderWriterInterface receives a packet:

    def interface_received(self, timestamp, packet):
        self.logger.info("notified that interface received: '%s' @ %0.4f" % (packet, timestamp))

put this in the ```__init__``` (after the call to ```super()```):

```python
        self.link_callback(self.interface, self.interface_received)
```

Callbacks are great for signalling other streams when data comes in or for transferring data between multiple Arduinos. Here it's pretty useless since we don't have any other data streams to talk to and we only have one Arduino.

Finally, below both of these classes, instantiate robot:

```python
robot = Robot()

reader_writer = ReaderWriterRobot()

robot.run(reader_writer)
```

If your Arduino code worked, running this python file should work too. Congratulations!! You now have a python project that controls your Arduino. This small project can easily be expanded to accept multiple Arduinos and process much more complex data at fast pace.

I encourage you to dig through the other serial examples for more complex implementations.

Return to the main readme for the next example: [README.md](../../README.md)