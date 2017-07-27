Welcome to the atlasbuggy repository! This readme will serve as a high level design document.

# Table of Contents
1. [Software setup](#setup)
    1. [Dependencies](#dependencies)
1. [Background](#background)
    1. [Why does this project exist?](#why)
    1. [How will we fulfill this purpose?](#how)
    1. [What does this require?](what)
    1. [When will this project finish?](#when)
    1. [Who does this project involve?](#who)
    1. [Where will the final product fit in with the rest of Atlas](#where)
1. [Examples](#examples)
    1. [Video player](#video-player)
    1. [Simple Arduino reader and writer](#simple-arduino-reader-and-writer)
    1. [Naboris](#naboris)
    1. [Naboris simulator](#naboris-simulator)
    1. [LMS200 LIDAR](#lms200-lidar)
    1. [LMS200 LIDAR simulator](#lms200-lidar-simulator)
    1. [RoboQuasar](#roboquasar)

# Software setup <a name="setup"></a>
## Dependencies

Atlasbuggy mostly uses modules in python's standard library. So the only critical dependency is python 3.5 or higher. Atlasbuggy utilizes asyncio which was made standard in 3.5.<br/><br/>

Most dependencies can be installed with python's "pip." Depending on your installation, pip can be run by either typing "pip" or "pip3" in the terminal. Make sure you know what version of pip you have so you don't install modules to the wrong place! I'm going to assume you're on macOS or linux and pip is installed under pip3.

If you encounter permission errors on macOS or linux, try adding ```sudo``` to the beginning of your command.

However, there are some dependencies you'll want to get if you want to get the most out of this repository:
1. pyserial - for working with usb serial devices such as arduino
    ```bash
    pip3 install pyserial
    ```
1. opencv - for camera visualization. https://www.pyimagesearch.com has some great tutorials on how to get this set up
1. flask - website hosting for remote control of robots
    ```bash
    pip3 install flask
    ```
1. matplotlib - for data visualization
    ```bash
    pip3 install matplotlib
    ```
1. picamera - for accessing the raspberry pi camera (obviously only get this if you're on a raspberry pi)
    ```bash
    pip3 install picamera
    ```
1. scipy and numpy - advanced matrix manipulation. Essential for autonomous algorithms. (Numpy is a dependency of scipy and opencv)
    ```bash
    pip3 install numpy scipy
    ```

That should be it!

## Installation
Since atlasbuggy is not on pip, you can't install it that way. Python packages are installed in either dist-packages or site-packages on your computer somewhere.

### macOS and linux instructions
Boot up your terminal application and download the repository into the directory of your choice. It will create a folder called atlasbuggy and fill it with the repository:
```bash
git clone https://github.com/AtlasBuggy/atlasbuggy.git
```

To find this directory, type the following:
```python
$ python3  # or whatever command starts the python repl for you
>>> import sys
>>> sys.path
```
Look for the path that ends with ```site-packages```. If you can't find it, sys.path lists every path it checks for modules in. Search those directories until you find site-packages.

On macOS and linux, to create a link between folders (or a symlink), type the following:
```bash
sudo ln -s $PWD/atlasbuggy /usr/local/lib/python3.6/site-packages
```
This is assuming my site-packages folder is called /usr/local/lib/python3.6/site-packages, I've installed atlasbuggy in ~/Documents, and I'm currently in the Documents directory. It's important to symlink absolute directories (not ../some_other_directory) so that links don't confused. $PWD inserts the current directory you're in. This operation requires administrator privileges.

Try it out:
```python
python3
>>> import atlasbuggy
>>> atlasbuggy.get_platform()  # for me this returns 'mac'
mac
```

## Development environment
I highly recommend PyCharm if you're developing in python: https://www.jetbrains.com/pycharm/. It's a battery guzzler, but it's free and offers some really fantastic features like jump to definition, code reformatting, and refactoring (moving and renaming elements without breaking code) to name a few. It's not necessary but PyCharm is worth at least checking out.

If you plan on creating your own robot, I recommend getting an SFTP and SSH client. Most robots run headless (without a display). SFTP and SSH allow you to access another computer's file system and terminal remotely provided you know the address, username, and password and the computer is broadcasting itself. I won't give details here since everyone's setup varies. For macOS users, I recommend Transmit by Panic (https://www.panic.com/transmit/).

# Background <a name="background"></a>
## Why does this project exist? <a name="why"></a>

Developing robotic systems is difficult. ROS (http://www.ros.org) made me an unhappy programmer, so I decided to write my own robotics development package; one that I would enjoy working with.<br/>

I used this framework I created on two robots:
RoboQuasar (URL on the way),<br/>
-insert image-<br/><br/>
and Naboris (https://github.com/AtlasBuggy/Naboris)<br/>
-insert image-<br/><br/>

I've had a fun time developing this platform. My goal is to offer people frustrated with ROS an alternative.

## How will we fulfill this purpose? <a name="how"></a>

By creating a pythonic collection of code that lets vastly different pieces of software play nice together independent of hardware platform. This should sound familiar to ROS. The only difference is the implementation and a few key design decisions.

## What does this require? <a name="what"></a>

We need a way of managing data transfer, low level hardware devices, high level algorithms, and user interfaces and a way to make all of this manageable and accessible.<br/><br/>

This translates to concurrency and multitasking, low level byte transfer via protocols, subscriptions, and microcontroller programming. Thankfully, Python and Arduino (as well as other languages and platforms) makes this feasible and, for some, fun. All of these concepts will be detailed in the coming sections.

## When will this project finish? <a name="when"></a>

This project is a portion of a larger autonomous vehicle project. The repository can already pilot complex robotics systems, but has yet to get the autonomous vehicle across the finish line. So the main deadline as of now is April 2018, but hopefully the project will continue indefinitely.<br/><br/>

Generally, the timeline is get the repository tested and running before returning to the main robot in fall, make sure the old low level Arduino code on the main robot still works with current system (there should be minimal changes), get manual mode operational, develop autonomous algorithms with the available sensors, perform tests, iterate until the deadline.

## Who does this project involve? <a name="who"></a>

The audience is primarily anyone on the Atlas team, but because of the flexible nature of the code, the audience is also anyone interested in building their own robot.

## Where will the final product fit in with the rest of Atlas? <a name="where"></a>

Atlasbuggy will be running on all of our robots including test rigs (such as Naboris). It will be running while the robot is driving the course and offline in simulations.

# Examples <a name="examples"></a>
Here's a collection of examples on how to use this repository effectively. I will be walking through code I've written on a high level. If you want to drive into the code, feel free. I'm doing my best to keep my comments up to date. The first two examples are in the examples folder.

## Video player

Assuming you have the dependencies set up and have followed the installation instructions, let's dive in! This demo assumes you have opencv 3 installed. Make a new python file and call it "video_demo.py" or whatever you want.

First, you'll want to import Robot. This class manages all the components of our robot.
```python
from atlasbuggy import Robot
```

Next we'll want to initialize the robot
```python
robot = Robot()
```

We want this to be a simple video player, so let's import the video player stream. Put all your imports at the top of the file.

```python
from atlasbuggy.cameras.videoplayer import VideoPlayer
```

Initialize the video player stream. It's important to put this after initializing the robot. Replace ```"..."``` with a path to a video. You can't resize the window after it launches, so put a small-ish width and height.
```python
video = VideoPlayer(file_name="...", width=800, height=500)
```

Next we'll want a way to view the video, so let's import a viewer stream. There a basic viewer, CameraViewer, and a featured viewer, CameraViewerWithTrackbar. CameraViewerWithTrackbar works out of the box while CameraViewer requires subclassing to function.
```python
from atlasbuggy.cameras.viewer import CameraViewerWithTrackbar  # put this at the top

viewer = CameraViewerWithTrackbar()  # put this below robot's definition
```

Now we need to tell the viewer where the video source is. First import subscriptions,
```python
from atlasbuggy.subscriptions import *
```

then link the viewer and the video.
```python
viewer.subscribe(Update(viewer.capture_tag, video))
```

Let me explain what's going on. CameraViewerWithTrackbar requires a subscription which is explicitly defined in its constructor (atlasbuggy/cameras/viewer/trackbar.py and see for yourself). A subscription is essential a data pipe that two data streams share. When the viewer "subscribes" to the video player, the viewer is now listening for data from the video player.

Update is a subscription type that defines one possible relationship these two streams can have. This subscription type acts like a mailbox. The video player "posts" one frame of the video in the mailbox. The viewer sees that there is something new in the mailbox so it "get"'s it. Get and post are the names of methods used in this process. If the video player adds a new frame before the viewer can grab it, the video player discards the old frame and replaces it with a new one. This is so the viewer doesn't get behind when displaying frames.

capture_tag is a property of CameraViewerWithTrackbar. Most data streams define the subscription tag with \<something\>_tag. Check the stream's documentation for that.

The last step is to tell the robot to run.
```python
robot.run(video, viewer)
```

To make sure the viewer displays every single frame the video player posts, try replacing Update with Feed. Under the hood, this is a shared Queue object. The first object in will be the first out (FIFO). If you're waiting in line, you're in a queue. The first person to get in line will be the first person who gets out of the line. Try changing Update to Feed. Notice how when you click the trackbar, the jump isn't as instantaneous. The viewer needs to catch up to the video.

This example is in atlasbuggy/examples.

So let's break that down. We initialized the Robot class before all our data streams, we initialized all the data streams we wanted the robot to run, we defined how streams pass data to each other with subscriptions, and we told the robot to run both the viewer and the video player.

Simple as that! Check the examples folder for more complex video viewers like adding your own key mappings and applying your own opencv filters to the video.

## Simple Arduino reader and writer

This is most important and most fun part of this code base in my opinion. What's a robot that can't move! Arduinos are the most common open source microcontroller, but atlasbuggy is flexible to any device that uses serial (MicroPython and the PyBoard is one example: http://micropython.org).

This example walks through the reader_writer.py example in examples/serial_demos. This example assumes you have some Arduino experience. If you don't, I would look up guides on getting started. Get to the point where you can run basic examples. Read up on the documentation for Serial: https://www.arduino.cc/en/Serial/Read and related pages.

### What does atlasbuggy for microcontrollers?
In short, atlasbuggy makes working with low level hardware easy and manageable. It creates a bridge high level software to low level devices (ex. sensors, motors, LEDs).

The general set up is an Arduino is hooked up to a unix computer (raspberry pi, ubuntu, or macOS machine) via USB or some other serial cable. The Arduino is serving as the mediator between low level sensors and actuators. Unless you have a special device, most personal computers can't directly interface with motors or sensors that you buy off Adafruit or Pololu. Nor would you need them to. The Arduino here isn't the main control unit but the glue between the PC and the sensors and motors.

### How do microcontrollers and PCs communicate?
Most computers at the time of writing have USB ports. Almost all Arduinos use this interface for loading programs and printing debug messages. We'll be using this same interface to transfer data. Serial.print isn't like a print statement in python. This function sends bytes over the USB wire to the serial monitor on your PC. Bytes can go the other way too (e.g. Serial.read).

Python has a great module called pyserial that allows Python programs to read and write data to and from serial devices. Atlasbuggy takes advantage of pyserial's functionality.

We'll only be atlasbuggy libraries to implement these examples. If you want to see how to use pyserial without atlasbuggy, check out this great example: https://www.instructables.com/id/Interface-Python-and-Arduino-with-pySerial/

This example uses the standard Arduino IDE, but platformio is encouraged for more advanced users comfortable with command line tools. Examples using both platforms are provided. Be sure to download this repository: https://github.com/Atlasbuggy/AtlasbuggyLowLevel

The low level libraries aren't included with atlasbuggy because this package doesn't care where the data comes from so long the device abides some loose protocols which we will discuss.

### Let's get started already!!
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

### Implementing the Arduino code
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

### Filling in the code blocks

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

Since that's the only thing I can guarentee you have on your Arduino, that's all I can do for this example unfortunately. I encourage you to get creative here and try adding some servos or sensors to this sketch. Take advantage of atlasbuggy's start and stop events for initializating and deinitializing elements and the isPaused method.

Before writing any python code, I suggest booting up Arduino's built-in serial monitor and testing your code out. The characters sent here are the same ones we'll be telling python to send.

Check the bottom right corner of the window. Make sure you see "Newlines" and "115200 baud." This ensures the correct baud rate and that we're sending \n characters every time we hit enter. All you really need to send is ```start\n```, but the sequence of commands sent are, ```whoareyou\n```, ```init?\n```, ```start\n```, program runs and data is transferred, ```stop\n```. I'll go over what all of these mean when we implement the python code. When you type ```start```, the Arduino is now ready to receive commands. 

If you wrote the example exactly as I wrote it, you should just see the current time since the Arduino started in milliseconds flooding your screen. Type ```stop``` to pause the Arduino.

While the Arduino is unpaused, try typing ```toggle```. You should see your Arduino's LED change state. Hooray!! You have the start of your own robot. Now let's do in python.

### Implementing the Python code



## Naboris

## Naboris simulator

## LMS200 LIDAR

## LMS200 LIDAR simulator

## RoboQuasar