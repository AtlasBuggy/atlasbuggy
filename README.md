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

# Background <a name="background"></a>
## Why does this project exist? <a name="why"></a>

Developing robotic systems is difficult. Atlasbuggy is an attempt to make robotics software development manageable and accessible.<br/><br/>
ROS (http://www.ros.org) is the most well known attempt at solving this problem. So if ROS exists, why does this project exist? When I dove into ROS, there were many aspects of the user experience I wasn't happy with. Managing multiple terminal windows and multiple files and directories over command line wasn't a fun experience for me. Python is currently my strongest language, so I decided to start from scratch and build a framework in python that I would enjoy working with.<br/><br/>

Initially, I built a framework for one robot. Specifically this robot (her name is RoboQuasar):<br/>[insert image]<br/>
Overtime as I added more and more features, I realized this code base could be applied to any robot with some work. After adapting the same code to another robot named Naboris (https://github.com/AtlasBuggy/Naboris) it was clear this code was viable as a development platform.

## How will we fulfill this purpose? <a name="how"></a>

By creating a pythonic collection of code that lets vastly different pieces of software play nice together independent of hardware platform.<br/><br/>
This should sound familiar to ROS. The only difference is the implementation and a few key design decisions.

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
Here's a collection of examples on how to use this repository effectively. I will be walking through code I've written on a high level. If you want to drive into the code, feel free. I'm doing my best to keep my comments up to date.

## Video player

## Simple Arduino reader and writer

## Naboris

## Naboris simulator

## LMS200 LIDAR

## LMS200 LIDAR simulator

## RoboQuasar