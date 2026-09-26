# Coreless Scaling Model

**Version:** 0.1  
**Status:** Draft

## Principle

Coreless-64 is one architecture that can instantiate machines of very different sizes.

Drive capacity is a major persistent-capacity input, while execution hardware determines computational throughput.

## Scalable resources

A Coreless machine may scale:

- CPU count
- CPU execution width
- memory capacity
- vector capacity
- AI/matrix capacity
- GPU capability
- storage capacity
- network interfaces
- guest-machine capacity

## Machine profiles

The architecture will not define separate ISAs for small, medium, and large machines.

Instead, firmware publishes a machine capability description.

## Resource discovery

Software discovers resources at boot and can query dynamic resources during operation.

## Dynamic changes

Future versions will support adding or removing resources while preserving software-visible architectural compatibility.

## Storage scaling

More drive capacity allows:

- larger OS/application environments
- more AI models
- more guest machines
- larger persistent memory images where supported
- more checkpoints
- more datasets

Storage capacity does not automatically imply more CPU throughput; native execution capacity must scale as well.

## Distributed scaling

Future Coreless systems may combine multiple Coreless devices into a single logical machine or cluster.
