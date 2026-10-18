# Coreless-64 physical power detection and auto-start hardware

## Status

**Required; physical implementation and validation pending.** The Python reference machine and virtual motherboard do not sense real voltage. This document defines the hardware boundary that must be implemented before Coreless can claim physical power-triggered startup.

## Signals and responsibilities

Use two distinct inputs to the startup controller:

- `POWER_PRESENT`: an electrically safe, appropriately isolated indication that the external input supply is connected and above its specified detection threshold.
- `POWER_GOOD`: a power-supervisor indication that every required low-voltage rail is within tolerance and has remained stable for its specified qualification interval.

`POWER_PRESENT` alone must never release reset or start the CPU. Startup is permitted only after `POWER_GOOD` is asserted and the detector/controller has completed debounce and sequencing. The detector must deassert power-good promptly when a monitored rail falls outside tolerance.

## Reference hardware architecture

1. **Input-supply presence detector:** use a purpose-built power monitor or comparator interface rated for the actual input voltage and transients. If the input is hazardous or mains-derived, use a certified isolated sensing stage; never connect mains or an unqualified divider directly to GPIO or low-voltage logic.
2. **Rail supervisor:** use a voltage supervisor / power-good IC matched to each required rail and its tolerance. For multiple rails, use a sequencer or combine supervisor outputs so every mandatory rail is valid before startup.
3. **Reset gate:** route the supervisor's valid output to the hardware reset/power-enable controller. Hold reset asserted during absent, unstable, brownout, or invalid power. Use the polarity and pull state required by the selected components.
4. **Startup controller:** after power-good is continuously valid for the selected qualification interval, emit one debounced `POWER_ON` event to the Coreless host/boot controller. Do not repeatedly reboot while power remains stable.
5. **Power-loss path:** on power-good deassertion, immediately inhibit new work and assert reset; where hold-up energy and hardware permit, signal orderly shutdown early enough to flush state. Never promise a graceful save after an abrupt loss without measured hold-up time and tested power-fail handling.
6. **Host interface:** expose power-present, power-good, reset, and fault state through defined electrical levels and documented connector pins. The digital Coreless identity/discovery protocol runs only after its host interface is powered and electrically ready.

## Required design inputs before choosing parts or resistor values

- External input supply type and nominal/minimum/maximum voltage.
- Every low-voltage rail, nominal voltage, tolerance, and startup order.
- Maximum input transient, reverse-polarity, and brownout conditions.
- Required detection threshold, assertion/deassertion delays, and reset polarity.
- Whether any input can be mains-referenced; required isolation class and safety certification.
- Available controller/host pins and electrical standards (for example, 3.3 V logic); never assume a GPIO is 5 V tolerant.
- Required shutdown behavior and measured energy/time available after a power-fail warning.

Do not select a divider ratio, pull-up, threshold, or specific component until these parameters are known. Any chosen component must be checked against its datasheet, input common-mode range, absolute maximum ratings, tolerance, temperature range, and fault behavior.

## Acceptance tests

- No power, undervoltage, brownout, or rail sequencing fault keeps reset asserted and prevents automatic boot.
- Power presence without all required rails valid does not start the machine.
- Valid, stable rails produce exactly one startup event and release reset in the specified order.
- Threshold hysteresis and qualification/debounce prevent chatter and repeated boot attempts around the threshold.
- Loss of any required rail deasserts `POWER_GOOD` and asserts reset within the supervisor's documented limits.
- Power-fail warning, hold-up interval, and persistent-state flush are measured under representative load; abrupt removal is tested separately.
- Input faults (open wire, short, reversed input, transient, supervisor disconnected) fail to a safe no-boot state.
- Test both the circuit on a bench and the integrated host/boot path. Software-only simulated tests are supplementary and cannot pass the physical validation gate.

## Safety boundary

This is a low-voltage architecture description, not a finished schematic or build authorization. Do not probe or wire mains directly. If the system is powered from mains, use a certified isolated AC/DC supply and an appropriately rated isolated detection circuit designed and reviewed for that application. Physical construction and measurements must be performed with suitable equipment and electrical-safety practices.

## Integration with Coreless software

The physical controller should report a normalized, timestamped power event to the host adapter. The host adapter must validate the event, confirm the selected persistent machine identity and boot target, then invoke the single canonical initialize → boot/resume → desktop attach lifecycle. The physical signal is an input to that lifecycle, not a second boot implementation.

Required event/state model: `ABSENT → PRESENT_UNQUALIFIED → POWER_GOOD → BOOTING → RUNNING`, with fault/power-loss transitions to `RESET_HELD` and safe recovery. Record fault cause and transition times for diagnostics. Physical power state and software machine state must be reported separately.

