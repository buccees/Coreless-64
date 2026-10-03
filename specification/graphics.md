# Coreless Graphics and Display

**Version:** 0.1  
**Status:** Draft

## Objective

Coreless has a native graphical subsystem. It is not inherently headless.

## Display

The architecture will support:

- one or more displays
- arbitrary supported resolutions
- framebuffer surfaces
- multiple pixel formats
- cursor
- display events
- input events

## GPU

The GPU is an independent Coreless resource.

Initial capabilities include 2D acceleration and display composition.

The architecture is designed to grow toward 3D rendering and general-purpose GPU compute.

## Remote display

A host can transport Coreless display output to a physical screen.

The host is not required to perform the Coreless rendering.

Input travels in the reverse direction.

## Future

The display architecture will eventually define command buffers, synchronization, memory sharing, acceleration capabilities, and GPU virtualization.

## Hardware-Independent Graphics Architecture

Graphics is a first-class Coreless subsystem. The architectural graphics interface defines display surfaces, command submission, synchronization, memory access, and input/output events without requiring a particular GPU architecture.

A conforming implementation may realize graphics using a conventional GPU, integrated accelerator, FPGA fabric, dedicated display engine, heterogeneous compute resources, or another implementation.

The software interface depends on architectural capabilities rather than vendor-specific hardware. Physical rendering pipelines, shader organization, cache structure, display controller design, and memory layout are implementation-defined.

Remote display and input are architectural services at the Coreless environment level and do not require the host to execute Coreless graphics workloads.


## Display and Graphics Execution Model

Coreless graphics has three architectural layers:

1. display resources and scanout;
2. graphics/compute command execution;
3. window/input services exposed to the Coreless operating environment.

The architecture does not require a specific shader ISA. Graphics acceleration is capability-discoverable, allowing implementations to use native GPUs, vector/matrix resources, dedicated render hardware, or heterogeneous combinations.

Display surfaces are memory objects with defined ownership and synchronization. Scanout cannot observe a surface before required producer synchronization has completed.

Input events are delivered through the Coreless device/event model. Remote display/input may transport these architectural events without changing the Coreless graphics model.

## Plug-and-play display transport

Display output is a Coreless architectural resource. A host may transport the resulting display stream to a physical monitor after Coreless identity and display capabilities have been negotiated. Input events travel through the same host-interface boundary in the reverse direction.

The host is a transport endpoint, not the Coreless graphics executor.
